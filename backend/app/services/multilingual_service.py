"""Multilingual utility service for StormOps WeatherGPT.

Handles language detection, language normalization, non-Latin Indian location
canonicalization, and localized deterministic fallback summary templates.
Supported languages: English (en), Hindi (hi), Bengali (bn), Tamil (ta), Telugu (te), Marathi (mr).
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

# Supported language codes
SUPPORTED_LANGUAGES = {"en", "hi", "bn", "ta", "te", "mr"}
DEFAULT_LANGUAGE = "en"

# Known non-Latin script mappings to canonical Latin city names for Open-Meteo geocoding
KNOWN_LOCATION_TRANSLITERATIONS: Dict[str, str] = {
    # Hindi / Marathi (Devanagari)
    "कोलकाता": "Kolkata",
    "कलकत्ता": "Kolkata",
    "मुंबई": "Mumbai",
    "बंबई": "Mumbai",
    "दिल्ली": "Delhi",
    "नई दिल्ली": "New Delhi",
    "नवी दिल्ली": "New Delhi",
    "दार्जिलिंग": "Darjeeling",
    "दार्जिलिंगला": "Darjeeling",
    "बेंगलुरु": "Bengaluru",
    "बैंगलोर": "Bengaluru",
    "बेंगळुरू": "Bengaluru",
    "चेन्नई": "Chennai",
    "मद्रास": "Chennai",
    "हैदराबाद": "Hyderabad",
    "अहमदाबाद": "Ahmedabad",
    "पुणे": "Pune",
    "पुण्यात": "Pune",
    "पुण्याचे": "Pune",
    "मुंबईत": "Mumbai",
    "मुंबईचे": "Mumbai",
    "नागपूर": "Nagpur",
    "नागपुरात": "Nagpur",
    "नाशिक": "Nashik",
    "नाशिकला": "Nashik",
    "ठाणे": "Thane",
    "औरंगाबाद": "Aurangabad",
    "सोलापूर": "Solapur",
    "कोल्हापूर": "Kolhapur",
    "जयपूर": "Jaipur",
    "जयपुर": "Jaipur",
    "लखनऊ": "Lucknow",
    "वाराणसी": "Varanasi",
    "पटना": "Patna",
    "रांची": "Ranchi",
    "गोवा": "Goa",
    "केरल": "Kerala",
    "केरळ": "Kerala",
    "केरला": "Kerala",
    "राजस्थान": "Rajasthan",
    "श्रीनगर": "Srinagar",
    "पेरिस": "Paris",
    "लंदन": "London",
    "टोक्यो": "Tokyo",

    # Bengali
    "কলকাতা": "Kolkata",
    "কলিকাতা": "Kolkata",
    "মুম্বাই": "Mumbai",
    "দিল্লি": "Delhi",
    "নতুন দিল্লি": "New Delhi",
    "দার্জিলিং": "Darjeeling",
    "বেঙ্গালুরু": "Bengaluru",
    "চেন্নাই": "Chennai",
    "হায়দ্রাবাদ": "Hyderabad",
    "আহমেদাবাদ": "Ahmedabad",
    "পুনে": "Pune",
    "জয়পুর": "Jaipur",
    "লখনউ": "Lucknow",
    "বারাণসী": "Varanasi",
    "পাটনা": "Patna",
    "রাঁচি": "Ranchi",
    "গোয়া": "Goa",
    "কেরল": "Kerala",
    "কেরালা": "Kerala",
    "রাজস্থান": "Rajasthan",
    "শ্রীনগর": "Srinagar",
    "প্যারিস": "Paris",
    "লন্ডন": "London",
    "টোকিও": "Tokyo",
    "ঢাকা": "Dhaka",
    "চট্টগ্রাম": "Chittagong",
    "সিলেট": "Sylhet",

    # Tamil (தமிழ்)
    "சென்னை": "Chennai",
    "சென்னையில்": "Chennai",
    "மதுரை": "Madurai",
    "மதுரையில்": "Madurai",
    "கோயம்புத்தூர்": "Coimbatore",
    "கோவை": "Coimbatore",
    "திருச்சி": "Tiruchirappalli",
    "சேலம்": "Salem",
    "மும்பை": "Mumbai",
    "டெல்லி": "Delhi",
    "புது தில்லி": "New Delhi",
    "கொல்கத்தா": "Kolkata",
    "ஹைதராபாத்": "Hyderabad",
    "பெங்களூரு": "Bengaluru",
    "கேரளா": "Kerala",
    "கேரளம்": "Kerala",
    "ராஜஸ்தான்": "Rajasthan",
    "டார்ஜிலிங்": "Darjeeling",
    "பாரிஸ்": "Paris",
    "லண்டன்": "London",
    "டோக்கியோ": "Tokyo",

    # Telugu (తెలుగు)
    "హైదరాబాద్": "Hyderabad",
    "హైదరాబాద్‌లో": "Hyderabad",
    "హైదరాబాద్‌": "Hyderabad",
    "విశాఖపట్నం": "Visakhapatnam",
    "వైజాగ్": "Visakhapatnam",
    "విజయవాడ": "Vijayawada",
    "గుంటూరు": "Guntur",
    "వరంగల్": "Warangal",
    "తిరుపతి": "Tirupati",
    "ముంబై": "Mumbai",
    "ముంబైలో": "Mumbai",
    "ఢిల్లీ": "Delhi",
    "కొత్త ఢిల్లీ": "New Delhi",
    "కోల్‌కతా": "Kolkata",
    "కోల్కతా": "Kolkata",
    "చెన్నై": "Chennai",
    "చెన్నైలో": "Chennai",
    "బెంగళూరు": "Bengaluru",
    "కేరళ": "Kerala",
    "రాజస్థాన్": "Rajasthan",
    "డార్జిలింగ్": "Darjeeling",
    "పారిస్": "Paris",
    "లండన్": "London",
    "టోక్యో": "Tokyo",
}

MARATHI_KEYWORDS = {
    "कसे", "कसा", "कशी", "काय", "आहे", "आहेत", "नाही", "नाहीत", "पाऊस", "पडेल", "पडणार",
    "छत्री", "हवामान", "उद्या", "मला", "घालावे", "घालायचे", "करावे", "जावे", "जावी", "शकेल",
    "होईल", "का", "मध्ये", "कधी", "फार", "खूप", "थंडी", "ऊन", "वारा", "वेळ", "करणार",
    "चांगलं", "चांगले", "पाहिजे", "द्या", "सांगा", "असेल", "राहू", "तापमान", "जाणे", "राहील", "घेऊन", "कोणते"
}

HINDI_KEYWORDS = {
    "कैसा", "कैसी", "कैसे", "क्या", "है", "हैं", "नहीं", "बारिश", "छाता", "मौसम", "कल",
    "मुझे", "पहनना", "चाहिए", "सकते", "होगा", "होगी", "होंगे", "होने", "बताओ", "बताइए",
    "दिखाओ", "में", "पर", "से", "का", "की", "के", "को", "ने", "रहेगा", "रहेगी", "रहेंगे",
    "गर्मी", "सर्दी", "ठंड"
}


class MultilingualService:
    """Service providing language detection, normalization, location canonicalization, and localized fallbacks."""

    KNOWN_LOCATION_TRANSLITERATIONS = KNOWN_LOCATION_TRANSLITERATIONS

    def __init__(self):
        self.KNOWN_LOCATION_TRANSLITERATIONS = KNOWN_LOCATION_TRANSLITERATIONS

    def normalize_language(self, lang: Optional[str]) -> str:
        """Normalize language identifier to a supported code ('en', 'hi', 'bn', 'ta', 'te', 'mr')."""
        if not lang:
            return DEFAULT_LANGUAGE
        norm = lang.strip().lower()
        if norm in ("hi", "hindi", "hin", "हिं", "हिंदी", "हिन्दी"):
            return "hi"
        if norm in ("bn", "bengali", "bangla", "বাং", "বাংলা"):
            return "bn"
        if norm in ("ta", "tamil", "தமிழ்", "தமி"):
            return "ta"
        if norm in ("te", "telugu", "తెలుగు", "తెల"):
            return "te"
        if norm in ("mr", "marathi", "मराठी", "मरा"):
            return "mr"
        if norm in ("en", "english", "eng"):
            return "en"
        return DEFAULT_LANGUAGE

    def detect_language(self, text: str, explicit_pref: Optional[str] = None) -> str:
        """Detect language from query text or explicit user preference.

        Priority:
        1. If explicit_pref is a valid supported language (and not 'auto'), return it.
        2. Fast Unicode script detection:
           - Tamil (\u0B80-\u0BFF) -> 'ta'
           - Telugu (\u0C00-\u0C7F) -> 'te'
           - Bengali (\u0980-\u09FF) -> 'bn'
           - Devanagari (\u0900-\u097F) -> differentiate between Marathi ('mr') and Hindi ('hi')
        3. Common code-mixed markers in Latin script (Hinglish, Banglish, Tanglish, Telgish, Marathish)
        4. Default to 'en'
        """
        if explicit_pref and explicit_pref.strip().lower() not in ("auto", "", "none"):
            normalized = self.normalize_language(explicit_pref)
            if normalized in SUPPORTED_LANGUAGES:
                return normalized

        cleaned = text.strip()
        if not cleaned:
            return DEFAULT_LANGUAGE

        # 1. Check distinct non-Devanagari scripts
        has_tamil = bool(re.search(r"[\u0B80-\u0BFF]", cleaned))
        if has_tamil:
            return "ta"

        has_telugu = bool(re.search(r"[\u0C00-\u0C7F]", cleaned))
        if has_telugu:
            return "te"

        has_bengali = bool(re.search(r"[\u0980-\u09FF]", cleaned))
        has_devanagari = bool(re.search(r"[\u0900-\u097F]", cleaned))

        if has_bengali and not has_devanagari:
            return "bn"

        # 2. Devanagari script: differentiate Marathi ('mr') vs Hindi ('hi')
        if has_devanagari:
            words = set(re.findall(r"[\u0900-\u097F]+", cleaned))
            mr_matches = len(words & MARATHI_KEYWORDS)
            hi_matches = len(words & HINDI_KEYWORDS)

            # Check Marathi genitive/locative suffixes (e.g. मुंबईचे, पुण्यात, हवामान)
            has_mr_suffix = any(
                w.endswith(("चे", "च्या", "ची", "तील", "हून", "यात", "ला"))
                for w in words if len(w) > 3
            )
            if has_mr_suffix:
                mr_matches += 1

            if mr_matches > hi_matches:
                return "mr"
            if mr_matches >= 1 and hi_matches == 0:
                return "mr"
            return "hi"

        # 3. Latin script code-mixing detection
        lower = cleaned.lower()
        hinglish_words = {
            "aaj", "kal", "baarish", "barish", "hogi", "hoga", "kya", "kaisa", "kaisi",
            "rahega", "rahegi", "leke", "jaana", "chahiye", "mausam", "garmi", "sardi",
            "thanda", "mein", "pehenna", "bahar"
        }
        banglish_words = {
            "ajke", "aj", "kalke", "brishti", "hobe", "kemon", "thakbe", "chata", "uchit",
            "abohawa", "gorom", "thanda", "poshak", "pore", "baire", "jaoa", "shohor"
        }
        tanglish_words = {
            "epdi", "irukku", "irukkum", "mazhai", "varuma", "kudai", "inniku", "naalaikku",
            "veyl", "kulir", "vanilai", "edukanuma"
        }
        telgish_words = {
            "ela", "undi", "untundi", "varsham", "padutunda", "paduthunda", "godugu",
            "eroju", "repu", "vatavaranam", "vesavi", "chali"
        }
        marathish_words = {
            "kasa", "kase", "kashi", "aahe", "paus", "padel", "chhatri", "havaman",
            "udya", "ghyalave", "cha"
        }

        tokens = set(re.findall(r"\b\w+\b", lower))
        hi_hits = len(tokens & hinglish_words)
        bn_hits = len(tokens & banglish_words)
        ta_hits = len(tokens & tanglish_words)
        te_hits = len(tokens & telgish_words)
        mr_hits = len(tokens & marathish_words)

        scores = {
            "hi": hi_hits,
            "bn": bn_hits,
            "ta": ta_hits,
            "te": te_hits,
            "mr": mr_hits,
        }
        best_lang, best_score = max(scores.items(), key=lambda x: x[1])
        if best_score >= 2:
            return best_lang

        if ta_hits >= 1 and any(w in lower for w in ["epdi", "irukku", "mazhai"]):
            return "ta"
        if te_hits >= 1 and any(w in lower for w in ["padutunda", "untundi", "varsham", "ela undi"]):
            return "te"
        if mr_hits >= 1 and any(w in lower for w in ["kasa aahe", "havaman", "padel"]):
            return "mr"
        if hi_hits >= 1 and any(w in lower for w in ["baarish", "kaisa", "hogi"]):
            return "hi"
        if bn_hits >= 1 and any(w in lower for w in ["brishti", "kemon", "thakbe"]):
            return "bn"

        return DEFAULT_LANGUAGE

    def canonicalize_known_location(self, raw_location: Optional[str]) -> Optional[str]:
        """Convert known Devanagari/Bengali/Tamil/Telugu location names to Latin English names for Open-Meteo."""
        if not raw_location:
            return None
        trimmed = raw_location.strip()
        # Direct lookup
        if trimmed in KNOWN_LOCATION_TRANSLITERATIONS:
            return KNOWN_LOCATION_TRANSLITERATIONS[trimmed]

        # Clean punctuation
        cleaned = re.sub(r"^[^\wऀ-ൿ]+|[^\wऀ-ൿ]+$", "", trimmed)
        if cleaned in KNOWN_LOCATION_TRANSLITERATIONS:
            return KNOWN_LOCATION_TRANSLITERATIONS[cleaned]

        # Substring replacement for inflected words (e.g. "சென்னையில்", "హైదరాబాద్‌లో", "मुंबईचे", "মুম্বাইয়ের")
        for key, canonical in KNOWN_LOCATION_TRANSLITERATIONS.items():
            if cleaned.startswith(key):
                return canonical

        return trimmed

    def get_localized_clarification(self, language: str) -> str:
        """Return localized missing location clarification prompt."""
        lang = self.normalize_language(language)
        if lang == "hi":
            return "आप किस शहर या स्थान का मौसम जानना चाहते हैं?"
        if lang == "bn":
            return "আপনি কোন স্থানের আবহাওয়া জানতে চান?"
        if lang == "ta":
            return "எந்த இடத்தின் வானிலையை அறிய விரும்புகிறீர்கள்?"
        if lang == "te":
            return "మీరు ఏ ప్రదేశం యొక్క వాతావరణాన్ని తెలుసుకోవాలనుకుంటున్నారు?"
        if lang == "mr":
            return "तुम्हाला कोणत्या ठिकाणचे हवामान जाणून घ्यायचे आहे?"
        return "Which location should I check the weather for?"

    def get_localized_location_not_found(self, location_name: str, language: str) -> str:
        """Return localized message when a location cannot be resolved globally."""
        lang = self.normalize_language(language)
        if lang == "hi":
            return f"'{location_name}' के लिए स्थान नहीं मिल सका। कृपया मान्य शहर या क्षेत्र का नाम निर्दिष्ट करें।"
        if lang == "bn":
            return f"'{location_name}'-এর জন্য কোনো স্থান খুঁজে পাওয়া যায়নি। অনুগ্রহ করে একটি সঠিক শহর বা অঞ্চল উল্লেখ করুন।"
        if lang == "ta":
            return f"'{location_name}'க்கான இருப்பிடம் கிடைக்கவில்லை. சரியான நகரத்தைக் குறிப்பிடவும்."
        if lang == "te":
            return f"'{location_name}' కోసం లొకేషన్ కనుగొనబడలేదు. దయచేసి సరైన నగరాన్ని పేర్కొనండి."
        if lang == "mr":
            return f"'{location_name}' साठी ठिकाण सापडले नाही. कृपया वैध शहर किंवा प्रदेश निर्दिष्ट करा."
        return f"Could not find coordinates for '{location_name}'. Please specify a valid city or region."

    def get_localized_comparison_clarification(self, language: str) -> str:
        """Return localized missing second location clarification prompt."""
        lang = self.normalize_language(language)
        if lang == "hi":
            return "आप किन दो स्थानों की तुलना करना चाहते हैं?"
        if lang == "bn":
            return "আপনি কোন দুটি স্থানের তুলনা করতে চান?"
        if lang == "ta":
            return "எந்த இரண்டு இடங்களை ஒப்பிட விரும்புகிறீர்கள்?"
        if lang == "te":
            return "మీరు ఏ రెండు ప్రదేశాలను పోల్చాలనుకుంటున్నారు?"
        if lang == "mr":
            return "तुम्हाला कोणत्या दोन ठिकाणांची तुलना करायची आहे?"
        return "Which two locations would you like me to compare?"

    def get_localized_missing_data(self, period_label: str, language: str) -> str:
        """Return localized unavailable forecast window clarification."""
        lang = self.normalize_language(language)
        if lang == "hi":
            return f"'{period_label}' के लिए मौसम पूर्वानुमान अभी उपलब्ध नहीं है। कृपया तारीख के करीब पुनः जाँच करें।"
        if lang == "bn":
            return f"'{period_label}'-এর জন্য আবহাওয়ার পূর্বাভাস বর্তমানে উপলব্ধ নেই। অনুগ্রহ করে তারিখের কাছাকাছি সময়ে দেখুন।"
        if lang == "ta":
            return f"'{period_label}'க்கான வானிலை முன்னறிவிப்பு தற்போது கிடைக்கவில்லை. தயவுசெய்து பின்னர் பார்க்கவும்."
        if lang == "te":
            return f"'{period_label}' కోసం వాతావరణ సూచన ప్రస్తుతం అందుబాటులో లేదు. దయచేసి తర్వాత చూడండి."
        if lang == "mr":
            return f"'{period_label}' साठी हवामान अंदाज सध्या उपलब्ध नाही. कृपया तारखेच्या जवळ पुन्हा तपासा."
        return f"Weather forecast data for '{period_label}' is not available in the current forecast window. Please check back closer to the date."

    def get_localized_weather_service_unavailable(self, location_name: str, language: str) -> str:
        """Return localized weather provider unavailable error message."""
        lang = self.normalize_language(language)
        if lang == "hi":
            return f"'{location_name}' के लिए मौसम सेवा वर्तमान में उपलब्ध नहीं है। कृपया कुछ क्षणों बाद पुनः प्रयास करें।"
        if lang == "bn":
            return f"'{location_name}'-এর জন্য আবহাওয়া পরিষেবা বর্তমানে উপলব্ধ নেই। অনুগ্রহ করে কিছু সময় পর আবার চেষ্টা করুন।"
        if lang == "ta":
            return f"'{location_name}'க்கான வானிலை சேவை தற்காலிகமாக கிடைக்கவில்லை. சிறிது நேரம் கழித்து மீண்டும் முயற்சிக்கவும்."
        if lang == "te":
            return f"'{location_name}' కోసం వాతావరణ సేవ తాత్కాలికంగా అందుబాటులో లేదు. దయచేసి కాసేపటి తర్వాత మళ్లీ ప్రయత్నించండి."
        if lang == "mr":
            return f"'{location_name}' साठी हवामान सेवा सध्या उपलब्ध नाही. कृपया थोड्या वेळाने पुन्हा प्रयत्न करा."
        return f"Weather service is temporarily unavailable for '{location_name}'. Please try again in a few moments."

    def generate_key_insight(
        self,
        language: str,
        query_info: Any,
        location_name: str,
        temp: float,
        feels_like: float,
        condition: str,
        humidity: int,
        wind_speed: float,
        precip_prob: int,
        precip: float,
        decision: Optional[Any] = None,
        period_label: str = "today",
        rain_duration_hours: int = 0,
    ) -> str:
        """Generate a concise, authoritative 1-sentence Key Weather Insight answering 'What is the one thing to know?'."""
        lang = self.normalize_language(language)
        loc = location_name
        temp_round = round(temp)
        period = period_label.strip() if period_label else "today"

        if decision and getattr(decision, "summary", None):
            return str(decision.summary).strip()

        if lang == "hi":
            if precip_prob >= 70 or precip > 1.5:
                return f"{loc} में {period} बारिश की उच्च संभावना ({precip_prob}%) और आर्द्र मौसम रहेगा।"
            if temp >= 35:
                return f"{loc} में {period} अत्यधिक गर्मी और तेज धूप का अनुमान है ({temp_round}°C)।"
            if temp <= 10:
                return f"{loc} में {period} ठंड और सर्द मौसम रहेगा ({temp_round}°C)।"
            if humidity >= 65 and temp >= 27:
                return f"{loc} में {period} उमस और गर्मी बनी रहेगी ({temp_round}°C)।"
            return f"{loc} में {period} मुख्य रूप से {condition} मौसम और {temp_round}°C तापमान रहेगा।"

        if lang == "bn":
            if precip_prob >= 70 or precip > 1.5:
                return f"{loc}-এ {period} বৃষ্টির প্রবল সম্ভাবনা ({precip_prob}%) এবং আর্দ্র আবহাওয়া থাকবে।"
            if temp >= 35:
                return f"{loc}-এ {period} তীব্র গরম ও রোদের পূর্বাভাস ({temp_round}°C)।"
            if temp <= 10:
                return f"{loc}-এ {period} শীত ও ঠান্ডার পূর্বাভাস ({temp_round}°C)।"
            if humidity >= 65 and temp >= 27:
                return f"{loc}-এ {period} ভ্যাপসা গরম ও আর্দ্রতা বজায় থাকবে ({temp_round}°C)।"
            return f"{loc}-এ {period} মূলত {condition} আবহাওয়া এবং {temp_round}°C তাপমাত্রা থাকবে।"

        # Default English
        if precip_prob >= 70 or precip > 1.5:
            if rain_duration_hours in (1, 2):
                return f"Passing showers are likely in {loc} during {period} with a peak {precip_prob}% rain probability."
            return f"Expect a warm and humid day in {loc} with a high likelihood of rain ({precip_prob}% probability)."
        if "thunder" in condition.lower():
            return f"Thunderstorms and gusty weather anticipated in {loc} during {period}."
        if precip_prob >= 40 or precip > 0.4:
            return f"Passing or brief showers are possible in {loc} during {period} with a {precip_prob}% chance of rain."
        if temp >= 38:
            return f"Intense heat anticipated in {loc} during {period}, peaking around {temp_round}°C."
        if temp <= 10:
            return f"Cold conditions expected in {loc} during {period} with temperatures dipping to {temp_round}°C."
        if humidity >= 65 and temp >= 27:
            return f"Expect a warm and humid day in {loc} during {period} around {temp_round}°C."
        return f"Predominantly {condition.lower()} conditions expected in {loc} during {period} around {temp_round}°C."

    def generate_detailed_interpretation(
        self,
        language: str,
        query_info: Any,
        location_name: str,
        temp: float,
        feels_like: float,
        condition: str,
        humidity: int,
        wind_speed: float,
        precip_prob: int,
        precip: float,
        decision: Optional[Any] = None,
        rain_duration_hours: int = 0,
        peak_hour: Optional[str] = None,
        total_precip: float = 0.0,
        period_label: str = "today",
    ) -> str:
        """Generate a rich, multi-sentence Detailed Interpretation synthesizing all structured metrics.
        Explains thermal comfort (temperature vs feels-like and humidity index effect), precipitation
        likelihood and accumulation, wind dynamics, and practical implications.
        """
        lang = self.normalize_language(language)
        loc = location_name
        temp_round = round(temp)
        feels_round = round(feels_like)
        period = period_label.strip() if period_label else "today"

        # English
        if lang == "en":
            sentences: list[str] = []

            # 1. Thermal comfort & feels-like comparison
            if feels_round >= temp_round + 3:
                sentences.append(
                    f"Temperatures in {loc} will reach around {temp_round}°C during {period}, but elevated relative humidity ({humidity}%) will push the feels-like index higher to approximately {feels_round}°C."
                )
            elif feels_round <= temp_round - 3:
                sentences.append(
                    f"Temperatures in {loc} will hover near {temp_round}°C during {period}, though wind chill will make it feel noticeably cooler at approximately {feels_round}°C."
                )
            else:
                sentences.append(
                    f"Temperatures in {loc} will hover near {temp_round}°C (feels like {feels_round}°C) under {condition.lower()} skies."
                )

            # 2. Precipitation details & duration
            effective_precip = total_precip if total_precip > 0 else precip
            precip_text = f"an estimated {effective_precip:.1f} mm of rainfall" if effective_precip > 0 else "passing shower accumulation"
            timing_text = f" around {peak_hour}" if peak_hour else ""

            if precip_prob >= 70 or effective_precip >= 1.0:
                if rain_duration_hours >= 3:
                    sentences.append(
                        f"Rain is expected to be sustained across several hours{timing_text} with a peak {precip_prob}% probability and {precip_text}."
                    )
                else:
                    sentences.append(
                        f"Showers are likely to be intermittent during the period{timing_text}, carrying a peak {precip_prob}% precipitation probability and {precip_text}."
                    )
            elif precip_prob >= 35 or effective_precip > 0.1:
                sentences.append(
                    f"Isolated or scattered showers remain possible ({precip_prob}% chance), though prolonged downpours are not anticipated."
                )
            else:
                sentences.append(
                    f"Precipitation chances remain minimal at {precip_prob}%, keeping the period largely dry."
                )

            # 3. Wind & Humidity dynamics
            if wind_speed >= 25.0:
                sentences.append(
                    f"Stronger winds of {wind_speed:.1f} km/h will create brisk conditions and active air circulation."
                )
            elif wind_speed >= 12.0:
                sentences.append(
                    f"Moderate winds of {wind_speed:.1f} km/h will accompany the {humidity}% humidity levels."
                )
            else:
                sentences.append(
                    f"Gentle winds averaging {wind_speed:.1f} km/h offer limited convective cooling against the {humidity}% moisture levels."
                )

            # 4. Practical guidance
            if decision and getattr(decision, "summary", None):
                sentences.append(f"Recommendation: {decision.summary}")
            elif precip_prob >= 60:
                sentences.append("Carrying rain protection and allowing extra transit time for wet roadways is advisable.")
            elif temp >= 35 or feels_round >= 40:
                sentences.append("Staying well hydrated and minimizing heavy outdoor exertion during peak heat hours is recommended.")
            elif temp <= 10:
                sentences.append("Wearing warm thermal layers when stepping outside is recommended.")
            else:
                sentences.append("Overall conditions remain manageable for regular daytime routines.")

            return " ".join(sentences)

        # Fall back to localized summary for non-English languages
        return self.generate_localized_summary(
            language=lang,
            query_info=query_info,
            location_name=location_name,
            temp=temp,
            feels_like=feels_like,
            condition=condition,
            humidity=humidity,
            wind_speed=wind_speed,
            precip_prob=precip_prob,
            precip=precip,
            decision=decision,
            rain_duration_hours=rain_duration_hours,
            peak_hour=peak_hour,
        )

    def generate_localized_summary(
        self,
        language: str,
        query_info: Any,
        location_name: str,
        temp: float,
        feels_like: float,
        condition: str,
        humidity: int,
        wind_speed: float,
        precip_prob: int,
        precip: float,
        decision: Optional[Any] = None,
        rain_duration_hours: int = 0,
        peak_hour: Optional[str] = None,
    ) -> str:
        """Generate deterministic natural language weather summary in the requested language."""
        lang = self.normalize_language(language)
        loc = location_name
        temp_round = round(temp)
        feels_round = round(feels_like)

        # English
        if lang == "en":
            raw_period = f"{query_info.date_context} {query_info.time_period}".replace("current", "").strip()
            period_str = raw_period if raw_period else "today"

            if query_info.intent == "ai_explain" and decision:
                factors_summary = ", ".join([f"{f.metric.replace('_', ' ')}: {f.value}" for f in decision.factors])
                return (
                    f"Explanation for {loc} ({period_str}): The Decision Engine recommends '{decision.recommendation}' "
                    f"for {decision.type.replace('_', ' ')} based on key factors: {factors_summary}. ({decision.summary})"
                )
            if decision:
                return f"{decision.summary} (Location: {loc})"

            if query_info.intent == "rain_query":
                if precip_prob >= 50 or precip > 0.0:
                    timing_hint = f" around the {peak_hour}" if peak_hour else ""
                    if rain_duration_hours in (1, 2):
                        return (
                            f"An isolated shower is possible{timing_hint} in {loc} ({period_str}) under {condition.lower()} skies, "
                            f"with a peak hourly rain chance of {precip_prob}%. Keeping a compact umbrella handy is sensible."
                        )
                    elif rain_duration_hours >= 3:
                        return (
                            f"Rain is expected across several hours in {loc} ({period_str}) under {condition.lower()} skies, "
                            f"with peak hourly precipitation probability reaching {precip_prob}%. Keeping an umbrella handy is recommended."
                        )
                    return (
                        f"Rain is possible in {loc} ({period_str}) under {condition.lower()} skies with a peak hourly "
                        f"precipitation probability of {precip_prob}%. Keeping an umbrella handy is recommended."
                    )
                return f"Dry conditions are expected in {loc} ({period_str}) under {condition.lower()} skies with low rain probability (peak {precip_prob}%)."

            if query_info.intent == "temperature_query":
                return f"Temperatures in {loc} ({period_str}) will hover around {temp_round}°C ({condition.lower()}), feeling like {feels_round}°C."

            if precip_prob >= 50 or precip > 0.0:
                if rain_duration_hours in (1, 2):
                    rain_phrase = f"an isolated shower possible (peak {precip_prob}%)"
                    advice = "A compact umbrella may come in handy."
                else:
                    rain_phrase = f"a {precip_prob}% chance of rain"
                    advice = "Carrying an umbrella or rain gear is sensible if heading outside."
            else:
                rain_phrase = f"a low rain chance (peak {precip_prob}%)"
                advice = "Conditions are generally favorable for outdoor activities."

            return f"Expect around {temp_round}°C in {loc} ({period_str}) under {condition.lower()} skies with {rain_phrase}. {advice}"

        # Hindi
        if lang == "hi":
            period_map_hi = {
                "today": "आज", "tomorrow": "कल", "weekend": "इस वीकेंड", "saturday": "शनिवार",
                "sunday": "रविवार", "tonight": "आज रात", "morning": "सुबह", "afternoon": "दोपहर",
                "evening": "शाम", "now": "अभी", "current": "वर्तमान",
            }
            d_ctx = period_map_hi.get(query_info.date_context, "आज")
            t_ctx = period_map_hi.get(query_info.time_period, "")
            period_hi = f"{d_ctx} {t_ctx}".strip() if t_ctx and t_ctx != "वर्तमान" else d_ctx

            if decision:
                rec_hi = {
                    "recommended": "सलाह दी जाती है",
                    "not_recommended": "सलाह नहीं दी जाती",
                    "caution": "सावधानी बरतने की सलाह है",
                }.get(getattr(decision, "recommendation", ""), "अनुकूल स्थिति है")
                type_hi = {
                    "umbrella": "छाता ले जाने की",
                    "outdoor_activity": "बाहरी गतिविधियों की",
                    "clothing": "उचित कपड़ों की",
                    "travel": "यात्रा की",
                }.get(getattr(decision, "type", ""), "मौसम संबंधी")
                return f"{loc} में {period_hi}: {type_hi} {rec_hi}। {decision.summary}"

            if query_info.intent == "rain_query":
                if precip_prob >= 50 or precip > 0.0:
                    return f"{loc} में {period_hi} बारिश की {precip_prob}% संभावना है। साथ में छाता रखना उचित रहेगा।"
                return f"{loc} में {period_hi} मौसम मुख्यतः शुष्क रहेगा और बारिश की संभावना केवल {precip_prob}% है।"

            if query_info.intent == "temperature_query":
                return f"{loc} में {period_hi} तापमान लगभग {temp_round}°C रहेगा, जो महसूस {feels_round}°C जैसा होगा।"

            rain_advice = "बारिश की संभावना अधिक होने के कारण छाता साथ रखें।" if precip_prob >= 50 else "मौसम बाहरी गतिविधियों के लिए सामान्य रूप से अनुकूल रहेगा।"
            return f"{loc} में {period_hi} तापमान {temp_round}°C रहने का अनुमान है (महसूस {feels_round}°C), और बारिश की संभावना {precip_prob}% है। {rain_advice}"

        # Bengali
        if lang == "bn":
            period_map_bn = {
                "today": "আজ", "tomorrow": "কাল", "weekend": "এই উইকএন্ডে", "saturday": "শনিবার",
                "sunday": "রবিবার", "tonight": "আজ রাতে", "morning": "সকালে", "afternoon": "দুপুরে",
                "evening": "সন্ধ্যায়", "now": "এখন", "current": "বর্তমান",
            }
            d_ctx = period_map_bn.get(query_info.date_context, "আজ")
            t_ctx = period_map_bn.get(query_info.time_period, "")
            period_bn = f"{d_ctx} {t_ctx}".strip() if t_ctx and t_ctx != "বর্তমান" else d_ctx

            if decision:
                rec_bn = {
                    "recommended": "পরামর্শ দেওয়া হচ্ছে",
                    "not_recommended": "পরামর্শ দেওয়া হচ্ছে না",
                    "caution": "সতর্কতা অবলম্বনের পরামর্শ",
                }.get(getattr(decision, "recommendation", ""), "অনুকূল")
                type_bn = {
                    "umbrella": "ছাতা সঙ্গে রাখার",
                    "outdoor_activity": "বাইরে যাওয়ার",
                    "clothing": "উপযুক্ত পোশাকের",
                    "travel": "ভ্রমণের",
                }.get(getattr(decision, "type", ""), "আবহাওয়ার")
                return f"{loc}-এ {period_bn}: {type_bn} {rec_bn}। {decision.summary}"

            if query_info.intent == "rain_query":
                if precip_prob >= 50 or precip > 0.0:
                    return f"{loc}-এ {period_bn} বৃষ্টির সম্ভাবনা প্রায় {precip_prob}%। বাইরে বের হলে সঙ্গে ছাতা রাখা ভালো।"
                return f"{loc}-এ {period_bn} আকাশ মূলত শুষ্ক থাকবে এবং বৃষ্টির সম্ভাবনা মাত্র {precip_prob}%।"

            if query_info.intent == "temperature_query":
                return f"{loc}-এ {period_bn} তাপমাত্রা প্রায় {temp_round}°C থাকবে, এবং অনুভূত হবে {feels_round}°C-এর মতো।"

            rain_advice = "বৃষ্টির संभावना থাকায় ছাতা সঙ্গে রাখুন।" if precip_prob >= 50 else "আবহাওয়া সাধারণভাবে বাইরে বেরোনোর উপযোগী থাকবে।"
            return f"{loc}-এ {period_bn} তাপমাত্রা আনুমানিক {temp_round}°C (অনুভূত {feels_round}°C), এবং বৃষ্টির সম্ভাবনা {precip_prob}%। {rain_advice}"

        # Tamil (தமிழ்)
        if lang == "ta":
            period_map_ta = {
                "today": "இன்று", "tomorrow": "நாளை", "weekend": "இந்த வார இறுதி", "saturday": "சனிக்கிழமை",
                "sunday": "ஞாயிற்றுக்கிழமை", "tonight": "இன்று இரவு", "morning": "காலை", "afternoon": "மதியம்",
                "evening": "மாலை", "now": "இப்போது", "current": "தற்போதைய",
            }
            d_ctx = period_map_ta.get(query_info.date_context, "இன்று")
            t_ctx = period_map_ta.get(query_info.time_period, "")
            period_ta = f"{d_ctx} {t_ctx}".strip() if t_ctx and t_ctx != "தற்போதைய" else d_ctx

            if decision:
                rec_ta = {
                    "recommended": "பரிந்துரைக்கப்படுகிறது",
                    "not_recommended": "பரிந்துரைக்கப்படவில்லை",
                    "caution": "எச்சரிக்கையுடன் செயல்படுவது நல்லது",
                }.get(getattr(decision, "recommendation", ""), "சாதகமான சூழல்")
                type_ta = {
                    "umbrella": "குடை எடுத்துச் செல்வது",
                    "outdoor_activity": "வெளியில் செல்வது",
                    "clothing": "பொருத்தமான ஆடை அணிவது",
                    "travel": "பயணம் செய்வது",
                }.get(getattr(decision, "type", ""), "வானிலை")
                return f"{loc} இல் {period_ta}: {type_ta} {rec_ta}."

            if query_info.intent == "rain_query":
                if precip_prob >= 50 or precip > 0.0:
                    return f"{loc} இல் {period_ta} மழை பெய்ய {precip_prob}% வாய்ப்புள்ளது. குடை எடுத்துச் செல்வது நல்லது."
                return f"{loc} இல் {period_ta} வானிலை பொதுவாக வறண்டதாக இருக்கும், மழைக்கான வாய்ப்பு {precip_prob}% மட்டுமே."

            if query_info.intent == "temperature_query":
                return f"{loc} இல் {period_ta} வெப்பநிலை சுமார் {temp_round}°C ஆக இருக்கும் (உணரப்படுவது {feels_round}°C)."

            rain_advice = "மழை பெய்ய வாய்ப்புள்ளதால் குடை எடுத்துச் செல்லவும்." if precip_prob >= 50 else "வானிலை வெளியில் செல்ல சாதகமாக உள்ளது."
            return f"{loc} இல் {period_ta} வெப்பநிலை சுமார் {temp_round}°C (உணரப்படுவது {feels_round}°C), மழை வாய்ப்பு {precip_prob}%. {rain_advice}"

        # Telugu (తెలుగు)
        if lang == "te":
            period_map_te = {
                "today": "ఈరోజు", "tomorrow": "రేపు", "weekend": "ఈ వారాంతంలో", "saturday": "శనివారం",
                "sunday": "ఆదివారం", "tonight": "ఈ రాత్రి", "morning": "ఉదయం", "afternoon": "మధ్యాహ్నం",
                "evening": "సాయంత్రం", "now": "ఇప్పుడు", "current": "ప్రస్తుత",
            }
            d_ctx = period_map_te.get(query_info.date_context, "ఈరోజు")
            t_ctx = period_map_te.get(query_info.time_period, "")
            period_te = f"{d_ctx} {t_ctx}".strip() if t_ctx and t_ctx != "ప్రస్తుత" else d_ctx

            if decision:
                rec_te = {
                    "recommended": "సిఫార్సు చేయబడింది",
                    "not_recommended": "సిఫార్సు చేయబడలేదు",
                    "caution": "జాగ్రత్తగా ఉండడం మంచిది",
                }.get(getattr(decision, "recommendation", ""), "అనుకూల పరిస్థితి")
                type_te = {
                    "umbrella": "గొడుగు తీసుకెళ్లడం",
                    "outdoor_activity": "బయటకు వెళ్లడం",
                    "clothing": "తగిన దుస్తులు ధరించడం",
                    "travel": "ప్రయాణం చేయడం",
                }.get(getattr(decision, "type", ""), "వాతావరణ")
                return f"{loc} లో {period_te}: {type_te} {rec_te}."

            if query_info.intent == "rain_query":
                if precip_prob >= 50 or precip > 0.0:
                    return f"{loc} లో {period_te} వర్షం పడే అవకాశం {precip_prob}% ఉంది. గొడుగు తీసుకెళ్లడం మంచిది."
                return f"{loc} లో {period_te} వాతావరణం పొడిగా ఉంటుంది మరియు వర్షం పడే అవకాశం {precip_prob}% మాత్రమే."

            if query_info.intent == "temperature_query":
                return f"{loc} లో {period_te} ఉష్ణోగ్రత దాదాపు {temp_round}°C గా ఉంటుంది (అనిపించేది {feels_round}°C)."

            rain_advice = "వర్షం పడే అవకాశం ఉన్నందున గొడుగు తీసుకెళ్లండి." if precip_prob >= 50 else "బయట కార్యకలాపాలకు వాతావరణం అనుకూలంగా ఉంటుంది."
            return f"{loc} లో {period_te} ఉష్ణోగ్రత దాదాపు {temp_round}°C (అనిపించేది {feels_round}°C), వర్ష సూచన {precip_prob}%. {rain_advice}"

        # Marathi (मराठी)
        period_map_mr = {
            "today": "आज", "tomorrow": "उद्या", "weekend": "या वीकेंडला", "saturday": "शनिवार",
            "sunday": "रविवार", "tonight": "आज रात्री", "morning": "सकाळी", "afternoon": "दुपारी",
            "evening": "संध्याकाळी", "now": "आता", "current": "सद्य",
        }
        d_ctx = period_map_mr.get(query_info.date_context, "आज")
        t_ctx = period_map_mr.get(query_info.time_period, "")
        period_mr = f"{d_ctx} {t_ctx}".strip() if t_ctx and t_ctx != "सद्य" else d_ctx

        if decision:
            rec_mr = {
                "recommended": "सल्ला दिला जातो",
                "not_recommended": "सल्ला दिला जात नाही",
                "caution": "सावधगिरी बाळगण्याचा सल्ला दिला जातो",
            }.get(getattr(decision, "recommendation", ""), "अनुकूल परिस्थिती आहे")
            type_mr = {
                "umbrella": "छत्री सोबत ठेवण्याचा",
                "outdoor_activity": "बाहेर जाण्याचा",
                "clothing": "योग्य कपडे घालण्याचा",
                "travel": "प्रवासाचा",
            }.get(getattr(decision, "type", ""), "हवामानाशी संबंधित")
            return f"{loc} मध्ये {period_mr}: {type_mr} {rec_mr}।"

        if query_info.intent == "rain_query":
            if precip_prob >= 50 or precip > 0.0:
                return f"{loc} मध्ये {period_mr} पाऊस पडण्याची {precip_prob}% शक्यता आहे. सोबत छत्री ठेवणे योग्य ठरेल."
            return f"{loc} मध्ये {period_mr} हवामान मुख्यतः कोरडे राहील आणि पावसाची शक्यता फक्त {precip_prob}% आहे."

        if query_info.intent == "temperature_query":
            return f"{loc} मध्ये {period_mr} तापमान साधारण {temp_round}°C राहील (जाणवणारे {feels_round}°C)."

        rain_advice = "पावसाची शक्यता असल्याने छत्री सोबत ठेवा." if precip_prob >= 50 else "बाहेरच्या कामांसाठी हवामान सामान्यतः अनुकूल राहील."
        return f"{loc} मध्ये {period_mr} तापमान सुमारे {temp_round}°C राहण्याचा अंदाज आहे (जाणवणारे {feels_round}°C), आणि पावसाची शक्यता {precip_prob}% आहे. {rain_advice}"


multilingual_service = MultilingualService()
