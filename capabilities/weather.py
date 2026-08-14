from pathlib import Path
from utils.read_yml import read_yml
from utils.define_capabilities import define

WEATHER_TOOL_PATH = Path(__file__).parents[1] / "tools" / "weather.yml"
GEOCODE_TOOL_PATH = Path(__file__).parents[1] / "tools" / "geocode.yml"


def define():
  """
  Define the capability
  """
  weather_tool = read_yml(WEATHER_TOOL_PATH)
  geocode_tool = read_yml(GEOCODE_TOOL_PATH)
  return define('weather', [weather_tool, geocode_tool])