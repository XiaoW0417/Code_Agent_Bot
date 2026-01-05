import asyncio
import logging
from typing import TypedDict, Optional
from datetime import datetime
import httpx

from ..errors import ToolExecutionError


class TimezoneResult(TypedDict):
    datetime: str
    timezone: str


TIMEZ_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_timezone_time",
        "description": "获取指定 IANA 时区的当前时间。",
        "parameters": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "IANA 时区名称，例如 'Asia/Shanghai' 或 'America/New_York'。",
                },
                "format": {
                    "type": "string",
                    "description": "可选的时间格式化字符串。",
                },
            },
            "required": ["timezone"],
        },
    },
}


async def get_timezone_time(
    timezone: str, format: Optional[str] = None
) -> TimezoneResult:
    """
    获取指定时区的当前时间。
    使用 worldtimeapi.org
    """
    api_url = f"https://worldtimeapi.org/api/timezone/{timezone}"

    
    timeout = httpx.Timeout(
        connect=3.0,
        read=5.0,
        write=5.0,
        pool=5.0,
    )

    async with httpx.AsyncClient(timeout=timeout, trust_env=True) as client:
        try:
            while True:
                try:
                    response = await client.get(api_url)
                    response.raise_for_status()
                    break
                except Exception as e:
                    wait = 0.3
                    logging.info(f"请求失败: {e}，{wait}s 后重试")
                    await asyncio.sleep(wait)
            data = response.json()

            iso_time = data["datetime"]  # worldtimeapi 原生 ISO 8601

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
                    tool_name="get_timezone_time",
                    error_msg=f"找不到时区 '{timezone}'。请使用有效的 IANA 时区名称。"
                )
            raise ToolExecutionError(
                tool_name="get_timezone_time",
                error_msg=f"worldtimeapi 请求失败: {e.response.status_code}"
            )

        except Exception as e:
            raise ToolExecutionError(
                tool_name="get_timezone_time",
                error_msg=f"获取时间时出错: {str(e)}"
            )


if __name__ == "__main__":
    from ..logging_setup import setup_logging
    setup_logging()

    async def main():
        try:
            result1 = await get_timezone_time("Asia/Tokyo")
            logging.info(f"东京当前时间: {result1['datetime']}")

            result2 = await get_timezone_time(
                "America/New_York",
                format="%Y-%m-%d %H:%M:%S"
            )
            logging.info(f"纽约当前时间: {result2['datetime']}")
        except ToolExecutionError as e:
            logging.error(e)

    asyncio.run(main())
