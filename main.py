"""
Entry point for the Agent Bot.
"""
import asyncio
import sys
from pathlib import Path

# Ensure src is in python path if not already
root_dir = Path(__file__).parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.interface.cli.main import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram terminated.")
