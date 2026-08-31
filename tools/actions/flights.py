from typing import Literal

import requests


FlightStatus = Literal[
    "scheduled",
    "active",
    "landed",
    "cancelled",
    "incident",
    "diverted",
]


def get_flights(
    limit: int = None,
    offset: int = None,
    flight_status: FlightStatus = None,
    flight_date: str = None,
    dep_iata: str = None,
    arr_iata: str = None,
    dep_icao: str = None,
    arr_icao: str = None,
    airline_name: str = None,
    airline_iata: str = None,
    airline_icao: str = None,
    flight_number: int = None,
    flight_iata: str = None,
    flight_icao: str = None,
    min_delay_dep: int = None,
    min_delay_arr: int = None,
    max_delay_dep: int = None,
    max_delay_arr: int = None,
    arr_scheduled_time_arr: str = None,
    arr_scheduled_time_dep: str = None,
) -> dict:
    """Return real-time or historical flights matching the supplied filters."""
    params = {
        "access_key": "1d4cd055836ebc6a34ea0d152f5c42f9",
        "limit": limit,
        "offset": offset,
        "flight_status": flight_status,
        "flight_date": flight_date,
        "dep_iata": dep_iata,
        "arr_iata": arr_iata,
        "dep_icao": dep_icao,
        "arr_icao": arr_icao,
        "airline_name": airline_name,
        "airline_iata": airline_iata,
        "airline_icao": airline_icao,
        "flight_number": flight_number,
        "flight_iata": flight_iata,
        "flight_icao": flight_icao,
        "min_delay_dep": min_delay_dep,
        "min_delay_arr": min_delay_arr,
        "max_delay_dep": max_delay_dep,
        "max_delay_arr": max_delay_arr,
        "arr_scheduled_time_arr": arr_scheduled_time_arr,
        "arr_scheduled_time_dep": arr_scheduled_time_dep,
    }

    response = requests.get(
        "https://api.aviationstack.com/v1/flights",
        params={key: value for key, value in params.items() if value is not None},
    )
    return response.json()
