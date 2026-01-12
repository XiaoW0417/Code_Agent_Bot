"""
Planner Agent.
Responsibility: Analyze user request, break it down into structured steps.
"""
import json
import logging
from typing import List, Dict, Any, AsyncGenerator, Optional
from dataclasses import dataclass

from src.core.llm.base import LLMProvider
from src.core.exceptions import AgentError

logger = logging.getLogger(__name__)

@dataclass
class PlanStep:
    id: str
    instruction: str
    expected_outcome: str

@dataclass
class Plan:
    goal: str
    steps: List[PlanStep]

PLANNER_SYSTEM_PROMPT = """
You are a Planner Agent (Architect). 
Your goal is to analyze the user's request and create a structured execution plan.

IMPORTANT: You MUST respond in the SAME language as the user's request. 
If user speaks Chinese, your plan goal and instructions MUST be in Chinese.
If user speaks English, use English.

Output Format:
You must output TWO parts.

PART 1: User-facing Plan (Markdown)
- A clear, readable Markdown description of the plan.
- Use headers, bullet points, and numbered lists.
- Explain the goal and the steps.
- Make it look professional and structured.

PART 2: System-facing Plan (Hidden JSON)
- A strictly valid JSON object wrapped in <hidden_plan> tags.
- The JSON must follow this structure:
{
    "goal": "High level goal description",
    "steps": [
        {
            "id": "1",
            "instruction": "Detailed instruction for the executor",
            "expected_outcome": "What success looks like for this step"
        },
        ...
    ]
}

Example Output:
# Project Analysis Plan
I will analyze the project structure and then...

## Steps
1. **Explore**: List files to understand layout.
2. **Search**: Find usage of 'foo'.

<hidden_plan>
{
    "goal": "Analyze project...",
    "steps": [...]
}
</hidden_plan>

Constraints:
- Break down complex tasks into logical, dependent steps.
- Each step should be actionable by an Executor Agent who has access to Skills (ExploreProject, ViewFile, etc).
- Do not execute the steps yourself.
- If the request is a simple conversation, create a single step plan: "Reply to user".
"""

class Planner:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def create_plan(self, user_input: str) -> AsyncGenerator[str | Plan, None]:
        """
        Generate a structured plan from user input.
        Yields chunks of text (thinking process) and finally yields the Plan object.
        """
        messages = [
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": user_input}
        ]

        logger.info("Planner: Generating plan...")
        
        full_content = ""
        hidden_marker = "<hidden_plan>"
        marker_detected = False
        yielded_len = 0
        
        try:
            async for chunk in self.llm.chat_stream(messages):
                full_content += chunk
                
                # Streaming Logic with Buffering:
                # If we haven't detected the marker yet, we check for it.
                # If we detect it, we stop yielding chunks to the UI.
                
                if not marker_detected:
                    idx = full_content.find(hidden_marker)
                    if idx != -1:
                        # Marker found.
                        # Yield everything up to the marker that hasn't been yielded yet.
                        if idx > yielded_len:
                            safe_chunk = full_content[yielded_len:idx]
                            yield safe_chunk
                            yielded_len = idx
                            
                        marker_detected = True
                        # Stop yielding further.
                    else:
                        # Marker not fully found yet.
                        # But we might have a partial marker at the end of full_content.
                        # We should only yield the part that is definitely NOT a marker prefix.
                        
                        # Check suffixes of full_content starting from yielded_len
                        # We want to find the longest suffix of unyielded content that is a prefix of hidden_marker.
                        
                        unyielded_content = full_content[yielded_len:]
                        if not unyielded_content:
                            continue
                            
                        # Find the longest suffix of unyielded_content that matches a prefix of hidden_marker
                        safe_end_index = len(unyielded_content)
                        
                        # We only need to check suffixes up to len(hidden_marker) - 1
                        # If unyielded content is "abc<hid", we hold "<hid".
                        # If unyielded content is "abc", we yield "abc".
                        
                        for k in range(1, min(len(unyielded_content), len(hidden_marker)) + 1):
                            # Check if the last k chars match the first k chars of marker
                            suffix = unyielded_content[-k:]
                            if hidden_marker.startswith(suffix):
                                # Found a potential marker start.
                                # The safe part is everything before this suffix.
                                safe_end_index = len(unyielded_content) - k
                                # We want the longest match (which corresponds to largest k),
                                # BUT actually we want to be conservative. 
                                # If we match "n>" (end of hidden_plan) it doesn't matter since we check prefix.
                                # We check if suffix matches PREFIX of marker.
                                # e.g. "<", "<h", "<hi".
                                # The longest such suffix must be held back.
                                # So we keep searching larger k? 
                                # No, unyielded_content[-k:] is the suffix. 
                                # If unyielded is "text<hi", k=1 suffix="i" (no), k=2 suffix="hi" (no), k=3 suffix="<hi" (yes).
                                # Wait, "i" is not prefix of "<hidden_plan>".
                                # So we just need to find ANY k that matches?
                                # If we have multiple matches? e.g. marker="aba", content="...aba".
                                # suffix "a" matches prefix "a". suffix "aba" matches prefix "aba".
                                # We should hold back the longest one.
                                pass
                        
                        # Let's do it correctly:
                        longest_match_len = 0
                        for k in range(1, min(len(unyielded_content), len(hidden_marker)) + 1):
                            if hidden_marker.startswith(unyielded_content[-k:]):
                                longest_match_len = k
                        
                        # Yield everything except the potentially matching suffix
                        if longest_match_len < len(unyielded_content):
                            chunk_to_yield = unyielded_content[:len(unyielded_content) - longest_match_len]
                            yield chunk_to_yield
                            yielded_len += len(chunk_to_yield)

            # End of stream. Now parse the JSON from full_content.
            # Extract content between <hidden_plan> and </hidden_plan>
            try:
                start_tag = "<hidden_plan>"
                end_tag = "</hidden_plan>"
                
                if start_tag in full_content and end_tag in full_content:
                    json_str = full_content.split(start_tag)[1].split(end_tag)[0].strip()
                    # Clean up markdown code blocks if present inside the tag
                    if json_str.startswith("```json"):
                        json_str = json_str.replace("```json", "").replace("```", "")
                    elif json_str.startswith("```"):
                        json_str = json_str.replace("```", "")
                        
                    data = json.loads(json_str)
                    
                    steps = []
                    for s in data.get("steps", []):
                        steps.append(PlanStep(
                            id=str(s.get("id", len(steps)+1)),
                            instruction=s.get("instruction", ""),
                            expected_outcome=s.get("expected_outcome", "")
                        ))
                    yield Plan(goal=data.get("goal", user_input), steps=steps)
                else:
                    # Fallback if tags missing
                    logger.warning("Planner output missing hidden tags. Attempting raw parse or fallback.")
                    # Try to find JSON block anyway?
                    # For now, fallback to single step
                    yield Plan(
                        goal=user_input,
                        steps=[PlanStep(id="1", instruction=user_input, expected_outcome="User request satisfied")]
                    )

            except json.JSONDecodeError as e:
                logger.error(f"Planner JSON decode error: {e}")
                yield Plan(
                    goal=user_input,
                    steps=[PlanStep(id="1", instruction=user_input, expected_outcome="User request satisfied")]
                )

        except Exception as e:
            logger.error(f"Planner failed: {e}")
            yield Plan(
                goal=user_input,
                steps=[PlanStep(id="1", instruction=user_input, expected_outcome="User request satisfied")]
            )
