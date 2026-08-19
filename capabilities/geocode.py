from pathlib import Path
from utils.read_yml import read_yml
from utils.define_capabilities import define_capabilities

GEOCODE_TOOL_PATH = Path(__file__).parents[1] / "tools" / "geocode.yml"


def define():
  """
  Define the capability
  """
  geocode_tool = read_yml(GEOCODE_TOOL_PATH)
  return define_capabilities('geocode', [geocode_tool])