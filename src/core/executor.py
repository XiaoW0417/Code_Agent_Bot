"""
Executor Agent.
Responsibility: Execute a single task/step using High-Level Skills.
"""
import json
import logging
import asyncio
from typing import Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass

from src.core.llm.base import LLMProvider
from src.core.exceptions import AgentError
from src.core.skills.registry import registry

logger = logging.getLogger(__name__)

@dataclass
class ExecutionResult:
    status: str # "success", "failed"
    output: str
    error: Optional[str] = None

@dataclass
class ToolEvent:
    name: str
    args: dict
    result: Any

EXECUTOR_SYSTEM_PROMPT = """
You are an Executor Agent (Coder). 
You receive a specific task and must execute it using the available Skills.

Responsibilities:
- Use Skills to gather information, modify files, or run tests.
- Your capabilities are high-level intents (e.g., ExploreProject, EditFile) rather than low-level file ops.
- If the task is simple and requires no skills, just answer it.
- Always verify your work if possible (e.g. read back the file you wrote).

Output:
- When you have completed the task, provide a final response summarizing what you did.
- Your final response MUST be in the same language as the task instruction.
"""

class Executor:
    """
    Agent that interacts with LLM and executes Skills.
    """
    def __init__(
        self, 
        llm: LLMProvider,
        # mcp_client is removed/deprecated in favor of Skill Registry
        max_tool_rounds: int = 10
    ):
        self.llm = llm
        self.max_tool_rounds = max_tool_rounds
        self.messages: List[dict[str, Any]] = []
        self.on_tool_event: Optional[Callable[[ToolEvent], Awaitable[None]]] = None

    def _add_message(
        self, 
        role: str, 
        content: str, 
        tool_calls: Optional[List[Any]] = None, 
        tool_call_id: Optional[str] = None
    ):
        message: dict[str, Any] = {"role": role, "content": content}
        if tool_calls:
            try:
                message["tool_calls"] = [tc.model_dump() for tc in tool_calls]
            except AttributeError:
                message["tool_calls"] = tool_calls
                
        if tool_call_id:
            message["tool_call_id"] = tool_call_id
        self.messages.append(message)

    async def execute_step(self, step_instruction: str) -> ExecutionResult:
        """
        Execute a single plan step.
        """
        if not self.messages:
            self._add_message("system", EXECUTOR_SYSTEM_PROMPT)
        
        self._add_message("user", f"Execute this step: {step_instruction}")

        # Get tools from Skill Registry
        tools_schema = registry.get_schemas()

        for i in range(self.max_tool_rounds):
            logger.info(f"Executor: Thinking... (Round {i+1})")

            try:
                response_message = await self.llm.chat_complete(
                    messages=self.messages,
                    tools=tools_schema,
                    tool_choice="auto"
                )
            except Exception as e:
                return ExecutionResult(status="failed", output="", error=f"LLM Error: {e}")

            content = response_message.content
            tool_calls = response_message.tool_calls

            if tool_calls:
                self._add_message(
                    role="assistant",
                    content=content or "",
                    tool_calls=tool_calls
                )

                tool_tasks = []
                for tool_call in tool_calls:
                    task = self._execute_tool_call(tool_call)
                    tool_tasks.append(task)

                await asyncio.gather(*tool_tasks)
                continue

            final_response = content or "Task completed."
            self._add_message("assistant", final_response)
            return ExecutionResult(status="success", output=final_response)

        return ExecutionResult(status="failed", output="", error="Max tool rounds reached.")

    async def _execute_tool_call(self, tool_call: Any):
        """Execute a tool call via Skill Registry."""
        tool_name = tool_call.function.name
        tool_args_json = tool_call.function.arguments

        try:
            tool_args = json.loads(tool_args_json)
            
            # Use Skill Registry instead of MCP Client
            skill = registry.get_skill(tool_name)
            tool_result = await skill.execute(**tool_args)
            
            result_str = json.dumps(tool_result, ensure_ascii=False)
            
            # Emit event
            if self.on_tool_event:
                await self.on_tool_event(ToolEvent(name=tool_name, args=tool_args, result=tool_result))
                
        except Exception as e:
            logger.error(f"Error executing skill '{tool_name}': {e}", exc_info=True)
            result_str = json.dumps({"error": str(e)}, ensure_ascii=False)
            
            if self.on_tool_event:
                try:
                    args = json.loads(tool_args_json)
                except:
                    args = {"raw": tool_args_json}
                await self.on_tool_event(ToolEvent(name=tool_name, args=args, result={"error": str(e)}))

        self._add_message(
            role="tool",
            content=result_str,
            tool_call_id=tool_call.id
        )

    @property
    def history(self) -> List[dict[str, Any]]:
        return self.messages
