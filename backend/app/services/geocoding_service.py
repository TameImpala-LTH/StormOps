"""Geocoding service using Open-Meteo Geocoding API for resolving location names to coordinates."""

import asyncio
import logging
import re
import unicodedata
from collections import OrderedDict
from typing import Optional, Tuple

from fastapi import HTTPException
import httpx

from app.schemas.query import GeocodedLocationSchema

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Bounded In-Memory Geocoding Cache
# ---------------------------------------------------------------------------
# Stores successful name -> (GeocodedLocationSchema, is_region_shortcut) lookups.
# Design constraints:
#   - Max 512 entries (bounded to avoid memory growth in long-running processes).
#   - LRU eviction: oldest entries dropped when capacity is exceeded.
#   - Only successful API results are stored; errors are never cached.
#   - Keys are normalized (lowercase, ASCII-folded, whitespace-collapsed) to
#     match across aliases like "Bangalore" / "bangalore" / "BANGALORE".
#   - Thread-safe via asyncio.Lock (Render runs async FastAPI workers on one loop).
#   - Never overrides device-provided GPS coordinates (reverse_geocode is uncached).
#   - Testable: exposes cache_size(), cache_keys(), and clear_cache() helpers.

_GEOCODE_CACHE: "OrderedDict[str, GeocodedLocationSchema]" = OrderedDict()
_GEOCODE_CACHE_LOCK = asyncio.Lock()
_GEOCODE_CACHE_MAX = 512


def _normalize_cache_key(location_name: str) -> str:
    """Produce a stable cache key from a location name.

    Steps:
      1. NFKD unicode normalization (decompose combined characters).
      2. Strip accent diacritics (non-ASCII combining characters).
      3. Lowercase.
      4. Collapse runs of whitespace/punctuation to a single space.
      5. Strip leading/trailing whitespace.

    This ensures "Bengaluru", "bengaluru", "Bengalūru" all map to the
    same key "bengaluru".
    """
    # NFKD then strip combining chars
    normalized = unicodedata.normalize("NFKD", location_name)
    ascii_folded = "".join(c for c in normalized if not unicodedata.combining(c))
    lowered = ascii_folded.lower()
    # Collapse whitespace sequences
    key = re.sub(r"[\s,]+", " ", lowered).strip()
    return key


async def _cache_get(key: str) -> Optional[GeocodedLocationSchema]:
    """Return a cached GeocodedLocationSchema or None, updating LRU order."""
    async with _GEOCODE_CACHE_LOCK:
        if key in _GEOCODE_CACHE:
            _GEOCODE_CACHE.move_to_end(key)
            return _GEOCODE_CACHE[key]
    return None


async def _cache_set(key: str, value: GeocodedLocationSchema) -> None:
    """Store a geocoding result, evicting the oldest entry if over capacity."""
    async with _GEOCODE_CACHE_LOCK:
        if key in _GEOCODE_CACHE:
            _GEOCODE_CACHE.move_to_end(key)
        _GEOCODE_CACHE[key] = value
        while len(_GEOCODE_CACHE) > _GEOCODE_CACHE_MAX:
            _GEOCODE_CACHE.popitem(last=False)


# ---------------------------------------------------------------------------
# Public testability helpers (used by unit tests and benchmarks)
# ---------------------------------------------------------------------------

def geocode_cache_size() -> int:
    """Return the current number of cached geocoding results."""
    return len(_GEOCODE_CACHE)


def geocode_cache_keys() -> Tuple[str, ...]:
    """Return a snapshot of all current cache keys (for inspection in tests)."""
    return tuple(_GEOCODE_CACHE.keys())


def geocode_cache_clear() -> None:
    """Clear the entire cache. Intended for test teardown only."""
    _GEOCODE_CACHE.clear()

GEOCODING_API_URL = "https://geocoding-api.open-meteo.com/v1/search"

