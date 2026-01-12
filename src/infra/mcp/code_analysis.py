"""
CodeAnalysis MCP Server.
"""
from typing import Any, Dict, List

from src.core.mcp.base import MCPServer, Tool
from src.infra.tools.code_analysis import (
    search_in_files, run_pytest, 
    SEARCH_IN_FILE_TOOL_SCHEMA, RUN_PYTEST_TOOL_SCHEMA
)

class CodeAnalysisServer(MCPServer):
    @property
    def name(self) -> str:
        return "code_analysis"

    async def list_tools(self) -> List[Tool]:
        tools = []
        schemas = [SEARCH_IN_FILE_TOOL_SCHEMA, RUN_PYTEST_TOOL_SCHEMA]
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
            "search_in_files": search_in_files,
            "run_pytest": run_pytest
        }
        if name not in mapping:
            raise ValueError(f"Unknown tool: {name}")
        
        return await mapping[name](**arguments)
