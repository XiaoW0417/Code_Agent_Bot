"""
Tool routing and execution.
"""
import json
import logging
from typing import Any, Dict, List, Callable, Awaitable

from src.core.exceptions import ToolNotFoundError, ToolExecutionError

logger = logging.getLogger(__name__)

class ToolRegistry:
    """
    Registry for available tools and their implementations.
    """
    def __init__(self, schemas: List[dict], functions: Dict[str, Callable[..., Awaitable[Any]]]):
        self.schemas = schemas
        self.functions = functions

    def get_tool_schemas(self) -> List[dict]:
        return self.schemas

    async def call_tool(self, tool_name: str, arguments_json: str) -> Any:
        """
        Execute a tool by name with JSON arguments.
        """
        logger.info(f"Calling tool: {tool_name}...")

        if tool_name not in self.functions:
            logger.error(f"Unknown tool: {tool_name}")
            raise ToolNotFoundError(tool_name)
        
        try:
            arguments = json.loads(arguments_json)
            if not isinstance(arguments, dict):
                raise ValueError("Arguments must be a JSON object.")
        except (json.JSONDecodeError, ValueError) as e:
            error_msg = f"Failed to parse arguments for '{tool_name}': {e}. Args: '{arguments_json}'"
            logger.error(error_msg)
            raise ToolExecutionError(tool_name, error_msg)

        tool_function = self.functions.get(tool_name)

        try:
            # We assume tool_function is async based on existing codebase
            result = await tool_function(**arguments)
            logger.info(f"Tool '{tool_name}' executed successfully.")
            return result
        except TypeError as e:
            error_msg = f"Argument mismatch for tool '{tool_name}': {e}"
            logger.error(error_msg)
            raise ToolExecutionError(tool_name, error_msg)
        except ToolExecutionError:
            raise
        except Exception as e:
            error_msg = f"Unknown error executing tool '{tool_name}': {e}"
            logger.error(error_msg, exc_info=True)
            raise ToolExecutionError(tool_name, error_msg)
