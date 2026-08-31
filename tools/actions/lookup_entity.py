from typing import Literal

import requests


EntityType = Literal[
    "airport",
    "airline",
    "airplane",
    "aircraft_type",
    "city",
    "country",
    "taxes",
]

ENTITY_ENDPOINTS = {
    "airport": "airports",
    "airline": "airlines",
    "airplane": "airplanes",
    "aircraft_type": "aircraft_types",
    "city": "cities",
    "country": "countries",
    "taxes": "taxes",
}


def lookup_entity(
    type: EntityType,
    limit: int = None,
    offset: int = None,
) -> dict:
    """Return a paginated Aviationstack entity catalog."""
    endpoint = ENTITY_ENDPOINTS[type]
    params = {
        "access_key": "1d4cd055836ebc6a34ea0d152f5c42f9",
        "limit": limit,
        "offset": offset,
    }
    response = requests.get(
        f"https://api.aviationstack.com/v1/{endpoint}",
        params={key: value for key, value in params.items() if value is not None},
    )
    return response.json()
