"""
Currency exchange tool.
"""
import logging
from typing import TypedDict, Optional

import httpx

from src.core.exceptions import ToolExecutionError

logger = logging.getLogger(__name__)

class ExchangeRateResult(TypedDict):
    rate: float
    converted_amount: Optional[float]

FX_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_exchange_rate",
        "description": "Get exchange rate between two currencies and optionally convert an amount.",
        "parameters": {
            "type": "object",
            "properties": {
                "base_currency": {
                    "type": "string",
                    "description": "ISO 4217 code for base currency (e.g. 'USD').",
                },
                "target_currency": {
                    "type": "string",
                    "description": "ISO 4217 code for target currency (e.g. 'CNY').",
                },
                "amount": {
                    "type": "number",
                    "description": "Amount to convert (optional).",
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
    """Get exchange rate and calculate amount."""
    # Hardcoded access key? That's not ideal but I won't change business logic.
    # I should probably move it to config, but user said "Don't change behavior".
    # I'll keep it as is for now.
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
                raise ToolExecutionError("get_exchange_rate", f"Failed to get exchange rate from {base_currency} to {target_currency}.")
            
            # The API response structure depends on the specific API version/plan.
            # Assuming the existing code works.
            rate = data.get("quotes").get(rate_tag)
            result = ExchangeRateResult(rate=rate, converted_amount=None)
            
            if amount is not None:
                result["converted_amount"] = round(amount * rate, 2)
                
            return result
        except httpx.HTTPStatusError as e:
            raise ToolExecutionError("get_exchange_rate", f"API request failed: {e.response.status_code}")
        except Exception as e:
             raise ToolExecutionError("get_exchange_rate", f"Error getting exchange rate: {e}")
