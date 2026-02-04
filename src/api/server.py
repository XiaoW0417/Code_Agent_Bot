"""
API Server entry point.
"""
import uvicorn
from src.core.config import settings
from src.infra.logging import setup_logging


def main():
    """Run the API server."""
    setup_logging()
    
    uvicorn.run(
        "src.api.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
        log_level="info" if settings.is_development else "warning"
    )


if __name__ == "__main__":
    main()
