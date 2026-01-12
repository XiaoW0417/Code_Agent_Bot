"""
Core MCP Abstractions.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

@dataclass
class Tool:
    name: str
    description: str
    input_schema: Dict[str, Any]

class MCPServer(ABC):
    """
    Abstract Base Class for an MCP Server.
    A server exposes a set of tools (and potentially resources/prompts, but we focus on tools).
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def list_tools(self) -> List[Tool]:
        pass

    @abstractmethod
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        pass

class MCPClient:
    """
    Client to interact with multiple MCP Servers.
    """
    def __init__(self, servers: List[MCPServer]):
        self.servers = {s.name: s for s in servers}
        # Flattened tool map for easy access: tool_name -> server
        # Note: In real MCP, we might need namespacing if tool names conflict.
        # For this refactor, we assume unique tool names or we should namespace them.
        self._tool_map: Dict[str, MCPServer] = {}

    async def initialize(self):
        """Discover tools from all servers."""
        self._tool_map.clear()
        for server in self.servers.values():
            tools = await server.list_tools()
            for tool in tools:
                if tool.name in self._tool_map:
                    # Conflict!
                    # Strategy: Prefix with server name? Or raise error?
                    # Let's raise warning and overwrite for now, or namespace.
                    print(f"Warning: Tool {tool.name} defined in multiple servers. Overwriting.")
                self._tool_map[tool.name] = server

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        Return tools in OpenAI schema format for the Agent.
        """
        schemas = []
        for server in self.servers.values():
            tools = await server.list_tools()
            for tool in tools:
                schemas.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.input_schema
                    }
                })
        return schemas

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        if name not in self._tool_map:
            raise ValueError(f"Tool {name} not found.")
        
        server = self._tool_map[name]
        return await server.call_tool(name, arguments)
