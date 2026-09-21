"""Geocoding service using Open-Meteo Geocoding API for resolving location names to coordinates."""

import asyncio
import logging
import re
import unicodedata
from collections import OrderedDict
from typing import Any, Dict, Optional, Tuple

from fastapi import HTTPException
import httpx

from app.schemas.query import GeocodedLocationSchema
from app.services.india_locality_service import india_locality_service

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

# ---------------------------------------------------------------------------
# Indian State / UT Names — used to detect state-qualified queries like
# "Newtown, West Bengal" and force country_filter = "IN" + state-level scoring.
# Covers all 28 states + 8 UTs with common abbreviations and alternate spellings.
# ---------------------------------------------------------------------------
INDIAN_STATE_NAMES: "frozenset[str]" = frozenset({
    # 28 States
    "andhra pradesh", "ap",
    "arunachal pradesh",
    "assam",
    "bihar",
    "chhattisgarh",
    "goa",
    "gujarat",
    "haryana",
    "himachal pradesh", "hp",
    "jharkhand",
    "karnataka",
    "kerala",
    "madhya pradesh", "mp",
    "maharashtra",
    "manipur",
    "meghalaya",
    "mizoram",
    "nagaland",
    "odisha", "orissa",
    "punjab",
    "rajasthan",
    "sikkim",
    "tamil nadu", "tamilnadu",
    "telangana",
    "tripura",
    "uttar pradesh", "up",
    "uttarakhand", "uttaranchal",
    "west bengal", "wb",
    # 8 Union Territories
    "andaman and nicobar", "andaman and nicobar islands",
    "chandigarh",
    "dadra and nagar haveli", "dadra and nagar haveli and daman and diu",
    "daman and diu",
    "delhi", "new delhi", "nct of delhi",
    "jammu and kashmir", "j&k", "jk",
    "ladakh",
    "lakshadweep",
    "puducherry", "pondicherry",
})

