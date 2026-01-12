"""
External Services MCP Server.
"""
from typing import Any, Dict, List

from src.core.mcp.base import MCPServer, Tool
from src.infra.tools.external.weather import get_current_weather, WEATHER_TOOL_SCHEMA
from src.infra.tools.external.fx import get_exchange_rate, FX_TOOL_SCHEMA
from src.infra.tools.external.wiki import get_wikipedia_summary, WIKI_TOOL_SCHEMA
from src.infra.tools.external.timez import get_timezone_time, TIMEZ_TOOL_SCHEMA

class ExternalServicesServer(MCPServer):
    @property
    def name(self) -> str:
        return "external_services"

    async def list_tools(self) -> List[Tool]:
        tools = []
        schemas = [WEATHER_TOOL_SCHEMA, FX_TOOL_SCHEMA, WIKI_TOOL_SCHEMA, TIMEZ_TOOL_SCHEMA]
        for schema in schemas:
            fn = schema["function"]
            tools.append(Tool(
                name=fn["name"],
                description=fn["description"],
                input_schema=fn["parameters"]
            ))
        return tools

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        mapping = {
            "get_current_weather": get_current_weather,
            "get_exchange_rate": get_exchange_rate,
            "get_wikipedia_summary": get_wikipedia_summary,
            "get_timezone_time": get_timezone_time
        }
        if name not in mapping:
            raise ValueError(f"Unknown tool: {name}")
        
        return await mapping[name](**arguments)
