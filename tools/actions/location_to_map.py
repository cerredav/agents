"""Open validated location data in Google Maps."""

from __future__ import annotations

import math
import webbrowser
from urllib.parse import quote_plus


DEFAULT_MAP_SPAN_M = 54_407


def build_google_maps_url(
    name: str,
    latitude: float,
    longitude: float,
    map_span_m: int = DEFAULT_MAP_SPAN_M,
) -> str:
    """Build the Google Maps place URL used by the web application."""
    location_name = name.strip() if isinstance(name, str) else ""
    if not location_name:
        raise ValueError("name must be a non-empty string")

    latitude = _coordinate(latitude, name="latitude", minimum=-90, maximum=90)
    longitude = _coordinate(longitude, name="longitude", minimum=-180, maximum=180)
    if isinstance(map_span_m, bool) or not isinstance(map_span_m, int) or map_span_m <= 0:
        raise ValueError("map_span_m must be a positive integer")

    encoded_name = quote_plus(location_name, safe="")
    return (
        f"https://www.google.com/maps/place/{encoded_name}/"
        f"@{latitude},{longitude},{map_span_m}m"
    )


def open_location_in_google_maps(
    name: str,
    latitude: float,
    longitude: float,
    map_span_m: int = DEFAULT_MAP_SPAN_M,
) -> dict[str, str | bool]:
    """Open a named coordinate in the default browser and report its URL."""
    url = build_google_maps_url(name, latitude, longitude, map_span_m)
    opened = webbrowser.open(url, new=2, autoraise=True)
    return {"url": url, "opened": opened}


def _coordinate(value: float, *, name: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number")
    coordinate = float(value)
    if not math.isfinite(coordinate) or not minimum <= coordinate <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return coordinate
