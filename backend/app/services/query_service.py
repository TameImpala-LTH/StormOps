"""Query understanding, entity extraction, session context, and orchestration service."""

import asyncio
from datetime import datetime, timezone
import logging
import re
from typing import Any, Dict, Optional
from fastapi import HTTPException

logger = logging.getLogger(__name__)

from app.schemas.decision import DecisionResponse
from app.schemas.query import ExtractedQueryInfo, GeocodedLocationSchema, QueryResponse, TargetPeriodWeather, WeatherPeriodInfo
from app.services.alert_service import alert_engine_service
from app.services.comparison_service import comparison_engine_service
from app.services.decision_service import decision_engine_service
from app.services.event_service import event_service
from app.services.geocoding_service import geocoding_service
from app.services.llm_service import llm_service
from app.services.multilingual_service import multilingual_service
from app.services.weather_service import weather_service

# Lightweight in-memory session storage (session_id -> {"location": GeocodedLocationSchema, "last_decision": DecisionResponse, "last_query": ExtractedQueryInfo, "last_weather": dict, "language": str})
SESSION_CONTEXT: Dict[str, Dict[str, Any]] = {}


INVALID_LOCATIONS = {
    "today", "tomorrow", "tonight", "this", "now", "right", "evening", "morning", "afternoon", "current",
    "then", "there", "wear", "clothes", "jacket", "coat", "pack", "dress", "bring", "take", "walk", "hike",
    "run", "drive", "trip", "outdoor", "activities", "better", "which", "should", "i", "travel", "to", "visit",
    "where", "place", "has", "less", "more", "rain", "cooler", "warmer", "colder", "hotter", "temperature",
    "weekend", "saturday", "sunday", "go", "my location", "my", "location", "current location", "my current location",
    "on my exact location", "my exact location", "exact location", "me", "here",
    "wind", "winds", "breeze", "humidity", "cloud", "clouds", "sun", "sunny", "storm", "chilly", "warm",
    "degrees", "celsius", "forecast", "conditions", "weather", "mausam", "kaisa", "kaisi", "kaise", "hai", "hain", "mein",
    # Hindi stop words
    "आज", "कल", "रात", "सुबह", "दोपहर", "शाम", "बारिश", "छाता", "कपड़े", "मौसम", "क्या", "कहाँ", "कहा", "यहाँ",
    "वहाँ", "मेरा", "मेरी", "स्थान", "शहर", "ठंडा", "गर्म", "तुलना", "जाना", "घूमना", "वेदर", "होगी", "होगा", "होने",
    "है", "हैं", "था", "थी", "लेकर", "चाहिए", "बाहर", "ठीक", "कैसा", "कैसी", "कितना", "कितनी", "गर्मी", "सर्दी", "ठंड",
    "बताओ", "बताइए", "दिखाओ", "की", "का", "के", "में", "से", "पर", "ने", "को", "रहेगा", "रहेगी", "जाए", "सकते",
    # Bengali stop words
    "आज", "আজকে", "কাল", "কালকে", "রাত", "রাতে", "সকাল", "সকালে", "দুপুর", "দুপুরে", "সন্ধ্যা", "সন্ধ্যায়",
    "বৃষ্টি", "ছাতা", "পোশাক", "আবহাওয়া", "ওয়েদার", "কি", "কী", "কোথায়", "এখানে", "সেখানে", "আমার", "স্থান",
    "শহর", "ঠান্ডা", "গরম", "তুলনা", "যাওয়া", "যাব", "হবে", "থাকবে", "উচিত", "নিয়ে", "বাইরে", "কেমন", "কতটা",
    "বলুন", "দেখান", "এর", "তে", "এ", "না", "বা", "পরা",
    # Tamil stop words
    "இன்று", "நாளை", "இரவு", "காலை", "மதியம்", "மாலை", "மழை", "குடை", "ஆடை", "உடை", "வானிலை",
    "எப்படி", "இருக்கிறது", "இருக்கு", "பெய்யுமா", "வருமா", "எடுத்துச்", "செல்ல", "வேண்டுமா", "என்ன",
    "வேண்டும்", "அணிய", "வெளியில்", "செல்லலாமா", "போகலாமா", "பயணம்", "வெப்பநிலை", "வெயில்", "குளிர்",
    "ஏன்", "காரணம்", "ஒப்பிட", "எந்த", "இடம்", "நகரம்", "எனது", "இருப்பிடம்",
    # Telugu stop words
    "ఈరోజు", "రేపు", "రాత్రి", "ఉదయం", "మధ్యాహ్నం", "సాయంత్రం", "వర్షం", "గొడుగు", "దుస్తులు", "బట్టలు",
    "వాతావరణం", "ఎలా", "ఉంది", "పడుతుంది", "పడుతుందా", "తీసుకెళ్లాలా", "ఏమి", "ధరించాలి", "వేసుకోవాలి",
    "బయటకు", "వెళ్లవచ్చా", "వెళ్లాలా", "ప్రయాణం", "ఉష్ణోగ్రత", "వేడి", "చలి", "ఎండ", "ఎందుకు", "కారణం",
    "పోల్చండి", "ఏ", "ప్రదేశం", "నగరం", "నా", "లొకేషన్",
    # Marathi stop words
    "आज", "उद्या", "रात्री", "सकाळी", "दुपारी", "संध्याकाळी", "पाऊस", "छत्री", "कपडे", "हवामान",
    "कसे", "कसा", "कशी", "आहे", "पडेल", "घेऊन", "जावी", "काय", "घालावे", "घालायचे", "बाहेर",
    "पडावे", "जावे", "प्रवास", "तापमान", "थंडी", "ऊन", "का", "कारण", "तुलना", "कोणते", "ठिकाण", "शहर",
    "माझे", "स्थान",
}




