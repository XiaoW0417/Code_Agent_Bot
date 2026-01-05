# src/agent/tools/wiki.py

import asyncio
import logging
from typing import TypedDict

import httpx

from ..errors import ToolExecutionError

class WikipediaSummaryResult(TypedDict):
    title: str
    summary: str
    url: str

WIKI_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_wikipedia_summary",
        "description": "根据查询词获取维基百科（中文或英文）条目的摘要信息。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "要查询的维基百科词条，例如 '埃隆·马斯克'。",
                },
                "language": {
                    "type": "string",
                    "description": "语言代码，'zh' 代表中文，'en' 代表英文。默认为 'zh'。",
                    "enum": ["zh", "en"],
                },
            },
            "required": ["query"],
        },
    },
}

async def get_wikipedia_summary(
    query: str, language: str = "zh"
) -> WikipediaSummaryResult:
    """
    获取维基百科条目摘要。
    """
    # 建议加上 URL 编码，防止特殊字符导致 URL 错误
    import urllib.parse
    encoded_query = urllib.parse.quote(query.replace(' ', '_'))
    
    api_url = f"https://{language}.wikipedia.org/api/rest_v1/page/summary/{encoded_query}"
    
    # 关键修改在这里：定义请求头
    headers = {
        # 格式推荐：应用名/版本号 (联系方式)
        "User-Agent": "MyAgentTool/1.0 (agent_bot@wj.com)" 
    }
    
    # 将 headers 传入 Client
    async with httpx.AsyncClient(headers=headers) as client:
        try:
            # 维基百科可能会有重定向，follow_redirects=True 是必须的
            response = await client.get(api_url, follow_redirects=True)
            response.raise_for_status()
            data = response.json()
            
            return WikipediaSummaryResult(
                title=data.get("title", "N/A"),
                summary=data.get("extract", "摘要不可用。"),
                url=data.get("content_urls", {}).get("desktop", {}).get("page", "#"),
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # 404 很多时候是因为简繁体或大小写，维基百科 API 对此很敏感
                raise ToolExecutionError(tool_name="get_wikipedia_summary", error_msg=f"找不到词条 '{query}'。请尝试更换关键词。")
            
            # 如果是 403，这里会捕获到
            if e.response.status_code == 403:
                 raise ToolExecutionError(tool_name="get_wikipedia_summary", error_msg="请求被拒绝 (403)。请检查 User-Agent 设置。")

            raise ToolExecutionError(tool_name="get_wikipedia_summary", error_msg=f"维基百科 API 请求失败: {e.response.status_code}")
        except Exception as e:
             raise ToolExecutionError(tool_name="get_wikipedia_summary", error_msg=f"获取维基百科摘要时出错: {e}")

if __name__ == "__main__":
    from ..logging_setup import setup_logging
    setup_logging()

    async def main():
        try:
            summary = await get_wikipedia_summary("埃隆·马斯克", language="zh")
            logging.info(f"标题: {summary['title']}\n摘要: {summary['summary']}\nURL: {summary['url']}")
        except ToolExecutionError as e:
            logging.error(e)
            
    asyncio.run(main())
