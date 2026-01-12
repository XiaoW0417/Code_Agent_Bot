"""
Timezone tool.
"""
import asyncio
import logging
from typing import TypedDict, Optional
from datetime import datetime
import httpx

from src.core.exceptions import ToolExecutionError

logger = logging.getLogger(__name__)

class TimezoneResult(TypedDict):
    datetime: str
    timezone: str


TIMEZ_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_timezone_time",
        "description": "Get current time for a specific IANA timezone.",
        "parameters": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "IANA timezone name (e.g. 'Asia/Shanghai', 'America/New_York').",
                },
                "format": {
                    "type": "string",
                    "description": "Optional format string.",
                },
            },
            "required": ["timezone"],
        },
    },
}


async def get_timezone_time(
    timezone: str, format: Optional[str] = None
) -> TimezoneResult:
    """Get current time in timezone."""
    api_url = f"https://worldtimeapi.org/api/timezone/{timezone}"

    timeout = httpx.Timeout(
        connect=3.0,
        read=5.0,
        write=5.0,
        pool=5.0,
    )

    async with httpx.AsyncClient(timeout=timeout, trust_env=True) as client:
        try:
            # Simple retry logic from original code
            while True:
                try:
                    response = await client.get(api_url)
                    response.raise_for_status()
                    break
                except Exception as e:
                    wait = 0.3
                    logger.info(f"Request failed: {e}, retrying in {wait}s")
                    await asyncio.sleep(wait)
            
            data = response.json()
            iso_time = data["datetime"]

            dt_object = datetime.fromisoformat(
                iso_time.replace("Z", "+00:00")
            )

            if format:
                formatted_time = dt_object.strftime(format)
            else:
                formatted_time = dt_object.isoformat()

            return TimezoneResult(
                datetime=formatted_time,
                timezone=data["timezone"],
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ToolExecutionError(
                    "get_timezone_time",
                    f"Timezone '{timezone}' not found."
                )
            raise ToolExecutionError(
                "get_timezone_time",
                f"API request failed: {e.response.status_code}"
            )

        except Exception as e:
            raise ToolExecutionError(
                "get_timezone_time",
                f"Error getting time: {str(e)}"
            )
