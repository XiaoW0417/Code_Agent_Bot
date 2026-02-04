"""
Dependency Injection Container.
Provides centralized dependency management for the application.
"""
from typing import Optional, Dict, Any, Type, TypeVar
from dataclasses import dataclass
import logging

from src.core.llm.base import LLMProvider, LLMConfig
from src.core.mcp.base import MCPClient, MCPServer
from src.core.skills.registry import SkillRegistry, registry as default_registry

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class Container:
    """
    Dependency Injection Container.
    Manages the lifecycle of application dependencies.
    """
    _llm_provider: Optional[LLMProvider] = None
    _mcp_client: Optional[MCPClient] = None
    _skill_registry: Optional[SkillRegistry] = None
    _config: Optional[Dict[str, Any]] = None
    _initialized: bool = False

    def __post_init__(self):
        self._services: Dict[Type, Any] = {}

    @property
    def llm(self) -> LLMProvider:
        """Get the LLM provider instance."""
        if self._llm_provider is None:
            raise RuntimeError("LLM Provider not initialized. Call container.initialize() first.")
        return self._llm_provider

    @property
    def mcp_client(self) -> MCPClient:
        """Get the MCP client instance."""
        if self._mcp_client is None:
            raise RuntimeError("MCP Client not initialized. Call container.initialize() first.")
        return self._mcp_client

    @property
    def skill_registry(self) -> SkillRegistry:
        """Get the skill registry instance."""
        if self._skill_registry is None:
            return default_registry
        return self._skill_registry

    def register(self, service_type: Type[T], instance: T) -> None:
        """Register a service instance."""
        self._services[service_type] = instance

    def resolve(self, service_type: Type[T]) -> T:
        """Resolve a service instance by type."""
        if service_type not in self._services:
            raise KeyError(f"Service {service_type.__name__} not registered.")
        return self._services[service_type]

    def has(self, service_type: Type[T]) -> bool:
        """Check if a service is registered."""
        return service_type in self._services

    async def initialize(
        self,
        llm_config: LLMConfig,
        mcp_servers: list[MCPServer],
        skill_registry: Optional[SkillRegistry] = None
    ) -> None:
        """
        Initialize all dependencies.
        
        Args:
            llm_config: Configuration for the LLM provider
            mcp_servers: List of MCP servers to initialize
            skill_registry: Optional custom skill registry
        """
        if self._initialized:
            logger.warning("Container already initialized. Skipping.")
            return

        # Initialize LLM Provider
        from src.infra.llm.openai import OpenAIProvider
        self._llm_provider = OpenAIProvider(llm_config)
        logger.info(f"LLM Provider initialized with model: {llm_config.model}")

        # Initialize MCP Client
        self._mcp_client = MCPClient(mcp_servers)
        await self._mcp_client.initialize()
        logger.info(f"MCP Client initialized with {len(mcp_servers)} servers")

        # Initialize Skill Registry
        self._skill_registry = skill_registry or default_registry
        logger.info(f"Skill Registry initialized with {len(self._skill_registry.list_skills())} skills")

        self._initialized = True

    async def shutdown(self) -> None:
        """Cleanup resources."""
        self._llm_provider = None
        self._mcp_client = None
        self._initialized = False
        logger.info("Container shutdown complete.")

    @property
    def is_initialized(self) -> bool:
        return self._initialized


# Global container instance (singleton)
container = Container()
