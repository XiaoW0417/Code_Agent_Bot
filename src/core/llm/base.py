"""
Abstract Base Class for LLM Providers.
"""
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from dataclasses import dataclass

@dataclass
class LLMConfig:
    """Configuration for LLM Provider."""
    api_key: str
    base_url: Optional[str] = None
    model: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    timeout: float = 60.0

@dataclass
class Message:
    """Standardized Message format."""
    role: str
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None

class LLMProvider(ABC):
    """Interface for LLM Providers."""

    def __init__(self, config: LLMConfig):
        self.config = config

    @abstractmethod
    async def chat_complete(
        self, 
        messages: List[Dict[str, Any]], 
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Any = "auto"
    ) -> Any:
        """
        Send a chat completion request.
        Returns the raw response object (provider specific) or a standardized response.
        For now, we return the standardized Message object or similar structure.
        """
        pass

    @abstractmethod
    async def chat_stream(
        self, 
        messages: List[Dict[str, Any]], 
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Any = "auto"
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat completion content.
        Yields chunks of content strings.
        """
        pass

    @property
    def model_name(self) -> str:
        return self.config.model
