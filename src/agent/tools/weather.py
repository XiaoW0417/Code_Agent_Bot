import asyncio 
import logging
import httpx

from typing import Literal, TypedDict, cast
from ..errors import ToolExecutionError

# 定义 OpenMeteo API 返回的结果类型
class GeocodingResult(TypedDict):
    id: int
    name: str
    latitude: float
    longitude: float

class WeatherResult(TypedDict):
    temperature: float
    windspeed: float
    weathercode: int
    unit: str

# 定义天气工具模板
WEATHER_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_current_weather",
        "description": "根据地理位置获取实时天气信息。",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "城市名，例如 '北京' 或 'San Francisco'。",
                },
                "unit": {
                    "type": "string",
                    "description": "温度单位，'celsius' (摄氏度) 或 'fahrenheit' (华氏度)。",
                    "enum": ["celsius", "fahrenheit"],
                },
            },
            "required": ["location"],
        },
    },
}

# 内部辅助函数，获取地理编码
async def _get_geocoding(location: str, client: httpx.AsyncClient) -> GeocodingResult:
    '''把城市名转换为经纬度'''
    geocoding_url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": location, "count": 1, "language": "en", "format": "json"}

    try:
        response = await client.get(geocoding_url, params=params)
        response.raise_for_status()
        data = response.json()
        if not data.get("results"):
            raise ToolExecutionError(tool_name="get_current_weather", error_msg=f"找不到城市: '{location}'")
        return cast(GeocodingResult, data["results"][0])
    
    except httpx.HTTPStatusError as e:
        raise ToolExecutionError(tool_name="get_current_weather", error_msg=f"地理编码api请求失败: {e.response.status_code}")
    except Exception as e:
        raise ToolExecutionError(tool_name="get_current_weather", error_msg=f"获取地理编码时出错: {e}")

# Agent调用主函数
async def get_current_weather(
    location: str, unit: Literal["celsius", "fahrenheit"] = "celsius"
) -> WeatherResult:
    '''获取指定地点的当前日期天气
    location: 城市名。
    unit: 温度单位
    return: 包含温度、风速、天气代码和单位的字典
    '''
    async with httpx.AsyncClient() as client:
        geo_info = await _get_geocoding(location, client)
        lat, lon = geo_info.get("latitude"), geo_info.get("longitude")

        weather_url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": "true",
            "temperature_unit": unit
        }

        try:
            response = await client.get(weather_url, params=params)
            response.raise_for_status()
            weather_data = response.json()["current_weather"]

            return WeatherResult(
                temperature=weather_data.get("temperature"),
                windspeed=weather_data.get("windspeed"),
                weathercode=weather_data.get("weathercode"),
                unit=unit
            )

        except httpx.HTTPStatusError as e:
            raise ToolExecutionError(tool_name="get_current_weather", error_msg=f"天气api请求失败: {e.response.status_code}")
        except Exception as e:
            raise ToolExecutionError(tool_name="get_current_weather", error_msg=f"获取天气时出错: {e}")

# 测试
if __name__ == "__main__":
    from ..logging_setup import setup_logging
    setup_logging()

    async def main():
        location = "Beijing"
        try:
            weather = await get_current_weather(location, unit="celsius")
            logging.info(f"{location} current weather: {weather}")
        except  Exception as e:
            logging.error(e)
    
    asyncio.run(main())