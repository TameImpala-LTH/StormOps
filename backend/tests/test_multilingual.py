"""Comprehensive unit and integration tests for Multilingual WeatherGPT (Phase 17.3).

Tests cover:
1. 78 core multilingual query matrix (13 English, 13 Hindi, 13 Bengali, 13 Tamil, 13 Telugu, 13 Marathi).
2. Conversational persistence and language switching flows across all supported languages.
3. Language detection (Tamil, Telugu, Bengali, Devanagari Hindi vs Marathi, Code-mixing, explicit preference).
4. Location canonicalization for non-Latin Indian city names across scripts.
5. Localized deterministic fallback generation for missing locations, comparisons, and weather summaries in 6 languages.
"""

import app.core.compat  # noqa: F401
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.query import GeocodedLocationSchema
from app.schemas.weather import (
    CurrentWeather,
    CurrentWeatherResponse,
    ForecastResponse,
    HourlyForecast,
    LocationCoordinates,
)
from app.services.multilingual_service import multilingual_service
from app.services.query_service import SESSION_CONTEXT, extract_query_entities_rule_based, query_service

client = TestClient(app)

# Standard mock location and weather responses
MOCK_KOLKATA = GeocodedLocationSchema(
    name="Kolkata", country="India", admin1="West Bengal",
    latitude=22.5726, longitude=88.3639, timezone="Asia/Kolkata"
)
MOCK_MUMBAI = GeocodedLocationSchema(
    name="Mumbai", country="India", admin1="Maharashtra",
    latitude=19.0760, longitude=72.8777, timezone="Asia/Kolkata"
)
MOCK_DELHI = GeocodedLocationSchema(
    name="Delhi", country="India", admin1="Delhi",
    latitude=28.6139, longitude=77.2090, timezone="Asia/Kolkata"
)
MOCK_CHENNAI = GeocodedLocationSchema(
    name="Chennai", country="India", admin1="Tamil Nadu",
    latitude=13.0827, longitude=80.2707, timezone="Asia/Kolkata"
)
MOCK_HYDERABAD = GeocodedLocationSchema(
    name="Hyderabad", country="India", admin1="Telangana",
    latitude=17.3850, longitude=78.4867, timezone="Asia/Kolkata"
)
MOCK_PUNE = GeocodedLocationSchema(
    name="Pune", country="India", admin1="Maharashtra",
    latitude=18.5204, longitude=73.8567, timezone="Asia/Kolkata"
)

MOCK_CURRENT = CurrentWeatherResponse(
    location=LocationCoordinates(latitude=22.5726, longitude=88.3639, name="Kolkata", timezone="Asia/Kolkata"),
    current=CurrentWeather(
        temperature=28.0, feels_like=32.0, condition="Partly cloudy", weather_code=2,
        humidity=75, wind_speed=14.0, precipitation=0.0, precipitation_probability=20,
        time="2026-09-08T12:00",
    ),
    source="open-meteo",
    timestamp="2026-09-08T12:00:00Z",
)

MOCK_FORECAST = ForecastResponse(
    location=LocationCoordinates(latitude=22.5726, longitude=88.3639, name="Kolkata", timezone="Asia/Kolkata"),
    hourly=[
        HourlyForecast(
            time=f"2026-09-08T{h:02d}:00", temperature=28.0, condition="Partly cloudy", weather_code=2,
            precipitation_probability=20, precipitation=0.0, wind_speed=14.0,
        ) for h in range(24)
    ],
    source="open-meteo",
    timestamp="2026-09-08T12:00:00Z",
)


# =============================================================================
# PART 1: 78 Core Language Queries Matrix (13 per language x 6 languages)
# =============================================================================

ENGLISH_QUERIES = [
    ("What's the weather today?", "today", "weather_information"),
    ("What's today's weather forecast?", "today", "weather_information"),
    ("Will it rain today?", "today", "rain_query"),
    ("Should I carry an umbrella?", "today", "umbrella_recommendation"),
    ("Will it rain tomorrow?", "tomorrow", "rain_query"),
    ("What should I wear today?", "today", "clothing_recommendation"),
    ("Is it good to go outside today?", "today", "outdoor_activity_recommendation"),
    ("What's the weather like tonight?", "today", "weather_information"),
    ("How hot will it be tomorrow?", "tomorrow", "temperature_query"),
    ("What's the weather in Mumbai today?", "today", "weather_information"),
    ("How's the weather in Kolkata tomorrow morning?", "tomorrow", "weather_information"),
    ("Which is cooler, Delhi or Mumbai?", "today", "comparison"),
    ("Will the weather be good this weekend?", "weekend", "weather_information"),
]

