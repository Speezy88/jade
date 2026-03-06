#!/usr/bin/env python3
"""
integrations/weather.py

Fetch current weather for Seattle from OpenWeatherMap free tier.
Returns a formatted string for the morning briefing.
Never raises — returns "Weather unavailable." on any error.
"""

import os
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path("/Users/spencerhatch/Jade/.env"))

_URL = "https://api.openweathermap.org/data/2.5/weather"
_LAT = 47.6062
_LON = -122.3321


def get_weather() -> str:
    """
    Returns:
        "52°F, overcast. High 58°F."
        "Weather unavailable." on any error.
    """
    api_key = os.getenv("OPENWEATHERMAP_API_KEY")
    if not api_key:
        return "Weather unavailable."

    try:
        resp = requests.get(
            _URL,
            params={"lat": _LAT, "lon": _LON, "units": "imperial", "appid": api_key},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()

        temp        = round(data["main"]["temp"])
        high        = round(data["main"]["temp_max"])
        description = data["weather"][0]["description"]

        return f"{temp}°F, {description}. High {high}°F."

    except Exception:
        return "Weather unavailable."
