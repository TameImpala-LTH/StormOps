"""Comprehensive unit and integration tests for the Official Environmental Advisory Intelligence backend."""

import asyncio
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.db.base import Base
from app.main import app
from app.models.advisory import Advisory
from app.schemas.advisory import AdvisoryQueryFilter
from app.services.advisory.base import BaseAdvisoryProvider
from app.services.advisory.ingestion import AdvisoryIngestionService
from app.services.advisory.models import NormalizedAdvisory
from app.services.advisory.normalizer import (
    map_hazard_type,
    map_severity,
    parse_datetime,
    sanitize_text,
)
from app.services.advisory.providers.cpcb_provider import CpcbAqiProvider
from app.services.advisory.providers.imd_provider import ImdDistrictProvider
from app.services.advisory.providers.incois_provider import IncoisMarineProvider
from app.services.advisory.providers.sachet_provider import SachetCapProvider
from app.services.advisory.taxonomy import Authority, HazardType, SeverityLevel
from app.services.advisory_service import AdvisoryService


# Setup in-memory SQLite for deterministic test database
@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_client():
    return TestClient(app)


# 1. Normalizer & Taxonomy Tests
def test_sanitize_text():
    assert sanitize_text("<script>alert(1)</script><b>Heavy Rain</b>") == "alert(1) Heavy Rain"
    assert sanitize_text("  Normal  Text  ") == "Normal Text"
    assert sanitize_text(None) == ""


def test_parse_datetime():
    dt = parse_datetime("2026-09-18T10:30:00Z")
    assert dt.year == 2026
    assert dt.tzinfo == timezone.utc

    dt_fallback = parse_datetime("invalid-date")
    assert dt_fallback.year == datetime.now(timezone.utc).year


def test_map_hazard_type():
    assert map_hazard_type("Heavy Rainfall Warning") == HazardType.HEAVY_RAIN.value
    assert map_hazard_type("Extremely Heavy Rain Alert") == HazardType.EXTREME_RAIN.value
    assert map_hazard_type("Thunderstorm with Lightning") == HazardType.THUNDERSTORM.value
    assert map_hazard_type("Severe Heatwave conditions") == HazardType.HEATWAVE.value
    assert map_hazard_type("Cyclonic Storm Michaung") == HazardType.CYCLONE.value
    assert map_hazard_type("High Wave Alert") == HazardType.HIGH_WAVE.value
    assert map_hazard_type("Flash flood warning") == HazardType.FLASH_FLOOD.value
    assert map_hazard_type("Air Quality Index Severe") == HazardType.AIR_QUALITY.value
    assert map_hazard_type("Unknown Event") == HazardType.OTHER.value


def test_map_severity():
    assert map_severity("RED") == SeverityLevel.RED.value
    assert map_severity("Take Action (Warning)") == SeverityLevel.RED.value
    assert map_severity("ORANGE") == SeverityLevel.ORANGE.value
    assert map_severity("Be Prepared (Alert)") == SeverityLevel.ORANGE.value
    assert map_severity("YELLOW") == SeverityLevel.YELLOW.value
    assert map_severity("Watch") == SeverityLevel.YELLOW.value
    assert map_severity("GREEN") == SeverityLevel.GREEN.value
    assert map_severity("No Warning") == SeverityLevel.GREEN.value
    assert map_severity("unspecified") == SeverityLevel.UNKNOWN.value


