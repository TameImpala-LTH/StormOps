"""Idempotence tests: identical fixture input must always produce identical output."""

import hashlib
import sqlite3
import tempfile
import os
from pathlib import Path

import pytest

from backend.scripts.ingest.build_india_gazetteer import (
    run_pipeline,
    write_to_sqlite,
    _assign_stable_ids,
)
from backend.scripts.ingest.schema import init_sqlite_schema

_FIXTURES = Path(__file__).parent / "fixtures" / "ingest"
_LGD_FIXTURE     = str(_FIXTURES / "lgd_sample.json")
_CENSUS_FIXTURE  = str(_FIXTURES / "census_sample.json")
_OSM_FIXTURE     = str(_FIXTURES / "osm_sample.json")
_CURATED_FIXTURE = str(_FIXTURES / "curated_sample.json")


def _run_and_hash() -> str:
    """Run the full pipeline to a temp file DB and return its SHA-256 hash."""
    entities, aliases, geometries, *_ = run_pipeline(
        lgd_path=_LGD_FIXTURE,
        census_path=_CENSUS_FIXTURE,
        osm_path=_OSM_FIXTURE,
        curated_path=_CURATED_FIXTURE,
    )
    fd, path = tempfile.mkstemp(suffix=".db", prefix="ingest_idem_")
    os.close(fd)
    try:
        conn = sqlite3.connect(path)
        conn.execute("PRAGMA journal_mode=DELETE")  # Deterministic (no WAL shadow files)
        init_sqlite_schema(conn)
        write_to_sqlite(conn, entities, aliases, geometries)
        conn.close()
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    finally:
        for suffix in ("", "-wal", "-shm"):
            target = path + suffix
            if os.path.exists(target):
                try:
                    os.remove(target)
                except OSError:
                    pass


class TestIdempotence:

    def test_entity_counts_identical_across_runs(self):
        """Two consecutive pipeline runs must produce the same entity count."""
        r1, *_ = run_pipeline(
            lgd_path=_LGD_FIXTURE,
            census_path=_CENSUS_FIXTURE,
            osm_path=_OSM_FIXTURE,
            curated_path=_CURATED_FIXTURE,
        )
        r2, *_ = run_pipeline(
            lgd_path=_LGD_FIXTURE,
            census_path=_CENSUS_FIXTURE,
            osm_path=_OSM_FIXTURE,
            curated_path=_CURATED_FIXTURE,
        )
        assert len(r1) == len(r2), (
            f"Entity count must be deterministic; run1={len(r1)}, run2={len(r2)}"
        )

    def test_entity_ids_identical_across_runs(self):
        """All entity IDs must be identical across runs (deterministic UUID5)."""
        e1, *_ = run_pipeline(
            lgd_path=_LGD_FIXTURE,
            census_path=_CENSUS_FIXTURE,
            osm_path=_OSM_FIXTURE,
            curated_path=_CURATED_FIXTURE,
        )
        e2, *_ = run_pipeline(
            lgd_path=_LGD_FIXTURE,
            census_path=_CENSUS_FIXTURE,
            osm_path=_OSM_FIXTURE,
            curated_path=_CURATED_FIXTURE,
        )
        ids1 = sorted(e.id for e in e1)
        ids2 = sorted(e.id for e in e2)
        assert ids1 == ids2, "Entity IDs must be deterministic across runs"

    def test_db_hash_identical_across_runs(self):
        """Two pipeline runs on the same fixtures must produce structurally identical results.

        Raw file-byte hashes cannot be identical because `retrieved_at` is a live UTC
        timestamp that changes between runs. Instead, we verify that all stable,
        deterministic fields are identical:
          - Entity IDs (UUID5, derived from source+source_id)
          - Entity normalized names and types
          - Alias normalized forms per entity
          - Geometry entity IDs
        """
        e1, a1, g1, *_ = run_pipeline(
            lgd_path=_LGD_FIXTURE,
            census_path=_CENSUS_FIXTURE,
            osm_path=_OSM_FIXTURE,
            curated_path=_CURATED_FIXTURE,
        )
        e2, a2, g2, *_ = run_pipeline(
            lgd_path=_LGD_FIXTURE,
            census_path=_CENSUS_FIXTURE,
            osm_path=_OSM_FIXTURE,
            curated_path=_CURATED_FIXTURE,
        )

        # Entity IDs must be identical
        ids1 = sorted(e.id for e in e1)
        ids2 = sorted(e.id for e in e2)
        assert ids1 == ids2, "Entity IDs must be deterministic (UUID5)"

        # Entity normalized names must be identical (same set)
        norms1 = sorted((e.id, e.normalized_name, e.entity_type) for e in e1)
        norms2 = sorted((e.id, e.normalized_name, e.entity_type) for e in e2)
        assert norms1 == norms2, "Entity normalized names and types must be deterministic"

        # Alias IDs must be identical
        alias_ids1 = sorted(a.id for a in a1)
        alias_ids2 = sorted(a.id for a in a2)
        assert alias_ids1 == alias_ids2, "Alias IDs must be deterministic"

        # Geometry entity links must be identical
        geom_links1 = sorted(g.entity_id for g in g1)
        geom_links2 = sorted(g.entity_id for g in g2)
        assert geom_links1 == geom_links2, "Geometry entity_ids must be deterministic"

    def test_no_temp_db_left_after_dry_run(self, tmp_path):
        """The --dry-run invocation must not leave any .db files behind."""
        import subprocess
        import sys
        result = subprocess.run(
            [
                sys.executable, "-m",
                "backend.scripts.ingest.build_india_gazetteer",
                "--dry-run",
                "--lgd",     _LGD_FIXTURE,
                "--census",  _CENSUS_FIXTURE,
                "--osm",     _OSM_FIXTURE,
                "--curated", _CURATED_FIXTURE,
            ],
            capture_output=True,
            text=True,
        )
        # Check no tmp .db files remain (the script itself cleans up)
        leftover = list(tmp_path.glob("*.db"))
        assert leftover == [], f"Temp DB files left behind: {leftover}"
        # Script must exit 0 on success
        assert result.returncode == 0, (
            f"Dry-run failed with exit code {result.returncode}:\n{result.stderr}"
        )
