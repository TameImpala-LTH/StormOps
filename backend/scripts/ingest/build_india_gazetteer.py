"""Nationwide India Gazetteer — deterministic ingestion pipeline.

Usage
-----
    # Dry-run: validate the full pipeline without generating the final DB
    python -m backend.scripts.ingest.build_india_gazetteer --dry-run \\
        --lgd   path/to/lgd_records.json \\
        --census path/to/census_records.json \\
        --osm   path/to/osm_features.json \\
        --curated path/to/curated_localities.json   # optional; defaults to repo path

    # Production run (creates backend/data/india_gazetteer.db)
    python -m backend.scripts.ingest.build_india_gazetteer \\
        --lgd   path/to/lgd_records.json \\
        --census path/to/census_records.json \\
        --osm   path/to/osm_features.json

Determinism Guarantee
----------------------
Given identical input files, this script always produces an identical SQLite
database.  Determinism is achieved by:

  1. Processing source adapters in a fixed order: LGD → Census → OSM → Curated.
  2. Within each adapter, records are sorted by (source, source_id) before any
     further processing.
  3. All entity UUIDs are generated with uuid5(NAMESPACE_DNS, f"{source}:{source_id}")
     — no random UUIDs are used.
  4. Deduplication and alias lists are processed in the same sorted order.
  5. SQLite rows are inserted in (source, source_id) sorted order.

Dry-Run Lifecycle
-----------------
  1. Build a temporary SQLite database in a tempfile.
  2. Validate schema structure.
  3. Run FTS5 sanity checks.
  4. Run a second ingestion pass and verify identical entity count (idempotence
     check within a single dry-run invocation).
  5. Print metrics summary.
  6. Delete the temporary database before exiting.
  7. Exit 0 on success, 1 on any validation failure.

Phase 22B Constraint
---------------------
The final `backend/data/india_gazetteer.db` is NOT generated during Phase 22B.
The production write path is guarded by the --production flag (a deliberate
two-step safeguard).
"""

import argparse
import hashlib
import json
import logging
import os
import sqlite3
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Path setup: allow running as `python -m backend.scripts.ingest.build_...`
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[3]  # → StormOps/
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.scripts.ingest.aliases import generate_deterministic_aliases
from backend.scripts.ingest.deduplicate import deduplicate_entities
from backend.scripts.ingest.hierarchy import HierarchyGraph
from backend.scripts.ingest.normalize import normalize_name
from backend.scripts.ingest.schema import (
    EntityAlias,
    EntityGeometry,
    GeographicEntity,
    init_sqlite_schema,
)
from backend.scripts.ingest.sources.census import CensusAdapter
from backend.scripts.ingest.sources.curated import CuratedAdapter
from backend.scripts.ingest.sources.lgd import LGDAdapter
from backend.scripts.ingest.sources.osm import OSMAdapter

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Fixed adapter execution order (deterministic)
_ADAPTER_ORDER = ["LGD", "CENSUS_2011", "OSM", "CURATED_URBAN"]

_FINAL_DB_PATH = _REPO_ROOT / "backend" / "data" / "india_gazetteer.db"


# ---------------------------------------------------------------------------
# Deterministic UUID5 helpers
# ---------------------------------------------------------------------------

