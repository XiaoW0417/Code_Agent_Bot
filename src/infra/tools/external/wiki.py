"""
Wikipedia tool.
"""
import asyncio
import logging
import urllib.parse
from typing import TypedDict

import httpx

from src.core.exceptions import ToolExecutionError

logger = logging.getLogger(__name__)

class WikipediaSummaryResult(TypedDict):
    title: str
    summary: str
    url: str

WIKI_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_wikipedia_summary",
        "description": "Get wikipedia summary for a query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Query term.",
                },
                "language": {
                    "type": "string",
                    "description": "Language code ('zh', 'en'). Default: 'zh'",
                    "enum": ["zh", "en"],
                    "default": "zh"
                },
            },
            "required": ["query"],
        },
    },
}

async def get_wikipedia_summary(
    query: str, language: str = "zh"
) -> WikipediaSummaryResult:
    """Get wikipedia summary."""
    encoded_query = urllib.parse.quote(query.replace(' ', '_'))
    
    api_url = f"https://{language}.wikipedia.org/api/rest_v1/page/summary/{encoded_query}"
    
    headers = {
        "User-Agent": "MyAgentTool/1.0 (agent_bot@wj.com)" 
    }
    
    async with httpx.AsyncClient(headers=headers) as client:
        try:
            response = await client.get(api_url, follow_redirects=True)
            response.raise_for_status()
            data = response.json()
            
            return WikipediaSummaryResult(
                title=data.get("title", "N/A"),
                summary=data.get("extract", "Summary not available."),
                url=data.get("content_urls", {}).get("desktop", {}).get("page", "#"),
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ToolExecutionError("get_wikipedia_summary", f"Term '{query}' not found.")
            
            if e.response.status_code == 403:
                 raise ToolExecutionError("get_wikipedia_summary", "Access denied (403). Check User-Agent.")

            raise ToolExecutionError("get_wikipedia_summary", f"Wikipedia API error: {e.response.status_code}")
        except Exception:
             raise ToolExecutionError("get_wikipedia_summary", "Unknown error calling Wikipedia API.")
