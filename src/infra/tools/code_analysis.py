"""
Code analysis and testing tools.
"""
import asyncio
import logging
import re
import os
import subprocess
from pathlib import Path
from typing import List, TypedDict, Union, Dict, Any, Optional

from src.core.config import settings
from src.core.exceptions import ToolExecutionError
from src.infra.tools.filesystem import _should_ignore

logger = logging.getLogger(__name__)

SEARCH_IN_FILE_TOOL_NAME = "search_in_files"
RUN_PYTEST_TOOL_NAME = "run_pytest"

class SearchInFilesToolResult(TypedDict):
    file_path: str
    line_number: int
    line_content: str

class RunPytestToolResult(TypedDict, total=False):
    success: bool
    summary: str
    details: str
    returncode: int

SEARCH_IN_FILE_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": SEARCH_IN_FILE_TOOL_NAME,
        "description": (
            "Search for a regex pattern in files within the sandbox. "
            "Automatically excludes common ignored files and directories."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Regex pattern to search for.",
                },
                "file_pattern": {
                    "type": "string",
                    "description": "Glob pattern for file selection (e.g. '**/*.py'). Default: '**/*'",
                    "default": "**/*",
                },
                "include_ignored": {
                    "type": "boolean",
                    "description": "If true, search includes ignored files. Default: false",
                    "default": False
                }
            },
            "required": ["query"],
        },
    },
}

RUN_PYTEST_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": RUN_PYTEST_TOOL_NAME,
        "description": "Run pytest in the sandbox directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Extra arguments for pytest (e.g. ['-q', '-k', 'test_x']).",
                    "default": [],
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds. Default: 120.",
                    "default": 120,
                    "minimum": 1,
                },
            },
            "required": [],
        },
    },
}

def _resolve_sandbox_path(file_path: str) -> Path:
    """
    Resolve and validate that the path is within the sandbox.
    """
    # 1. Strip absolute prefix to enforce relative path
    if os.path.isabs(file_path):
        file_path = file_path.lstrip("/")
        
    sandbox_root = settings.sandbox_dir.resolve()
    
    # 2. Join and resolve
    abs_path = (sandbox_root / file_path).resolve()

    # 3. Check containment
    if sandbox_root not in abs_path.parents and abs_path != sandbox_root:
        raise ToolExecutionError("filesystem", f"Access denied: Path '{file_path}' is outside sandbox.")

    return abs_path

async def search_in_files(
    query: str, file_pattern: str = "**/*", include_ignored: bool = False
) -> Union[List[SearchInFilesToolResult], str]:
    """
    Search for regex pattern in files.
    """
    try:
        query_re = re.compile(query)
    except re.error as e:
        return f"Error: Invalid regex: {e}"

    # Security check for glob pattern
    if ".." in file_pattern:
        return "Error: Pattern cannot contain '..'"
    if os.path.isabs(file_pattern):
        return "Error: Pattern cannot be absolute path"

    def _search() -> List[SearchInFilesToolResult]:
        sandbox = settings.sandbox_dir.resolve()
        results: List[SearchInFilesToolResult] = []

        if not sandbox.exists():
            return []

        for p in sorted(sandbox.glob(file_pattern)):
            try:
                if not p.is_file():
                    continue

                # Security check (Double check)
                resolved_p = p.resolve()
                if sandbox not in resolved_p.parents and resolved_p != sandbox:
                    continue
                
                # Check for ignored files using shared logic
                rel_path_obj = p.relative_to(sandbox)
                if not include_ignored:
                    # We check the relative path object. 
                    # Note: _should_ignore in filesystem.py checks 'p' which might be absolute.
                    # Let's import it and pass 'rel_path_obj' if logic supports it or 'p' if it handles full path checking
                    # The logic in filesystem.py checks parts. Passing relative path is safer for directory checking.
                    if _should_ignore(rel_path_obj, include_ignored):
                        continue

                rel_path = str(rel_path_obj)

                with open(p, "r", encoding="utf-8") as f:
                    for i, line in enumerate(f, start=1):
                        if query_re.search(line):
                            results.append(
                                SearchInFilesToolResult(
                                    file_path=rel_path,
                                    line_number=i,
                                    line_content=line.rstrip("\n"),
                                )
                            )
            except Exception:
                continue

        return results

    try:
        return await asyncio.to_thread(_search)
    except Exception as e:
        logger.error(f"Error searching files: {e}")
        return f"Error searching files: {e}"

def _extract_pytest_summary(output: str) -> str:
    """Extract summary line from pytest output."""
    lines = [ln.strip() for ln in output.strip().splitlines() if ln.strip()]
    summary_candidates = [ln for ln in lines if "===" in ln]
    if summary_candidates:
        return summary_candidates[-1].strip("= ").strip()
    return lines[-1] if lines else ""

async def run_pytest(args: Optional[List[str]] = None, timeout: int = 120) -> Union[RunPytestToolResult, Dict[str, Any]]:
    """Run pytest in sandbox."""
    args = args or []
    sandbox_dir = settings.sandbox_dir.resolve()

    def _run() -> RunPytestToolResult:
        try:
            # Check if pytest is installed or available
            # We assume it is available in the environment
            process = subprocess.run(
                ["pytest", *args],
                cwd=sandbox_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            stdout = process.stdout or ""
            stderr = process.stderr or ""
            combined = (stdout + ("\n" if stdout and stderr else "") + stderr).strip()

            summary = _extract_pytest_summary(combined)

            if process.returncode == 0:
                return RunPytestToolResult(
                    success=True,
                    summary=summary,
                    details="All tests passed.",
                    returncode=process.returncode,
                )
            else:
                return RunPytestToolResult(
                    success=False,
                    summary=summary,
                    details=combined,
                    returncode=process.returncode,
                )

        except FileNotFoundError:
            raise ToolExecutionError("run_pytest", "pytest command not found.")
        except subprocess.TimeoutExpired:
            raise ToolExecutionError("run_pytest", "pytest execution timed out.")
        except Exception as e:
            raise ToolExecutionError("run_pytest", f"Unknown error: {e}")

    try:
        return await asyncio.to_thread(_run)
    except ToolExecutionError:
        raise
    except Exception as e:
        logger.error(f"Error running pytest: {e}")
        # Return a dict to match signature if needed, or raise
        raise ToolExecutionError("run_pytest", str(e))
