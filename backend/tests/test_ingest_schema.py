"""Tests for SQLite schema creation and FTS5 virtual table structure."""

import sqlite3
import pytest

from backend.scripts.ingest.schema import init_sqlite_schema, SCHEMA_SQL


@pytest.fixture
def fresh_conn():
    conn = sqlite3.connect(":memory:")
    yield conn
    conn.close()


def test_schema_creates_entities_table(fresh_conn):
    init_sqlite_schema(fresh_conn)
    rows = fresh_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='geographic_entities'"
    ).fetchall()
    assert len(rows) == 1, "geographic_entities table must be created"


def test_schema_creates_aliases_table(fresh_conn):
    init_sqlite_schema(fresh_conn)
    rows = fresh_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='entity_aliases'"
    ).fetchall()
    assert len(rows) == 1, "entity_aliases table must be created"


def test_schema_creates_geometries_table(fresh_conn):
    init_sqlite_schema(fresh_conn)
    rows = fresh_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='entity_geometries'"
    ).fetchall()
    assert len(rows) == 1, "entity_geometries table must be created"


def test_schema_creates_fts5_table(fresh_conn):
    init_sqlite_schema(fresh_conn)
    # FTS5 tables appear as type='table' or 'shadow' depending on SQLite version
    rows = fresh_conn.execute(
        "SELECT name FROM sqlite_master WHERE name='entities_fts'"
    ).fetchall()
    assert len(rows) >= 1, "entities_fts FTS5 virtual table must be created"


def test_fts5_has_entity_id_unindexed_column(fresh_conn):
    """FTS5 must retain entity_id as an unindexed column for result resolution."""
    init_sqlite_schema(fresh_conn)
    fresh_conn.execute(
        "INSERT INTO entities_fts (name, normalized_name, aliases, entity_id, "
        "entity_category, state_id, district_id) VALUES (?,?,?,?,?,?,?)",
        ("Kolkata", "kolkata", "Calcutta", "some-uuid", "SETTLEMENT", "STATE_WB", "DIST_WB_KOLKATA"),
    )
    fresh_conn.commit()
    row = fresh_conn.execute(
        "SELECT entity_id FROM entities_fts WHERE entities_fts MATCH 'kolkata'"
    ).fetchone()
    assert row is not None, "FTS5 query must return a row"
    assert row[0] == "some-uuid", "entity_id must be retrievable from FTS5 result"


def test_schema_is_idempotent(fresh_conn):
    """Calling init_sqlite_schema twice must not raise or duplicate tables."""
    init_sqlite_schema(fresh_conn)
    init_sqlite_schema(fresh_conn)  # Should be a no-op due to IF NOT EXISTS
    rows = fresh_conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='geographic_entities'"
    ).fetchone()
    assert rows[0] == 1


def test_entities_table_has_required_columns(fresh_conn):
    init_sqlite_schema(fresh_conn)
    info = fresh_conn.execute("PRAGMA table_info(geographic_entities)").fetchall()
    col_names = {row[1] for row in info}
    required = {
        "id", "name", "normalized_name", "entity_category", "entity_type",
        "admin_level", "parent_id", "state_id", "district_id", "subdistrict_id",
        "country_code", "latitude", "longitude", "source", "source_id",
        "source_version", "source_release_date", "retrieved_at",
        "valid_from", "valid_to", "confidence", "is_active",
    }
    missing = required - col_names
    assert not missing, f"Missing columns in geographic_entities: {missing}"


def test_aliases_table_has_required_columns(fresh_conn):
    init_sqlite_schema(fresh_conn)
    info = fresh_conn.execute("PRAGMA table_info(entity_aliases)").fetchall()
    col_names = {row[1] for row in info}
    required = {"id", "entity_id", "alias", "normalized_alias", "alias_type", "language", "confidence", "source"}
    missing = required - col_names
    assert not missing, f"Missing columns in entity_aliases: {missing}"
