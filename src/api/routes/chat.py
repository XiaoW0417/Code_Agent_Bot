"""
Chat API endpoints with streaming support.
Integrated with real LLM provider and Tool Execution.
"""
import logging
import asyncio
import json
from typing import AsyncGenerator, Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.infra.database.connection import get_db
from src.infra.database.models import User, Session as ChatSession, Message
from src.infra.database.repositories import SessionRepository, MessageRepository
from src.infra.auth.dependencies import get_current_active_user
from src.infra.llm.openai import OpenAIProvider
from src.core.llm.base import LLMConfig
from src.core.config import settings
from src.core.skills.registry import registry

logger = logging.getLogger(__name__)
router = APIRouter()

# LLM Provider singleton
_llm_provider: Optional[OpenAIProvider] = None


def get_llm_provider() -> OpenAIProvider:
    """Get or create LLM provider instance."""
    global _llm_provider
    if _llm_provider is None:
        if not settings.openai_api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM provider not configured. Please set OPENAI_API_KEY."
            )
        
        config = LLMConfig(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.model_name,
            temperature=0.7
        )
        _llm_provider = OpenAIProvider(config)
    return _llm_provider


class ChatRequest(BaseModel):
    """Chat request with message."""
    session_id: str
    message: str = Field(..., min_length=1, max_length=50000)


class ChatResponse(BaseModel):
    """Non-streaming chat response."""
    session_id: str
    user_message_id: str
    assistant_message_id: str
    content: str
    tokens_used: int


def build_messages_for_llm(messages: List[Message], system_prompt: Optional[str] = None) -> list:
    """Build message list for LLM from database messages."""
    llm_messages = []
    
    # Add system prompt if provided
    if system_prompt:
        llm_messages.append({
            "role": "system",
            "content": system_prompt
        })
    else:
        # Default system prompt
        llm_messages.append({
            "role": "system",
            "content": """You are Agent Bot, a helpful AI coding assistant. You have access to a set of tools to help you with your tasks.
When asked to perform actions (like reading files, searching code, etc.), use the available tools.
If you need to explore the project, use ExploreProject.
If you need to read a file, use ViewFile.
If you need to edit a file, use EditFile.
Always explain your plan before executing tools.
Respond in the same language the user uses."""
        })
    
    # Add conversation history
    for msg in messages:
        message_dict = {
            "role": msg.role,
            "content": msg.content
        }
        if msg.tool_calls:
            message_dict["tool_calls"] = msg.tool_calls
        if msg.tool_call_id:
            message_dict["tool_call_id"] = msg.tool_call_id
            
        llm_messages.append(message_dict)
    
    return llm_messages


