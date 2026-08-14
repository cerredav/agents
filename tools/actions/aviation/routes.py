# This tool is used to get the weather for a given location
from typing import Literal
import requests

def get_routes() -> str:
    """Airline route metadata"""
    base_url = f"https://api.aviationstack.com/v1/routes?access_key=1d4cd055836ebc6a34ea0d152f5c42f9"

    response = requests.get(base_url)
    data = response.json()
    return data