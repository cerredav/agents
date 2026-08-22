from typing import Literal

import requests


ScheduleType = Literal["arrival", "departure"]
ScheduleStatus = Literal[
    "scheduled",
    "active",
    "landed",
    "cancelled",
    "unknown",
    "diverted",
]


def get_future_flights(
    iataCode: str,
    type: ScheduleType,
    status: ScheduleStatus = None,
    airline_name: str = None,
    airline_iata: str = None,
    airline_icao: str = None,
    flight_num: int = None,
    flight_iata: str = None,
    flight_icao: str = None,
    codeshared: str = None,
) -> dict:
    """Return the live arrival or departure timetable for an airport."""
    params = {
        "access_key": "1d4cd055836ebc6a34ea0d152f5c42f9",
        "iataCode": iataCode,
        "type": type,
        "status": status,
        "airline_name": airline_name,
        "airline_iata": airline_iata,
        "airline_icao": airline_icao,
        "flight_num": flight_num,
        "flight_iata": flight_iata,
        "flight_icao": flight_icao,
        "codeshared": codeshared,
    }
    response = requests.get(
        "https://api.aviationstack.com/v1/timetable",
        params={key: value for key, value in params.items() if value is not None},
    )
    return response.json()
