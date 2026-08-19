from pathlib import Path
from utils.read_yml import read_yml
from utils.define_capabilities import define_capabilities

ASK_TOOL_PATH = Path(__file__).parents[1] / "tools" / "ask.yml"


def define():
  """
  Define the capability
  """
  ask_tool = read_yml(ASK_TOOL_PATH)
  return define_capabilities('ask', [ask_tool])