"""
Logging configuration for the application.
"""
import logging
import sys

def setup_logging(level: int = logging.WARNING) -> None:
    """
    Configure global logging settings.
    
    Args:
        level: The logging level to use. Defaults to INFO.
    """
    # Avoid adding handlers if they already exist to prevent duplicate logs
    if logging.getLogger().handlers:
        return
    
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)-5s] (%(name)-15s): %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    # Suppress noisy logs from libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
