"""Resolve named locations with OpenStreetMap Nominatim."""

import requests


def get_geocode(location: str) -> dict | None:
    """Return coordinates and, when available, the location's IATA code."""
    base_url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": location,
        "format": "json",
        "extratags": 1,
    }
    headers = {
        'User-Agent': 'weather-agent/1.0'
    }
    response = requests.get(base_url, params=params, headers=headers)
    if response.status_code != 200:
        print(f"Error getting geocode for {location}: {response.text}")
        return None
    data = response.json()
    if not data:
        return None

    result = data[0]
    extra_tags = result.get("extratags") or {}
    result["iata_code"] = extra_tags.get("iata")
    return result
