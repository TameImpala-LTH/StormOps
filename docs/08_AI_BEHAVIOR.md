# 08_AI_BEHAVIOR.md

# AI Behavior

## 1. Purpose

This document defines how the AI component of WeatherGPT should behave when interpreting user requests and generating responses.

---

## 2. Core Principle

WeatherGPT is an intelligence layer over meteorological data.

The AI may interpret, summarize, compare, explain, and reason from available weather data.

The AI must **never invent weather facts**.

---

## 3. What the AI Should Understand

The AI should extract relevant information from natural-language queries, including:

- User intent
- Location
- Date or time
- Relevant weather metrics
- Decision being requested
- Comparison requirements
- Language preference

Example:

> "Should I take an umbrella to Kolkata tomorrow evening?"

The system should understand:

```text
Intent: Decision
Location: Kolkata
Time: Tomorrow evening
Decision: Carry umbrella
Relevant data: Rain probability, precipitation, weather condition