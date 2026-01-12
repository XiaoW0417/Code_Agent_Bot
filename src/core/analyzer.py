"""
Execution Risk Analyzer.
"""
from typing import Dict, Any
from dataclasses import dataclass
import json
import logging

from src.core.llm.base import LLMProvider

logger = logging.getLogger(__name__)

@dataclass
class ExecutionRiskAnalysis:
    requires_tools: bool
    has_side_effects: bool
    requires_multi_step: bool
    is_fast_path: bool
    reason: str

RISK_ANALYSIS_SYSTEM_PROMPT = """
You are an Execution Risk Analyzer. 
Your goal is to evaluate the user's request to determine the appropriate execution path (Fast Path vs Slow Path).

Decision Logic (Execution-Gated Decision):
You MUST classify the request as "Fast Path" ONLY IF ALL of the following are TRUE:
1. No tools are required (no file access, no search, no code execution).
2. No side effects (no file modification, no system state change).
3. No complex reasoning or multi-step planning is needed.
4. The request can be answered in a single turn of natural language generation.

If ANY of the above is False, you MUST classify as "Slow Path".

Output Format:
Return a strictly valid JSON object:
{
    "requires_tools": boolean,
    "has_side_effects": boolean,
    "requires_multi_step": boolean,
    "is_fast_path": boolean,
    "reason": "Brief explanation of the decision"
}
"""

class ExecutionRiskAnalyzer:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def analyze(self, user_input: str) -> ExecutionRiskAnalysis:
        messages = [
            {"role": "system", "content": RISK_ANALYSIS_SYSTEM_PROMPT},
            {"role": "user", "content": user_input}
        ]
        
        try:
            response = await self.llm.chat_complete(messages)
            content = response.content.strip()
            
            if content.startswith("```"):
                content = content.strip("`").replace("json\n", "")
            
            data = json.loads(content)
            return ExecutionRiskAnalysis(
                requires_tools=data.get("requires_tools", True),
                has_side_effects=data.get("has_side_effects", True),
                requires_multi_step=data.get("requires_multi_step", True),
                is_fast_path=data.get("is_fast_path", False),
                reason=data.get("reason", "Default to Slow Path due to parsing error")
            )
        except Exception as e:
            logger.warning(f"Risk analysis failed: {e}. Defaulting to Slow Path.")
            return ExecutionRiskAnalysis(
                requires_tools=True,
                has_side_effects=True,
                requires_multi_step=True,
                is_fast_path=False,
                reason=f"Analysis failed: {e}"
            )
