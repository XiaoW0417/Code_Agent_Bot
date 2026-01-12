"""
Core Agent Logic.
"""
import json
import logging
import asyncio
from typing import Any, List, Optional

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageToolCall

from src.core.router import ToolRegistry
from src.core.exceptions import AgentError

logger = logging.getLogger(__name__)

class Agent:
    """
    Autonomous agent that interacts with LLM and executes tools.
    """
    def __init__(
        self, 
        api_key: str, 
        base_url: Optional[str], 
        model_name: str, 
        router: ToolRegistry,
        max_tool_rounds: int = 100
    ):
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self.model = model_name
        self.router = router
        self.messages: List[dict[str, Any]] = []
        self.max_tool_rounds = max_tool_rounds

    def _add_message(
        self, 
        role: str, 
        content: str, 
        tool_calls: Optional[List[ChatCompletionMessageToolCall]] = None, 
        tool_call_id: Optional[str] = None
    ):
        """Add a message to the conversation history."""
        message: dict[str, Any] = {"role": role, "content": content}
        if tool_calls:
            message["tool_calls"] = [tc.model_dump() for tc in tool_calls]
        if tool_call_id:
            message["tool_call_id"] = tool_call_id
        self.messages.append(message)

    async def chat(self, user_input: str) -> str:
        """
        Run a chat loop with the agent.
        """
        self._add_message("user", user_input)

        for i in range(self.max_tool_rounds):
            logger.info(f"Thinking... (Round {i+1}/{self.max_tool_rounds})")

            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    tools=self.router.get_tool_schemas(),
                    tool_choice="auto",
                )
            except Exception as e:
                logger.error(f"OpenAI API error: {e}. Retrying...", exc_info=True)
                # Should we retry immediately or wait? 
                continue

            response_message = response.choices[0].message

            if response_message.tool_calls:
                self._add_message(
                    role="assistant",
                    content=response_message.content or "",
                    tool_calls=response_message.tool_calls
                )

                tool_tasks = []
                for tool_call in response_message.tool_calls:
                    task = self._execute_tool_call(tool_call)
                    tool_tasks.append(task)

                await asyncio.gather(*tool_tasks)
                continue

            final_response = response_message.content or "No response generated."
            self._add_message("assistant", final_response)
            return final_response

        logger.warning("Max tool rounds reached.")
        return "I seem to be stuck in a loop. Please try rephrasing."

    async def _execute_tool_call(self, tool_call: ChatCompletionMessageToolCall):
        """Execute a tool call and record the result."""
        tool_name = tool_call.function.name
        tool_args_json = tool_call.function.arguments

        try:
            # Use self.router instead of global router
            tool_result = await self.router.call_tool(tool_name, tool_args_json)
            result_str = json.dumps(tool_result, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {e}", exc_info=True)
            result_str = json.dumps({"error": str(e)}, ensure_ascii=False)

        self._add_message(
            role="tool",
            content=result_str,
            tool_call_id=tool_call.id
        )