# 2. Provider Parsing Tests
def test_sachet_cap_provider_parsing():
    sample_cap_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
        <identifier>IN-NDMA-2026-0918-001</identifier>
        <sender>ndma.gov.in</sender>
        <sent>2026-09-18T12:00:00+05:30</sent>
        <status>Actual</status>
        <msgType>Alert</msgType>
        <scope>Public</scope>
        <info>
            <category>Met</category>
            <event>Heavy to Very Heavy Rainfall</event>
            <urgency>Expected</urgency>
            <severity>Severe</severity>
            <certainty>Likely</certainty>
            <headline>ORANGE ALERT: Heavy rainfall expected in coastal districts</headline>
            <description>Widespread heavy to very heavy rain likely over South 24 Parganas.</description>
            <instruction>Avoid going outdoors unless necessary. Fishermen advised not to venture into sea.</instruction>
            <area>
                <areaDesc>South 24 Parganas, West Bengal</areaDesc>
                <circle>22.15,88.50 35.0</circle>
            </area>
        </info>
    </alert>"""

    provider = SachetCapProvider()
    advisories = provider.parse_payload(sample_cap_xml)

    assert len(advisories) == 1
    adv = advisories[0]
    assert adv.source_id == "IN-NDMA-2026-0918-001"
    assert adv.authority == Authority.NDMA.value
    assert adv.hazard_type == HazardType.VERY_HEAVY_RAIN.value
    assert adv.severity == SeverityLevel.ORANGE.value
    assert adv.district == "South 24 Parganas"
    assert adv.state == "West Bengal"
    assert adv.latitude == 22.15
    assert adv.longitude == 88.50
    assert adv.radius_km == 35.0


def test_imd_provider_parsing():
    sample_imd_json = {
        "data": [
            {
                "id": "imd-kolkata-001",
                "district_name": "Kolkata",
                "state_name": "West Bengal",
                "subdivision_name": "Gangetic West Bengal",
                "warning_color": "RED",
                "hazard_type": "Extremely Heavy Rainfall",
                "headline": "RED WARNING: Inundation risk in Kolkata",
                "warning_text": "Extremely heavy rainfall exceeding 210 mm expected within 24 hours.",
                "action_advice": "Stay indoors, avoid waterlogged arterial corridors.",
                "date": "2026-09-18T08:30:00Z",
                "from_date": "2026-09-18T08:30:00Z",
                "to_date": "2026-09-19T08:30:00Z",
            }
        ]
    }

    provider = ImdDistrictProvider()
    advisories = provider.parse_payload(sample_imd_json)

    assert len(advisories) == 1
    adv = advisories[0]
    assert adv.source_id == "imd-kolkata-001"
    assert adv.authority == Authority.IMD.value
    assert adv.hazard_type == HazardType.EXTREME_RAIN.value
    assert adv.severity == SeverityLevel.RED.value
    assert adv.district == "Kolkata"
    assert adv.subdivision == "Gangetic West Bengal"


def test_cpcb_aqi_provider_parsing():
    sample_cpcb_data = [
        {
            "city": "Delhi",
            "state": "Delhi",
            "station_name": "Anand Vihar",
            "aqi": 342,
            "prominent_pollutant": "PM2.5",
            "latitude": 28.65,
            "longitude": 77.31,
        }
    ]

    provider = CpcbAqiProvider()
    advisories = provider.parse_payload(sample_cpcb_data)

    assert len(advisories) == 1
    adv = advisories[0]
    assert adv.hazard_type == HazardType.AIR_QUALITY.value
    assert adv.severity == SeverityLevel.RED.value  # Very Poor
    assert "AQI 342" in adv.official_level
    assert adv.authority == Authority.CPCB.value


# 3. Ingestion, Deduplication, & Expiry Tests
@pytest.mark.anyio
async def test_advisory_ingestion_and_deduplication(db_session):
    now_utc = datetime.now(timezone.utc)

    # Mock provider returning deterministic alerts
    class MockProvider(BaseAdvisoryProvider):
        @property
        def authority(self):
            return "IMD"

        @property
        def name(self):
            return "Mock IMD"

        async def fetch_raw(self):
            return "ok"

        def parse_payload(self, raw_data):
            return [
                NormalizedAdvisory(
                    source_id="test-imd-001",
                    authority="IMD",
                    hazard_type="HEAVY_RAIN",
                    severity="orange",
                    issued_at=now_utc,
                    effective_at=now_utc,
                    expires_at=now_utc + timedelta(hours=12),
                    headline="Original Headline",
                    description="Original Description",
                    district="Kolkata",
                    state="West Bengal",
                )
            ]

    ingestion = AdvisoryIngestionService(providers=[MockProvider()])

    # Cycle 1: Insert
    res1 = await ingestion.ingest_all(db_session)
    assert res1["inserted"] == 1
    assert res1["updated"] == 0

    count = db_session.query(Advisory).count()
    assert count == 1

    # Cycle 2: Same source_id, updated content -> Should Update, not Duplicate!
    class UpdatedMockProvider(MockProvider):
        def parse_payload(self, raw_data):
            return [
                NormalizedAdvisory(
                    source_id="test-imd-001",
                    authority="IMD",
                    hazard_type="HEAVY_RAIN",
                    severity="red",  # Upgraded to Red!
                    issued_at=now_utc,
                    effective_at=now_utc,
                    expires_at=now_utc + timedelta(hours=12),
                    headline="Upgraded RED WARNING",
                    description="Updated Description",
                    district="Kolkata",
                    state="West Bengal",
                )
            ]

    ingestion_v2 = AdvisoryIngestionService(providers=[UpdatedMockProvider()])
    res2 = await ingestion_v2.ingest_all(db_session)
    assert res2["inserted"] == 0
    assert res2["updated"] == 1

    # Count must remain 1
    assert db_session.query(Advisory).count() == 1
    updated_record = db_session.query(Advisory).first()
    assert updated_record.severity == "red"
    assert updated_record.headline == "Upgraded RED WARNING"


@pytest.mark.anyio
async def test_expiry_pruning(db_session):
    now_utc = datetime.now(timezone.utc)
    expired_adv = Advisory(
        source_id="exp-001",
        authority="IMD",
        hazard_type="FOG",
        severity="yellow",
        issued_at=now_utc - timedelta(days=2),
        effective_at=now_utc - timedelta(days=2),
        expires_at=now_utc - timedelta(days=1),  # Already expired
        is_active=True,
        headline="Expired Fog Warning",
        description="Expired description",
    )
    db_session.add(expired_adv)
    db_session.commit()

    ingestion = AdvisoryIngestionService(providers=[])
    pruned = ingestion.prune_expired(db_session, now_utc)

    assert pruned == 1
    db_session.refresh(expired_adv)
    assert expired_adv.is_active is False


# 4. Hierarchical Location Resolution Tests
def test_advisory_service_hierarchical_matching(db_session):
    now_utc = datetime.now(timezone.utc)
    adv_district = Advisory(
        source_id="kolkata-rain",
        authority="IMD",
        hazard_type="HEAVY_RAIN",
        severity="orange",
        issued_at=now_utc,
        effective_at=now_utc,
        expires_at=now_utc + timedelta(hours=6),
        is_active=True,
        granularity="district",
        district="Kolkata",
        state="West Bengal",
        headline="Orange Alert Kolkata",
        description="Heavy rain in Kolkata district",
    )
    adv_state = Advisory(
        source_id="wb-cyclone",
        authority="IMD",
        hazard_type="CYCLONE",
        severity="red",
        issued_at=now_utc,
        effective_at=now_utc,
        expires_at=now_utc + timedelta(hours=12),
        is_active=True,
        granularity="state",
        state="West Bengal",
        headline="Red Alert Coastal West Bengal",
        description="Cyclone warning across state",
    )
    adv_other = Advisory(
        source_id="mumbai-heat",
        authority="IMD",
        hazard_type="HEATWAVE",
        severity="yellow",
        issued_at=now_utc,
        effective_at=now_utc,
        expires_at=now_utc + timedelta(hours=6),
        is_active=True,
        granularity="district",
        district="Mumbai",
        state="Maharashtra",
        headline="Yellow Alert Mumbai",
        description="Heatwave in Mumbai",
    )
    db_session.add_all([adv_district, adv_state, adv_other])
    db_session.commit()

    service = AdvisoryService()

    # Query for Kolkata: should match Kolkata (district) and West Bengal (state), but NOT Mumbai
    kolkata_res = service.get_advisories(
        db_session,
        AdvisoryQueryFilter(district="Kolkata", state="West Bengal"),
    )
    assert len(kolkata_res) == 2
    # Highest severity (Red cyclone) must be sorted first, followed by Orange rain
    assert kolkata_res[0].severity == "red"
    assert kolkata_res[1].severity == "orange"

    # Query for Mumbai: should match only Mumbai
    mumbai_res = service.get_advisories(
        db_session,
        AdvisoryQueryFilter(district="Mumbai"),
    )
    assert len(mumbai_res) == 1
    assert mumbai_res[0].district == "Mumbai"


def test_advisory_temporal_query_filters(db_session):
    """Verify that include_expired=False returns active and upcoming advisories, but excludes expired ones."""
    now_utc = datetime.now(timezone.utc)
    service = AdvisoryService()

    active_adv = Advisory(
        source_id="temp-active-01",
        authority="IMD",
        hazard_type="HEAVY_RAIN",
        severity="red",
        issued_at=now_utc - timedelta(hours=1),
        effective_at=now_utc - timedelta(hours=1),
        expires_at=now_utc + timedelta(hours=4),
        is_active=True,
        district="Bengaluru",
        headline="Active Heavy Rain Warning",
        description="Active description",
    )
    upcoming_adv = Advisory(
        source_id="temp-upcoming-01",
        authority="IMD",
        hazard_type="THUNDERSTORM",
        severity="orange",
        issued_at=now_utc,
        effective_at=now_utc + timedelta(hours=6),
        expires_at=now_utc + timedelta(hours=24),
        is_active=False,  # not yet active, but upcoming
        district="Bengaluru",
        headline="Upcoming Thunderstorm Watch",
        description="Upcoming description",
    )
    expired_adv = Advisory(
        source_id="temp-expired-01",
        authority="IMD",
        hazard_type="HEATWAVE",
        severity="yellow",
        issued_at=now_utc - timedelta(days=2),
        effective_at=now_utc - timedelta(days=2),
        expires_at=now_utc - timedelta(hours=2),
        is_active=False,
        district="Bengaluru",
        headline="Expired Heatwave Advisory",
        description="Expired description",
    )

    db_session.add_all([active_adv, upcoming_adv, expired_adv])
    db_session.commit()

    # Query with default include_expired=False
    results_unexpired = service.get_advisories(
        db_session,
        AdvisoryQueryFilter(district="Bengaluru", include_expired=False),
    )
    source_ids = [r.source_id for r in results_unexpired]
    assert "temp-active-01" in source_ids
    assert "temp-upcoming-01" in source_ids
    assert "temp-expired-01" not in source_ids
    assert len(results_unexpired) == 2

    # Query with include_expired=True
    results_all = service.get_advisories(
        db_session,
        AdvisoryQueryFilter(district="Bengaluru", include_expired=True),
    )
    assert len(results_all) == 3


# 5. API Endpoint & Filter Tests
def test_api_get_advisories(test_client):
    response = test_client.get("/api/weather/advisories?district=Kolkata")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "advisories" in data
    assert isinstance(data["advisories"], list)


def test_geographic_precedence_hierarchy(db_session):
    """Verify exact precedence hierarchy: point/radius -> district -> subdivision -> state -> national."""
    now_utc = datetime.now(timezone.utc)
    base_time = now_utc

    # Create 5 advisories with identical severity ('orange') to test spatial precedence sorting
    adv_national = Advisory(
        source_id="nat-01",
        authority="NDMA",
        hazard_type="CYCLONE",
        severity="orange",
        issued_at=base_time,
        effective_at=base_time,
        expires_at=base_time + timedelta(hours=24),
        is_active=True,
        granularity="national",
        headline="National Orange Advisory",
        description="Pan-India alert",
    )
    adv_state = Advisory(
        source_id="state-01",
        authority="IMD",
        hazard_type="HEAVY_RAIN",
        severity="orange",
        issued_at=base_time,
        effective_at=base_time,
        expires_at=base_time + timedelta(hours=24),
        is_active=True,
        granularity="state",
        state="Maharashtra",
        headline="Maharashtra Orange Advisory",
        description="State alert",
    )
    adv_subdivision = Advisory(
        source_id="sub-01",
        authority="IMD",
        hazard_type="THUNDERSTORM",
        severity="orange",
        issued_at=base_time,
        effective_at=base_time,
        expires_at=base_time + timedelta(hours=24),
        is_active=True,
        granularity="subdivision",
        subdivision="Konkan & Goa",
        state="Maharashtra",
        headline="Konkan Subdivision Orange Advisory",
        description="Subdivision alert",
    )
    adv_district = Advisory(
        source_id="dist-01",
        authority="IMD",
        hazard_type="FLASH_FLOOD",
        severity="orange",
        issued_at=base_time,
        effective_at=base_time,
        expires_at=base_time + timedelta(hours=24),
        is_active=True,
        granularity="district",
        district="Mumbai Suburban",
        state="Maharashtra",
        headline="Mumbai District Orange Advisory",
        description="District alert",
    )
    adv_point = Advisory(
        source_id="point-01",
        authority="IMD",
        hazard_type="EXTREME_RAIN",
        severity="orange",
        issued_at=base_time,
        effective_at=base_time,
        expires_at=base_time + timedelta(hours=24),
        is_active=True,
        granularity="nowcast",
        latitude=19.0760,
        longitude=72.8777,
        radius_km=15.0,
        headline="Santacruz Radar Nowcast",
        description="Point radius alert",
    )

    db_session.add_all([adv_national, adv_state, adv_subdivision, adv_district, adv_point])
    db_session.commit()

    service = AdvisoryService()
    results = service.get_advisories(
        db_session,
        AdvisoryQueryFilter(
            district="Mumbai Suburban",
            state="Maharashtra",
            subdivision="Konkan & Goa",
            latitude=19.0760,
            longitude=72.8777,
        ),
    )

    # All 5 levels should match and be ordered by geographic precedence:
    # 1st: Point (Tier 5)
    # 2nd: District (Tier 4)
    # 3rd: Subdivision (Tier 3)
    # 4th: State (Tier 2)
    # 5th: National (Tier 1)
    assert len(results) == 5
    assert results[0].source_id == "point-01"
    assert results[1].source_id == "dist-01"
    assert results[2].source_id == "sub-01"
    assert results[3].source_id == "state-01"
    assert results[4].source_id == "nat-01"


def test_advisory_filters_comprehensive(db_session):
    """Verify filtering by state, district, lat/lon, severity, authority, hazard_type, and expiry."""
    now_utc = datetime.now(timezone.utc)
    adv_active = Advisory(
        source_id="cpcb-delhi-01",
        authority="CPCB",
        hazard_type="AIR_QUALITY",
        severity="red",
        issued_at=now_utc,
        effective_at=now_utc,
        expires_at=now_utc + timedelta(hours=4),
        is_active=True,
        district="Delhi",
        state="Delhi",
        headline="Severe AQI Delhi",
        description="AQI exceeds 420",
    )
    adv_expired = Advisory(
        source_id="cpcb-delhi-old",
        authority="CPCB",
        hazard_type="AIR_QUALITY",
        severity="red",
        issued_at=now_utc - timedelta(days=2),
        effective_at=now_utc - timedelta(days=2),
        expires_at=now_utc - timedelta(days=1),
        is_active=False,
        district="Delhi",
        state="Delhi",
        headline="Expired AQI Alert",
        description="Old alert",
    )
    db_session.add_all([adv_active, adv_expired])
    db_session.commit()

    service = AdvisoryService()

    # Filter by authority CPCB
    r_auth = service.get_advisories(db_session, AdvisoryQueryFilter(authority="CPCB"))
    assert len(r_auth) == 1
    assert r_auth[0].source_id == "cpcb-delhi-01"

    # Filter by wrong authority IMD
    r_none = service.get_advisories(db_session, AdvisoryQueryFilter(authority="IMD"))
    assert len(r_none) == 0

    # Filter by hazard_type AIR_QUALITY
    r_haz = service.get_advisories(db_session, AdvisoryQueryFilter(hazard_type="AIR_QUALITY"))
    assert len(r_haz) == 1

    # Filter by severity red
    r_sev = service.get_advisories(db_session, AdvisoryQueryFilter(severity="red"))
    assert len(r_sev) == 1

    # Filter with include_expired=True
    r_all = service.get_advisories(db_session, AdvisoryQueryFilter(district="Delhi", include_expired=True))
    assert len(r_all) == 2


class BrokenProvider(BaseAdvisoryProvider):
    @property
    def authority(self) -> str:
        return "IMD"

    @property
    def name(self) -> str:
        return "Failing Provider"

    async def fetch_raw(self):
        raise ConnectionResetError("Simulated government server connection drop")

    def parse_payload(self, raw_data):
        return []


@pytest.mark.asyncio
async def test_failure_isolation_retains_database(db_session):
    """Verify that failing providers do not throw, retain database records, and complete ingestion."""
    now_utc = datetime.now(timezone.utc)
    existing_adv = Advisory(
        source_id="retained-01",
        authority="IMD",
        hazard_type="HEAVY_RAIN",
        severity="yellow",
        issued_at=now_utc,
        effective_at=now_utc,
        expires_at=now_utc + timedelta(hours=8),
        is_active=True,
        district="Pune",
        state="Maharashtra",
        headline="Existing Yellow Alert",
        description="Valid alert in DB",
    )
    db_session.add(existing_adv)
    db_session.commit()

    # Run ingestion with broken provider
    ingestion = AdvisoryIngestionService(providers=[BrokenProvider()])
    result = await ingestion.ingest_all(db_session)

    # Should report 0 fetched, 0 inserted, 0 updated, without throwing
    assert result["fetched"] == 0
    assert result["inserted"] == 0

    # Retained database record must still be present and accessible
    service = AdvisoryService()
    active = service.get_advisories(db_session, AdvisoryQueryFilter(district="Pune"))
    assert len(active) == 1
    assert active[0].source_id == "retained-01"


def test_ingest_endpoint_security(test_client):
    """Verify that POST /api/weather/advisories/ingest requires authentication."""
    # Anonymous call must return 401
    r_anon = test_client.post("/api/weather/advisories/ingest")
    assert r_anon.status_code == 401
    assert "Ingestion authorization required" in r_anon.json()["detail"]

    # Invalid token must return 401
    r_bad = test_client.post(
        "/api/weather/advisories/ingest",
        headers={"Authorization": "Bearer invalid-token-123"},
    )
    assert r_bad.status_code == 401

    # Valid secret via Bearer token
    from app.core.config import settings
    secret = settings.advisory_ingest_secret or settings.jwt_secret
    r_bearer = test_client.post(
        "/api/weather/advisories/ingest",
        headers={"Authorization": f"Bearer {secret}"},
    )
    assert r_bearer.status_code == 200
    assert r_bearer.json()["status"] == "success"

    # Valid secret via X-Ingest-Key header
    r_header = test_client.post(
        "/api/weather/advisories/ingest",
        headers={"X-Ingest-Key": secret},
    )
    assert r_header.status_code == 200
    assert r_header.json()["status"] == "success"


def test_database_idempotent_upsert_and_lifecycle(db_session):
    """Verify insertion, duplicate source_id idempotency, updates, and expiry."""
    now_utc = datetime.now(timezone.utc)
    base_dto = NormalizedAdvisory(
        source_id="test-idempotent-01",
        authority="IMD",
        hazard_type="HEAVY_RAIN",
        severity="yellow",
        issued_at=now_utc,
        effective_at=now_utc,
        expires_at=now_utc + timedelta(hours=12),
        headline="Initial Yellow Warning",
        description="Initial advisory description",
        district="Bengaluru",
        state="Karnataka",
    )

    class MockProvider(BaseAdvisoryProvider):
        @property
        def authority(self) -> str:
            return "IMD"

        @property
        def name(self) -> str:
            return "Mock Provider"

        async def fetch_raw(self):
            return "ok"

        def parse_payload(self, raw_data):
            return [base_dto]

    # 1. Initial Ingestion
    ingestion = AdvisoryIngestionService(providers=[MockProvider()])
    res1 = asyncio.run(ingestion.ingest_all(db_session))
    assert res1["inserted"] == 1
    assert res1["updated"] == 0

    record = db_session.query(Advisory).filter(Advisory.source_id == "test-idempotent-01").first()
    assert record is not None
    assert record.severity == "yellow"
    assert record.headline == "Initial Yellow Warning"

    # 2. Duplicate / Escalated Ingestion (Idempotent update)
    escalated_dto = NormalizedAdvisory(
        source_id="test-idempotent-01",
        authority="IMD",
        hazard_type="EXTREME_RAIN",
        severity="red",
        issued_at=now_utc,
        effective_at=now_utc,
        expires_at=now_utc + timedelta(hours=18),
        headline="Escalated Red Warning",
        description="Updated severity description",
        district="Bengaluru",
        state="Karnataka",
    )

    class MockEscalatedProvider(BaseAdvisoryProvider):
        @property
        def authority(self) -> str:
            return "IMD"

        @property
        def name(self) -> str:
            return "Mock Escalated Provider"

        async def fetch_raw(self):
            return "ok"

        def parse_payload(self, raw_data):
            return [escalated_dto]

    ingestion_esc = AdvisoryIngestionService(providers=[MockEscalatedProvider()])
    res2 = asyncio.run(ingestion_esc.ingest_all(db_session))
    assert res2["inserted"] == 0
    assert res2["updated"] == 1

    # Verify existing record was updated and NOT duplicated
    all_records = db_session.query(Advisory).filter(Advisory.source_id == "test-idempotent-01").all()
    assert len(all_records) == 1
    assert all_records[0].severity == "red"
    assert all_records[0].headline == "Escalated Red Warning"


