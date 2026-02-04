"""
OpenAI Provider Implementation.
"""
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from openai import AsyncOpenAI, APIStatusError, RateLimitError
from openai.types.chat import ChatCompletionMessage
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from src.core.llm.base import LLMProvider, LLMConfig
from src.core.exceptions import ModelResponseError

logger = logging.getLogger(__name__)

class OpenAIProvider(LLMProvider):
    """OpenAI Implementation of LLMProvider."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout
        )

    @retry(
        retry=retry_if_exception_type((RateLimitError, APIStatusError)),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def chat_complete(
        self, 
        messages: List[Dict[str, Any]], 
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Any = "auto"
    ) -> ChatCompletionMessage:
        """
        Execute chat completion.
        Returns the OpenAI ChatCompletionMessage object.
        """
        try:
            kwargs = {
                "model": self.config.model,
                "messages": messages,
                "temperature": self.config.temperature,
            }
            
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = tool_choice

            response = await self.client.chat.completions.create(**kwargs)
            return response.choices[0].message
        except Exception as e:
            # Check if it's a rate limit error to be retried by tenacity
            # RateLimitError is raised by openai library for 429
            if isinstance(e, (RateLimitError, APIStatusError)):
                # If it's a 4xx error (except 429), usually we shouldn't retry, 
                # but APIStatusError covers 5xx too. 
                # Specifically for 429, we definitely want to retry.
                # OpenAI's RateLimitError covers 429.
                raise e 
            
            logger.error(f"OpenAI completion error: {e}")
            raise ModelResponseError(f"OpenAI API Error: {e}")

    async def chat_stream(
        self, 
        messages: List[Dict[str, Any]], 
        tools: Optional[List[Dict[str, Any]]] = None, 
        tool_choice: Any = "auto"
    ) -> AsyncGenerator[Any, None]:
        """
        Stream content tokens or tool calls.
        Yields the raw chunk from OpenAI.
        """
        # Manual retry logic for generator since tenacity decorators don't work easily with async generators
        # We can implement a simple retry loop here.
        max_retries = 5
        attempt = 0
        backoff = 2
        
        while True:
            try:
                kwargs = {
                    "model": self.config.model,
                    "messages": messages,
                    "temperature": self.config.temperature,
                    "stream": True
                }
                
                if tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = tool_choice

                stream = await self.client.chat.completions.create(**kwargs)
                
                async for chunk in stream:
                    yield chunk
                
                return # Success, exit loop

            except (RateLimitError, APIStatusError) as e:
                attempt += 1
                if attempt >= max_retries:
                    logger.error(f"OpenAI Stream Max Retries reached: {e}")
                    raise ModelResponseError(f"OpenAI Stream Error after retries: {e}")
                
                logger.warning(f"OpenAI Stream Rate Limit/Error (Attempt {attempt}/{max_retries}): {e}. Retrying in {backoff}s...")
                import asyncio
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)
            
            except Exception as e:
                logger.error(f"OpenAI stream error: {e}")
                raise ModelResponseError(f"OpenAI Stream Error: {e}")
