"""Deterministic Location and Weather Decision Comparison Service."""

import logging
from typing import List, Optional

from app.schemas.alert import WeatherAlert
from app.schemas.comparison import (
    ComparisonDecision,
    ComparisonMetricDifference,
    ComparisonResponse,
)
from app.schemas.query import GeocodedLocationSchema, TargetPeriodWeather

logger = logging.getLogger(__name__)


class ComparisonEngineService:
    """Deterministic comparison engine evaluating weather metrics between two locations."""

    def compare_locations(
        self,
        location_a: GeocodedLocationSchema,
        location_b: GeocodedLocationSchema,
        pw_a: TargetPeriodWeather,
        pw_b: TargetPeriodWeather,
        alerts_a: List[WeatherAlert],
        alerts_b: List[WeatherAlert],
        goal: Optional[str] = "general",
    ) -> ComparisonResponse:
        """Compare two locations deterministically for a target period and decision goal."""
        loc_a_name = location_a.name
        loc_b_name = location_b.name
        period_str = pw_a.period_label.replace("_", " ")

        target_goal = (goal or "general").lower()
        if any(k in target_goal for k in ["travel", "trip", "drive", "flight"]):
            effective_goal = "travel"
        elif any(k in target_goal for k in ["outdoor", "walk", "hike", "event", "run", "outside"]):
            effective_goal = "outdoor_activity"
        elif any(k in target_goal for k in ["rain", "umbrella", "shower", "dry", "drizzle"]):
            effective_goal = "rain"
        elif any(k in target_goal for k in ["cool", "cooler", "cold", "colder", "chilly"]):
            effective_goal = "cooler"
        elif any(k in target_goal for k in ["warm", "warmer", "hot", "hotter", "heat"]):
            effective_goal = "warmer"
        elif any(k in target_goal for k in ["temp", "temperature"]):
            effective_goal = "temperature"
        else:
            effective_goal = "general"

        # Build metric differences
        factors: List[ComparisonMetricDifference] = []

        # Rain Probability
        prob_diff = pw_a.precipitation_probability - pw_b.precipitation_probability
        if abs(prob_diff) < 10:
            prob_better = "equal"
            prob_note = f"Similar rain probability ({pw_a.precipitation_probability}% vs {pw_b.precipitation_probability}%)"
        elif prob_diff < 0:
            prob_better = "a"
            prob_note = f"{loc_a_name} has lower rain probability ({pw_a.precipitation_probability}% vs {pw_b.precipitation_probability}%)"
        else:
            prob_better = "b"
            prob_note = f"{loc_b_name} has lower rain probability ({pw_b.precipitation_probability}% vs {pw_a.precipitation_probability}%)"

        factors.append(
            ComparisonMetricDifference(
                metric="precipitation_probability",
                value_a=f"{pw_a.precipitation_probability}%",
                value_b=f"{pw_b.precipitation_probability}%",
                better_location=prob_better,
                impact_note=prob_note,
            )
        )

        # Precipitation Amount
        precip_diff = round(pw_a.precipitation - pw_b.precipitation, 1)
        if abs(precip_diff) < 0.5:
            precip_better = "equal"
            precip_note = f"Similar precipitation amount ({pw_a.precipitation} mm vs {pw_b.precipitation} mm)"
        elif precip_diff < 0:
            precip_better = "a"
            precip_note = f"{loc_a_name} expects less rainfall ({pw_a.precipitation} mm vs {pw_b.precipitation} mm)"
        else:
            precip_better = "b"
            precip_note = f"{loc_b_name} expects less rainfall ({pw_b.precipitation} mm vs {pw_a.precipitation} mm)"

        factors.append(
            ComparisonMetricDifference(
                metric="precipitation",
                value_a=f"{pw_a.precipitation} mm",
                value_b=f"{pw_b.precipitation} mm",
                better_location=precip_better,
                impact_note=precip_note,
            )
        )

        # Temperature (Respecting direction: cooler vs warmer)
        temp_diff = round(pw_a.temperature - pw_b.temperature, 1)
        if effective_goal == "cooler":
            if temp_diff < 0:
                temp_better = "a"
                temp_note = f"{loc_a_name} is cooler ({pw_a.temperature}°C vs {pw_b.temperature}°C)"
            elif temp_diff > 0:
                temp_better = "b"
                temp_note = f"{loc_b_name} is cooler ({pw_b.temperature}°C vs {pw_a.temperature}°C)"
            else:
                temp_better = "equal"
                temp_note = f"Same temperature ({pw_a.temperature}°C vs {pw_b.temperature}°C)"
        elif effective_goal == "warmer":
            if temp_diff > 0:
                temp_better = "a"
                temp_note = f"{loc_a_name} is warmer ({pw_a.temperature}°C vs {pw_b.temperature}°C)"
            elif temp_diff < 0:
                temp_better = "b"
                temp_note = f"{loc_b_name} is warmer ({pw_b.temperature}°C vs {pw_a.temperature}°C)"
            else:
                temp_better = "equal"
                temp_note = f"Same temperature ({pw_a.temperature}°C vs {pw_b.temperature}°C)"
        else:
            if abs(temp_diff) < 2.0:
                temp_better = "equal"
                temp_note = f"Similar temperature ({pw_a.temperature}°C vs {pw_b.temperature}°C)"
            elif temp_diff > 0:
                temp_better = "a"
                temp_note = f"{loc_a_name} is warmer ({pw_a.temperature}°C vs {pw_b.temperature}°C)"
            else:
                temp_better = "b"
                temp_note = f"{loc_b_name} is warmer ({pw_b.temperature}°C vs {pw_a.temperature}°C)"

        factors.append(
            ComparisonMetricDifference(
                metric="temperature",
                value_a=f"{pw_a.temperature}°C",
                value_b=f"{pw_b.temperature}°C",
                better_location=temp_better,
                impact_note=temp_note,
            )
        )

        # Wind Speed
        wind_diff = round(pw_a.wind_speed - pw_b.wind_speed, 1)
        if abs(wind_diff) < 8.0:
            wind_better = "equal"
            wind_note = f"Similar wind speeds ({pw_a.wind_speed} km/h vs {pw_b.wind_speed} km/h)"
        elif wind_diff < 0:
            wind_better = "a"
            wind_note = f"{loc_a_name} has calmer winds ({pw_a.wind_speed} km/h vs {pw_b.wind_speed} km/h)"
        else:
            wind_better = "b"
            wind_note = f"{loc_b_name} has calmer winds ({pw_b.wind_speed} km/h vs {pw_a.wind_speed} km/h)"

        factors.append(
            ComparisonMetricDifference(
                metric="wind_speed",
                value_a=f"{pw_a.wind_speed} km/h",
                value_b=f"{pw_b.wind_speed} km/h",
                better_location=wind_better,
                impact_note=wind_note,
            )
        )

        # Severe Alert Risk Scoring
        warning_count_a = sum(1 for a in alerts_a if a.severity == "warning")
        warning_count_b = sum(1 for a in alerts_b if a.severity == "warning")
        alert_count_a = len(alerts_a)
        alert_count_b = len(alerts_b)

        if warning_count_a > warning_count_b:
            alert_better = "b"
        elif warning_count_b > warning_count_a:
            alert_better = "a"
        elif alert_count_a > alert_count_b:
            alert_better = "b"
        elif alert_count_b > alert_count_a:
            alert_better = "a"
        else:
            alert_better = "equal"

        # Evaluate Broadly Similar Conditions
        is_broadly_similar = (
            abs(pw_a.precipitation_probability - pw_b.precipitation_probability) <= 15
            and abs(pw_a.precipitation - pw_b.precipitation) <= 1.5
            and abs(pw_a.temperature - pw_b.temperature) <= 3.0
            and abs(pw_a.wind_speed - pw_b.wind_speed) <= 10.0
            and warning_count_a == 0
            and warning_count_b == 0
        )

        # Do not override explicit directional temperature request when temps differ
        if effective_goal in ["cooler", "warmer"] and abs(pw_a.temperature - pw_b.temperature) >= 0.5:
            is_broadly_similar = False

        if is_broadly_similar:
            decision = ComparisonDecision(
                recommended_location="Broadly Similar",
                recommended_key="equal",
                confidence="high",
                summary=f"Conditions in {loc_a_name} and {loc_b_name} are broadly similar during {period_str}.",
                winner_reason=f"Meteorological metrics for both locations ({pw_a.temperature}°C vs {pw_b.temperature}°C, rain {pw_a.precipitation_probability}% vs {pw_b.precipitation_probability}%) are within comparable ranges.",
                factors=factors,
            )
        else:
            # Deterministic Winner Evaluation
            score_a = 0
            score_b = 0

            # Alert penalty
            score_a -= warning_count_a * 5 + alert_count_a * 2
            score_b -= warning_count_b * 5 + alert_count_b * 2

            # Goal-specific scoring
            if effective_goal in ["rain", "travel", "outdoor_activity", "general"]:
                if prob_better == "a":
                    score_a += 3
                elif prob_better == "b":
                    score_b += 3

                if precip_better == "a":
                    score_a += 2
                elif precip_better == "b":
                    score_b += 2

                if wind_better == "a":
                    score_a += 1
                elif wind_better == "b":
                    score_b += 1

                # Extreme heat penalty for outdoor/travel
                if effective_goal in ["travel", "outdoor_activity"]:
                    if pw_a.temperature >= 38.0 or pw_a.temperature <= 2.0:
                        score_a -= 3
                    if pw_b.temperature >= 38.0 or pw_b.temperature <= 2.0:
                        score_b -= 3
            elif effective_goal == "cooler":
                if pw_a.temperature < pw_b.temperature:
                    score_a += 10
                elif pw_b.temperature < pw_a.temperature:
                    score_b += 10
            elif effective_goal == "warmer":
                if pw_a.temperature > pw_b.temperature:
                    score_a += 10
                elif pw_b.temperature > pw_a.temperature:
                    score_b += 10
            elif effective_goal == "temperature":
                if temp_better == "a":
                    score_a += 4
                elif temp_better == "b":
                    score_b += 4

            if score_a > score_b:
                winner_key = "a"
                winner_name = loc_a_name
                reasons = []
                if effective_goal == "cooler":
                    reasons.append(f"{loc_a_name} is cooler at {pw_a.temperature}°C compared with {loc_b_name} at {pw_b.temperature}°C")
                elif effective_goal == "warmer":
                    reasons.append(f"{loc_a_name} is warmer at {pw_a.temperature}°C compared with {loc_b_name} at {pw_b.temperature}°C")
                else:
                    if prob_better == "a":
                        reasons.append(f"lower rain probability ({pw_a.precipitation_probability}% vs {pw_b.precipitation_probability}%)")
                    if precip_better == "a":
                        reasons.append(f"less rainfall ({pw_a.precipitation} mm vs {pw_b.precipitation} mm)")
                    if alert_better == "a":
                        reasons.append("fewer severe weather risks")
                    if wind_better == "a":
                        reasons.append(f"calmer winds ({pw_a.wind_speed} km/h vs {pw_b.wind_speed} km/h)")
                    if not reasons:
                        reasons.append(f"more favorable overall conditions ({pw_a.temperature}°C vs {pw_b.temperature}°C)")

                winner_reason_str = f"{reasons[0]}." if effective_goal in ["cooler", "warmer"] else f"{loc_a_name} is preferable due to " + ", ".join(reasons) + "."
            elif score_b > score_a:
                winner_key = "b"
                winner_name = loc_b_name
                reasons = []
                if effective_goal == "cooler":
                    reasons.append(f"{loc_b_name} is cooler at {pw_b.temperature}°C compared with {loc_a_name} at {pw_a.temperature}°C")
                elif effective_goal == "warmer":
                    reasons.append(f"{loc_b_name} is warmer at {pw_b.temperature}°C compared with {loc_a_name} at {pw_a.temperature}°C")
                else:
                    if prob_better == "b":
                        reasons.append(f"lower rain probability ({pw_b.precipitation_probability}% vs {pw_a.precipitation_probability}%)")
                    if precip_better == "b":
                        reasons.append(f"less rainfall ({pw_b.precipitation} mm vs {pw_a.precipitation} mm)")
                    if alert_better == "b":
                        reasons.append("fewer severe weather risks")
                    if wind_better == "b":
                        reasons.append(f"calmer winds ({pw_b.wind_speed} km/h vs {pw_a.wind_speed} km/h)")
                    if not reasons:
                        reasons.append(f"more favorable overall conditions ({pw_b.temperature}°C vs {pw_a.temperature}°C)")

                winner_reason_str = f"{reasons[0]}." if effective_goal in ["cooler", "warmer"] else f"{loc_b_name} is preferable due to " + ", ".join(reasons) + "."
            else:
                winner_key = "equal"
                winner_name = "Broadly Similar"
                winner_reason_str = f"Conditions in {loc_a_name} and {loc_b_name} are comparable for {effective_goal.replace('_', ' ')} plans."

            confidence_level = "high" if abs(score_a - score_b) >= 3 else ("medium" if abs(score_a - score_b) >= 1 else "low")

            if effective_goal in ["cooler", "warmer"]:
                other_loc = loc_b_name if winner_key == "a" else loc_a_name
                winner_temp = pw_a.temperature if winner_key == "a" else pw_b.temperature
                other_temp = pw_b.temperature if winner_key == "a" else pw_a.temperature
                adj = "cooler" if effective_goal == "cooler" else "warmer"
                summary_text = f"{winner_name} is {adj} at {winner_temp}°C compared with {other_loc} at {other_temp}°C."
            elif winner_key != "equal":
                summary_text = f"{winner_name} is the recommended choice for your {effective_goal.replace('_', ' ')} plans during {period_str}."
            else:
                summary_text = f"Conditions in {loc_a_name} and {loc_b_name} are broadly similar during {period_str}."

            decision = ComparisonDecision(
                recommended_location=winner_name,
                recommended_key=winner_key,
                confidence=confidence_level,
                summary=summary_text,
                winner_reason=winner_reason_str,
                factors=factors,
            )

        return ComparisonResponse(
            location_a=location_a,
            location_b=location_b,
            target_period=period_str,
            period_weather_a=pw_a,
            period_weather_b=pw_b,
            decision=decision,
            alerts_a=alerts_a,
            alerts_b=alerts_b,
            comparison_goal=effective_goal,
        )


comparison_engine_service = ComparisonEngineService()