HINDI_QUERIES = [
    ("आज का मौसम कैसा है?", "today", "weather_information"),
    ("आज का वेदर कैसा रहेगा?", "today", "weather_information"),
    ("आज बारिश होगी क्या?", "today", "rain_query"),
    ("क्या मुझे छाता लेकर जाना चाहिए?", "today", "umbrella_recommendation"),
    ("कल बारिश होगी क्या?", "tomorrow", "rain_query"),
    ("आज मुझे क्या पहनना चाहिए?", "today", "clothing_recommendation"),
    ("क्या आज बाहर जाना ठीक रहेगा?", "today", "outdoor_activity_recommendation"),
    ("आज रात मौसम कैसा रहेगा?", "today", "weather_information"),
    ("कल कितनी गर्मी होगी?", "tomorrow", "temperature_query"),
    ("मुंबई में आज मौसम कैसा है?", "today", "weather_information"),
    ("कल सुबह कोलकाता का मौसम कैसा रहेगा?", "tomorrow", "weather_information"),
    ("दिल्ली या मुंबई में कौन सा शहर ठंडा है?", "today", "comparison"),
    ("इस वीकेंड मौसम कैसा रहेगा?", "weekend", "weather_information"),
]

BENGALI_QUERIES = [
    ("আজকের আবহাওয়া কেমন?", "today", "weather_information"),
    ("আজকের ওয়েদার কেমন থাকবে?", "today", "weather_information"),
    ("আজ কি বৃষ্টি হবে?", "today", "rain_query"),
    ("আমার কি ছাতা নিয়ে যাওয়া উচিত?", "today", "umbrella_recommendation"),
    ("কাল কি বৃষ্টি হবে?", "tomorrow", "rain_query"),
    ("আজ কী পোশাক পরা উচিত?", "today", "clothing_recommendation"),
    ("আজ বাইরে যাওয়া কি ঠিক হবে?", "today", "outdoor_activity_recommendation"),
    ("আজ রাতে আবহাওয়া কেমন থাকবে?", "today", "weather_information"),
    ("কাল কতটা গরম হবে?", "tomorrow", "temperature_query"),
    ("মুম্বাইয়ের আজকের আবহাওয়া কেমন?", "today", "weather_information"),
    ("কাল সকালে কলকাতার আবহাওয়া কেমন থাকবে?", "tomorrow", "weather_information"),
    ("দিল্লি না মুম্বাই, কোনটা ঠান্ডা?", "today", "comparison"),
    ("এই উইকএন্ডে আবহাওয়া কেমন থাকবে?", "weekend", "weather_information"),
]

TAMIL_QUERIES = [
    ("இன்று வானிலை எப்படி இருக்கிறது?", "today", "weather_information"),
    ("இன்று சென்னையில் வானிலை எப்படி இருக்கிறது?", "today", "weather_information"),
    ("இன்று மழை பெய்யுமா?", "today", "rain_query"),
    ("குடை எடுத்துச் செல்ல வேண்டுமா?", "today", "umbrella_recommendation"),
    ("நாளை மழை பெய்யுமா?", "tomorrow", "rain_query"),
    ("இன்று என்ன ஆடை அணிய வேண்டும்?", "today", "clothing_recommendation"),
    ("இன்று வெளியில் செல்வது நல்லதா?", "today", "outdoor_activity_recommendation"),
    ("இன்று இரவு வானிலை எப்படி இருக்கும்?", "today", "weather_information"),
    ("நாளை எவ்வளவு வெப்பம் இருக்கும்?", "tomorrow", "temperature_query"),
    ("மதுரையில் இன்று வானிலை எப்படி?", "today", "weather_information"),
    ("நாளை காலை கோயம்புத்தூர் வானிலை எப்படி?", "tomorrow", "weather_information"),
    ("டெல்லி அல்லது மும்பை, எது குளிர்?", "today", "comparison"),
    ("இந்த வார இறுதி வானிலை எப்படி இருக்கும்?", "weekend", "weather_information"),
]

