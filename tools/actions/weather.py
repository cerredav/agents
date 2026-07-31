# This tool is used to get the weather for a given location
import requests

def get_weather(latitude: float, longitude: float) -> str:
    """Get the weather for a given location"""
    base_url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,wind_speed_10m&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m" 
    response = requests.get(base_url)
    data = response.json()
    return data.get('current', {})