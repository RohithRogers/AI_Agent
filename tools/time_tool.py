import datetime
from tools.registry import tool

@tool(
    name="get_current_time",
    description="Returns the current local time.",
    parameters={"type": "object", "properties": {}}
)
def get_current_time():
    return datetime.datetime.now().strftime("%I:%M %p")
