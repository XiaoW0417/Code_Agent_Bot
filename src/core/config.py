"""
Configuration management for the Agent Bot.
Enhanced with validation, environment profiles, and security features.
"""
import os
import logging
import secrets
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Set, Literal
from functools import lru_cache

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Environment type
EnvironmentType = Literal["development", "testing", "production"]


@dataclass
class DatabaseConfig:
    """Database configuration."""
    url: str = "sqlite:///./data/agent_bot.db"
    echo: bool = False  # SQL logging
    pool_size: int = 5
    max_overflow: int = 10


@dataclass
class AuthConfig:
    """Authentication configuration."""
    secret_key: str = field(default_factory=lambda: secrets.token_hex(32))
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours
    refresh_token_expire_days: int = 7


@dataclass
class CORSConfig:
    """CORS configuration."""
    allow_origins: list[str] = field(default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"])
    allow_credentials: bool = True
    allow_methods: list[str] = field(default_factory=lambda: ["*"])
    allow_headers: list[str] = field(default_factory=lambda: ["*"])


@dataclass
class Settings:
    """Application settings with enhanced configuration."""
    # Environment
    environment: EnvironmentType = "development"
    debug: bool = False
    
    # API Keys
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    model_name: str = "gpt-3.5-turbo"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Paths
    root_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parents[2])
    sandbox_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parents[2] / "sandbox")
    data_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parents[2] / "data")
    
    # Sub-configs
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    cors: CORSConfig = field(default_factory=CORSConfig)
    
    # Global Exclusion Configuration
    ignore_dirs: Set[str] = field(default_factory=lambda: {
        # SCM
        ".git", ".svn", ".hg",
        # IDEs
        ".idea", ".vscode", ".vs",
        # Python
        "__pycache__", ".venv", "venv", "env", "site-packages", ".pytest_cache", ".mypy_cache",
        # Node.js
        "node_modules", "bower_components",
        # Build artifacts
        "build", "dist", "target", "out",
        # Dependencies
        "libs", "lib", "vendor",
        # Misc
        ".DS_Store", "logs", "tmp", "temp"
    })
    
    ignore_extensions: Set[str] = field(default_factory=lambda: {
        # Compiled / Binary
        ".pyc", ".pyo", ".pyd", ".so", ".dll", ".dylib", ".class", ".o", ".obj", ".exe", ".bin",
        # Images / Assets
        ".jpg", ".jpeg", ".png", ".gif", ".ico", ".svg", ".bmp", ".tiff", ".webp",
        # Archives
        ".zip", ".tar", ".gz", ".rar", ".7z", ".whl", ".egg",
        # Docs / Misc
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".lock"
    })

    @property
    def is_valid(self) -> bool:
        """Check if essential configuration is present."""
        return bool(self.openai_api_key)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    def __post_init__(self):
        """Post-initialization setup."""
        # Ensure directories exist
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Update database URL to use data directory
        if "sqlite" in self.database.url and self.database.url == "sqlite:///./data/agent_bot.db":
            self.database.url = f"sqlite:///{self.data_dir}/agent_bot.db"


@lru_cache()
def load_settings() -> Settings:
    """
    Load settings from environment variables.
    Uses lru_cache for singleton behavior.
    """
    # Determine root directory
    root_dir = Path(__file__).resolve().parents[2]
    env_path = root_dir / '.env'
    
    # Load .env file if exists
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)

    # Determine environment
    environment = os.getenv('ENVIRONMENT', 'development')
    if environment not in ('development', 'testing', 'production'):
        environment = 'development'

    # Load API configuration
    api_key = os.getenv('OPENAI_API_KEY')
    base_url = os.getenv('OPENAI_BASE_URL')
    model_name = os.getenv('OPENAI_MODEL_NAME', 'gpt-3.5-turbo')
    
    # Load server configuration
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '8000'))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    # Load auth configuration
    secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))
    access_token_expire = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '1440'))
    
    # Load database configuration
    database_url = os.getenv('DATABASE_URL', f"sqlite:///{root_dir}/data/agent_bot.db")
    
    # Build settings
    settings = Settings(
        environment=environment,
        debug=debug,
        openai_api_key=api_key,
        openai_base_url=base_url,
        model_name=model_name,
        host=host,
        port=port,
        root_dir=root_dir,
        sandbox_dir=root_dir / 'sandbox',
        data_dir=root_dir / 'data',
        database=DatabaseConfig(
            url=database_url,
            echo=debug
        ),
        auth=AuthConfig(
            secret_key=secret_key,
            access_token_expire_minutes=access_token_expire
        )
    )
    
    return settings


# Global settings instance
settings = load_settings()
