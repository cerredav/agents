from typing import Literal

import requests


ScheduleType = Literal["arrival", "departure"]


def get_future_flight_schedule(
    iataCode: str = None,
    type: ScheduleType = None,
    date: str = None,
    dep_iataCode: str = None,
    dep_icaoCode: str = None,
    arr_iataCode: str = None,
    arr_icaoCode: str = None,
    airline_iata: str = None,
    airline_icao: str = None,
    flight_num: int = None,
) -> dict:
    """Return an airport's arrival or departure schedule for a future date."""
    params = {
        "access_key": "1d4cd055836ebc6a34ea0d152f5c42f9",
        "iataCode": iataCode,
        "type": type,
        "date": date,
        "dep_iataCode": dep_iataCode,
        "dep_icaoCode": dep_icaoCode,
        "arr_iataCode": arr_iataCode,
        "arr_icaoCode": arr_icaoCode,
        "airline_iata": airline_iata,
        "airline_icao": airline_icao,
        "flight_num": flight_num,
    }
    response = requests.get(
        "https://api.aviationstack.com/v1/flightsFuture",
        params={key: value for key, value in params.items() if value is not None},
    )
    return response.json()
