# This tool is used to get the weather for a given location
import requests

def get_geocode(location: str) -> str:
    """Get the weather for a given location"""
    base_url = f" https://nominatim.openstreetmap.org/search?q={location}&format=json" 
    headers = {
        'User-Agent': 'weather-agent/1.0'
    }
    response = requests.get(base_url, headers=headers)
    if response.status_code != 200:
        print(f"Error getting geocode for {location}: {response.text}")
        return None
    data = response.json()
    if not data:
        return None
    return data[0]