TELUGU_QUERIES = [
    ("ఈరోజు వాతావరణం ఎలా ఉంది?", "today", "weather_information"),
    ("ఈరోజు హైదరాబాద్‌లో వాతావరణం ఎలా ఉంది?", "today", "weather_information"),
    ("ఈరోజు వర్షం పడుతుందా?", "today", "rain_query"),
    ("నేను గొడుగు తీసుకెళ్లాలా?", "today", "umbrella_recommendation"),
    ("రేపు వర్షం పడుతుందా?", "tomorrow", "rain_query"),
    ("ఈరోజు ఏమి దుస్తులు ధరించాలి?", "today", "clothing_recommendation"),
    ("ఈరోజు బయటకు వెళ్లడం మంచిదేనా?", "today", "outdoor_activity_recommendation"),
    ("ఈ రాత్రి వాతావరణం ఎలా ఉంటుంది?", "today", "weather_information"),
    ("రేపు ఎంత వేడి ఉంటుంది?", "tomorrow", "temperature_query"),
    ("విశాఖపట్నం లో నేడు వాతావరణం ఎలా ఉంది?", "today", "weather_information"),
    ("రేపు ఉదయం విజయవాడ వాతావరణం ఎలా ఉంటుంది?", "tomorrow", "weather_information"),
    ("ఢిల్లీ లేదా ముంబై, ఏది చల్లగా ఉంటుంది?", "today", "comparison"),
    ("ఈ వారాంతంలో వాతావరణం ఎలా ఉంటుంది?", "weekend", "weather_information"),
]

MARATHI_QUERIES = [
    ("आज हवामान कसे आहे?", "today", "weather_information"),
    ("आज मुंबईचे हवामान कसे आहे?", "today", "weather_information"),
    ("आज पाऊस पडेल का?", "today", "rain_query"),
    ("मला छत्री घेऊन जावी का?", "today", "umbrella_recommendation"),
    ("उद्या पाऊस पडेल का?", "tomorrow", "rain_query"),
    ("आज कोणते कपडे घालावे?", "today", "clothing_recommendation"),
    ("आज बाहेर जाणे ठीक राहील का?", "today", "outdoor_activity_recommendation"),
    ("आज रात्री हवामान कसे राहील?", "today", "weather_information"),
    ("उद्या किती ऊन असेल?", "tomorrow", "temperature_query"),
    ("पुण्यात आज हवामान कसे आहे?", "today", "weather_information"),
    ("उद्या सकाळी नागपूरचे हवामान कसे राहील?", "tomorrow", "weather_information"),
    ("दिल्ली किंवा मुंबई, कोणते शहर थंड आहे?", "today", "comparison"),
    ("या वीकेंडला हवामान कसे राहील?", "weekend", "weather_information"),
]


@pytest.mark.parametrize("query,expected_date,expected_intent", ENGLISH_QUERIES)
def test_english_queries_matrix(query, expected_date, expected_intent):
    """Test 13 English natural language queries for language, date, and intent."""
    extracted = extract_query_entities_rule_based(query)
    assert extracted.language == "en"
    assert extracted.date_context == expected_date
    assert extracted.intent == expected_intent


@pytest.mark.parametrize("query,expected_date,expected_intent", HINDI_QUERIES)
def test_hindi_queries_matrix(query, expected_date, expected_intent):
    """Test 13 Hindi natural language queries for language, date, and intent."""
    extracted = extract_query_entities_rule_based(query)
    assert extracted.language == "hi"
    assert extracted.date_context == expected_date
    assert extracted.intent == expected_intent


@pytest.mark.parametrize("query,expected_date,expected_intent", BENGALI_QUERIES)
def test_bengali_queries_matrix(query, expected_date, expected_intent):
    """Test 13 Bengali natural language queries for language, date, and intent."""
    extracted = extract_query_entities_rule_based(query)
    assert extracted.language == "bn"
    assert extracted.date_context == expected_date
    assert extracted.intent == expected_intent


@pytest.mark.parametrize("query,expected_date,expected_intent", TAMIL_QUERIES)
def test_tamil_queries_matrix(query, expected_date, expected_intent):
    """Test 13 Tamil natural language queries for language, date, and intent."""
    extracted = extract_query_entities_rule_based(query)
    assert extracted.language == "ta"
    assert extracted.date_context == expected_date
    assert extracted.intent == expected_intent