def _stable_entity_id(source: str, source_id: str) -> str:
    """Generate a deterministic UUID5 for an entity from its source identity."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{source}:{source_id}"))


def _stable_alias_id(entity_id: str, alias_norm: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"alias:{entity_id}:{alias_norm}"))


def _stable_geometry_id(entity_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"geom:{entity_id}"))


def _assign_stable_ids(
    entities: List[GeographicEntity],
    aliases: List[EntityAlias],
    geometries: List[EntityGeometry],
) -> None:
    """Replace any auto-generated UUIDs with deterministic UUID5 values."""
    id_remap: Dict[str, str] = {}

    for e in entities:
        stable_id = _stable_entity_id(e.source, e.source_id or e.normalized_name)
        id_remap[e.id] = stable_id
        e.id = stable_id

    # Remap foreign keys
    for a in aliases:
        a.entity_id = id_remap.get(a.entity_id, a.entity_id)
        a.id = _stable_alias_id(a.entity_id, a.normalized_alias)

    for g in geometries:
        g.entity_id = id_remap.get(g.entity_id, g.entity_id)
        g.id = _stable_geometry_id(g.entity_id)

    # Also remap parent_id references within entities
    for e in entities:
        if e.parent_id and e.parent_id in id_remap:
            e.parent_id = id_remap[e.parent_id]
        if e.state_id and e.state_id in id_remap:
            e.state_id = id_remap[e.state_id]
        if e.district_id and e.district_id in id_remap:
            e.district_id = id_remap[e.district_id]
        if e.subdistrict_id and e.subdistrict_id in id_remap:
            e.subdistrict_id = id_remap[e.subdistrict_id]


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

def _load_json(path: Optional[str]) -> Any:
    if not path:
        return []
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def run_pipeline(
    lgd_path: Optional[str],
    census_path: Optional[str],
    osm_path: Optional[str],
    curated_path: Optional[str] = None,
) -> Tuple[List[GeographicEntity], List[EntityAlias], List[EntityGeometry], List[str], List[str]]:
    """Execute the full ingestion pipeline and return normalized, deduplicated data.

    Returns:
        (entities, aliases, geometries, hard_errors, warnings)
    """
    all_entities: List[GeographicEntity] = []
    all_aliases: List[EntityAlias] = []
    all_geometries: List[EntityGeometry] = []

    # --- Stage 1: Parse each source adapter in fixed order ---
    adapter_map = {
        "LGD": (LGDAdapter(), _load_json(lgd_path)),
        "CENSUS_2011": (CensusAdapter(), _load_json(census_path)),
        "OSM": (OSMAdapter(), _load_json(osm_path)),
        "CURATED_URBAN": (
            CuratedAdapter(curated_path) if curated_path else CuratedAdapter(),
            None,  # CuratedAdapter self-loads when data_or_path is None
        ),
    }

    for source_name in _ADAPTER_ORDER:
        adapter, data = adapter_map[source_name]
        entities, aliases, geometries = adapter.parse(data)
        logger.info(
            "Parsed %-14s → %d entities, %d aliases, %d geometries",
            source_name,
            len(entities),
            len(aliases),
            len(geometries),
        )
        all_entities.extend(entities)
        all_aliases.extend(aliases)
        all_geometries.extend(geometries)

    # --- Stage 2: Assign deterministic UUID5 IDs ---
    _assign_stable_ids(all_entities, all_aliases, all_geometries)

    # --- Stage 3: Generate deterministic historical/colloquial aliases ---
    for entity in all_entities:
        gen_aliases = generate_deterministic_aliases(entity)
        # Assign stable IDs to generated aliases
        for a in gen_aliases:
            a.entity_id = entity.id
            a.id = _stable_alias_id(a.entity_id, a.normalized_alias)
        all_aliases.extend(gen_aliases)

    # --- Stage 4: Deduplication (preserves homonyms) ---
    logger.info("Deduplicating %d entities …", len(all_entities))
    deduped_entities, dedup_log = deduplicate_entities(all_entities)
    logger.info("  → %d entities after deduplication (%d merges/homonyms logged)",
                len(deduped_entities), len(dedup_log))
    for line in dedup_log:
        logger.debug("  dedup: %s", line)

    # --- Stage 5: Hierarchy graph construction and ancestor resolution ---
    graph = HierarchyGraph()
    for e in deduped_entities:
        graph.add_entity(e)

    # Apply LGD crosswalks for Census entities that have one
    for e in deduped_entities:
        if e.source == "CENSUS_2011" and e.metadata.get("lgd_crosswalk_parent_id"):
            lgd_code = e.metadata["lgd_crosswalk_parent_id"]
            lgd_parent = graph.find_by_source_id("LGD", str(lgd_code))
            if lgd_parent:
                graph.apply_lgd_crosswalk(e, lgd_parent.id)

    hard_errors, warnings = graph.resolve_ancestors()

    if hard_errors:
        logger.warning("Hierarchy hard errors (%d):", len(hard_errors))
        for err in hard_errors:
            logger.warning("  %s", err)
    if warnings:
        logger.info("Hierarchy warnings (%d):", len(warnings))
        for w in warnings:
            logger.info("  %s", w)

    final_entities = graph.get_all_entities()

    # Null out parent_id on entities with INVALID_PARENT hard errors.
    # This ensures the SQLite database never contains dangling UUID references:
    # the FK constraint on parent_id is meaningful and enforced at write time.
    # The hard_errors list is still returned to the caller for reporting.
    invalid_parent_entity_ids: set = set()
    for err_msg in hard_errors:
        if err_msg.startswith("INVALID_PARENT:"):
            # Extract the entity id from: "INVALID_PARENT: entity '...' (id=UUID, ...)"
            try:
                id_part = err_msg.split("(id=", 1)[1].split(",", 1)[0].strip()
                invalid_parent_entity_ids.add(id_part)
            except IndexError:
                pass
    for e in deduped_entities:
        if e.id in invalid_parent_entity_ids:
            e.parent_id = None  # Cleared: cannot reference a non-existent parent in the DB

    # Deduplicate aliases (drop exact duplicates on entity_id + normalized_alias)
    seen_alias_keys = set()
    final_aliases: List[EntityAlias] = []
    for a in sorted(all_aliases, key=lambda x: (x.entity_id, x.normalized_alias, x.source)):
        key = (a.entity_id, a.normalized_alias)
        if key not in seen_alias_keys:
            seen_alias_keys.add(key)
            final_aliases.append(a)

    # Keep only geometries whose entity survived deduplication
    surviving_ids = {e.id for e in final_entities}
    final_geometries = [g for g in all_geometries if g.entity_id in surviving_ids]

    return final_entities, final_aliases, final_geometries, hard_errors, warnings


# ---------------------------------------------------------------------------
# SQLite writer
# ---------------------------------------------------------------------------

def write_to_sqlite(
    conn: sqlite3.Connection,
    entities: List[GeographicEntity],
    aliases: List[EntityAlias],
    geometries: List[EntityGeometry],
) -> None:
    """Insert all entities, aliases, geometries, and FTS5 rows into the open connection.

    All parent_id values must resolve to existing geographic_entities rows before
    this function is called.  run_pipeline() guarantees this by calling
    HierarchyGraph.resolve_ancestors() and then nulling out any parent_id that
    generated an INVALID_PARENT hard error.  The SQLite FK constraint on parent_id
    is therefore active and enforced — it is NOT disabled here.
    """
    # Insert in (source, source_id) sorted order for determinism
    sorted_entities = sorted(entities, key=lambda e: (e.source or "", e.source_id or "", e.id))

    for e in sorted_entities:
        conn.execute(
            """
            INSERT OR REPLACE INTO geographic_entities
            (id, name, normalized_name, entity_category, entity_type, specific_subtype,
             admin_level, parent_id, state_id, district_id, subdistrict_id, country_code,
             latitude, longitude, source, source_id, source_version, source_release_date,
             retrieved_at, valid_from, valid_to, confidence, is_active)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                e.id, e.name, e.normalized_name, e.entity_category.value,
                e.entity_type.value, e.specific_subtype, e.admin_level,
                e.parent_id, e.state_id, e.district_id, e.subdistrict_id,
                e.country_code, e.latitude, e.longitude,
                e.source, e.source_id, e.source_version, e.source_release_date,
                e.retrieved_at, e.valid_from, e.valid_to,
                e.confidence, 1 if e.is_active else 0,
            ),
        )

    sorted_aliases = sorted(
        aliases,
        key=lambda a: (a.entity_id, a.normalized_alias, a.source),
    )
    for a in sorted_aliases:
        conn.execute(
            """
            INSERT OR REPLACE INTO entity_aliases
            (id, entity_id, alias, normalized_alias, alias_type, language, confidence, source)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                a.id, a.entity_id, a.alias, a.normalized_alias,
                a.alias_type.value, a.language, a.confidence, a.source,
            ),
        )

    sorted_geoms = sorted(geometries, key=lambda g: (g.entity_id, g.source))
    for g in sorted_geoms:
        conn.execute(
            """
            INSERT OR REPLACE INTO entity_geometries
            (id, entity_id, rep_latitude, rep_longitude, rep_strategy, bounding_box,
             source, retrieved_at)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                g.id, g.entity_id, g.rep_latitude, g.rep_longitude,
                g.rep_strategy.value, g.bounding_box, g.source, g.retrieved_at,
            ),
        )

    # Populate FTS5 — one row per entity, aliases concatenated
    alias_map: Dict[str, List[str]] = {}
    for a in sorted_aliases:
        alias_map.setdefault(a.entity_id, []).append(a.alias)

    for e in sorted_entities:
        aliases_text = " | ".join(alias_map.get(e.id, []))
        conn.execute(
            """
            INSERT INTO entities_fts (name, normalized_name, aliases, entity_id,
                                      entity_category, state_id, district_id)
            VALUES (?,?,?,?,?,?,?)
            """,
            (
                e.name, e.normalized_name, aliases_text,
                e.id, e.entity_category.value, e.state_id, e.district_id,
            ),
        )

    conn.commit()


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_schema(conn: sqlite3.Connection) -> List[str]:
    """Verify that all required tables and the FTS5 index exist."""
    errors = []
    required_tables = [
        "geographic_entities", "entity_aliases", "entity_geometries", "entities_fts"
    ]
    for tbl in required_tables:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','shadow') AND name=?", (tbl,)
        ).fetchone()
        if not row:
            errors.append(f"Missing table: {tbl}")
    return errors


