# This tool is used to get the weather for a given location
import requests

def get_weather(latitude: float, longitude: float) -> str:
    """Get the weather for a given location"""
    base_url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,relative_humidity_2m,dew_point_2m,precipitation_probability,rain,pressure_msl,cloud_cover,visibility,wind_speed_10m,temperature_80m,soil_temperature_0cm&format=json&timeformat=unixtime" 
    response = requests.get(base_url)
    data = response.json()
    return data