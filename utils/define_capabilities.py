
def define(capability_name: str, tool_list: list):
  """
  Define the capability
  """
  tools = {}
  for tool in [tool_list]:
    tools[tool.get('name')] = {
      "description": tool.get('description'),
      "parameters": tool.get('parameters'),
    }

  return {
    'capability': capability_name,
    'tools': tools
  }