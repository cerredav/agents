import requests


def get_routes(
    limit: int = None,
    offset: int = None,
    dep_iata: str = None,
    dep_icao: str = None,
    arr_iata: str = None,
    arr_icao: str = None,
    airline_iata: str = None,
    airline_icao: str = None,
    flight_number: int = None,
    flight_iata: str = None,
    flight_icao: str = None,
) -> dict:
    """Return airline routes matching the supplied filters."""
    params = {
        "access_key": "1d4cd055836ebc6a34ea0d152f5c42f9",
        "limit": limit,
        "offset": offset,
        "dep_iata": dep_iata,
        "dep_icao": dep_icao,
        "arr_iata": arr_iata,
        "arr_icao": arr_icao,
        "airline_iata": airline_iata,
        "airline_icao": airline_icao,
        "flight_number": flight_number,
        "flight_iata": flight_iata,
        "flight_icao": flight_icao,
    }
    response = requests.get(
        "https://api.aviationstack.com/v1/routes",
        params={key: value for key, value in params.items() if value is not None},
    )
    return response.json()
