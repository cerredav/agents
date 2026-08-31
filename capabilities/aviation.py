from pathlib import Path
from utils.read_yml import read_yml
from utils.define_capabilities import define_capabilities

aviation_path = Path(__file__).parents[1] / "tools"
FLIGHTS_TOOL_PATH = aviation_path / "flights.yml"
AIRPORT_TIMETABLE_TOOL_PATH = aviation_path / "airport_timetable.yml"
LOOKUP_ENTITY_TOOL_PATH = aviation_path / "lookup_entity.yml"
ROUTES_TOOL_PATH = aviation_path / "routes.yml"
FUTURE_FLIGHT_SCHEDULE_TOOL_PATH = aviation_path / "future_flight_schedule.yml"



def define():
  """
  Define the capability
  """
  tools = []
  for t in [
    FLIGHTS_TOOL_PATH,
    AIRPORT_TIMETABLE_TOOL_PATH,
    LOOKUP_ENTITY_TOOL_PATH,
    ROUTES_TOOL_PATH,
    FUTURE_FLIGHT_SCHEDULE_TOOL_PATH
  ]:
    tools.append(
        read_yml(t)
    )
  return define_capabilities('aviation', tools)
