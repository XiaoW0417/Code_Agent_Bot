"""
Configuration management for the Agent Bot.
"""
import os
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Set
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

@dataclass
class Settings:
    """Application settings."""
    openai_api_key: Optional[str]
    openai_base_url: Optional[str]
    model_name: Optional[str]
    sandbox_dir: Path
    
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
        # Dependencies (User Request)
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

def load_settings() -> Settings:
    """Load settings from .env file and environment variables."""
    # src/core/config.py -> src/core -> src -> root
    root_dir = Path(__file__).resolve().parents[2]
    env_path = root_dir / '.env'
    
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)

    api_key = os.getenv('OPENAI_API_KEY')
    base_url = os.getenv('OPENAI_BASE_URL')
    model_name = os.getenv('OPENAI_MODEL_NAME')
    
    sandbox_dir = root_dir / 'sandbox'
    try:
        sandbox_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        # We can't log here effectively if logging isn't set up yet, 
        # but we can print to stderr or just pass. 
        # Since this is "load_settings", raising might be better.
        print(f"Warning: Could not create sandbox directory: {e}")

    return Settings(
        openai_api_key=api_key,
        openai_base_url=base_url,
        model_name=model_name,
        sandbox_dir=sandbox_dir
    )

settings = load_settings()