def extract_query_entities_rule_based(query: str, language_hint: Optional[str] = "auto") -> ExtractedQueryInfo:
    """Fallback deterministic rule-based entity extraction supporting English, Hindi, and Bengali."""
    text = query.strip()
    lower_text = text.lower()
    detected_lang = multilingual_service.detect_language(text, explicit_pref=language_hint)

    extracted_location_a: Optional[str] = None
    extracted_location_b: Optional[str] = None
    comparison_goal: Optional[str] = None

    # Check comparison intent (English, Hindi, Bengali, Hinglish)
    is_comparison_query = False
    comp_keywords = [
        "compare", " vs ", " versus ", " better for ", " difference between ",
        "which place", "which location", "which city", "which is better",
        "less rain", "warmer", "cooler", "colder", "hotter", "where should i go",
        "तुलना", "তুলনা", "ஒப்பிட", "போల్చండి", "तुलना करा", "कौन सा शहर", "কোনটা", "কোন শহর", "எந்த நகரம்", "ఏ నగరం"
    ]
    if any(k in lower_text or k in text for k in comp_keywords):
        is_comparison_query = True
    elif any(k in text for k in [" या ", " ना ", " বা ", " அல்லது ", " அல்லது", " அல்லது ", " లేదా ", " లేదా", " किंवा ", " किंवा"]) and any(k in text or k in lower_text for k in ["ठंडा", "ঠান্ডা", "குளிர்", "చల్లగా", "चల్లగా", "थंड", "गर्म", "গরম", "வெப்பம்", "వేడి", "barish", "brishti", "should i", "which", "better"]):
        is_comparison_query = True
    elif " or " in lower_text and any(k in lower_text for k in ["should i", "visit", "go to", "travel to", "which", "prefer", "better", "choose", "where"]):
        is_comparison_query = True

    # Date Extraction (English, Hindi, Bengali, Tamil, Telugu, Marathi)
    if any(k in lower_text for k in ["weekend", "saptahant"]) or any(k in text for k in ["वीकेंड", "উইকএন্ড", "সप्ताहান্ত", "வார இறுதி", "వారాంతంలో", "వారాంతం", "या वीकेंडला"]):
        date_context = "weekend"
    elif any(k in lower_text for k in ["saturday", "shanivar"]) or any(k in text for k in ["शनिवार", "শনিবার", "சனிக்கிழமை", "శనివారం"]):
        date_context = "saturday"
    elif any(k in lower_text for k in ["sunday", "ravivar"]) or any(k in text for k in ["रविवार", "রবিবার", "ஞாயிற்றுக்கிழமை", "ఆదివారం"]):
        date_context = "sunday"
    elif any(k in text for k in ["कल", "কাল", "நாளை", "రేపు", "उद्या"]) or any(re.search(r"\b" + re.escape(w) + r"\b", lower_text) for w in ["tomorrow", "kal", "kalke", "repu", "udya", "naalaikku"]):
        date_context = "tomorrow"
    else:
        date_context = "today"

    # Time Period Extraction
    if any(k in text for k in ["रात", "রাত", "இரவு", "రాత్రి", "रात्री"]) or any(re.search(r"\b" + re.escape(w) + r"\b", lower_text) for w in ["tonight", "night", "raat", "iravu", "ratri"]):
        time_period = "tonight"
    elif any(k in text for k in ["शाम", "সন্ধ্যা", "সন্ধ্যে", "மாலை", "సాయంత్రం", "संध्याकाळी"]) or "evening" in lower_text:
        time_period = "evening"
    elif any(k in text for k in ["सुबह", "সকাল", "সকালে", "காலை", "ఉదయం", "सकाळी"]) or any(re.search(r"\b" + re.escape(w) + r"\b", lower_text) for w in ["morning", "subah", "shokal", "kaalai", "udayam", "sakali"]):
        time_period = "morning"
    elif any(k in text for k in ["दोपहर", "দুপুর", "দুপুরে", "மதியம்", "மத்தியானம்", "మధ్యాహ్నం", "दुपारी"]) or "afternoon" in lower_text:
        time_period = "afternoon"
    elif any(k in text for k in ["अभी", "এখন", "இப்போது", "ఇప్పుడు", "आता"]) or any(w in lower_text for w in ["now", "right now"]):
        time_period = "now"
    else:
        time_period = "current"

    def clean_loc(loc: Optional[str]) -> Optional[str]:
        if not loc:
            return None
        loc_clean = re.sub(
            r"\b(?:should|i|go|visit|travel|fly|drive|head|pack|to|is|better|for|outdoor|activities|in|at|near|the|where|place|has|cooler|warmer|colder|hotter|temperature|tomorrow|today|tonight|this|evening|morning|afternoon|weekend|saturday|sunday|mein|me|ka|te|er|r)\b",
            "",
            loc,
            flags=re.IGNORECASE,
        ).strip()
        loc_clean = re.sub(r"\s+", " ", loc_clean)
        loc_clean = re.sub(r"^[^\w\u0900-\u0D7F]+|[^\w\u0900-\u0D7F]+$", "", loc_clean).strip()
        loc_clean = loc_clean.rstrip(",").strip()
        canonical = multilingual_service.canonicalize_known_location(loc_clean)
        if not canonical or canonical.lower() in INVALID_LOCATIONS:
            return None
        return canonical

    if is_comparison_query:
        intent = "comparison"
        if any(k in lower_text or k in text for k in ["travel", "trip", "visit", "go to", "vacation", "where should i go", "घूमना", "ভ্রমণ"]):
            comparison_goal = "travel"
        elif any(k in lower_text or k in text for k in ["outdoor", "walk", "hike", "sports", "outside", "run", "event", "बाहर", "বাইরে"]):
            comparison_goal = "outdoor_activity"
        elif any(k in lower_text or k in text for k in ["rain", "precipitation", "shower", "dry", "drizzle", "बारिश", "বৃষ্টি", "baarish", "brishti"]):
            comparison_goal = "rain"
        elif any(k in lower_text or k in text for k in ["cooler", "colder", "cool", "cold", "chilly", "ठंडा", "ঠান্ডা", "குளிர்", "చల్లగా", "थंड", "thanda"]):
            comparison_goal = "cooler"
        elif any(k in lower_text or k in text for k in ["warmer", "hotter", "warm", "hot", "heat", "गर्म", "গরম", "garmi", "gorom"]):
            comparison_goal = "warmer"
        elif any(k in lower_text or k in text for k in ["temp", "temperature", "तापमान", "तापমাত্রা"]):
            comparison_goal = "temperature"
        else:
            comparison_goal = "general"

        # Check known transliterated Indian cities in the query
        found_cities = []
        for raw_name in multilingual_service.KNOWN_LOCATION_TRANSLITERATIONS:
            if raw_name in text:
                canonical = multilingual_service.KNOWN_LOCATION_TRANSLITERATIONS[raw_name]
                if canonical not in found_cities:
                    found_cities.append(canonical)

        if len(found_cities) >= 2:
            extracted_location_a = found_cities[0]
            extracted_location_b = found_cities[1]
        else:
            # Regex patterns for dual location extraction
            m1 = re.search(
                r",\s*([A-Za-z\u0900-\u0D7F\s\.\-']+?)\s+(?:or|and|vs|versus|या|ना|বা|அல்லது|లేదా|किंवा)\s+([A-Za-z\u0900-\u0D7F\s\.\-']+?)(?=\s+(?:today|tomorrow|tonight|this|now|right|evening|morning|afternoon|weekend|saturday|sunday|आज|कल|रात|सुबह|আজ|কাল)|[\?\!\.\,]|\s*$)",
                text, re.IGNORECASE
            )
            if m1:
                extracted_location_a = m1.group(1).strip()
                extracted_location_b = m1.group(2).strip()
            else:
                m2 = re.search(
                    r"\b(?:compare|तुलना)\s+([A-Za-z\u0900-\u0D7F\s\.\-']+?)\s+(?:and|vs|versus|with|to|और|ओर|এবং)\s+([A-Za-z\u0900-\u0D7F\s\.\-']+?)(?=\s+(?:today|tomorrow|tonight|this|now|right|evening|morning|afternoon|weekend|saturday|sunday|आज|कल|रात|सुबह|আজ|কাল)|[\?\!\.\,]|\s*$)",
                    text, re.IGNORECASE
                )
                if m2:
                    extracted_location_a = m2.group(1).strip()
                    extracted_location_b = m2.group(2).strip()
                else:
                    m3 = re.search(
                        r"([A-Za-z\u0900-\u0D7F\s\.\-']+?)\s+(?:or|vs|versus|या|ना|বা|அல்லது|లేదా|किंवा)\s+([A-Za-z\u0900-\u0D7F\s\.\-']+?)(?=\s+(?:today|tomorrow|tonight|this|now|right|evening|morning|afternoon|weekend|saturday|sunday|आज|कल|रात|सुबह|আজ|কাল)|[\?\!\.\,]|\s*$)",
                        text, re.IGNORECASE
                    )
                    if m3:
                        extracted_location_a = m3.group(1).strip()
                        extracted_location_b = m3.group(2).strip()

        extracted_location_a = clean_loc(extracted_location_a)
        extracted_location_b = clean_loc(extracted_location_b)

        return ExtractedQueryInfo(
            original_query=text,
            intent=intent,
            extracted_location=extracted_location_a,
            extracted_location_a=extracted_location_a,
            extracted_location_b=extracted_location_b,
            comparison_goal=comparison_goal,
            date_context=date_context,
            time_period=time_period,
            language=detected_lang,
        )

    # Single-Location Intent Classification
    if any(k in text for k in ["क्यों", "কেন", "ஏன்", "எందుకు", "का बरं", "कशासाठी", "कारण"]) or any(lower_text.startswith(k) or f" {k}" in lower_text for k in ["why", "explain", "reason"]):
        intent = "ai_explain"
    elif any(k in text for k in ["छाता", "ছাতা", "குடை", "గొడుగు", "छत्री"]) or any(k in lower_text for k in ["umbrella", "raincoat", "waterproof", "chata", "kudai", "godugu", "chhatri"]):
        intent = "umbrella_recommendation"
    elif any(k in text for k in ["बाहर जाना", "बाहर", "বাইরে যাওয়া", "বাইরে", "வெளியில்", "வெளியே", "బయటకు", "బయట", "बाहेर जाणे", "बाहेर"]) or any(k in lower_text for k in ["walk", "run", "outdoor", "event", "postpone", "hike", "sports", "outside", "bahar", "baire"]):
        intent = "outdoor_activity_recommendation"
    elif any(k in text for k in ["यात्रा", "सफ़र", "ভ্রমণ", "பயணம்", "பிரயாணம்", "ప్రయాణం", "प्रवास", "सफर"]) or any(k in lower_text for k in ["travel", "drive", "flight", "road", "trip", "safe", "yatra"]):
        intent = "travel_recommendation"
    elif any(k in text for k in ["कपड़े", "कपड़ा", "पहनना", "पहन", "पोশাক", "পরা", "ஜামা", "ஆடை", "உடை", "அணிய", "దుస్తులు", "బట్టలు", "ధరించాలి", "వేసుకోవాలి", "घालावे", "घालायचे"]) or any(k in lower_text for k in ["jacket", "coat", "wear", "clothes", "sweater", "warm", "pehenna", "poshak"]):
        intent = "clothing_recommendation"
    elif any(k in text for k in ["बारिश", "बरसात", "বৃষ্টি", "மழை", "தூறல்", "వర్షం", "వాన", "पाऊस", "वृष्टी"]) or any(k in lower_text for k in ["rain", "precipitation", "shower", "drizzle", "downpour", "baarish", "barish", "brishti", "mazhai", "varsham", "paus"]):
        intent = "rain_query"
    elif any(k in text for k in ["गर्मी", "ठंड", "तापमान", "तापমাত্রা", "ঠান্ডা", "গরম", "வெப்பநிலை", "வெப்பம்", "வெயில்", "குளிர்", "சூடு", "ఉష్ణోగ్రత", "వేడి", "చలి", "చల్లగా", "ఎండ", "थंडी", " ऊन", "ऊन "]) or any(k in lower_text for k in ["hot", "cold", "temperature", "degrees", "chilly", "heat", "garmi", "gorom", "thanda"]):
        intent = "temperature_query"
    else:
        intent = "weather_information"

    # Check known transliterated Indian cities in the query
    extracted_location: Optional[str] = None
    for raw_name in multilingual_service.KNOWN_LOCATION_TRANSLITERATIONS:
        if raw_name in text:
            extracted_location = multilingual_service.KNOWN_LOCATION_TRANSLITERATIONS[raw_name]
            break

    # Primary preposition extraction (preserves full location phrases including commas: "Park Street, London", "Newtown, West Bengal")
    if not extracted_location:
        loc_matches = re.findall(
            r"\b(?:in|at|near|about|में|এ|তে)\s+([A-Za-z\u0900-\u0D7F\s\.\-',]+?)(?=\s+(?:today|tomorrow|tonight|this|now|right\s+now|right|evening|morning|afternoon|weekend|saturday|sunday|आज|कल|रात|सुबह|আজ|কাল)\b|[\?\!;]|\s*$)",
            text,
            re.IGNORECASE,
        )
        if loc_matches:
            candidate = clean_loc(loc_matches[-1].strip().rstrip(","))
            if candidate and candidate.lower() not in INVALID_LOCATIONS:
                extracted_location = candidate

    # Post-position extraction (e.g. "Kolkata mein", "Park Street, London mein")
    if not extracted_location:
        post_matches = re.findall(
            r"\b([A-Za-z\u0900-\u0D7F\s\.\-',]+?)\s+(?:mein|me|में|এ|তে)\b",
            text,
            re.IGNORECASE,
        )
        if post_matches:
            candidate = clean_loc(post_matches[-1].strip().rstrip(","))
            if candidate and candidate.lower() not in INVALID_LOCATIONS:
                extracted_location = candidate

    # Secondary preposition extraction ("for <Loc>", "to <Loc>")
    if not extracted_location:
        secondary_matches = list(
            re.finditer(
                r"\b(for|to)\s+([A-Za-z\u0900-\u0D7F\s\.\-',]+?)(?=\s+(?:today|tomorrow|tonight|this|now|right\s+now|right|evening|morning|afternoon|weekend|saturday|sunday)\b|[\?\!;]|\s*$)",
                text,
                re.IGNORECASE,
            )
        )
        valid_candidates = []
        for m in secondary_matches:
            prep = m.group(1).lower()
            val = m.group(2).strip().rstrip(",")
            if prep == "to" and re.match(
                r"^(go|carry|visit|take|walk|travel|fly|drive|have|do|see|pack|head|run|wear)\b", val, re.IGNORECASE
            ):
                continue
            if prep == "for" and re.match(
                r"^(a|an|the)?\s*(walk|run|hike|drive|trip|event|picnic|stroll|outing)\b", val, re.IGNORECASE
            ):
                continue
            if val.lower() not in INVALID_LOCATIONS:
                valid_candidates.append(val)
        if valid_candidates:
            extracted_location = clean_loc(valid_candidates[-1])

    # Prefix location extraction ("<Location> weather", "<Location> forecast")
    if not extracted_location:
        prefix_matches = re.findall(
            r"^\s*([A-Za-z\u0900-\u0D7F\s\.\-',]+?)\s+(?:weather|forecast|temperature|temp|mausam|hawa|barish|brishti)\b",
            text,
            re.IGNORECASE,
        )
        if prefix_matches:
            candidate = clean_loc(prefix_matches[0].strip().rstrip(","))
            if candidate and candidate.lower() not in INVALID_LOCATIONS:
                extracted_location = candidate

    # Fallback cleaned tokens (preserves comma qualifiers)
    if not extracted_location:
        cleaned = re.sub(
            r"\b(what's|whats|what|will|is|it|the|weather|like|how|hot|cold|should|i|carry|an|umbrella|rain|be|in|at|for|near|to|about|and|or|then|there|today|tomorrow|tonight|this|evening|morning|afternoon|now|right|why|explain|reason|wear|clothes|jacket|coat|pack|dress|bring|take|wind|winds|breeze|humidity|cloud|clouds|mausam|kaisa|kaisi|kaise|hai|hain|mein|\?)\b",
            "",
            lower_text,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"^[^\w\u0900-\u0D7F]+|[^\w\u0900-\u0D7F]+$", "", cleaned).strip()
        if "," in cleaned:
            parts = [p.strip() for p in cleaned.split(",") if p.strip()]
            cleaned_parts = []
            for p in parts:
                toks = [t for t in re.split(r"[\s\?\!;]+", p) if t and t.lower() not in INVALID_LOCATIONS]
                if toks:
                    cleaned_parts.append(" ".join(toks))
            cleaned_filtered = ", ".join(cleaned_parts)
        else:
            tokens = [t for t in re.split(r"[\s\?\!\.,]+", cleaned) if t and t.lower() not in INVALID_LOCATIONS]
            cleaned_filtered = " ".join(tokens).strip()
        cleaned_canonical = multilingual_service.canonicalize_known_location(cleaned_filtered) if cleaned_filtered else ""
        if cleaned_canonical and len(cleaned_canonical) >= 2 and cleaned_canonical.lower() not in INVALID_LOCATIONS:
            extracted_location = cleaned_canonical.title()
        else:
            extracted_location = None

    if extracted_location:
        extracted_location = clean_loc(extracted_location)
        if extracted_location and extracted_location.lower() in INVALID_LOCATIONS:
            extracted_location = None


    return ExtractedQueryInfo(
        original_query=text,
        intent=intent,
        extracted_location=extracted_location,
        date_context=date_context,
        time_period=time_period,
        language=detected_lang,
    )