@pytest.mark.parametrize("query,expected_date,expected_intent", TELUGU_QUERIES)
def test_telugu_queries_matrix(query, expected_date, expected_intent):
    """Test 13 Telugu natural language queries for language, date, and intent."""
    extracted = extract_query_entities_rule_based(query)
    assert extracted.language == "te"
    assert extracted.date_context == expected_date
    assert extracted.intent == expected_intent


@pytest.mark.parametrize("query,expected_date,expected_intent", MARATHI_QUERIES)
def test_marathi_queries_matrix(query, expected_date, expected_intent):
    """Test 13 Marathi natural language queries for language, date, and intent."""
    extracted = extract_query_entities_rule_based(query)
    assert extracted.language == "mr"
    assert extracted.date_context == expected_date
    assert extracted.intent == expected_intent


# =============================================================================
# PART 2: Language Persistence & Switching Flows
# =============================================================================

@pytest.mark.asyncio
async def test_conversational_flow_1_english_persistence():
    """English -> English follow-up preserves location and English language."""
    session = "sess_flow_en_en"
    SESSION_CONTEXT.pop(session, None)

    with patch("app.services.query_service.llm_service.extract_structured_intent", return_value=None), \
         patch("app.services.query_service.llm_service.generate_grounded_response", return_value=None), \
         patch("app.services.query_service.geocoding_service.geocode_location", return_value=MOCK_KOLKATA), \
         patch("app.services.weather_service.weather_service.get_current_weather", return_value=MOCK_CURRENT), \
         patch("app.services.weather_service.weather_service.get_forecast", return_value=MOCK_FORECAST):

        r1 = await query_service.process_query("What's the weather in Kolkata?", session_id=session)
        assert r1.language == "en"
        assert r1.location.name == "Kolkata"

        r2 = await query_service.process_query("Will it rain tomorrow?", session_id=session)
        assert r2.language == "en"
        assert r2.location.name == "Kolkata"
        assert r2.query.date_context == "tomorrow"


@pytest.mark.asyncio
async def test_conversational_flow_2_hindi_persistence():
    """Hindi -> Hindi follow-up preserves location and Hindi language."""
    session = "sess_flow_hi_hi"
    SESSION_CONTEXT.pop(session, None)

    with patch("app.services.query_service.llm_service.extract_structured_intent", return_value=None), \
         patch("app.services.query_service.llm_service.generate_grounded_response", return_value=None), \
         patch("app.services.query_service.geocoding_service.geocode_location", return_value=MOCK_KOLKATA), \
         patch("app.services.weather_service.weather_service.get_current_weather", return_value=MOCK_CURRENT), \
         patch("app.services.weather_service.weather_service.get_forecast", return_value=MOCK_FORECAST):

        r1 = await query_service.process_query("कोलकाता में आज मौसम कैसा है?", session_id=session)
        assert r1.language == "hi"
        assert r1.location.name == "Kolkata"

        r2 = await query_service.process_query("कल बारिश होगी क्या?", session_id=session)
        assert r2.language == "hi"
        assert r2.location.name == "Kolkata"
        assert r2.query.date_context == "tomorrow"


@pytest.mark.asyncio
async def test_conversational_flow_3_bengali_persistence():
    """Bengali -> Bengali follow-up preserves location and Bengali language."""
    session = "sess_flow_bn_bn"
    SESSION_CONTEXT.pop(session, None)

    with patch("app.services.query_service.llm_service.extract_structured_intent", return_value=None), \
         patch("app.services.query_service.llm_service.generate_grounded_response", return_value=None), \
         patch("app.services.query_service.geocoding_service.geocode_location", return_value=MOCK_KOLKATA), \
         patch("app.services.weather_service.weather_service.get_current_weather", return_value=MOCK_CURRENT), \
         patch("app.services.weather_service.weather_service.get_forecast", return_value=MOCK_FORECAST):

        r1 = await query_service.process_query("আজ কলকাতার আবহাওয়া কেমন?", session_id=session)
        assert r1.language == "bn"
        assert r1.location.name == "Kolkata"

        r2 = await query_service.process_query("কাল কি বৃষ্টি হবে?", session_id=session)
        assert r2.language == "bn"
        assert r2.location.name == "Kolkata"
        assert r2.query.date_context == "tomorrow"


