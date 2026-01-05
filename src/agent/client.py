# src/agent/client.py

import json
import logging
import asyncio
from typing import Any

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageToolCall

from .config import settings
from .errors import ModelResponseError
from .router import router

logger = logging.getLogger(__name__)

class AgentClient:
    def __init__(self, max_tool_rounds: int = 5):
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY 未设置。")

        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self.model = settings.model_name
        self.messages: list[dict[str, Any]] = []
        self.max_tool_rounds = max_tool_rounds # 防止工具调用循环

    def _add_message(self, role: str, content: str, tool_calls: list[ChatCompletionMessageToolCall] | None = None, tool_call_id: str | None = None):
        """向对话历史中添加一条消息"""
        message: dict[str, Any] = {"role": role, "content": content}
        if tool_calls:
            # 为了序列化，将 tool_calls 对象转换为字典列表
            message["tool_calls"] = [tc.model_dump() for tc in tool_calls]
        if tool_call_id:
            message["tool_call_id"] = tool_call_id
        self.messages.append(message)

    async def chat(self, user_input: str) -> str:
        """
        与 Agent 进行一次完整的对话交互。

        :param user_input: 用户的输入。
        :return: Agent 的最终回复。
        """
        self._add_message("user", user_input)

        for _ in range(self.max_tool_rounds):
            logger.info(f"向 OpenAI 发送请求, 模型: {self.model}, 消息条数: {len(self.messages)}")

            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    tools=router.get_tool_schemas(),
                    tool_choice="auto",
                )
            except Exception as e:
                logger.error(f"调用 OpenAI API 时出错: {e}", exc_info=True)
                raise ModelResponseError(f"API 调用失败: {e}")

            response_message = response.choices[0].message

            # 如果有工具调用请求
            if response_message.tool_calls:
                logger.info(f"模型请求工具调用。{response_message.tool_calls}")
                self._add_message(
                    role="assistant",
                    content=response_message.content or "",
                    tool_calls=response_message.tool_calls
                )

                # 并行执行所有工具调用
                tool_tasks = []
                for tool_call in response_message.tool_calls:
                    task = self._execute_tool_call(tool_call)
                    tool_tasks.append(task)

                await asyncio.gather(*tool_tasks)

                # 在所有工具都执行完毕后，继续循环，再次请求模型
                continue

            # 如果没有工具调用，说明是最终回复
            logger.info("模型生成了最终回复。")
            final_response = response_message.content or "我不知道该如何回复。"
            self._add_message("assistant", final_response)
            return final_response

        # 如果达到最大工具调用轮次
        logger.warning("已达到最大工具调用轮次，强制结束对话。")
        return "我似乎陷入了循环，无法解决你的问题。请尝试换一种问法。"

    async def _execute_tool_call(self, tool_call: ChatCompletionMessageToolCall):
        """执行单个工具调用并将其结果添加到消息历史中"""
        tool_name = tool_call.function.name
        tool_args_json = tool_call.function.arguments

        try:
            tool_result = await router.call_tool(tool_name, tool_args_json)
            # 将工具结果序列化为 JSON 字符串
            result_str = json.dumps(tool_result, ensure_ascii=False)
        except Exception as e:
            logger.error(f"执行工具 '{tool_name}' 时捕获到异常: {e}", exc_info=True)
            result_str = json.dumps({"error": str(e)}, ensure_ascii=False)

        self._add_message(
            role="tool",
            content=result_str,
            tool_call_id=tool_call.id
        )