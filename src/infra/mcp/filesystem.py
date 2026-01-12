"""
FileSystem MCP Server.
"""
from typing import Any, Dict, List

from src.core.mcp.base import MCPServer, Tool
from src.infra.tools.filesystem import (
    read_file, list_files, write_file, apply_patch, delete_file, delete_directory,
    LIST_FILES_TOOL_SCHEMA, READ_FILE_TOOL_SCHEMA, WRITE_FILE_TOOL_SCHEMA, 
    APPLY_PATCH_TOOL_SCHEMA, DELETE_FILE_TOOL_SCHEMA, DELETE_DIRECTORY_TOOL_SCHEMA
)

class FileSystemServer(MCPServer):
    @property
    def name(self) -> str:
        return "filesystem"

    async def list_tools(self) -> List[Tool]:
        # Convert schemas to Tool objects
        tools = []
        schemas = [
            LIST_FILES_TOOL_SCHEMA, READ_FILE_TOOL_SCHEMA, WRITE_FILE_TOOL_SCHEMA,
            APPLY_PATCH_TOOL_SCHEMA, DELETE_FILE_TOOL_SCHEMA, DELETE_DIRECTORY_TOOL_SCHEMA
        ]
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
            "read_file": read_file,
            "list_files": list_files,
            "write_file": write_file,
            "apply_patch": apply_patch,
            "delete_file": delete_file,
            "delete_directory": delete_directory
        }
        if name not in mapping:
            raise ValueError(f"Unknown tool: {name}")
        
        return await mapping[name](**arguments)
