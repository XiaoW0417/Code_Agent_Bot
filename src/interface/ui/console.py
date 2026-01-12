"""
UI Manager using Rich.
Handles structured display of Agent activities.
"""
from typing import Optional, List, Any
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree
from rich.live import Live
from rich.markdown import Markdown
from rich.status import Status
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.highlighter import ReprHighlighter

# Initialize Console with forced terminal support to ensure colors work even in some IDEs
console = Console(force_terminal=True)
highlighter = ReprHighlighter()

class UIManager:
    """
    Manages terminal output with rich formatting.
    """
    def __init__(self):
        self.console = console
        self._live: Optional[Live] = None
        self._status: Optional[Status] = None
        self._stream_buffer: str = ""

    def print_system_message(self, message: str, style: str = "bold blue"):
        self.console.print(f"[{style}]{message}[/{style}]")

    def print_user_input(self, message: str):
        self.console.print(Panel(message, title="User", border_style="green", padding=(1, 2)))

    def print_agent_response(self, message: str):
        self.console.print(Panel(Markdown(message), title="Agent", border_style="blue", padding=(1, 2)))
    
    def start_stream(self, title: str = "Agent"):
        """Start a live stream update for markdown content."""
        self._stream_buffer = ""
        # We create a Live display that we will update continuously
        # The content will be a Panel containing Markdown
        # refresh_per_second increased for smoother streaming
        # vertical_overflow="visible" ensures long content scrolls naturally
        self._live = Live(
            Panel("", title=title, border_style="blue", padding=(1, 2)),
            console=self.console,
            refresh_per_second=12,
            vertical_overflow="visible"
        )
        self._live.start()

    def update_stream(self, chunk: str):
        """Update the live stream with new content."""
        if self._live:
            self._stream_buffer += chunk
            # Re-render the Markdown with the updated buffer
            # Adding padding makes it look more professional
            self._live.update(
                Panel(
                    Markdown(self._stream_buffer), 
                    title="Agent", 
                    border_style="blue", 
                    padding=(1, 2)
                )
            )
        else:
            # Fallback if start_stream wasn't called
            self.console.print(chunk, end="")

    def end_stream(self):
        """Stop the live stream."""
        if self._live:
            # Force one final update to ensure complete content is rendered
            # This handles cases where the last chunk arrived but Live didn't refresh yet
            self._live.update(
                Panel(
                    Markdown(self._stream_buffer), 
                    title="Agent", 
                    border_style="blue", 
                    padding=(1, 2)
                )
            )
            self._live.stop()
            self._live = None
            self._stream_buffer = ""

    def print_stream_chunk(self, chunk: str):
        """Deprecated: Use start_stream/update_stream/end_stream cycle instead."""
        self.console.print(chunk, end="")

    def start_phase(self, phase_name: str, description: str):
        """Start a phase (e.g. Planning, Executing)."""
        self.console.print(f"\n[bold magenta]➜ {phase_name}[/bold magenta]: {description}")

    def show_plan(self, plan_data: Any):
        """Display the plan structure."""
        tree = Tree(f"[bold]{plan_data.goal}[/bold]")
        for step in plan_data.steps:
            tree.add(f"[cyan][{step.id}][/cyan] {step.instruction}")
        
        self.console.print(Panel(tree, title="Execution Plan", border_style="yellow"))

    def show_step_start(self, step_id: str, instruction: str):
        self.console.print(f"\n[bold yellow]Step {step_id}[/bold yellow]: {instruction}")

    def show_tool_event(self, name: str, args: dict, result: Any):
        """Display a tool execution event in a concise, structured way."""
        # 1. Tool Call Line
        # Format: 🔨 ToolName(arg1=val1, ...)
        args_str = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
        # Truncate args if too long
        if len(args_str) > 100:
            args_str = args_str[:100] + "..."
            
        call_text = Text("🔨 ")
        call_text.append(name, style="bold cyan")
        call_text.append("(")
        call_text.append(args_str, style="dim")
        call_text.append(")")
        
        self.console.print(call_text)

        # 2. Result Line
        # Format:    → ResultSummary
        # We need to handle different result types.
        # If result is a dict with 'write_result', 'files', etc, use that.
        
        res_summary = ""
        if isinstance(result, dict):
            if "error" in result:
                res_summary = f"[red]Error: {result['error']}[/red]"
            elif "write_result" in result:
                res_summary = f"[green]{result['write_result']}[/green]"
            elif "files" in result:
                # Assuming list_files returns a newline separated string in 'files'
                # or maybe a list? In filesystem.py it returns FileLists(files=str)
                files = result['files']
                count = len(files.splitlines()) if files else 0
                res_summary = f"Found {count} files."
            elif "content" in result:
                # Read file
                content = result['content']
                preview = content[:50].replace("\n", " ") + "..." if len(content) > 50 else content
                res_summary = f"Read {len(content)} chars: {preview}"
            elif "rate" in result:
                 # FX
                 res_summary = f"Rate: {result['rate']}, Amount: {result.get('converted_amount')}"
            else:
                # Generic dict
                res_summary = str(result)[:100]
        else:
            res_summary = str(result)[:100]
            
        res_text = Text("   → ")
        res_text.append(Text.from_markup(res_summary))
        self.console.print(res_text)

    def show_critic_feedback(self, approved: bool, comments: str):
        if approved:
            self.console.print(f"  [bold green]✅ Approved[/bold green]")
        else:
            self.console.print(f"  [bold red]❌ Rejected[/bold red]: {comments}")
    
    def show_error(self, error: str):
        self.console.print(f"[bold red]Error:[/bold red] {error}")

ui = UIManager()