async def generate_stream_response(
    session_id: str,
    user_message: str,
    user: User,
    db: Session
) -> AsyncGenerator[str, None]:
    """Generate streaming response using real LLM with tool execution loop."""
    session_repo = SessionRepository(db)
    message_repo = MessageRepository(db)
    
    try:
        # Verify session ownership
        session = session_repo.get_user_session(session_id, user.id)
        if not session:
            yield f"data: {json.dumps({'event': 'error', 'data': {'message': 'Session not found'}})}\n\n"
            return
        
        # Store user message
        user_msg = message_repo.add_message(
            session_id=session_id,
            role="user",
            content=user_message
        )
        
        # Get LLM provider
        try:
            llm = get_llm_provider()
        except HTTPException as e:
            yield f"data: {json.dumps({'event': 'error', 'data': {'message': e.detail}})}\n\n"
            return

        # Get available tools
        tools_schema = registry.get_schemas()
        
        # Max rounds to prevent infinite loops
        max_rounds = 5
        current_round = 0
        
        while current_round < max_rounds:
            current_round += 1
            
            # Send phase update
            phase = "thinking" if current_round == 1 else "planning"
            yield f"data: {json.dumps({'event': 'phase', 'data': {'phase': phase}})}\n\n"
            
            # Get conversation history for context
            # Note: We need to fetch fresh messages in each round as we might have added tool outputs
            messages = message_repo.get_session_messages(session_id, limit=50)
            llm_messages = build_messages_for_llm(messages)
            
            # Stream response from LLM
            full_content = ""
            tool_calls_buffer = []
            
            # Temporary storage for tool call chunks
            current_tool_call = {}
            
            try:
                # We need to handle the stream carefully to detect tool calls vs content
                async for chunk in llm.chat_stream(llm_messages, tools=tools_schema):
                    delta = chunk.choices[0].delta
                    
                    # Handle Content
                    if delta.content:
                        full_content += delta.content
                        yield f"data: {json.dumps({'event': 'message', 'data': {'chunk': delta.content}})}\n\n"
                    
                    # Handle Tool Calls
                    if delta.tool_calls:
                        for tool_call_chunk in delta.tool_calls:
                            index = tool_call_chunk.index
                            
                            # Extend buffer if needed
                            while len(tool_calls_buffer) <= index:
                                tool_calls_buffer.append({
                                    "id": "",
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""}
                                })
                            
                            # Update buffer
                            if tool_call_chunk.id:
                                tool_calls_buffer[index]["id"] = tool_call_chunk.id
                            
                            if tool_call_chunk.function:
                                if tool_call_chunk.function.name:
                                    tool_calls_buffer[index]["function"]["name"] += tool_call_chunk.function.name
                                if tool_call_chunk.function.arguments:
                                    tool_calls_buffer[index]["function"]["arguments"] += tool_call_chunk.function.arguments

            except Exception as e:
                logger.error(f"LLM streaming error: {e}")
                yield f"data: {json.dumps({'event': 'error', 'data': {'message': f'LLM error: {str(e)}'}})}\n\n"
                return
            
            # Check if we have tool calls
            if tool_calls_buffer:
                # Store assistant message with tool calls
                assistant_msg = message_repo.add_message(
                    session_id=session_id,
                    role="assistant",
                    content=full_content,
                    tool_calls=tool_calls_buffer
                )
                
                # Execute tools
                yield f"data: {json.dumps({'event': 'phase', 'data': {'phase': 'executing'}})}\n\n"
                
                for tool_call in tool_calls_buffer:
                    function_name = tool_call["function"]["name"]
                    arguments_str = tool_call["function"]["arguments"]
                    tool_call_id = tool_call["id"]
                    
                    try:
                        arguments = json.loads(arguments_str)
                        
                        # Find skill
                        skill = registry.get_skill(function_name)
                        
                        # Execute
                        result = await skill.execute(**arguments)
                        result_str = str(result)
                        
                    except Exception as e:
                        result_str = f"Error executing tool {function_name}: {str(e)}"
                    
                    # Store tool output
                    message_repo.add_message(
                        session_id=session_id,
                        role="tool",
                        content=result_str,
                        tool_call_id=tool_call_id
                    )
                    
                    # Send tool output event (optional, for UI to show)
                    # yield f"data: {json.dumps({'event': 'tool_output', 'data': {'name': function_name, 'output': result_str}})}\n\n"
                
                # Continue loop to get LLM's interpretation of tool outputs
                continue
            
            else:
                # No tool calls, this is the final response
                assistant_msg = message_repo.add_message(
                    session_id=session_id,
                    role="assistant",
                    content=full_content
                )
                
                # Update session timestamp
                session_repo.update(session_id)
                
                # Send done event
                yield f"data: {json.dumps({'event': 'done', 'data': {'assistant_message_id': assistant_msg.id, 'user_message_id': user_msg.id}})}\n\n"
                break
        
        if current_round >= max_rounds:
             yield f"data: {json.dumps({'event': 'error', 'data': {'message': 'Max conversation turns reached'}})}\n\n"

    except Exception as e:
        logger.error(f"Error in chat stream: {e}", exc_info=True)
        yield f"data: {json.dumps({'event': 'error', 'data': {'message': str(e)}})}\n\n"


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Stream chat response using Server-Sent Events (SSE).
    """
    return StreamingResponse(
        generate_stream_response(
            request.session_id,
            request.message,
            current_user,
            db
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> ChatResponse:
    """Non-streaming chat endpoint."""
    # ... (Keep existing implementation or update similarly if needed)
    # For now, we focus on streaming as that's what the UI uses.
    # But to be safe, let's just return a placeholder or implement basic tool loop without streaming.
    
    session_repo = SessionRepository(db)
    message_repo = MessageRepository(db)
    
    # Verify session
    session = session_repo.get_user_session(request.session_id, current_user.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Store user message
    user_msg = message_repo.add_message(
        session_id=request.session_id,
        role="user",
        content=request.message
    )
    
    # Get LLM
    llm = get_llm_provider()
    tools_schema = registry.get_schemas()
    
    # Simple single-turn implementation for non-streaming (or implement loop)
    messages = message_repo.get_session_messages(request.session_id, limit=50)
    llm_messages = build_messages_for_llm(messages)
    
    try:
        response = await llm.chat_complete(llm_messages, tools=tools_schema)
        response_content = response.content or ""
        
        # Note: This non-streaming endpoint doesn't handle tool execution loop here for brevity
        # In production, you'd want to refactor the loop logic to be shared.
        
    except Exception as e:
        logger.error(f"LLM error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM error: {str(e)}"
        )
    
    # Store assistant message
    assistant_msg = message_repo.add_message(
        session_id=request.session_id,
        role="assistant",
        content=response_content,
        tool_calls=response.tool_calls if hasattr(response, 'tool_calls') else None
    )
    
    session_repo.update(request.session_id)
    
    return ChatResponse(
        session_id=request.session_id,
        user_message_id=user_msg.id,
        assistant_message_id=assistant_msg.id,
        content=response_content,
        tokens_used=0
    )