# Alias for backward compatibility
extract_query_entities = extract_query_entities_rule_based


def is_high_confidence_extraction(
    rule_info: ExtractedQueryInfo,
    query_text: str,
    session_data: Dict[str, Any],
    has_device_location: bool,
) -> bool:
    """
    Determine if deterministic rule-based entity extraction is high-confidence,
    allowing the system to skip the costly (~1.5s) LLM intent extraction call.
    """
    clean_text = query_text.strip().lower()

    # Rule 1: Explicit comparison query with two valid, distinct locations
    if rule_info.intent == "comparison":
        if (
            rule_info.extracted_location_a
            and rule_info.extracted_location_b
            and rule_info.extracted_location_a.lower() not in INVALID_LOCATIONS
            and rule_info.extracted_location_b.lower() not in INVALID_LOCATIONS
            and rule_info.extracted_location_a.lower() != rule_info.extracted_location_b.lower()
        ):
            return True
        return False

    # Rule 2: Query with explicit device GPS coordinates
    if has_device_location:
        return True

    # Rule 3: Single location explicitly extracted and validated
    if (
        rule_info.extracted_location
        and rule_info.extracted_location.lower() not in INVALID_LOCATIONS
        and len(rule_info.extracted_location.strip()) >= 2
    ):
        return True

    # Rule 4: Contextual follow-up query relying on active session location
    has_session_loc = bool(session_data.get("location"))
    if has_session_loc and not rule_info.extracted_location:
        followup_signals = [
            "what about", "how about", "and ", "why", "explain", "temperature",
            "temp", "rain", "wind", "humidity", "weather", "forecast", "chata",
            "baarish", "garmi", "thanda", "umbrella", "clothes", "jacket",
            "outside", "outdoor", "travel", "drive", "safe", "will it", "is it",
            "how is", "what is", "kaisa", "kaisi", "kaise", "thik", "theek"
        ]
        if any(sig in clean_text for sig in followup_signals) or rule_info.intent != "weather_information":
            return True

    # Ambiguous, missing location, or unclear structure -> fallback to LLM intent extraction
    return False