@pytest.mark.asyncio
async def test_conversational_flow_tamil_persistence():
    """Tamil -> Tamil follow-up preserves location and Tamil language."""
    session = "sess_flow_ta_ta"
    SESSION_CONTEXT.pop(session, None)

    with patch("app.services.query_service.llm_service.extract_structured_intent", return_value=None), \
         patch("app.services.query_service.llm_service.generate_grounded_response", return_value=None), \
         patch("app.services.query_service.geocoding_service.geocode_location", return_value=MOCK_CHENNAI), \
         patch("app.services.weather_service.weather_service.get_current_weather", return_value=MOCK_CURRENT), \
         patch("app.services.weather_service.weather_service.get_forecast", return_value=MOCK_FORECAST):

        r1 = await query_service.process_query("இன்று சென்னையில் வானிலை எப்படி இருக்கிறது?", session_id=session)
        assert r1.language == "ta"
        assert r1.location.name == "Chennai"

        r2 = await query_service.process_query("நாளை மழை பெய்யுமா?", session_id=session)
        assert r2.language == "ta"
        assert r2.location.name == "Chennai"
        assert r2.query.date_context == "tomorrow"


@pytest.mark.asyncio
async def test_conversational_flow_telugu_persistence():
    """Telugu -> Telugu follow-up preserves location and Telugu language."""
    session = "sess_flow_te_te"
    SESSION_CONTEXT.pop(session, None)

    with patch("app.services.query_service.llm_service.extract_structured_intent", return_value=None), \
         patch("app.services.query_service.llm_service.generate_grounded_response", return_value=None), \
         patch("app.services.query_service.geocoding_service.geocode_location", return_value=MOCK_HYDERABAD), \
         patch("app.services.weather_service.weather_service.get_current_weather", return_value=MOCK_CURRENT), \
         patch("app.services.weather_service.weather_service.get_forecast", return_value=MOCK_FORECAST):

        r1 = await query_service.process_query("ఈరోజు హైదరాబాద్‌లో వాతావరణం ఎలా ఉంది?", session_id=session)
        assert r1.language == "te"
        assert r1.location.name == "Hyderabad"

        r2 = await query_service.process_query("రేపు వర్షం పడుతుందా?", session_id=session)
        assert r2.language == "te"
        assert r2.location.name == "Hyderabad"
        assert r2.query.date_context == "tomorrow"


@pytest.mark.asyncio
async def test_conversational_flow_marathi_persistence():
    """Marathi -> Marathi follow-up preserves location and Marathi language."""
    session = "sess_flow_mr_mr"
    SESSION_CONTEXT.pop(session, None)

    with patch("app.services.query_service.llm_service.extract_structured_intent", return_value=None), \
         patch("app.services.query_service.llm_service.generate_grounded_response", return_value=None), \
         patch("app.services.query_service.geocoding_service.geocode_location", return_value=MOCK_MUMBAI), \
         patch("app.services.weather_service.weather_service.get_current_weather", return_value=MOCK_CURRENT), \
         patch("app.services.weather_service.weather_service.get_forecast", return_value=MOCK_FORECAST):

        r1 = await query_service.process_query("आज मुंबईचे हवामान कसे आहे?", session_id=session)
        assert r1.language == "mr"
        assert r1.location.name == "Mumbai"

        r2 = await query_service.process_query("उद्या पाऊस पडेल का?", session_id=session)
        assert r2.language == "mr"
        assert r2.location.name == "Mumbai"
        assert r2.query.date_context == "tomorrow"


@pytest.mark.asyncio
async def test_conversational_flow_switch_tamil_to_marathi():
    """Language switch from Tamil to Marathi retains location context."""
    session = "sess_flow_switch_ta_mr"
    SESSION_CONTEXT.pop(session, None)

    with patch("app.services.query_service.llm_service.extract_structured_intent", return_value=None), \
         patch("app.services.query_service.llm_service.generate_grounded_response", return_value=None), \
         patch("app.services.query_service.geocoding_service.geocode_location", return_value=MOCK_PUNE), \
         patch("app.services.weather_service.weather_service.get_current_weather", return_value=MOCK_CURRENT), \
         patch("app.services.weather_service.weather_service.get_forecast", return_value=MOCK_FORECAST):

        r1 = await query_service.process_query("புனே வானிலை எப்படி?", session_id=session)
        assert r1.language == "ta"

        r2 = await query_service.process_query("उद्या पाऊस पडेल का?", session_id=session)
        assert r2.language == "mr"
        assert r2.location.name == "Pune"
        assert r2.query.date_context == "tomorrow"

# =============================================================================
# PART 3: Location Canonicalization & Localized Fallbacks
# =============================================================================

