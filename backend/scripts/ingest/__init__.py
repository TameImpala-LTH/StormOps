"""Nationwide India Gazetteer ingestion package.

This package provides the deterministic ingestion pipeline for building
backend/data/india_gazetteer.db from LGD, Census 2011, OSM, and curated sources.

It is intentionally isolated from the runtime application code and must not
be imported by any backend service module.
"""
