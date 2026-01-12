"""
Orchestrator.
Manages the Planner-Executor-Critic flow with Rich UI integration.
Implements Execution-Gated Fast Path.
"""
import logging
import asyncio
from typing import AsyncGenerator, Optional, List, Any

from src.core.llm.base import LLMProvider
from src.core.mcp.base import MCPClient
from src.core.planner import Planner, Plan
from src.core.executor import Executor, ExecutionResult, ToolEvent
from src.core.critic import Critic
from src.core.analyzer import ExecutionRiskAnalyzer
from src.interface.ui.console import ui

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(
        self, 
        llm: LLMProvider,
        mcp_client: MCPClient
    ):
        self.llm = llm
        self.mcp_client = mcp_client
        
        self.planner = Planner(llm)
        # Executor now uses Skill Registry internally, mcp_client passed only for legacy/compat if needed
        # but in our refactor Executor init signature changed.
        # We need to update this call.
        self.executor = Executor(llm) 
        self.critic = Critic(llm)
        self.analyzer = ExecutionRiskAnalyzer(llm)
        
        # Wire up events
        self.executor.on_tool_event = self._on_tool_event

    async def _on_tool_event(self, event: ToolEvent):
        """Callback for tool events."""
        ui.show_tool_event(event.name, event.args, event.result)

    async def chat(self, user_input: str) -> None:
        """
        Main entry point.
        """
        # 0. Execution Risk Analysis (Fast Path Check)
        # Replaces heuristic check with LLM-based risk analysis
        analysis = await self.analyzer.analyze(user_input)
        logger.info(f"Execution Analysis: {analysis}")
        
        if analysis.is_fast_path:
            logger.info("Fast Path triggered.")
            # Fast Path: Direct Chat
            # No UI phases, no logs visible to user except the response.
            
            messages = [
                {"role": "system", "content": (
                    "You are a helpful assistant. "
                    "CRITICAL: You MUST respond in the SAME language as the user's input. "
                    "If the user speaks Chinese, you MUST answer in Chinese. "
                    "If the user speaks English, you MUST answer in English. "
                    "Do not mix languages."
                )},
                {"role": "user", "content": user_input}
            ]
            
            ui.start_stream(title="Agent")
            try:
                async for chunk in self.llm.chat_stream(messages):
                    ui.update_stream(chunk)
            finally:
                ui.end_stream()
            return

        # Complex Path: Full Agent Loop
        
        # 1. Plan
        ui.start_phase("Architect", "Analyzing request & Planning...")
        
        plan: Optional[Plan] = None
        
        # Start Live Stream for Planner output
        ui.start_stream(title="Planning")
        
        try:
            async for item in self.planner.create_plan(user_input):
                if isinstance(item, str):
                    # Update Live Stream with new Markdown chunk
                    ui.update_stream(item)
                elif isinstance(item, Plan):
                    plan = item
        finally:
            # Ensure stream is stopped even if error occurs
            ui.end_stream()
        
        if not plan:
            ui.show_error("Failed to generate plan.")
            # yield "Failed to generate plan." # REMOVED: No longer yielding
            return

        # ui.show_plan(plan) # REMOVED: Avoid duplicate output since we streamed the markdown plan

        # 2. Loop
        execution_history = []
        
        for step in plan.steps:
            ui.show_step_start(step.id, step.instruction)
            
            # Retry loop for Critic
            max_retries = 3
            retry_count = 0
            approved = False
            
            while not approved and retry_count < max_retries:
                if retry_count > 0:
                    ui.console.print(f"  [yellow](Retry {retry_count}/{max_retries})[/yellow]")
                
                # Execute
                ui.start_phase("Executor", f"Executing Step {step.id}...")
                
                result = await self.executor.execute_step(step.instruction)
                
                if result.status == "failed":
                    ui.show_error(result.error or "Unknown error")
                else:
                    ui.console.print(f"  [dim]📝 Summary: {result.output[:100]}...[/dim]")

                # Reflect
                ui.start_phase("Critic", "Reviewing execution...")
                feedback = await self.critic.review(step, result)
                
                ui.show_critic_feedback(feedback.approved, feedback.comments)
                
                if feedback.approved:
                    approved = True
                    execution_history.append(f"Step {step.id}: Success. {result.output}")
                else:
                    retry_count += 1
                    # Add feedback to Executor context
                    self.executor._add_message("user", f"Critic Feedback: {feedback.comments}. Please fix and retry.")
            
            if not approved:
                ui.show_error(f"Step {step.id} failed after retries.")
                execution_history.append(f"Step {step.id}: Failed. Last error: {result.error or result.output}")

        # 3. Final Response
        ui.start_phase("Agent", "Generating final response...")
        
        summary_prompt = (
            "Based on the executed steps and their results, provide a final comprehensive answer to the user. "
            "CRITICAL: You MUST respond in the SAME language as the user's original request. "
            "If user asked in Chinese, answer in Chinese. "
            "If user asked in English, answer in English. "
            "Do not translate technical terms if they are standard, but keep the narrative language consistent."
        )
        
        ui.start_stream(title="Final Response")
        try:
            async for chunk in self.executor.llm.chat_stream(
                messages=self.executor.messages + [{"role": "user", "content": summary_prompt}]
            ):
                ui.update_stream(chunk)
        finally:
            ui.end_stream()

    def set_model(self, model_name: str):
        self.llm.config.model = model_name

    async def handle_file_ref(self, file_path: str):
        self.executor._add_message("system", f"User is referring to file: {file_path}. You can read it using filesystem tools.")
