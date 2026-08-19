from pathlib import Path
from utils.read_yml import read_yml
from utils.define_capabilities import define_capabilities

aviation_path = Path(__file__).parents[1] / "tools" / "aviation"
FLIGHTS_TOOL_PATH = aviation_path / "flights.yml"
FUTURE_FLIGHTS_TOOL_PATH = aviation_path / "future_flights.yml"
LOOKUP_ENTITY_TOOL_PATH = aviation_path / "lookup_entity.yml"
ROUTES_TOOL_PATH = aviation_path / "routes.yml"
SCHEDULED_FLIGHTS_TOOL_PATH = aviation_path / "schedule_flights.yml"



def define():
  """
  Define the capability
  """
  tools = []
  for t in [
    FLIGHTS_TOOL_PATH,
    FUTURE_FLIGHTS_TOOL_PATH,
    LOOKUP_ENTITY_TOOL_PATH,
    ROUTES_TOOL_PATH,
    SCHEDULED_FLIGHTS_TOOL_PATH
  ]:
    tools.append(
        read_yml(t)
    )
  return define_capabilities('aviation', tools)