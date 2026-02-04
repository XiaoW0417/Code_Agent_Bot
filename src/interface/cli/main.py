"""
CLI Entry point.
"""
import asyncio
import logging
import re

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style

from src.core.config import settings
from src.core.orchestrator import Orchestrator
from src.core.mcp.base import MCPClient
from src.core.llm.base import LLMConfig
from src.infra.llm.openai import OpenAIProvider
from src.infra.logging import setup_logging
from src.infra.mcp.filesystem import FileSystemServer
from src.infra.mcp.code_analysis import CodeAnalysisServer
from src.infra.mcp.external import ExternalServicesServer
from src.interface.ui.console import ui

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Style for prompt_toolkit
style = Style.from_dict({
    'prompt': '#00aa00 bold',
})

async def main():
    """CLI Main Loop."""
    ui.print_system_message("\nAgent: Hi I am your agent bot! Input 'exit' or 'quit' to end.")
    ui.print_system_message("Features: \n - Use @model_name to switch models.\n - Use #filename to reference files.\n", style="dim")

    if not settings.is_valid:
        logger.error("Error: OPENAI_API_KEY is not set.")
        ui.show_error("Please set OPENAI_API_KEY in your .env file.")
        return

    try:
        # Initialize Components
        llm_config = LLMConfig(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.model_name or "gpt-3.5-turbo"
        )
        llm_provider = OpenAIProvider(llm_config)
        
        # Initialize MCP Servers
        mcp_servers = [
            FileSystemServer(),
            CodeAnalysisServer(),
            ExternalServicesServer()
        ]
        mcp_client = MCPClient(mcp_servers)
        await mcp_client.initialize()
        
        # Initialize Orchestrator
        orchestrator = Orchestrator(llm_provider, mcp_client)
        
        # Initialize Prompt Session
        session = PromptSession(history=InMemoryHistory())

    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        return

    while True:
        try:
            # prompt_toolkit is blocking, run in thread? 
            # Actually prompt_toolkit has async support: session.prompt_async()
            user_input = await session.prompt_async("> ", style=style)
            user_input = user_input.strip()

            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit"]:
                ui.print_system_message("Goodbye!")
                break

            # Handle @model
            model_match = re.search(r'@([\w.-]+)', user_input)
            if model_match:
                new_model = model_match.group(1)
                orchestrator.set_model(new_model)
                ui.print_system_message(f"Switched model to: {new_model}")
                user_input = user_input.replace(model_match.group(0), "").strip()

            # Handle #file
            file_match = re.search(r'#([\w./-]+)', user_input)
            if file_match:
                file_path = file_match.group(1)
                await orchestrator.handle_file_ref(file_path)
                ui.print_system_message(f"Referenced file: {file_path}")

            if not user_input:
                continue

            # Stream response
            # Note: Orchestrator now uses UI manager for structured output AND stream handling.
            # We just need to await the task.
            
            await orchestrator.chat(user_input)
            
            print("\n") # Newline after stream

        except (KeyboardInterrupt, EOFError):
            ui.print_system_message("\nGoodbye!")
            break
        except Exception as e:
            logger.critical(f"Unexpected error: {e}", exc_info=True)
            ui.show_error(f"Critical error occurred: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram terminated.")
