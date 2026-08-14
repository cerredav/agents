# This tool is used to get the weather for a given location
from typing import Literal
import requests

def get_future_flights(type: Literal['arrival', 'departure'] = None) -> str:
    """Future flight schedule lookup"""
    base_url = f"https://api.aviationstack.com/v1/flight_schedules?access_key=1d4cd055836ebc6a34ea0d152f5c42f9"
    if type:
        base_url += f"&type={type}"

    response = requests.get(base_url)
    data = response.json()
    return data