def test_location_canonicalization():
    """Verify non-Latin Indian script locations convert cleanly across all 6 languages."""
    # Hindi & Bengali
    assert multilingual_service.canonicalize_known_location("कोलकाता") == "Kolkata"
    assert multilingual_service.canonicalize_known_location("কলকাতা") == "Kolkata"
    assert multilingual_service.canonicalize_known_location("मुंबई") == "Mumbai"
    assert multilingual_service.canonicalize_known_location("দিল্লি") == "Delhi"

    # Tamil
    assert multilingual_service.canonicalize_known_location("சென்னை") == "Chennai"
    assert multilingual_service.canonicalize_known_location("சென்னையில்") == "Chennai"
    assert multilingual_service.canonicalize_known_location("மதுரை") == "Madurai"
    assert multilingual_service.canonicalize_known_location("கோயம்புத்தூர்") == "Coimbatore"

    # Telugu
    assert multilingual_service.canonicalize_known_location("హైదరాబాద్") == "Hyderabad"
    assert multilingual_service.canonicalize_known_location("హైదరాబాద్‌లో") == "Hyderabad"
    assert multilingual_service.canonicalize_known_location("విశాఖపట్నం") == "Visakhapatnam"
    assert multilingual_service.canonicalize_known_location("విజయవాడ") == "Vijayawada"

    # Marathi
    assert multilingual_service.canonicalize_known_location("पुण्यात") == "Pune"
    assert multilingual_service.canonicalize_known_location("मुंबईचे") == "Mumbai"
    assert multilingual_service.canonicalize_known_location("नागपूर") == "Nagpur"
    assert multilingual_service.canonicalize_known_location("नाशिक") == "Nashik"


def test_localized_clarifications_all_six():
    """Verify clarification strings render correctly in all 6 languages."""
    assert "Which location" in multilingual_service.get_localized_clarification("en")
    assert "स्थान" in multilingual_service.get_localized_clarification("hi")
    assert "আবহাওয়া" in multilingual_service.get_localized_clarification("bn")
    assert "வானிலை" in multilingual_service.get_localized_clarification("ta")
    assert "వాతావరణ" in multilingual_service.get_localized_clarification("te")
    assert "हवामान" in multilingual_service.get_localized_clarification("mr")

    assert "compare" in multilingual_service.get_localized_comparison_clarification("en")
    assert "तुलना" in multilingual_service.get_localized_comparison_clarification("hi")
    assert "তুলনা" in multilingual_service.get_localized_comparison_clarification("bn")
    assert "ஒப்பிட" in multilingual_service.get_localized_comparison_clarification("ta")
    assert "పోల్చ" in multilingual_service.get_localized_comparison_clarification("te")
    assert "तुलना" in multilingual_service.get_localized_comparison_clarification("mr")


def test_code_mixing_detection():
    """Verify code-mixed queries are recognized for respective languages."""
    assert multilingual_service.detect_language("Aaj Kolkata mein baarish hogi kya?") == "hi"
    assert multilingual_service.detect_language("Kolkata-te ajke brishti hobe?") == "bn"
    assert multilingual_service.detect_language("Chennai weather epdi irukku?") == "ta"
    assert multilingual_service.detect_language("Hyderabad lo rain padutunda?") == "te"
    assert multilingual_service.detect_language("Mumbai cha weather kasa aahe?") == "mr"
    assert multilingual_service.detect_language("What's the weather in Mumbai?") == "en"


def test_explicit_preference_priority():
    """Verify explicit preference takes priority over auto detection unless auto is specified."""
    assert multilingual_service.detect_language("What is the weather?", explicit_pref="ta") == "ta"
    assert multilingual_service.detect_language("What is the weather?", explicit_pref="te") == "te"
    assert multilingual_service.detect_language("What is the weather?", explicit_pref="mr") == "mr"
    assert multilingual_service.detect_language("இன்று வானிலை?", explicit_pref="auto") == "ta"
    assert multilingual_service.detect_language("ఈరోజు వాతావరణం?", explicit_pref="auto") == "te"
    assert multilingual_service.detect_language("आज हवामान कसे आहे?", explicit_pref="auto") == "mr"


def test_invalid_language_fallback():
    """Verify unsupported/invalid language gracefully falls back to 'en'."""
    assert multilingual_service.normalize_language("invalid_lang") == "en"
    assert multilingual_service.normalize_language(None) == "en"