def generate_grounded_summary_template(
    query_info: ExtractedQueryInfo,
    location_name: str,
    temp: float,
    feels_like: float,
    condition: str,
    humidity: int,
    wind_speed: float,
    precip_prob: int,
    precip: float,
    decision: Optional[DecisionResponse] = None,
    rain_duration_hours: int = 0,
    peak_hour: Optional[str] = None,
) -> str:
    """Concise natural language weather interpretation strictly grounded in input metrics."""
    loc_display = location_name
    raw_period = f"{query_info.date_context} {query_info.time_period}".replace("current", "").strip()
    period_str = raw_period if raw_period else "today"

    if query_info.intent == "ai_explain" and decision:
        factors_summary = ", ".join([f"{f.metric.replace('_', ' ')}: {f.value}" for f in decision.factors])
        return (
            f"Explanation for {loc_display} ({period_str}): The Decision Engine recommends '{decision.recommendation}' "
            f"for {decision.type.replace('_', ' ')} based on key factors: {factors_summary}. ({decision.summary})"
        )

    if decision:
        return f"{decision.summary} (Location: {loc_display})"

    temp_round = round(temp)
    if temp_round >= 32:
        temp_desc = "hot"
    elif temp_round >= 25:
        temp_desc = "warm"
    elif temp_round >= 18:
        temp_desc = "pleasant"
    elif temp_round >= 10:
        temp_desc = "cool"
    else:
        temp_desc = "chilly"

    humidity_desc = "humid" if humidity >= 70 else "comfortable"
    cond_lower = condition.lower()

    if query_info.intent == "rain_query":
        if precip_prob >= 50 or precip > 0.0:
            timing_hint = f" around the {peak_hour}" if peak_hour else ""
            if rain_duration_hours in (1, 2):
                return (
                    f"An isolated shower is possible{timing_hint} in {loc_display} ({period_str}) under {cond_lower} skies, "
                    f"with a peak hourly rain chance of {precip_prob}%. Keeping a compact umbrella handy is sensible."
                )
            elif rain_duration_hours >= 3:
                return (
                    f"Rain is expected across several hours in {loc_display} ({period_str}) under {cond_lower} skies, "
                    f"with peak hourly precipitation probability reaching {precip_prob}%. Keeping an umbrella handy is recommended."
                )
            return (
                f"Rain is possible in {loc_display} ({period_str}) under {cond_lower} skies with a peak hourly "
                f"precipitation probability of {precip_prob}%. Keeping an umbrella handy is recommended."
            )
        else:
            return (
                f"Dry conditions are expected in {loc_display} ({period_str}) under {cond_lower} skies with low rain probability (peak {precip_prob}%)."
            )

    if query_info.intent == "temperature_query":
        return (
            f"Temperatures in {loc_display} ({period_str}) will hover around {temp_round}°C ({cond_lower}), feeling like {round(feels_like)}°C. "
            f"Conditions are {temp_desc} and {humidity_desc}."
        )

    if precip_prob >= 70 or "rain" in cond_lower or "thunderstorm" in cond_lower:
        if rain_duration_hours in (1, 2):
            rain_desc = f"with an isolated shower possible (peak hourly {precip_prob}%)"
            advice = "A compact umbrella or light rain gear is sensible if heading out."
        else:
            rain_desc = f"with a high chance of rain across the period (peak {precip_prob}%)"
            advice = "Carrying an umbrella or rain gear is sensible if you're heading outside."
    elif precip_prob >= 40:
        rain_desc = f"with a moderate chance of rain (peak {precip_prob}%)"
        advice = "Conditions may be unsettled; keep an umbrella handy."
    else:
        rain_desc = f"with low rain chance (peak {precip_prob}%)"
        advice = "Conditions are generally favorable for outdoor travel and activities."

    return (
        f"Expect {temp_desc}, {humidity_desc} conditions in {loc_display} ({period_str}) under {cond_lower} skies {rain_desc}. "
        f"{advice}"
    )



