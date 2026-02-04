"""
Core exceptions for the Agent Bot.
Comprehensive exception hierarchy with error codes and HTTP status mapping.
"""
from typing import Optional, Dict, Any
from enum import Enum


class ErrorCode(str, Enum):
    """Standard error codes for the application."""
    # General errors (1000-1099)
    UNKNOWN_ERROR = "E1000"
    VALIDATION_ERROR = "E1001"
    NOT_FOUND = "E1002"
    ALREADY_EXISTS = "E1003"
    
    # Authentication errors (1100-1199)
    AUTHENTICATION_FAILED = "E1100"
    INVALID_TOKEN = "E1101"
    TOKEN_EXPIRED = "E1102"
    UNAUTHORIZED = "E1103"
    FORBIDDEN = "E1104"
    
    # Configuration errors (1200-1299)
    CONFIG_ERROR = "E1200"
    MISSING_API_KEY = "E1201"
    INVALID_CONFIG = "E1202"
    
    # Tool errors (1300-1399)
    TOOL_NOT_FOUND = "E1300"
    TOOL_EXECUTION_ERROR = "E1301"
    TOOL_TIMEOUT = "E1302"
    
    # LLM errors (1400-1499)
    LLM_ERROR = "E1400"
    LLM_RATE_LIMIT = "E1401"
    LLM_CONTEXT_LENGTH = "E1402"
    MODEL_RESPONSE_ERROR = "E1403"
    
    # Session errors (1500-1599)
    SESSION_NOT_FOUND = "E1500"
    SESSION_EXPIRED = "E1501"
    
    # File system errors (1600-1699)
    FILE_NOT_FOUND = "E1600"
    FILE_ACCESS_DENIED = "E1601"
    PATH_OUTSIDE_SANDBOX = "E1602"


class AgentError(Exception):
    """
    Base exception for all agent-related errors.
    
    Attributes:
        message: Human-readable error message
        code: Machine-readable error code
        details: Additional error context
        http_status: Suggested HTTP status code
    """
    def __init__(
        self, 
        message: str,
        code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        details: Optional[Dict[str, Any]] = None,
        http_status: int = 500
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.http_status = http_status

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "details": self.details
            }
        }


class ConfigError(AgentError):
    """Configuration related errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code=ErrorCode.CONFIG_ERROR,
            details=details,
            http_status=500
        )


class AuthenticationError(AgentError):
    """Authentication related errors."""
    def __init__(
        self, 
        message: str = "Authentication failed",
        code: ErrorCode = ErrorCode.AUTHENTICATION_FAILED,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code=code,
            details=details,
            http_status=401
        )


class AuthorizationError(AgentError):
    """Authorization related errors."""
    def __init__(
        self, 
        message: str = "Not authorized to perform this action",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code=ErrorCode.FORBIDDEN,
            details=details,
            http_status=403
        )


class ValidationError(AgentError):
    """Validation related errors."""
    def __init__(
        self, 
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code=ErrorCode.VALIDATION_ERROR,
            details=details,
            http_status=422
        )


class NotFoundError(AgentError):
    """Resource not found errors."""
    def __init__(
        self, 
        resource: str,
        identifier: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} '{identifier}' not found"
        super().__init__(
            message=message,
            code=ErrorCode.NOT_FOUND,
            details=details,
            http_status=404
        )


class ToolError(AgentError):
    """Base class for tool-related errors."""
    def __init__(
        self,
        message: str,
        tool_name: str,
        code: ErrorCode = ErrorCode.TOOL_EXECUTION_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        details["tool_name"] = tool_name
        super().__init__(
            message=message,
            code=code,
            details=details,
            http_status=500
        )


class ToolNotFoundError(ToolError):
    """Raised when a requested tool is not found."""
    def __init__(self, tool_name: str):
        super().__init__(
            message=f"Tool '{tool_name}' not found",
            tool_name=tool_name,
            code=ErrorCode.TOOL_NOT_FOUND,
            http_status=404
        )
        # Override http_status after parent init
        self.http_status = 404


class ToolExecutionError(ToolError):
    """Raised when a tool fails to execute."""
    def __init__(self, tool_name: str, error_msg: str):
        super().__init__(
            message=f"Error executing tool '{tool_name}': {error_msg}",
            tool_name=tool_name,
            code=ErrorCode.TOOL_EXECUTION_ERROR
        )


class ModelResponseError(AgentError):
    """Raised when the model response is invalid or fails."""
    def __init__(
        self, 
        message: str = "Model response error",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code=ErrorCode.MODEL_RESPONSE_ERROR,
            details=details,
            http_status=502
        )


class RateLimitError(AgentError):
    """Raised when rate limit is exceeded."""
    def __init__(
        self, 
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None
    ):
        details = {}
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(
            message=message,
            code=ErrorCode.LLM_RATE_LIMIT,
            details=details,
            http_status=429
        )


class SessionError(AgentError):
    """Session related errors."""
    def __init__(
        self, 
        message: str,
        session_id: Optional[str] = None,
        code: ErrorCode = ErrorCode.SESSION_NOT_FOUND
    ):
        details = {}
        if session_id:
            details["session_id"] = session_id
        super().__init__(
            message=message,
            code=code,
            details=details,
            http_status=404 if code == ErrorCode.SESSION_NOT_FOUND else 400
        )


class FileSystemError(AgentError):
    """File system related errors."""
    def __init__(
        self, 
        message: str,
        path: Optional[str] = None,
        code: ErrorCode = ErrorCode.FILE_NOT_FOUND
    ):
        details = {}
        if path:
            details["path"] = path
        super().__init__(
            message=message,
            code=code,
            details=details,
            http_status=404 if code == ErrorCode.FILE_NOT_FOUND else 403
        )