# Maps normalized state qualifier → canonical Open-Meteo admin1 display name.
# Used to score / prefer Open-Meteo results whose admin1 matches the user's intent.
INDIAN_STATE_TO_CANONICAL: "dict[str, str]" = {
    "andhra pradesh": "Andhra Pradesh", "ap": "Andhra Pradesh",
    "arunachal pradesh": "Arunachal Pradesh",
    "assam": "Assam",
    "bihar": "Bihar",
    "chhattisgarh": "Chhattisgarh",
    "goa": "Goa",
    "gujarat": "Gujarat",
    "haryana": "Haryana",
    "himachal pradesh": "Himachal Pradesh", "hp": "Himachal Pradesh",
    "jharkhand": "Jharkhand",
    "karnataka": "Karnataka",
    "kerala": "Kerala",
    "madhya pradesh": "Madhya Pradesh", "mp": "Madhya Pradesh",
    "maharashtra": "Maharashtra",
    "manipur": "Manipur",
    "meghalaya": "Meghalaya",
    "mizoram": "Mizoram",
    "nagaland": "Nagaland",
    "odisha": "Odisha", "orissa": "Odisha",
    "punjab": "Punjab",
    "rajasthan": "Rajasthan",
    "sikkim": "Sikkim",
    "tamil nadu": "Tamil Nadu", "tamilnadu": "Tamil Nadu",
    "telangana": "Telangana",
    "tripura": "Tripura",
    "uttar pradesh": "Uttar Pradesh", "up": "Uttar Pradesh",
    "uttarakhand": "Uttarakhand", "uttaranchal": "Uttarakhand",
    "west bengal": "West Bengal", "wb": "West Bengal",
    "andaman and nicobar": "Andaman and Nicobar Islands",
    "andaman and nicobar islands": "Andaman and Nicobar Islands",
    "chandigarh": "Chandigarh",
    "dadra and nagar haveli": "Dadra and Nagar Haveli and Daman and Diu",
    "dadra and nagar haveli and daman and diu": "Dadra and Nagar Haveli and Daman and Diu",
    "daman and diu": "Dadra and Nagar Haveli and Daman and Diu",
    "delhi": "Delhi", "new delhi": "Delhi", "nct of delhi": "Delhi",
    "jammu and kashmir": "Jammu and Kashmir", "j&k": "Jammu and Kashmir", "jk": "Jammu and Kashmir",
    "ladakh": "Ladakh",
    "lakshadweep": "Lakshadweep",
    "puducherry": "Puducherry", "pondicherry": "Puducherry",
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

# Common US State names and two-letter abbreviations for queries like "Newtown, Pennsylvania" or "Springfield, IL"
US_STATE_NAMES: "dict[str, str]" = {
    "alabama": "Alabama", "al": "Alabama",
    "alaska": "Alaska", "ak": "Alaska",
    "arizona": "Arizona", "az": "Arizona",
    "arkansas": "Arkansas", "ar": "Arkansas",
    "california": "California", "ca": "California",
    "colorado": "Colorado", "co": "Colorado",
    "connecticut": "Connecticut", "ct": "Connecticut",
    "delaware": "Delaware", "de": "Delaware",
    "florida": "Florida", "fl": "Florida",
    "georgia": "Georgia", "ga": "Georgia",
    "hawaii": "Hawaii", "hi": "Hawaii",
    "idaho": "Idaho", "id": "Idaho",
    "illinois": "Illinois", "il": "Illinois",
    "indiana": "Indiana",
    "iowa": "Iowa", "ia": "Iowa",
    "kansas": "Kansas", "ks": "Kansas",
    "kentucky": "Kentucky", "ky": "Kentucky",
    "louisiana": "Louisiana", "la": "Louisiana",
    "maine": "Maine", "me": "Maine",
    "maryland": "Maryland", "md": "Maryland",
    "massachusetts": "Massachusetts", "ma": "Massachusetts",
    "michigan": "Michigan", "mi": "Michigan",
    "minnesota": "Minnesota", "mn": "Minnesota",
    "mississippi": "Mississippi", "ms": "Mississippi",
    "missouri": "Missouri", "mo": "Missouri",
    "montana": "Montana", "mt": "Montana",
    "nebraska": "Nebraska", "ne": "Nebraska",
    "nevada": "Nevada", "nv": "Nevada",
    "new hampshire": "New Hampshire", "nh": "New Hampshire",
    "new jersey": "New Jersey", "nj": "New Jersey",
    "new mexico": "New Mexico", "nm": "New Mexico",
    "new york": "New York", "ny": "New York",
    "north carolina": "North Carolina", "nc": "North Carolina",
    "north dakota": "North Dakota", "nd": "North Dakota",
    "ohio": "Ohio", "oh": "Ohio",
    "oklahoma": "Oklahoma", "ok": "Oklahoma",
    "oregon": "Oregon", "or": "Oregon",
    "pennsylvania": "Pennsylvania", "pa": "Pennsylvania",
    "rhode island": "Rhode Island", "ri": "Rhode Island",
    "south carolina": "South Carolina", "sc": "South Carolina",
    "south dakota": "South Dakota", "sd": "South Dakota",
    "tennessee": "Tennessee", "tn": "Tennessee",
    "texas": "Texas", "tx": "Texas",
    "utah": "Utah", "ut": "Utah",
    "vermont": "Vermont", "vt": "Vermont",
    "virginia": "Virginia", "va": "Virginia",
    "washington": "Washington", "wa": "Washington",
    "west virginia": "West Virginia", "wv": "West Virginia",
    "wisconsin": "Wisconsin", "wi": "Wisconsin",
    "wyoming": "Wyoming", "wy": "Wyoming",
}

# Common Indian metropolitan cities/districts that act as regional qualifiers (e.g. "Behala, Kolkata")
INDIAN_METRO_QUALIFIERS: "frozenset[str]" = frozenset({
    "kolkata", "calcutta", "bengaluru", "bangalore", "mumbai", "bombay",
    "chennai", "madras", "delhi", "new delhi", "hyderabad", "pune",
    "ahmedabad", "jaipur", "lucknow", "surat", "kanpur", "nagpur",
    "patna", "indore", "thane", "bhopal", "visakhapatnam", "vadodara",
    "ghaziabad", "ludhiana", "agra", "nashik", "faridabad", "varanasi",
    "ranchi", "coimbatore", "vijayawada", "jodhpur", "madurai", "raipur",
    "guwahati", "chandigarh", "mysore", "mysuru", "gurgaon", "gurugram",
    "noida", "kochi", "cochin", "dehradun", "siliguri", "mangalore",
})

# Curated dictionary of prominent Indian urban localities mapping to (metro/city, state, country_code)
# Enables zero-context resolution on fresh sessions for prominent neighbourhoods across India.
INDIAN_PROMINENT_LOCALITIES: Dict[str, Tuple[str, str, str]] = {
    # Kolkata & Greater Kolkata Urban Localities & Suburbs
    "park street": ("Kolkata", "West Bengal", "IN"),
    "gariahat": ("Kolkata", "West Bengal", "IN"),
    "ballygunge": ("Kolkata", "West Bengal", "IN"),
    "jadavpur": ("Kolkata", "West Bengal", "IN"),
    "tollygunge": ("Kolkata", "West Bengal", "IN"),
    "behala": ("Kolkata", "West Bengal", "IN"),
    "dum dum": ("Kolkata", "West Bengal", "IN"),
    "dumdum": ("Kolkata", "West Bengal", "IN"),
    "alipore": ("Kolkata", "West Bengal", "IN"),
    "shyambazar": ("Kolkata", "West Bengal", "IN"),
    "howrah": ("Howrah", "West Bengal", "IN"),
    "esplanade": ("Kolkata", "West Bengal", "IN"),
    "kalighat": ("Kolkata", "West Bengal", "IN"),
    "sealdah": ("Kolkata", "West Bengal", "IN"),
    "bowbazar": ("Kolkata", "West Bengal", "IN"),
    "bhawanipore": ("Kolkata", "West Bengal", "IN"),
    "bhowanipore": ("Kolkata", "West Bengal", "IN"),
    "barasat": ("Kolkata", "West Bengal", "IN"),
    "baghajatin": ("Kolkata", "West Bengal", "IN"),
    "kasba": ("Kolkata", "West Bengal", "IN"),
    "lake gardens": ("Kolkata", "West Bengal", "IN"),
    "dhakuria": ("Kolkata", "West Bengal", "IN"),
    "chetla": ("Kolkata", "West Bengal", "IN"),
    "khidirpur": ("Kolkata", "West Bengal", "IN"),
    "kidderpore": ("Kolkata", "West Bengal", "IN"),
    "barrackpore": ("Kolkata", "West Bengal", "IN"),
    "dakshineswar": ("Kolkata", "West Bengal", "IN"),
    "batanagar": ("Kolkata", "West Bengal", "IN"),
    "shyamnagar": ("Kolkata", "West Bengal", "IN"),
    "ruby more": ("Kolkata", "West Bengal", "IN"),
    "ruby crossing": ("Kolkata", "West Bengal", "IN"),

    # Mumbai Localities
    "bandra": ("Mumbai", "Maharashtra", "IN"),
    "andheri": ("Mumbai", "Maharashtra", "IN"),
    "juhu": ("Mumbai", "Maharashtra", "IN"),
    "colaba": ("Mumbai", "Maharashtra", "IN"),
    "dadar": ("Mumbai", "Maharashtra", "IN"),
    "borivali": ("Mumbai", "Maharashtra", "IN"),
    "powai": ("Mumbai", "Maharashtra", "IN"),
    "worli": ("Mumbai", "Maharashtra", "IN"),
    "marine drive": ("Mumbai", "Maharashtra", "IN"),
    "ghatkopar": ("Mumbai", "Maharashtra", "IN"),
    "malad": ("Mumbai", "Maharashtra", "IN"),
    "chembur": ("Mumbai", "Maharashtra", "IN"),
    "kurla": ("Mumbai", "Maharashtra", "IN"),
    "vile parle": ("Mumbai", "Maharashtra", "IN"),
    "santacruz": ("Mumbai", "Maharashtra", "IN"),
    "bkc": ("Mumbai", "Maharashtra", "IN"),
    "bandra kurla complex": ("Mumbai", "Maharashtra", "IN"),
    "kandivali": ("Mumbai", "Maharashtra", "IN"),
    "goregaon": ("Mumbai", "Maharashtra", "IN"),
    "mulund": ("Mumbai", "Maharashtra", "IN"),

    # Delhi / NCR Localities
    "connaught place": ("New Delhi", "Delhi", "IN"),
    "cp": ("New Delhi", "Delhi", "IN"),
    "chandni chowk": ("Delhi", "Delhi", "IN"),
    "hauz khas": ("New Delhi", "Delhi", "IN"),
    "saket": ("New Delhi", "Delhi", "IN"),
    "rohini": ("Delhi", "Delhi", "IN"),
    "dwarka": ("New Delhi", "Delhi", "IN"),
    "karol bagh": ("New Delhi", "Delhi", "IN"),
    "lajpat nagar": ("New Delhi", "Delhi", "IN"),
    "vasant kunj": ("New Delhi", "Delhi", "IN"),
    "chanakyapuri": ("New Delhi", "Delhi", "IN"),
    "greater kailash": ("New Delhi", "Delhi", "IN"),
    "gurugram": ("Gurugram", "Haryana", "IN"),
    "gurgaon": ("Gurugram", "Haryana", "IN"),
    "noida": ("Noida", "Uttar Pradesh", "IN"),
    "indirapuram": ("Ghaziabad", "Uttar Pradesh", "IN"),

    # Bengaluru Localities
    "koramangala": ("Bengaluru", "Karnataka", "IN"),
    "indiranagar": ("Bengaluru", "Karnataka", "IN"),
    "whitefield": ("Bengaluru", "Karnataka", "IN"),
    "jayanagar": ("Bengaluru", "Karnataka", "IN"),
    "hsr layout": ("Bengaluru", "Karnataka", "IN"),
    "electronic city": ("Bengaluru", "Karnataka", "IN"),
    "marathahalli": ("Bengaluru", "Karnataka", "IN"),
    "bellandur": ("Bengaluru", "Karnataka", "IN"),
    "malleshwaram": ("Bengaluru", "Karnataka", "IN"),
    "hebbal": ("Bengaluru", "Karnataka", "IN"),
    "btm layout": ("Bengaluru", "Karnataka", "IN"),
    "rajajinagar": ("Bengaluru", "Karnataka", "IN"),
    "banashankari": ("Bengaluru", "Karnataka", "IN"),
    "yelahanka": ("Bengaluru", "Karnataka", "IN"),

    # Chennai Localities
    "t nagar": ("Chennai", "Tamil Nadu", "IN"),
    "t. nagar": ("Chennai", "Tamil Nadu", "IN"),
    "adyar": ("Chennai", "Tamil Nadu", "IN"),
    "velachery": ("Chennai", "Tamil Nadu", "IN"),
    "anna nagar": ("Chennai", "Tamil Nadu", "IN"),
    "mylapore": ("Chennai", "Tamil Nadu", "IN"),
    "nungambakkam": ("Chennai", "Tamil Nadu", "IN"),
    "thiruvanmiyur": ("Chennai", "Tamil Nadu", "IN"),
    "guindy": ("Chennai", "Tamil Nadu", "IN"),
    "alwarpet": ("Chennai", "Tamil Nadu", "IN"),
    "besant nagar": ("Chennai", "Tamil Nadu", "IN"),
    "tambaram": ("Chennai", "Tamil Nadu", "IN"),
    "porur": ("Chennai", "Tamil Nadu", "IN"),

    # Hyderabad Localities
    "hitec city": ("Hyderabad", "Telangana", "IN"),
    "gachibowli": ("Hyderabad", "Telangana", "IN"),
    "jubilee hills": ("Hyderabad", "Telangana", "IN"),
    "banjara hills": ("Hyderabad", "Telangana", "IN"),
    "madhapur": ("Hyderabad", "Telangana", "IN"),
    "kondapur": ("Hyderabad", "Telangana", "IN"),
    "secunderabad": ("Secunderabad", "Telangana", "IN"),
    "kukatpally": ("Hyderabad", "Telangana", "IN"),
    "begumpet": ("Hyderabad", "Telangana", "IN"),
    "charminar": ("Hyderabad", "Telangana", "IN"),
    "dilsukhnagar": ("Hyderabad", "Telangana", "IN"),

    # Pune Localities
    "kothrud": ("Pune", "Maharashtra", "IN"),
    "viman nagar": ("Pune", "Maharashtra", "IN"),
    "hinjewadi": ("Pune", "Maharashtra", "IN"),
    "baner": ("Pune", "Maharashtra", "IN"),
    "wakad": ("Pune", "Maharashtra", "IN"),
    "aundh": ("Pune", "Maharashtra", "IN"),
    "hadapsar": ("Pune", "Maharashtra", "IN"),
    "kalyani nagar": ("Pune", "Maharashtra", "IN"),
    "shivajinagar": ("Pune", "Maharashtra", "IN"),
    "pimpri": ("Pune", "Maharashtra", "IN"),
    "chinchwad": ("Pune", "Maharashtra", "IN"),
}


class GeocodingService:
    """Service providing global location resolution to latitude/longitude coordinates."""

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self._client = client

    async def _query_nominatim(
        self,
        query: str,
        country_code: Optional[str],
        target_city_name: str,
        cleaned_name: str,
        cache_key: str,
        state_hint: Optional[str] = None,
    ) -> Optional[GeocodedLocationSchema]:
        """Helper to query Nominatim and return normalized GeocodedLocationSchema with full administrative hierarchy."""
        try:
            nom_url = "https://nominatim.openstreetmap.org/search"
            nom_params: Dict[str, Any] = {
                "q": query,
                "format": "json",
                "limit": 5,
                "addressdetails": 1,
            }
            if country_code:
                nom_params["countrycodes"] = country_code.lower()

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

                    # Extract full administrative hierarchy
                    locality = (
                        addr.get("suburb")
                        or addr.get("neighbourhood")
                        or addr.get("quarter")
                        or addr.get("city_district")
                        or addr.get("residential")
                        or addr.get("road")
                        or addr.get("village")
                        or addr.get("hamlet")
                    )
                    city = (
                        addr.get("city")
                        or addr.get("town")
                        or addr.get("municipality")
                        or addr.get("city_district")
                    )
                    subdivision = addr.get("county") or addr.get("subdistrict") or addr.get("tehsil") or addr.get("taluk")
                    district = addr.get("state_district") or addr.get("county") or addr.get("district")
                    state = addr.get("state") or state_hint
                    country = addr.get("country", "")
                    cc = (addr.get("country_code") or "").upper() or None

                    # If target is a known prominent locality, use target_city_name as authoritative locality
                    if target_city_name.lower() in INDIAN_PROMINENT_LOCALITIES:
                        locality = target_city_name.title()

                    # Construct honest, informative hierarchical display name
                    primary_name = locality or top_item.get("name") or city or cleaned_name
                    if locality and city and locality.lower() != city.lower():
                        base_label = f"{locality}, {city}"
                    else:
                        base_label = primary_name

                    if state and country:
                        if state.lower() not in base_label.lower():
                            disp_name = f"{base_label}, {state}, {country}"
                        else:
                            disp_name = f"{base_label}, {country}"
                    elif country:
                        disp_name = f"{base_label}, {country}"
                    else:
                        disp_name = base_label

                    # If this is an administrative state/region, label honestly
                    if top_item.get("class") == "boundary" and top_item.get("type") == "administrative":
                        state_val = addr.get("state") or top_item.get("name")
                        if state_val and state_val.lower() == cleaned_name.lower():
                            disp_name = f"{state_val} (Region)"

                    tz = "Asia/Kolkata" if (cc == "IN" or (country and country.lower() == "india")) else "UTC"

                    result = GeocodedLocationSchema(
                        name=disp_name,
                        country=country,
                        country_code=cc,
                        admin1=state,
                        state=state,
                        district=district,
                        subdivision=subdivision,
                        city=city,
                        locality=locality,
                        latitude=float(top_item["lat"]),
                        longitude=float(top_item["lon"]),
                        timezone=tz,
                    )
                    is_explicit_foreign = bool(country_code and country_code.upper() != "IN")
                    if not is_explicit_foreign and not india_locality_service.validate_administrative_hierarchy(result, target_city_name):
                        logger.warning(
                            "Nominatim result '%s' failed administrative validation for '%s'",
                            result.name, target_city_name,
                        )
                        return None
                    await _cache_set(cache_key, result)
                    return result
        except Exception as exc:
            logger.warning(f"Nominatim lookup failed for '{query}': {exc}")
        return None

    async def geocode_location(
        self,
        location_name: str,
        context_location: Optional[GeocodedLocationSchema] = None,
    ) -> GeocodedLocationSchema:
        """Resolve location name globally to coordinates and timezone metadata.

        Results are stored in an in-memory bounded LRU cache (max 512 entries) keyed
        on the normalized, alias-resolved city name and geographic constraints. Cache hits return in <0.1 ms.
        Failed lookups (HTTPException) are never cached to avoid serving stale errors.
        Device-provided GPS coordinates (reverse_geocode) are always uncached.
        """
        cleaned_name = location_name.strip()
        if not cleaned_name:
            raise HTTPException(status_code=400, detail="Location name cannot be empty.")

        # Step 1: Detect explicit qualifier after comma.
        # Handles qualifiers in order of geographic precedence:
        #   a) Country name          — "London, UK"          → country_filter = "GB"
        #   b) Indian state / UT     — "Newtown, West Bengal"→ country_filter = "IN", state_filter = "West Bengal"
        #   c) US state name / code  — "Newtown, Pennsylvania"→ country_filter = "US", state_filter = "Pennsylvania"
        #   d) Indian metro district — "Behala, Kolkata"     → country_filter = "IN", metro_filter = "kolkata"
        #   e) 2-letter ISO code     — "Paris, FR"           → country_filter = "FR"
        query_city = cleaned_name
        country_filter: Optional[str] = None
        state_filter: Optional[str] = None  # canonical state name for scoring
        metro_filter: Optional[str] = None
        is_explicit_geography = False

        if "," in cleaned_name:
            parts = [p.strip() for p in cleaned_name.split(",") if p.strip()]
            if len(parts) >= 2:
                candidate_city = parts[0]
                candidate_qualifier = parts[-1].lower().strip()
                if candidate_qualifier in COUNTRY_NAME_TO_CODE:
                    # Case (a): explicit country name
                    country_filter = COUNTRY_NAME_TO_CODE[candidate_qualifier]
                    query_city = candidate_city
                    is_explicit_geography = True
                elif candidate_qualifier in INDIAN_STATE_NAMES:
                    # Case (b): Indian state / UT — force India country scope
                    country_filter = "IN"
                    state_filter = INDIAN_STATE_TO_CANONICAL.get(candidate_qualifier)
                    query_city = candidate_city
                    if state_filter == "West Bengal" and candidate_city.lower().strip() == "newtown":
                        query_city = "New Town"
                    is_explicit_geography = True
                    logger.debug(
                        "India state qualifier detected: '%s' → country_filter=IN, state='%s'",
                        candidate_qualifier, state_filter,
                    )
                elif candidate_qualifier in US_STATE_NAMES:
                    # Case (c): US State — force US country scope + state match
                    country_filter = "US"
                    state_filter = US_STATE_NAMES[candidate_qualifier]
                    query_city = candidate_city
                    is_explicit_geography = True
                    logger.debug(
                        "US state qualifier detected: '%s' → country_filter=US, state='%s'",
                        candidate_qualifier, state_filter,
                    )
                elif candidate_qualifier in INDIAN_METRO_QUALIFIERS:
                    # Case (d): Indian metro qualifier (e.g. Behala, Kolkata)
                    country_filter = "IN"
                    metro_filter = candidate_qualifier
                    query_city = candidate_city
                    is_explicit_geography = True
                    logger.debug(
                        "India metro qualifier detected: '%s' → country_filter=IN, metro='%s'",
                        candidate_qualifier, metro_filter,
                    )
                elif len(candidate_qualifier) == 2 and candidate_qualifier.isalpha():
                    # Case (e): 2-letter ISO country code
                    country_filter = candidate_qualifier.upper()
                    query_city = candidate_city
                    is_explicit_geography = True
                else:
                    # Case (f): Generic explicit geographic qualifier (e.g. "Park Street, London")
                    is_explicit_geography = True

        query_city_lower = query_city.lower()

        # Step 2: Strong India/place intelligence match (fresh session support)
        # When no explicit foreign qualifier was provided, match against prominent Indian localities
        is_prominent_india = False
        if not is_explicit_geography:
            if query_city_lower in INDIAN_PROMINENT_LOCALITIES:
                metro, state, cc = INDIAN_PROMINENT_LOCALITIES[query_city_lower]
                country_filter = cc
                metro_filter = metro.lower()
                state_filter = state
                is_prominent_india = True
                logger.debug(
                    "India prominent locality matched: '%s' → metro='%s', state='%s', country='IN'",
                    query_city, metro, state,
                )
            elif (
                context_location
                and context_location.country_code
                and query_city_lower not in INDIAN_METRO_QUALIFIERS
                and query_city_lower not in INDIAN_REGION_CENTERS
                and query_city_lower not in INDIAN_STATE_NAMES
            ):
                # Step 3: Use active session geographic context
                country_filter = context_location.country_code
                state_filter = context_location.state or context_location.admin1
                if context_location.city:
                    metro_filter = context_location.city.lower()
                logger.debug(
                    "Session context applied to '%s': country='%s', state='%s', metro='%s'",
                    query_city, country_filter, state_filter, metro_filter,
                )

        # Step 4: Canonicalize known city aliases (e.g. Bangalore → Bengaluru, Calcutta → Kolkata)
        if query_city_lower in INDIAN_CITY_ALIASES:
            target_city_name = INDIAN_CITY_ALIASES[query_city_lower]
        else:
            target_city_name = query_city

        # Cache key: build on canonical target name + active geographic constraints.
        # This prevents cross-context collisions (e.g. "Park Street" in Kolkata vs "Park Street, London")
        cache_key_str = f"{target_city_name}|{country_filter}|{state_filter}|{metro_filter}"
        cache_key = _normalize_cache_key(cache_key_str)

        # Cache lookup before any network I/O.
        cached = await _cache_get(cache_key)
        if cached is not None:
            logger.debug("Geocoding cache hit for '%s' (key=%s)", cleaned_name, cache_key)
            return cached

        # Step 5: Handle ambiguous state/region queries (e.g., "Kerala", "Goa", "Punjab")
        if query_city_lower in INDIAN_REGION_CENTERS and not is_explicit_geography:
            lat, lon, region_name, country_name, cc = INDIAN_REGION_CENTERS[query_city_lower]
            result = GeocodedLocationSchema(
                name=f"{region_name} (Region)",
                country=country_name,
                country_code=cc,
                admin1=region_name,
                state=region_name,
                latitude=lat,
                longitude=lon,
                timezone="Asia/Kolkata",
            )
            await _cache_set(cache_key, result)
            return result

        # Step 6: High-confidence India Locality Database match (Structured Dataset)
        # Enables instant, authoritative fresh-session resolution for urban localities/neighbourhoods
        # across 30+ major Indian cities with complete administrative hierarchy (locality, city, district,
        # subdivision, state, country, tz, lat/lon).
        if not is_explicit_geography or country_filter == "IN":
            ctx_c = metro_filter or (
                context_location.city if context_location and context_location.country_code == "IN" else None
            )
            ctx_s = state_filter or (
                (context_location.state or context_location.admin1)
                if context_location and context_location.country_code == "IN"
                else None
            )
            india_match = india_locality_service.find_locality(
                target_city_name,
                context_city=ctx_c,
                context_state=ctx_s,
            )
            if india_match is not None:
                logger.debug(
                    "India locality dataset hit: '%s' → %s (%s, %s)",
                    target_city_name, india_match.name, india_match.city, india_match.state,
                )
                await _cache_set(cache_key, india_match)
                return india_match

        # Step 7: Targeted Nominatim lookup for prominent Indian localities
        if is_prominent_india:
            nom_query = f"{target_city_name}, {metro_filter or state_filter}, India"
            nom_res = await self._query_nominatim(
                query=nom_query,
                country_code="in",
                target_city_name=target_city_name,
                cleaned_name=cleaned_name,
                cache_key=cache_key,
                state_hint=state_filter,
            )
            if nom_res is not None:
                return nom_res

        # Step 7: Primary global resolution via Open-Meteo Geocoding API
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

        # If country filter was applied, filter results strictly to that country.
        if country_filter:
            results = [
                r for r in results
                if (r.get("country_code") or "").upper() == country_filter.upper()
            ]

        if results:
            exact_matches = [
                r for r in results
                if r.get("name", "").strip().lower() == target_city_name.lower()
            ]
            any_matches = results  # already country-filtered

            top_result = None
            if state_filter:
                # Prefer exact-name results that also match the user's state
                state_exact = [
                    r for r in exact_matches
                    if (r.get("admin1") or "").strip().lower() == state_filter.lower()
                ]
                if state_exact:
                    state_exact.sort(key=lambda x: x.get("population") or 0, reverse=True)
                    top_result = state_exact[0]
                    logger.debug(
                        "State match (exact+state): '%s' in %s",
                        top_result.get("name"), top_result.get("admin1"),
                    )

                if top_result is None and exact_matches:
                    exact_matches.sort(key=lambda x: x.get("population") or 0, reverse=True)
                    top_result = exact_matches[0]

                if top_result is None:
                    state_any = [
                        r for r in any_matches
                        if (r.get("admin1") or "").strip().lower() == state_filter.lower()
                    ]
                    if state_any:
                        state_any.sort(key=lambda x: x.get("population") or 0, reverse=True)
                        top_result = state_any[0]

            if top_result is None:
                if exact_matches:
                    exact_matches.sort(key=lambda x: x.get("population") or 0, reverse=True)
                    top_result = exact_matches[0]
                else:
                    any_matches.sort(key=lambda x: x.get("population") or 0, reverse=True)
                    top_result = any_matches[0]

            resolved_name = top_result.get("name", cleaned_name)
            resolved_admin1 = top_result.get("admin1")
            resolved_country = top_result.get("country", "")

            if state_filter and resolved_admin1:
                parts = [resolved_name]
                if resolved_admin1 and resolved_admin1.lower() != resolved_name.lower():
                    parts.append(resolved_admin1)
                if resolved_country and resolved_country.lower() not in [p.lower() for p in parts]:
                    parts.append(resolved_country)
                display_name = ", ".join(parts)
            else:
                display_name = resolved_name

            tz = top_result.get("timezone", "UTC")
            if (top_result.get("country_code") or "").upper() == "IN":
                tz = "Asia/Kolkata"

            result = GeocodedLocationSchema(
                name=display_name,
                country=resolved_country,
                country_code=(top_result.get("country_code") or "").upper() or None,
                admin1=resolved_admin1,
                state=resolved_admin1,
                district=top_result.get("admin2"),
                subdivision=top_result.get("admin3"),
                city=top_result.get("name"),
                latitude=float(top_result["latitude"]),
                longitude=float(top_result["longitude"]),
                timezone=tz,
            )
            is_explicit_foreign = is_explicit_geography and bool(country_filter and country_filter != "IN")
            if not is_explicit_foreign and not india_locality_service.validate_administrative_hierarchy(result, target_city_name):
                logger.warning(
                    "Open-Meteo result '%s' failed administrative validation for '%s'",
                    result.name, target_city_name,
                )
            else:
                await _cache_set(cache_key, result)
                return result

        # Step 8: Global fallback to OpenStreetMap Nominatim
        nom_fallback_res = await self._query_nominatim(
            query=cleaned_name,
            country_code=country_filter,
            target_city_name=target_city_name,
            cleaned_name=cleaned_name,
            cache_key=cache_key,
            state_hint=state_filter,
        )
        if nom_fallback_res is None and (metro_filter or state_filter):
            nom_fallback_res = await self._query_nominatim(
                query=f"{target_city_name}, {metro_filter or state_filter}",
                country_code=country_filter,
                target_city_name=target_city_name,
                cleaned_name=cleaned_name,
                cache_key=cache_key,
                state_hint=state_filter,
            )
        if nom_fallback_res is not None:
            return nom_fallback_res

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

                district = address.get("state_district") or address.get("county")
                subdivision = address.get("county")

                return GeocodedLocationSchema(
                    name=name,
                    country=country,
                    country_code=(address.get("country_code") or "").upper() or None,
                    admin1=state,
                    state=state,
                    district=district,
                    subdivision=subdivision,
                    city=city,
                    locality=locality,
                    latitude=latitude,
                    longitude=longitude,
                    timezone="UTC",
                )
        except Exception as exc:
            logger.warning(f"Reverse geocoding lookup failed for ({latitude}, {longitude}): {exc}")

        return GeocodedLocationSchema(
            name=default_name,
            country="",
            country_code=None,
            admin1=None,
            latitude=latitude,
            longitude=longitude,
            timezone="UTC",
        )



geocoding_service = GeocodingService()