generate_grounded_summary = generate_grounded_summary_template


class QueryService:
    """Orchestrator connecting query understanding, session context, geocoding, weather retrieval, decision evaluation, and comparison."""

    async def process_query(
        self,
        query_text: str,
        session_id: str = "default",
        device_location: Optional[Any] = None,
        language: Optional[str] = "auto",
    ) -> QueryResponse:
        """Process natural language query with in-memory session context, language tracking, and missing-location clarification."""
        sess_key = session_id or "default"
        session_data = SESSION_CONTEXT.get(sess_key, {})

        # Language Resolution (Auto vs Explicit preference + script detection)
        explicit_lang = multilingual_service.normalize_language(language) if (language and language.strip().lower() not in ("auto", "none", "")) else None
        detected_lang = multilingual_service.detect_language(query_text, explicit_pref=explicit_lang)

        if explicit_lang:
            active_lang = explicit_lang
        else:
            if "language" in session_data and session_data["language"] and not any(w in query_text.lower() for w in ["what", "how", "why", "which", "will", "is", "compare", "weather", "forecast", "rain"]):
                if detected_lang != "en":
                    active_lang = detected_lang
                else:
                    active_lang = session_data["language"]
            else:
                active_lang = detected_lang

        if sess_key not in SESSION_CONTEXT:
            SESSION_CONTEXT[sess_key] = {}
        SESSION_CONTEXT[sess_key]["language"] = active_lang

        # Step 1: Entity & Intent Extraction (Fast-Path Rule-Based when High Confidence, else LLM with Rule Fallback)
        rule_info = extract_query_entities_rule_based(query_text, language_hint=active_lang)
        has_device_loc = bool(
            device_location
            and getattr(device_location, "latitude", None) is not None
            and getattr(device_location, "longitude", None) is not None
        )
        if is_high_confidence_extraction(rule_info, query_text, session_data, has_device_loc):
            query_info = rule_info
        else:
            query_info = await llm_service.extract_structured_intent(query_text, language_hint=active_lang)
            if not query_info:
                query_info = rule_info

        query_info.language = active_lang
        query_info.extracted_location = multilingual_service.canonicalize_known_location(query_info.extracted_location)
        query_info.extracted_location_a = multilingual_service.canonicalize_known_location(query_info.extracted_location_a)
        query_info.extracted_location_b = multilingual_service.canonicalize_known_location(query_info.extracted_location_b)

        # Reverse geocode structured device location if provided
        device_geocoded: Optional[GeocodedLocationSchema] = None
        if device_location and getattr(device_location, "latitude", None) is not None and getattr(device_location, "longitude", None) is not None:
            device_geocoded = await geocoding_service.reverse_geocode(
                device_location.latitude, device_location.longitude
            )
            query_info.extracted_location = device_geocoded.name
            SESSION_CONTEXT[sess_key]["location"] = device_geocoded

        # Sanitize extracted locations against invalid words
        if query_info.extracted_location and query_info.extracted_location.lower().strip() in INVALID_LOCATIONS:
            query_info.extracted_location = None
        if query_info.extracted_location_a and query_info.extracted_location_a.lower().strip() in INVALID_LOCATIONS:
            query_info.extracted_location_a = None
        if query_info.extracted_location_b and query_info.extracted_location_b.lower().strip() in INVALID_LOCATIONS:
            query_info.extracted_location_b = None

        # Reclassify generic follow-up queries as comparison if last_comparison exists and no new single location is mentioned
        if "last_comparison" in session_data and query_info.intent != "comparison" and not query_info.extracted_location:
            last_comp = session_data["last_comparison"]
            prev_intent = query_info.intent
            query_info.intent = "comparison"
            query_info.extracted_location_a = last_comp.get("location_a")
            query_info.extracted_location_b = last_comp.get("location_b")
            
            # Map specific weather intent to appropriate comparison goal if present
            if prev_intent == "outdoor_activity_recommendation":
                query_info.comparison_goal = "outdoor_activity"
            elif prev_intent == "travel_recommendation":
                query_info.comparison_goal = "travel"
            elif prev_intent == "rain_query" or prev_intent == "umbrella_recommendation":
                query_info.comparison_goal = "rain"
            elif prev_intent == "temperature_query":
                query_info.comparison_goal = "temperature"
            elif not query_info.comparison_goal or query_info.comparison_goal == "general":
                query_info.comparison_goal = last_comp.get("comparison_goal", "general")

        # Step 1.5: Handle Comparison Intent Flow
        if query_info.intent == "comparison":
            loc_a_name = query_info.extracted_location_a
            loc_b_name = query_info.extracted_location_b

            # Session context lookup for follow-up comparison queries
            if "last_comparison" in session_data and session_data["last_comparison"]:
                last_comp = session_data["last_comparison"]
                loc_a_name = loc_a_name or last_comp.get("location_a")
                loc_b_name = loc_b_name or last_comp.get("location_b")
                query_info.extracted_location_a = loc_a_name
                query_info.extracted_location_b = loc_b_name
                if not query_info.comparison_goal or query_info.comparison_goal == "general":
                    query_info.comparison_goal = last_comp.get("comparison_goal", "general")
                if not any(d in query_text.lower() or d in query_text for d in ["tomorrow", "today", "weekend", "saturday", "sunday", "कल", "কাল", "நாளை", "இன்று", "రేపు", "ఈరోజు", "నేడు", "उद्या", "आज", "repu", "udya", "naalai", "aaj", "kal"]):
                    query_info.date_context = last_comp.get("date_context", query_info.date_context)
                if not any(t in query_text.lower() or t in query_text for t in ["morning", "afternoon", "evening", "tonight", "night", "now", "सुबह", "रात", "காலை", "மாலை", "இரவு", "உதயம்", "ఉదయం", "సాయంత్రం", "రాత్రి", "सकाळी", "संध्याकाळी", "रात्री", "दुपारी", "மதியம்"]):
                    query_info.time_period = last_comp.get("time_period", query_info.time_period)

            # If missing second location (or first location)
            if not loc_a_name or not loc_b_name:
                return QueryResponse(
                    query=query_info,
                    location=None,
                    current=None,
                    forecast=None,
                    decision=None,
                    alerts=[],
                    comparison=None,
                    summary=multilingual_service.get_localized_comparison_clarification(active_lang),
                    needs_clarification=True,
                    language=active_lang,
                    session_id=sess_key,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

            # Geocode both locations concurrently
            res_a, res_b = await asyncio.gather(
                geocoding_service.geocode_location(loc_a_name),
                geocoding_service.geocode_location(loc_b_name),
                return_exceptions=True,
            )

            if isinstance(res_a, HTTPException):
                return QueryResponse(
                    query=query_info,
                    location=None,
                    current=None,
                    forecast=None,
                    decision=None,
                    alerts=[],
                    comparison=None,
                    summary=multilingual_service.get_localized_location_not_found(loc_a_name, active_lang),
                    needs_clarification=True,
                    language=active_lang,
                    session_id=sess_key,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            if isinstance(res_a, Exception):
                raise res_a
            loc_a_geo = res_a

            if isinstance(res_b, HTTPException):
                return QueryResponse(
                    query=query_info,
                    location=loc_a_geo,
                    current=None,
                    forecast=None,
                    decision=None,
                    alerts=[],
                    comparison=None,
                    summary=multilingual_service.get_localized_location_not_found(loc_b_name, active_lang),
                    needs_clarification=True,
                    language=active_lang,
                    session_id=sess_key,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            if isinstance(res_b, Exception):
                raise res_b
            loc_b_geo = res_b

            if not loc_a_geo or not loc_b_geo:
                unresolved = loc_a_name if not loc_a_geo else loc_b_name
                return QueryResponse(
                    query=query_info,
                    location=loc_a_geo or loc_b_geo,
                    current=None,
                    forecast=None,
                    decision=None,
                    alerts=[],
                    comparison=None,
                    summary=multilingual_service.get_localized_location_not_found(unresolved, active_lang),
                    needs_clarification=True,
                    language=active_lang,
                    session_id=sess_key,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

            # Fetch weather for Location A and Location B concurrently (168 hours = 7 days)
            res_bundle_a, res_bundle_b = await asyncio.gather(
                weather_service.get_weather_bundle(loc_a_geo.latitude, loc_a_geo.longitude, hours=168),
                weather_service.get_weather_bundle(loc_b_geo.latitude, loc_b_geo.longitude, hours=168),
                return_exceptions=True,
            )

            if isinstance(res_bundle_a, Exception) or isinstance(res_bundle_b, Exception):
                return QueryResponse(
                    query=query_info,
                    location=loc_a_geo,
                    current=None,
                    forecast=None,
                    decision=None,
                    alerts=[],
                    comparison=None,
                    summary=multilingual_service.get_localized_weather_service_unavailable(
                        f"{loc_a_geo.name} / {loc_b_geo.name}", active_lang
                    ),
                    needs_clarification=True,
                    language=active_lang,
                    session_id=sess_key,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

            current_a, forecast_a = res_bundle_a
            current_b, forecast_b = res_bundle_b

            loc_a_display = f"{loc_a_geo.name}, {loc_a_geo.country}" if loc_a_geo.country else loc_a_geo.name
            loc_b_display = f"{loc_b_geo.name}, {loc_b_geo.country}" if loc_b_geo.country else loc_b_geo.name

            # Filter period weather for both locations
            period_metrics_a = decision_engine_service.filter_forecast_by_period(
                current=current_a.current,
                forecast=forecast_a.hourly,
                date_context=query_info.date_context,
                time_period=query_info.time_period,
            )
            period_metrics_b = decision_engine_service.filter_forecast_by_period(
                current=current_b.current,
                forecast=forecast_b.hourly,
                date_context=query_info.date_context,
                time_period=query_info.time_period,
            )

            if period_metrics_a.has_missing_data or period_metrics_b.has_missing_data:
                target_lbl = period_metrics_a.period_label
                return QueryResponse(
                    query=query_info,
                    location=loc_a_geo,
                    current=current_a.current,
                    period_weather=None,
                    period_forecast=[],
                    forecast=forecast_a.hourly[:24],
                    decision=None,
                    alerts=[],
                    comparison=None,
                    summary=multilingual_service.get_localized_missing_data(target_lbl, active_lang),
                    needs_clarification=True,
                    language=active_lang,
                    session_id=sess_key,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

            pw_a = TargetPeriodWeather(
                period_label=period_metrics_a.period_label,
                temperature=period_metrics_a.temperature,
                feels_like=period_metrics_a.feels_like,
                condition=period_metrics_a.condition,
                weather_code=period_metrics_a.weather_code,
                humidity=period_metrics_a.humidity,
                wind_speed=period_metrics_a.wind_speed,
                precipitation=period_metrics_a.precipitation,
                precipitation_probability=period_metrics_a.precipitation_probability,
                rain_duration_hours=period_metrics_a.rain_duration_hours,
                peak_hour=period_metrics_a.peak_hour,
                total_precipitation=period_metrics_a.total_precipitation,
            )
            pw_b = TargetPeriodWeather(
                period_label=period_metrics_b.period_label,
                temperature=period_metrics_b.temperature,
                feels_like=period_metrics_b.feels_like,
                condition=period_metrics_b.condition,
                weather_code=period_metrics_b.weather_code,
                humidity=period_metrics_b.humidity,
                wind_speed=period_metrics_b.wind_speed,
                precipitation=period_metrics_b.precipitation,
                precipitation_probability=period_metrics_b.precipitation_probability,
                rain_duration_hours=period_metrics_b.rain_duration_hours,
                peak_hour=period_metrics_b.peak_hour,
                total_precipitation=period_metrics_b.total_precipitation,
            )

            alerts_a = alert_engine_service.evaluate_alerts(pw_a, loc_a_display)
            alerts_b = alert_engine_service.evaluate_alerts(pw_b, loc_b_display)

            comp_res = comparison_engine_service.compare_locations(
                location_a=loc_a_geo,
                location_b=loc_b_geo,
                pw_a=pw_a,
                pw_b=pw_b,
                alerts_a=alerts_a,
                alerts_b=alerts_b,
                goal=query_info.comparison_goal,
            )

            summary: Optional[str] = None
            if llm_service.is_configured:
                summary = await llm_service.generate_comparison_explanation(
                    query_text, query_info, comp_res, target_language=active_lang
                )
            if not summary:
                summary = f"{comp_res.decision.summary} {comp_res.decision.winner_reason}"

            # Save session context
            SESSION_CONTEXT[sess_key]["location"] = loc_a_geo
            SESSION_CONTEXT[sess_key]["last_query"] = query_info
            SESSION_CONTEXT[sess_key]["last_comparison"] = {
                "location_a": loc_a_geo.name,
                "location_b": loc_b_geo.name,
                "date_context": query_info.date_context,
                "time_period": query_info.time_period,
                "comparison_goal": comp_res.comparison_goal,
            }

            comp_events = event_service.get_location_events(loc_a_geo.name) + event_service.get_location_events(loc_b_geo.name)

            return QueryResponse(
                query=query_info,
                location=loc_a_geo,
                current=current_a.current,
                period_weather=pw_a,
                period_forecast=period_metrics_a.matching_items,
                forecast=forecast_a.hourly[:24],
                decision=None,
                alerts=alerts_a + alerts_b,
                environmental_events=comp_events,
                comparison=comp_res,
                summary=summary,
                needs_clarification=False,
                language=active_lang,
                session_id=sess_key,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        target_location_name: Optional[str] = query_info.extracted_location
        geocoded: Optional[GeocodedLocationSchema] = device_geocoded

        # Step 2: Handle AI Explain ("Why?") queries using session context
        if query_info.intent == "ai_explain":
            if "location" in session_data and session_data["location"]:
                geocoded = session_data["location"]
                query_info.extracted_location = geocoded.name
                if "last_query" in session_data and session_data["last_query"]:
                    last_q: ExtractedQueryInfo = session_data["last_query"]
                    if query_info.date_context == "today" and last_q.date_context == "tomorrow":
                        query_info.date_context = last_q.date_context
                    if query_info.time_period == "current" and last_q.time_period != "current":
                        query_info.time_period = last_q.time_period
            else:
                return QueryResponse(
                    query=query_info,
                    location=None,
                    current=None,
                    forecast=None,
                    decision=None,
                    alerts=[],
                    summary=multilingual_service.get_localized_clarification(active_lang),
                    needs_clarification=True,
                    language=active_lang,
                    session_id=sess_key,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

        # Step 3: Location Resolution & Session Context Lookup
        if geocoded:
            SESSION_CONTEXT[sess_key]["location"] = geocoded
        elif target_location_name:
            try:
                ctx_loc = session_data.get("location")
                if ctx_loc is not None:
                    try:
                        geocoded = await geocoding_service.geocode_location(
                            target_location_name, context_location=ctx_loc
                        )
                    except TypeError:
                        geocoded = await geocoding_service.geocode_location(target_location_name)
                else:
                    geocoded = await geocoding_service.geocode_location(target_location_name)
                SESSION_CONTEXT[sess_key]["location"] = geocoded
            except HTTPException:
                return QueryResponse(
                    query=query_info,
                    location=None,
                    current=None,
                    forecast=None,
                    decision=None,
                    alerts=[],
                    summary=multilingual_service.get_localized_location_not_found(target_location_name, active_lang),
                    needs_clarification=True,
                    language=active_lang,
                    session_id=sess_key,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

            if "last_query" in session_data and session_data["last_query"]:
                last_q: ExtractedQueryInfo = session_data["last_query"]
                if not any(d in query_text.lower() or d in query_text for d in ["tomorrow", "today", "weekend", "saturday", "sunday", "कल", "কাল", "நாளை", "இன்று", "రేపు", "ఈరోజు", "నేడు", "उद्या", "आज", "repu", "udya", "naalai", "aaj", "kal"]):
                    query_info.date_context = last_q.date_context
                if not any(t in query_text.lower() or t in query_text for t in ["morning", "afternoon", "evening", "tonight", "night", "now", "सुबह", "रात", "காலை", "மாலை", "இரவு", "உதயம்", "ఉదయం", "సాయంత్రం", "రాత్రి", "सकाळी", "संध्याकाळी", "रात्री", "दुपारी", "மதியம்"]):
                    query_info.time_period = last_q.time_period
                if query_info.intent == "weather_information" and last_q.intent not in ["weather_information", "ai_explain"]:
                    query_info.intent = last_q.intent
        elif "location" in session_data and session_data["location"]:
            geocoded = session_data["location"]
            query_info.extracted_location = geocoded.name
            if "last_query" in session_data and session_data["last_query"]:
                last_q: ExtractedQueryInfo = session_data["last_query"]
                if not any(d in query_text.lower() or d in query_text for d in ["tomorrow", "today", "weekend", "saturday", "sunday", "कल", "কাল", "நாளை", "இன்று", "రేపు", "ఈరోజు", "నేడు", "उद्या", "आज", "repu", "udya", "naalai", "aaj", "kal"]):
                    query_info.date_context = last_q.date_context
                if not any(t in query_text.lower() or t in query_text for t in ["morning", "afternoon", "evening", "tonight", "night", "now", "सुबह", "रात", "காலை", "மாலை", "இரவு", "உதயம்", "ఉదయం", "సాయంత్రం", "రాత్రి", "सकाळी", "संध्याकाळी", "रात्री", "दुपारी", "மதியம்"]):
                    query_info.time_period = last_q.time_period
                if query_info.intent == "weather_information" and last_q.intent not in ["weather_information", "ai_explain"]:
                    query_info.intent = last_q.intent
        else:
            return QueryResponse(
                query=query_info,
                location=None,
                current=None,
                forecast=None,
                decision=None,
                alerts=[],
                summary=multilingual_service.get_localized_clarification(active_lang),
                needs_clarification=True,
                language=active_lang,
                session_id=sess_key,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )


        # Step 4: Fetch Real Weather Data in ONE unified Open-Meteo request (168h forecast = 7 days)
        try:
            current_res, forecast_res = await weather_service.get_weather_bundle(
                geocoded.latitude, geocoded.longitude, hours=168
            )
        except HTTPException:
            return QueryResponse(
                query=query_info,
                location=geocoded,
                current=None,
                forecast=None,
                decision=None,
                alerts=[],
                summary=multilingual_service.get_localized_weather_service_unavailable(geocoded.name, active_lang),
                needs_clarification=True,
                language=active_lang,
                session_id=sess_key,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        if current_res.location.timezone:
            geocoded.timezone = current_res.location.timezone

        curr = current_res.current
        loc_display = f"{geocoded.name}, {geocoded.country}" if geocoded.country else geocoded.name

        # Step 5: Centralized Period Weather Filtering
        period_metrics = decision_engine_service.filter_forecast_by_period(
            current=curr,
            forecast=forecast_res.hourly,
            date_context=query_info.date_context,
            time_period=query_info.time_period,
        )

        target_date_str: Optional[str] = None
        if period_metrics.matching_items:
            try:
                target_date_str = period_metrics.matching_items[0].time.split("T")[0]
            except Exception:
                target_date_str = None

        is_future_forecast = (
            query_info.date_context != "today"
            or query_info.time_period not in ["current", "now"]
        )

        period_type = (
            query_info.date_context
            if query_info.date_context != "today"
            else ("current" if query_info.time_period in ["current", "now"] else "today")
        )

        period_info = WeatherPeriodInfo(
            type=period_type,
            label=period_metrics.period_label,
            date=target_date_str,
            is_forecast=is_future_forecast,
        )

        if period_metrics.has_missing_data:
            return QueryResponse(
                query=query_info,
                location=geocoded,
                current=curr,
                period=period_info,
                period_weather=None,
                period_forecast=[],
                forecast=forecast_res.hourly[:24],
                decision=None,
                alerts=[],
                summary=multilingual_service.get_localized_missing_data(period_metrics.period_label, active_lang),
                needs_clarification=True,
                language=active_lang,
                session_id=sess_key,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        target_period_weather = TargetPeriodWeather(
            period_label=period_metrics.period_label,
            temperature=period_metrics.temperature,
            feels_like=period_metrics.feels_like,
            condition=period_metrics.condition,
            weather_code=period_metrics.weather_code,
            humidity=period_metrics.humidity,
            wind_speed=period_metrics.wind_speed,
            precipitation=period_metrics.precipitation,
            precipitation_probability=period_metrics.precipitation_probability,
            rain_duration_hours=period_metrics.rain_duration_hours,
            peak_hour=period_metrics.peak_hour,
            total_precipitation=period_metrics.total_precipitation,
        )

        weather_summary_data = {
            "target_period": period_metrics.period_label,
            "is_forecast": is_future_forecast,
            "target_date": target_date_str,
            "temperature": period_metrics.temperature,
            "feels_like": period_metrics.feels_like,
            "condition": period_metrics.condition,
            "weather_code": period_metrics.weather_code,
            "humidity": period_metrics.humidity,
            "wind_speed": period_metrics.wind_speed,
            "precipitation": period_metrics.precipitation,
            "precipitation_probability": period_metrics.precipitation_probability,
            "rain_duration_hours": period_metrics.rain_duration_hours,
            "peak_hour": period_metrics.peak_hour,
            "total_precipitation": period_metrics.total_precipitation,
        }
        if not is_future_forecast:
            weather_summary_data["observation_time"] = curr.time
        else:
            weather_summary_data["forecast_period"] = period_metrics.period_label

        # Step 6: Decision Engine & Alert Evaluation
        decision: Optional[DecisionResponse] = None
        if query_info.intent == "ai_explain" and "last_decision" in session_data:
            decision = session_data["last_decision"]
        else:
            decision = decision_engine_service.evaluate_decision(
                query_info=query_info,
                current=curr,
                forecast=forecast_res.hourly,
            )

        alerts = alert_engine_service.evaluate_alerts(
            period_weather=target_period_weather,
            location_name=loc_display,
        )

        SESSION_CONTEXT[sess_key]["last_query"] = query_info
        SESSION_CONTEXT[sess_key]["last_weather"] = weather_summary_data
        if decision:
            SESSION_CONTEXT[sess_key]["last_decision"] = decision

        # Step 7: Grounded Response Generation
        summary: Optional[str] = None
        if query_info.intent == "ai_explain" and decision:
            summary = await llm_service.generate_ai_explanation(
                query_text=query_text,
                query_info=query_info,
                location_name=loc_display,
                decision=decision,
                target_language=active_lang,
            )
        elif llm_service.is_configured:
            summary = await llm_service.generate_grounded_response(
                query_text=query_text,
                query_info=query_info,
                location_name=loc_display,
                weather_summary_data=weather_summary_data,
                decision=decision,
                target_language=active_lang,
            )

        # Weather Grounding Safety Invariant:
        # If structured weather data exists, REJECT any LLM unavailable-data apologies or hallucinations.
        def _is_apology_or_unavailable(text: Optional[str]) -> bool:
            if not text or len(text.strip()) < 10:
                return True
            lowered = text.lower()
            apology_markers = [
                "not available in the information i have",
                "is not available in the information",
                "not available in the data",
                "data is not available",
                "weather data for tomorrow in",
                "weather data for today in",
                "i'm sorry, but the weather data",
                "i am sorry, but the weather data",
                "i do not have access to the weather",
                "cannot provide the weather",
                "forecast is currently unavailable",
                "information is not available",
                "do not have the forecast",
                "cannot provide weather",
            ]
            return any(marker in lowered for marker in apology_markers)

        if not summary or _is_apology_or_unavailable(summary):
            if summary and _is_apology_or_unavailable(summary):
                logger.warning(
                    "LLM summary contained an unavailable-data apology while structured data was present. "
                    "Rejecting apology and generating authoritative detailed interpretation."
                )
            summary = multilingual_service.generate_detailed_interpretation(
                language=active_lang,
                query_info=query_info,
                location_name=loc_display,
                temp=period_metrics.temperature,
                feels_like=period_metrics.feels_like,
                condition=period_metrics.condition,
                humidity=period_metrics.humidity,
                wind_speed=period_metrics.wind_speed,
                precip_prob=period_metrics.precipitation_probability,
                precip=period_metrics.precipitation,
                decision=decision,
                rain_duration_hours=period_metrics.rain_duration_hours,
                peak_hour=period_metrics.peak_hour,
                total_precip=period_metrics.total_precipitation,
                period_label=period_metrics.period_label,
            )

        key_insight = multilingual_service.generate_key_insight(
            language=active_lang,
            query_info=query_info,
            location_name=loc_display,
            temp=period_metrics.temperature,
            feels_like=period_metrics.feels_like,
            condition=period_metrics.condition,
            humidity=period_metrics.humidity,
            wind_speed=period_metrics.wind_speed,
            precip_prob=period_metrics.precipitation_probability,
            precip=period_metrics.precipitation,
            decision=decision,
            period_label=period_metrics.period_label,
            rain_duration_hours=period_metrics.rain_duration_hours,
        )

        env_events = event_service.get_location_events(geocoded.name)

        return QueryResponse(
            query=query_info,
            location=geocoded,
            current=curr,
            period=period_info,
            period_weather=target_period_weather,
            period_forecast=period_metrics.matching_items,
            forecast=forecast_res.hourly[:24],
            decision=decision,
            alerts=alerts,
            environmental_events=env_events,
            summary=summary,
            key_insight=key_insight,
            needs_clarification=False,
            language=active_lang,
            session_id=sess_key,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )



query_service = QueryService()