# Curated Indian states and territories mapped to genuine geographic center coordinates and explicit region labeling
INDIAN_REGION_CENTERS = {
    "kerala": (10.3529, 76.5120, "Kerala", "India", "IN"),
    "goa": (15.3005, 74.0855, "Goa", "India", "IN"),
    "punjab": (30.9293, 75.5005, "Punjab", "India", "IN"),
    "gujarat": (22.3094, 72.1362, "Gujarat", "India", "IN"),
    "west bengal": (22.9868, 87.8550, "West Bengal", "India", "IN"),
    "andhra pradesh": (15.9129, 79.7400, "Andhra Pradesh", "India", "IN"),
    "arunachal pradesh": (28.2180, 94.7278, "Arunachal Pradesh", "India", "IN"),
    "assam": (26.2006, 92.9376, "Assam", "India", "IN"),
    "bihar": (25.0961, 85.3131, "Bihar", "India", "IN"),
    "chhattisgarh": (21.2787, 81.8661, "Chhattisgarh", "India", "IN"),
    "haryana": (29.0588, 76.0856, "Haryana", "India", "IN"),
    "himachal pradesh": (31.1048, 77.1734, "Himachal Pradesh", "India", "IN"),
    "jharkhand": (23.6102, 85.2799, "Jharkhand", "India", "IN"),
    "karnataka": (15.3173, 75.7139, "Karnataka", "India", "IN"),
    "madhya pradesh": (22.9734, 78.6569, "Madhya Pradesh", "India", "IN"),
    "maharashtra": (19.7515, 75.7139, "Maharashtra", "India", "IN"),
    "manipur": (24.6637, 93.9063, "Manipur", "India", "IN"),
    "meghalaya": (25.4670, 91.3662, "Meghalaya", "India", "IN"),
    "mizoram": (23.1645, 92.9376, "Mizoram", "India", "IN"),
    "nagaland": (26.1584, 94.5624, "Nagaland", "India", "IN"),
    "odisha": (20.9517, 85.0985, "Odisha", "India", "IN"),
    "orissa": (20.9517, 85.0985, "Odisha", "India", "IN"),
    "rajasthan": (27.0238, 74.2179, "Rajasthan", "India", "IN"),
    "sikkim": (27.5330, 88.5122, "Sikkim", "India", "IN"),
    "tamil nadu": (11.1271, 78.6569, "Tamil Nadu", "India", "IN"),
    "telangana": (18.1124, 79.0193, "Telangana", "India", "IN"),
    "tripura": (23.9408, 91.9882, "Tripura", "India", "IN"),
    "uttar pradesh": (26.8467, 80.9462, "Uttar Pradesh", "India", "IN"),
    "uttarakhand": (30.0668, 79.0193, "Uttarakhand", "India", "IN"),
    "andaman and nicobar": (11.7401, 92.6586, "Andaman and Nicobar Islands", "India", "IN"),
    "jammu and kashmir": (33.7782, 76.5762, "Jammu and Kashmir", "India", "IN"),
    "ladakh": (34.1526, 77.5771, "Ladakh", "India", "IN"),
}

# Common historical / colloquial Indian city alias normalization
INDIAN_CITY_ALIASES = {
    "bangalore": "Bengaluru",
    "bengaluru": "Bengaluru",
    "calcutta": "Kolkata",
    "bombay": "Mumbai",
    "madras": "Chennai",
    "ooty": "Udhagamandalam",
    "cochin": "Kochi",
    "baroda": "Vadodara",
    "trivandrum": "Thiruvananthapuram",
    "benares": "Varanasi",
    "banaras": "Varanasi",
    "kashi": "Varanasi",
    "gurgaon": "Gurugram",
    "poona": "Pune",
    "simla": "Shimla",
    "waltair": "Visakhapatnam",
    "vizag": "Visakhapatnam",
}

# Common country name/code mappings for parsing explicit country-qualified queries ("City, Country")
COUNTRY_NAME_TO_CODE = {
    "uk": "GB",
    "united kingdom": "GB",
    "great britain": "GB",
    "england": "GB",
    "scotland": "GB",
    "wales": "GB",
    "france": "FR",
    "us": "US",
    "usa": "US",
    "united states": "US",
    "united states of america": "US",
    "india": "IN",
    "japan": "JP",
    "germany": "DE",
    "australia": "AU",
    "canada": "CA",
    "uae": "AE",
    "united arab emirates": "AE",
    "italy": "IT",
    "spain": "ES",
    "china": "CN",
    "russia": "RU",
    "brazil": "BR",
}


