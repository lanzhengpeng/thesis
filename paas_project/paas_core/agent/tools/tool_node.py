from langgraph.prebuilt import ToolNode

from .calculator import calculator
from .database import query_database
from .search import search
from .weather import get_weather

TOOLS = [calculator, get_weather, search, query_database]

tool_node = ToolNode(TOOLS)
