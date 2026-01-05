# src/agent/tools/__init__.py

from .weather import get_current_weather, WEATHER_TOOL_SCHEMA
from .fx import get_exchange_rate, FX_TOOL_SCHEMA
from .wiki import get_wikipedia_summary, WIKI_TOOL_SCHEMA
from .timez import get_timezone_time, TIMEZ_TOOL_SCHEMA

# 导出所有工具的 schema
ALL_TOOLS = [
    WEATHER_TOOL_SCHEMA,
    FX_TOOL_SCHEMA,
    WIKI_TOOL_SCHEMA,
    TIMEZ_TOOL_SCHEMA,
]

# 导出一个从工具名到调用函数的映射
TOOL_FUNCTIONS = {
    "get_current_weather": get_current_weather,
    "get_exchange_rate": get_exchange_rate,
    "get_wikipedia_summary": get_wikipedia_summary,
    "get_timezone_time": get_timezone_time,
}
