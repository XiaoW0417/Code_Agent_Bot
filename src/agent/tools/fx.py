import asyncio
import time
import httpx
import logging

from typing import TypedDict, Optional
from ..errors import ToolExecutionError

class ExchangeRateResult(TypedDict):
    rate: float
    converted_amount: Optional[float]

FX_TOOL_SCHEMA = {
        "type": "function",
    "function": {
        "name": "get_exchange_rate",
        "description": "获取两种货币之间的汇率，并可选择性地计算特定金额的兑换结果。",
        "parameters": {
            "type": "object",
            "properties": {
                "base_currency": {
                    "type": "string",
                    "description": "基础货币的 ISO 4217 代码，例如 'USD' (美元)。",
                },
                "target_currency": {
                    "type": "string",
                    "description": "目标货币的 ISO 4217 代码，例如 'CNY' (人民币)。",
                },
                "amount": {
                    "type": "number",
                    "description": "要兑换的金额，为可选参数。",
                },
            },
            "required": ["base_currency", "target_currency"],
        },
    },
}

async def get_exchange_rate(
    base_currency: str,
    target_currency: str,
    amount: Optional[float] = None
) -> ExchangeRateResult:
    '''
    获取汇率、计算金额
    '''
    api_url = (
    f"https://api.exchangerate.host/live"
    f"?access_key=efbdf2a97996246214b3a007a254e908"
    f"&source={base_currency.upper()}"
    f"&currencies={target_currency.upper()}"
)   

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(api_url)
            response.raise_for_status()
            data = response.json()
            rate_tag = f"{base_currency.upper()}{target_currency.upper()}"

            if not data.get("success"):
                raise ToolExecutionError(tool_name="get_exchange_rate", error_msg=f"无法获取从 {base_currency} 到 {target_currency} 的汇率。")
            
            rate = data.get("quotes").get(rate_tag)
            result = ExchangeRateResult(rate=rate, converted_amount=None)
            
            if amount is not None:
                result["converted_amount"] = round(amount * rate, 2)
                
            return result
        except httpx.HTTPStatusError as e:
            raise ToolExecutionError(tool_name="get_exchange_rate", error_msg=f"汇率 API 请求失败: {e.response.status_code}")
        except Exception as e:
             raise ToolExecutionError(tool_name="get_exchange_rate", error_msg=f"获取汇率时出错: {e}")

if __name__ == "__main__":
    from ..logging_setup import setup_logging
    setup_logging()

    async def main():
        try:
            result1 = await get_exchange_rate("USD", "CNY")
            logging.info(f"USD 到 CNY 的汇率: {result1['rate']:.4f}")
            
            time.sleep(0.3) # 避免请求过快
            # 场景二: 查询汇率并计算兑换金额
            result2 = await get_exchange_rate("USD", "CNY", 100)
            logging.info(f"100 USD 兑换为 CNY: {result2['converted_amount']}")
        except ToolExecutionError as e:
            logging.error(e)
            
    asyncio.run(main())
