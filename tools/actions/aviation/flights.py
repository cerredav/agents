# This tool is used to get the weather for a given location
import requests

def get_flights(flight_date: str = None) -> str:
    """Real‑time or historical flights"""
    base_url = f"https://api.aviationstack.com/v1/flights?access_key=1d4cd055836ebc6a34ea0d152f5c42f9"
    if flight_date:
        base_url += f"&flight_date={flight_date}"

    response = requests.get(base_url)
    data = response.json()
    return data