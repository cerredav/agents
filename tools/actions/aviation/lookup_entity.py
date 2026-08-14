# This tool is used to get the weather for a given location
from typing import Literal
import requests

def lookup_entity(type: Literal['airport', 'airline', 'airplane', 'aircraft_type', 'city', 'country', 'taxes'] = None) -> str:
    """Entity catalogs lookup"""
    endpoint = ''
    match type:
        case 'airport': endpoint = '/v1/airports'
        case 'airline': endpoint = '/v1/airlines'
        case 'airplane': endpoint = '/v1/airplanes'
        case 'aircraft_type': endpoint = '/v1/aircraft_types'
        case 'city': endpoint = '/v1/cities'
        case 'country': endpoint = '/v1/countries'
        case 'taxes': endpoint = '/v1/taxes'

    base_url = f"https://api.aviationstack.com{endpoint}?access_key=1d4cd055836ebc6a34ea0d152f5c42f9"
    if type:
        base_url += f"&type={type}"

    response = requests.get(base_url)
    data = response.json()
    return data