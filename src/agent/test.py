from .router import router
from .logging_setup import setup_logging
import asyncio

setup_logging()

async def main():
    result = await router.call_tool("get_current_weather", '{"location": "Beijing"}')
    print(result)

asyncio.run(main())