"""
Base Skill definition.
A Skill is a high-level capability exposed to the Agent.
It wraps one or more low-level tools (MCP) and provides a semantic interface.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

@dataclass
class SkillSchema:
    name: str
    description: str
    parameters: Dict[str, Any]

class Skill(ABC):
    name: str
    description: str
    
    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """JSON Schema for parameters."""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the skill."""
        pass

    def to_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI Tool Schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