def validate_fts(conn: sqlite3.Connection) -> List[str]:
    """Run a basic FTS5 sanity check."""
    errors = []
    try:
        rows = conn.execute(
            "SELECT entity_id FROM entities_fts WHERE entities_fts MATCH 'kolkata' LIMIT 5"
        ).fetchall()
        # Not an error if 0 results — depends on fixture data
        logger.info("FTS5 sanity check: query 'kolkata' → %d result(s)", len(rows))
    except Exception as exc:
        errors.append(f"FTS5 query failed: {exc}")
    return errors


def db_hash(db_path: str) -> str:
    """SHA-256 hash of the SQLite file contents."""
    h = hashlib.sha256()
    with open(db_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the Nationwide India Gazetteer SQLite database."
    )
    parser.add_argument("--lgd",     metavar="PATH", help="LGD source JSON path")
    parser.add_argument("--census",  metavar="PATH", help="Census 2011 source JSON path")
    parser.add_argument("--osm",     metavar="PATH", help="OSM features JSON path")
    parser.add_argument("--curated", metavar="PATH", help="Curated locality JSON path (optional)")
    parser.add_argument(
        "--dry-run", action="store_true",
        help=(
            "Validate the pipeline using a temporary DB; "
            "delete it after validation. Do NOT write the final DB."
        ),
    )
    parser.add_argument(
        "--production", action="store_true",
        help="Write the final india_gazetteer.db (Phase 22B: NOT enabled).",
    )
    args = parser.parse_args(argv)

    if args.production:
        logger.error(
            "Production write is disabled in Phase 22B. "
            "Remove this guard when the ingestion pipeline is fully validated."
        )
        return 1

    if not args.dry_run:
        logger.error("Either --dry-run or --production must be specified.")
        return 1

    logger.info("=== Phase 22B India Gazetteer — DRY RUN ===")

    # Run pipeline
    entities, aliases, geometries, hard_errors, warnings = run_pipeline(
        lgd_path=args.lgd,
        census_path=args.census,
        osm_path=args.osm,
        curated_path=args.curated,
    )

    # Write to temp DB
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".db", prefix="india_gazetteer_tmp_")
    os.close(tmp_fd)

    try:
        conn = sqlite3.connect(tmp_path)
        # Use DELETE journal mode in dry-run: WAL creates .db-wal/.db-shm side-files
        # that Windows locks exclusively, preventing cleanup while the process exits.
        conn.execute("PRAGMA journal_mode=DELETE")
        init_sqlite_schema(conn)
        write_to_sqlite(conn, entities, aliases, geometries)
        conn.close()

        # Schema validation
        conn = sqlite3.connect(tmp_path)
        schema_errors = validate_schema(conn)
        fts_errors = validate_fts(conn)

        # Idempotence check: re-run and compare counts
        entities2, aliases2, geometries2, _, _ = run_pipeline(
            lgd_path=args.lgd,
            census_path=args.census,
            osm_path=args.osm,
            curated_path=args.curated,
        )
        idempotence_ok = (
            len(entities2) == len(entities)
            and len(aliases2) == len(aliases)
            and len(geometries2) == len(geometries)
        )
        conn.close()

        # Metrics
        logger.info("")
        logger.info("=== DRY RUN METRICS ===")
        logger.info("  Entities  : %d", len(entities))
        logger.info("  Aliases   : %d", len(aliases))
        logger.info("  Geometries: %d", len(geometries))
        logger.info("  Hierarchy hard errors : %d", len(hard_errors))
        logger.info("  Hierarchy warnings    : %d", len(warnings))
        logger.info("  Schema errors : %d", len(schema_errors))
        logger.info("  FTS errors    : %d", len(fts_errors))
        logger.info("  Idempotence   : %s", "PASS" if idempotence_ok else "FAIL")

        all_errors = schema_errors + fts_errors
        if not idempotence_ok:
            all_errors.append("Idempotence check failed: second run produced different counts")

        if all_errors:
            logger.error("Validation FAILED:")
            for err in all_errors:
                logger.error("  %s", err)
            return 1

        logger.info("")
        logger.info("Dry-run validation PASSED.")
        return 0

    finally:
        # Remove the temp DB and any SQLite WAL/SHM side-files (important on Windows)
        for suffix in ("", "-wal", "-shm"):
            target = tmp_path + suffix
            if os.path.exists(target):
                try:
                    os.remove(target)
                    logger.info("Temporary file removed: %s", target)
                except OSError as exc:
                    logger.warning("Could not remove temporary file %s: %s", target, exc)


if __name__ == "__main__":
    sys.exit(main())