class GeocodingService:
    """Service providing global location resolution to latitude/longitude coordinates."""

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self._client = client

    async def geocode_location(self, location_name: str) -> GeocodedLocationSchema:
        """Resolve location name globally to coordinates and timezone metadata.

        Results are stored in an in-memory bounded LRU cache (max 512 entries) keyed
        on the normalized, alias-resolved city name. Cache hits return in <0.1 ms.
        Failed lookups (HTTPException) are never cached to avoid serving stale errors.
        Device-provided GPS coordinates (reverse_geocode) are always uncached.
        """
        cleaned_name = location_name.strip()
        if not cleaned_name:
            raise HTTPException(status_code=400, detail="Location name cannot be empty.")

        # Step 1: Detect explicit country qualifier (e.g. "London, UK", "Paris, France", "Springfield, USA")
        query_city = cleaned_name
        country_filter: Optional[str] = None

        if "," in cleaned_name:
            parts = [p.strip() for p in cleaned_name.split(",") if p.strip()]
            if len(parts) >= 2:
                candidate_city = parts[0]
                candidate_country = parts[-1].lower()
                if candidate_country in COUNTRY_NAME_TO_CODE:
                    country_filter = COUNTRY_NAME_TO_CODE[candidate_country]
                    query_city = candidate_city
                elif len(candidate_country) == 2 and candidate_country.isalpha():
                    country_filter = candidate_country.upper()
                    query_city = candidate_city

        query_city_lower = query_city.lower()

        # Step 2: Canonicalize known city aliases (e.g. Bangalore -> Bengaluru, Calcutta -> Kolkata)
        if query_city_lower in INDIAN_CITY_ALIASES:
            target_city_name = INDIAN_CITY_ALIASES[query_city_lower]
        else:
            target_city_name = query_city

        # Cache key: build on the post-alias canonical target name (+ country filter if any).
        # Country-qualified lookups ("London, UK" vs "London, CA") get distinct keys.
        cache_key_str = target_city_name if not country_filter else f"{target_city_name},{country_filter}"
        cache_key = _normalize_cache_key(cache_key_str)

        # Cache lookup before any network I/O.
        cached = await _cache_get(cache_key)
        if cached is not None:
            logger.debug("Geocoding cache hit for '%s' (key=%s)", cleaned_name, cache_key)
            return cached

        # Step 3: Handle ambiguous state/region queries (e.g., "Kerala", "Goa", "Punjab")
        # Preserve genuine regional geographic entity and explicitly label as region
        if query_city_lower in INDIAN_REGION_CENTERS and not country_filter:
            lat, lon, region_name, country_name, cc = INDIAN_REGION_CENTERS[query_city_lower]
            result = GeocodedLocationSchema(
                name=f"{region_name} (Region)",
                country=country_name,
                country_code=cc,
                admin1=region_name,
                latitude=lat,
                longitude=lon,
                timezone="Asia/Kolkata",
            )
            await _cache_set(cache_key, result)
            return result

        # Step 4: Primary global resolution via Open-Meteo Geocoding API
        params = {
            "name": target_city_name,
            "count": 10,
            "language": "en",
            "format": "json",
        }
        if country_filter:
            params["countryCode"] = country_filter

        timeout = httpx.Timeout(10.0, connect=5.0)

        try:
            if self._client:
                response = await self._client.get(GEOCODING_API_URL, params=params, timeout=timeout)
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.get(GEOCODING_API_URL, params=params, timeout=timeout)

            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException as exc:
            logger.error(f"Geocoding provider timeout: {exc}")
            raise HTTPException(status_code=504, detail="Geocoding service gateway timeout")
        except httpx.HTTPStatusError as exc:
            logger.error(f"Geocoding provider HTTP error: {exc.response.status_code}")
            raise HTTPException(
                status_code=502,
                detail=f"Geocoding service returned HTTP error {exc.response.status_code}",
            )
        except httpx.RequestError as exc:
            logger.error(f"Geocoding network request failed: {exc}")
            raise HTTPException(status_code=502, detail="Geocoding network request failed")

        results = data.get("results") or []

        # If country filter was applied, filter results strictly
        if country_filter:
            results = [
                r for r in results
                if (r.get("country_code") or "").upper() == country_filter.upper()
            ]

        if results:
            # Prioritize exact name matches, sorted by population
            exact_matches = [
                r for r in results
                if r.get("name", "").strip().lower() == target_city_name.lower()
            ]
            if exact_matches:
                exact_matches.sort(key=lambda x: x.get("population") or 0, reverse=True)
                top_result = exact_matches[0]
            else:
                # If no exact match, sort by population descending
                results.sort(key=lambda x: x.get("population") or 0, reverse=True)
                top_result = results[0]

            result = GeocodedLocationSchema(
                name=top_result.get("name", cleaned_name),
                country=top_result.get("country", ""),
                country_code=(top_result.get("country_code") or "").upper() or None,
                admin1=top_result.get("admin1"),
                latitude=float(top_result["latitude"]),
                longitude=float(top_result["longitude"]),
                timezone=top_result.get("timezone", "UTC"),
            )
            await _cache_set(cache_key, result)
            return result

        # Step 5: Global fallback to OpenStreetMap Nominatim (handles complex or country-qualified queries)
        try:
            nom_url = "https://nominatim.openstreetmap.org/search"
            nom_params = {
                "q": cleaned_name,
                "format": "json",
                "limit": 5,
                "addressdetails": 1,
            }
            if country_filter:
                nom_params["countrycodes"] = country_filter.lower()

            nom_headers = {"User-Agent": "StormOps-WeatherGPT/1.0"}

            if self._client:
                nom_resp = await self._client.get(nom_url, params=nom_params, headers=nom_headers, timeout=6.0)
            else:
                async with httpx.AsyncClient() as client:
                    nom_resp = await client.get(nom_url, params=nom_params, headers=nom_headers, timeout=6.0)

            if nom_resp.status_code == 200:
                nom_data = nom_resp.json()
                if nom_data:
                    top_item = nom_data[0]
                    addr = top_item.get("address", {})
                    disp_name = (
                        addr.get("city")
                        or addr.get("town")
                        or addr.get("municipality")
                        or addr.get("state_district")
                        or top_item.get("name")
                        or cleaned_name
                    )
                    # If this is an administrative state/region, label honestly
                    if top_item.get("class") == "boundary" and top_item.get("type") == "administrative":
                        state_val = addr.get("state") or top_item.get("name")
                        if state_val and state_val.lower() == cleaned_name.lower():
                            disp_name = f"{state_val} (Region)"

                    result = GeocodedLocationSchema(
                        name=disp_name,
                        country=addr.get("country", ""),
                        country_code=(addr.get("country_code") or "").upper() or None,
                        admin1=addr.get("state"),
                        latitude=float(top_item["lat"]),
                        longitude=float(top_item["lon"]),
                        timezone="UTC",
                    )
                    await _cache_set(cache_key, result)
                    return result
        except Exception as exc:
            logger.warning(f"Nominatim global fallback lookup failed for '{cleaned_name}': {exc}")

        logger.warning(f"Global location not found: {cleaned_name}")
        raise HTTPException(
            status_code=404,
            detail=f"Location '{cleaned_name}' could not be resolved. Please specify a valid city or region.",
        )


    async def reverse_geocode(self, latitude: float, longitude: float) -> GeocodedLocationSchema:
        """Resolve device latitude/longitude coordinates directly to a GeocodedLocationSchema with city/country display name."""
        lat_formatted = f"{latitude:.2f}"
        lng_formatted = f"{longitude:.2f}"
        default_name = f"Current Location ({lat_formatted}, {lng_formatted})"

        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": latitude,
            "lon": longitude,
            "format": "json",
            "zoom": 16,
        }
        headers = {"User-Agent": "StormOps-WeatherGPT/1.0"}

        try:
            if self._client:
                response = await self._client.get(url, params=params, headers=headers, timeout=5.0)
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, params=params, headers=headers, timeout=5.0)

            if response.status_code == 200:
                data = response.json()
                address = data.get("address", {})

                # Micro-locality / neighbourhood / suburb
                locality = (
                    address.get("suburb")
                    or address.get("neighbourhood")
                    or address.get("quarter")
                    or address.get("city_district")
                    or address.get("residential")
                    or address.get("village")
                    or address.get("hamlet")
                )
                # Broader city / municipality / town
                city = (
                    address.get("city")
                    or address.get("town")
                    or address.get("municipality")
                    or address.get("county")
                    or address.get("state_district")
                )

                country = address.get("country", "")
                state = address.get("state")

                # Prefer hierarchical "Locality, City" e.g. "Behala, Kolkata" when available
                if locality and city and locality.strip().lower() != city.strip().lower():
                    name = f"{locality.strip()}, {city.strip()}"
                elif locality:
                    name = locality.strip()
                elif city:
                    name = city.strip()
                else:
                    name = default_name

                return GeocodedLocationSchema(
                    name=name,
                    country=country,
                    admin1=state,
                    latitude=latitude,
                    longitude=longitude,
                    timezone="UTC",
                )
        except Exception as exc:
            logger.warning(f"Reverse geocoding lookup failed for ({latitude}, {longitude}): {exc}")

        return GeocodedLocationSchema(
            name=default_name,
            country="",
            admin1=None,
            latitude=latitude,
            longitude=longitude,
            timezone="UTC",
        )



geocoding_service = GeocodingService()
