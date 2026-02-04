"""
Entry point for the Agent Bot.
"""
import asyncio

from src.interface.cli.main import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram terminated.")
