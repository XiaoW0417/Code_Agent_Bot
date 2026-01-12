"""
Critic Agent.
Responsibility: Review the execution result of a step against the plan.
"""
import json
import logging
from typing import Any, List, Optional
from dataclasses import dataclass

from src.core.llm.base import LLMProvider
from src.core.exceptions import AgentError
from src.core.planner import PlanStep
from src.core.executor import ExecutionResult

logger = logging.getLogger(__name__)

@dataclass
class ReviewFeedback:
    approved: bool
    comments: str

CRITIC_SYSTEM_PROMPT = """
You are a Critic Agent (Reviewer).
Your goal is to review the work done by the Executor Agent and ensure it matches the Planner's instructions.

Input:
1. Plan Step: The instruction given to the Executor.
2. Expected Outcome: What was expected.
3. Execution Result: What the Executor did and the output/error.

Output Format:
Return a valid JSON object:
{
    "approved": true/false,
    "comments": "Explanation of why it is approved or rejected. If rejected, give specific advice."
}

Criteria:
- If the execution result indicates a failure (error), reject it unless the error was expected.
- If the output is vague or doesn't address the instruction, reject it.
- If the output looks correct and satisfies the expected outcome, approve it.
"""

class Critic:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def review(self, step: PlanStep, result: ExecutionResult) -> ReviewFeedback:
        """
        Review the execution of a step.
        """
        # Construct the context for review
        user_content = (
            f"Step Instruction: {step.instruction}\n"
            f"Expected Outcome: {step.expected_outcome}\n"
            f"Execution Status: {result.status}\n"
            f"Execution Output: {result.output}\n"
            f"Execution Error: {result.error}\n"
        )
        
        messages = [
            {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ]

        try:
            response_message = await self.llm.chat_complete(messages)
            content = response_message.content.strip()

            if content.startswith("```"):
                 content = content.strip("`").replace("json\n", "")
            
            data = json.loads(content)
            return ReviewFeedback(
                approved=data.get("approved", False),
                comments=data.get("comments", "No comments.")
            )
        except Exception as e:
            logger.error(f"Critic review failed: {e}")
            # Fail safe: if critic fails, we probably should warn but maybe default to approved if it looks okay?
            # Or default to rejected to be safe. Let's reject.
            return ReviewFeedback(approved=False, comments=f"Critic failed to parse review: {e}")
