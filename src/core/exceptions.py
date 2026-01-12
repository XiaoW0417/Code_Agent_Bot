"""
Core exceptions for the Agent Bot.
"""

class AgentError(Exception):
    """Base exception for all agent-related errors."""
    pass

class ConfigError(AgentError):
    """Configuration related errors."""
    pass

class ToolError(AgentError):
    """Base class for tool-related errors."""
    pass

class ToolNotFoundError(ToolError):
    """Raised when a requested tool is not found."""
    def __init__(self, tool_name: str):
        super().__init__(f"Tool '{tool_name}' not found.")

class ToolExecutionError(ToolError):
    """Raised when a tool fails to execute."""
    def __init__(self, tool_name: str, error_msg: str):
        super().__init__(f"Error executing tool '{tool_name}': {error_msg}")

class ModelResponseError(AgentError):
    """Raised when the model response is invalid or fails."""
    pass
