"""Resolve named locations and their nearest relevant airports."""

from __future__ import annotations

import csv
import io
import math
import re
from functools import lru_cache
from typing import Any

import requests


NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
AIRPORTS_CSV_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
USER_AGENT = "weather-agent/1.0"
IATA_CODE = re.compile(r"^[A-Z]{3}$")
EARTH_RADIUS_KM = 6_371.0088


def get_geocode(location: str) -> dict:
    """Return location coordinates and the nearest relevant airport."""
    normalized_location = location.strip() if isinstance(location, str) else ""
    if not normalized_location:
        raise ValueError("location must be a non-empty string")

    params = {
        "q": normalized_location,
        "format": "jsonv2",
        "extratags": 1,
        "limit": 1,
    }
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(
        NOMINATIM_SEARCH_URL,
        params=params,
        headers=headers,
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list) or not data:
        raise LookupError(f"Location could not be resolved: {normalized_location}")

    result = data[0]
    latitude = float(result["lat"])
    longitude = float(result["lon"])
    result["latitude"] = latitude
    result["longitude"] = longitude
    result.update(
        _resolve_airport_for_coordinates(
            latitude,
            longitude,
            query=normalized_location,
        )
    )
    return result


def _resolve_airport_for_coordinates(
    latitude: float,
    longitude: float,
    *,
    query: str,
) -> dict[str, Any]:
    candidates = _rank_airports(latitude, longitude, _load_airports())
    if not candidates:
        raise LookupError(f"No airport with an IATA code was found near: {query}")

    airport, distance_km = candidates[0]
    return {
        "airport_name": airport["name"],
        "iata_code": airport["iata_code"],
        "airport_latitude": float(airport["latitude_deg"]),
        "airport_longitude": float(airport["longitude_deg"]),
        "municipality": airport.get("municipality") or None,
        "distance_km": round(distance_km, 2),
        "airport_source": "OurAirports",
    }


@lru_cache(maxsize=1)
def _load_airports() -> tuple[dict[str, str], ...]:
    response = requests.get(
        AIRPORTS_CSV_URL,
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    response.raise_for_status()
    return tuple(csv.DictReader(io.StringIO(response.text)))


def _rank_airports(
    latitude: float,
    longitude: float,
    airports: tuple[dict[str, str], ...],
) -> list[tuple[dict[str, str], float]]:
    ranked: list[tuple[tuple[int, float], dict[str, str], float]] = []
    for airport in airports:
        iata_code = airport.get("iata_code", "").upper().strip()
        if not IATA_CODE.fullmatch(iata_code):
            continue
        try:
            distance = _haversine(
                latitude,
                longitude,
                float(airport["latitude_deg"]),
                float(airport["longitude_deg"]),
            )
        except (KeyError, TypeError, ValueError):
            continue

        airport_type = airport.get("type")
        scheduled = airport.get("scheduled_service") == "yes"
        if airport_type == "large_airport" and distance <= 250:
            tier = 0
        elif scheduled and airport_type == "medium_airport" and distance <= 150:
            tier = 1
        elif scheduled:
            tier = 2
        else:
            tier = 3
        normalized_airport = {**airport, "iata_code": iata_code}
        ranked.append(((tier, distance), normalized_airport, distance))

    ranked.sort(key=lambda item: item[0])
    return [(airport, distance) for _, airport, distance in ranked]


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(value))
