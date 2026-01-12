"""
Filesystem tools for the agent.
"""
import asyncio
import io
import os
import shutil
import logging
from pathlib import Path
from typing import TypedDict, List, Set

from unidiff import PatchSet

from src.core.config import settings
from src.core.exceptions import ToolExecutionError

logger = logging.getLogger(__name__)

class FileLists(TypedDict):
    files: str

class FileContent(TypedDict):
    content: str

class WriteFileResult(TypedDict):
    write_result: str

LIST_FILES_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "list_files",
        "description": (
            "List files in the sandbox directory. "
            "Supports glob patterns, returns files and directories relative to sandbox."
            " Automatically filters out common ignored directories (e.g., .git, venv) and files."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern for filtering files (e.g. '**/*', '*.txt'). Default: '**/*'",
                    "default": "**/*"
                },
                "include_ignored": {
                    "type": "boolean",
                    "description": "If true, includes files that are normally ignored (e.g. .git, venv). Default: false",
                    "default": False
                }
            },
            "required": []
        }
    }
}

READ_FILE_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read the content of a file in the sandbox.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file in the sandbox."
                }
            },
            "required": ["path"]
        }
    }
}

WRITE_FILE_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Write content to a file in the sandbox. Creates parent directories if needed.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file."
                },
                "content": {
                    "type": "string",
                    "description": "Content to write."
                },
                "append": {
                    "type": "boolean",
                    "description": "If true, append to file. If false, overwrite. Default: false",
                    "default": False
                }
            },
            "required": ["path", "content"]
        }
    }
}

APPLY_PATCH_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "apply_patch",
        "description": "Apply a unidiff patch to a single file in the sandbox.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Target file path relative to sandbox."
                },
                "patch_content": {
                    "type": "string",
                    "description": "Strict unidiff content."
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, check if patch applies without writing.",
                    "default": False
                }
            },
            "required": ["path", "patch_content"]
        }
    }
}

DELETE_FILE_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "delete_file",
        "description": "Delete a single file in the sandbox.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file."
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, return what would be deleted.",
                    "default": False
                }
            },
            "required": ["path"]
        }
    }
}

DELETE_DIRECTORY_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "delete_directory",
        "description": "Recursively delete a directory in the sandbox.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the directory."
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, return what would be deleted.",
                    "default": False
                }
            },
            "required": ["path"]
        }
    }
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

def _should_ignore(path: Path, include_ignored: bool) -> bool:
    """Check if path should be ignored based on settings."""
    if include_ignored:
        return False
        
    # Check for ignore dirs in parts
    # e.g. /sandbox/node_modules/foo.js -> parts: (sandbox, node_modules, foo.js)
    # We check relative to sandbox ideally, but here we can check if any part matches.
    # However, 'src/components/button.js' shouldn't be ignored if 'src' is not in ignore list.
    
    # Check filename extensions
    if path.suffix in settings.ignore_extensions:
        return True
    
    # Check directory components
    # We only care about components relative to the search root, but here path is absolute or relative.
    # Let's assume we check the name of the file/dir itself and its parents.
    
    # Optimization: Check if any part of the path is in ignore_dirs
    for part in path.parts:
        if part in settings.ignore_dirs:
            return True
            
    return False

async def list_files(pattern: str = "**/*", include_ignored: bool = False) -> FileLists:
    """List files in the sandbox."""
    sandbox_path = settings.sandbox_dir.resolve()

    # Security check for glob pattern
    if ".." in pattern:
        raise ToolExecutionError("list_files", "Pattern cannot contain '..'")
    if os.path.isabs(pattern):
        raise ToolExecutionError("list_files", "Pattern cannot be absolute path")

    def _list() -> FileLists:
        # Ensure sandbox exists
        if not sandbox_path.exists():
             return FileLists(files="")
             
        matched_paths = sorted(sandbox_path.glob(pattern))
        relative_paths = []
        for p in matched_paths:
            try:
                # Ensure each matched path is actually inside sandbox (double check)
                resolved_p = p.resolve()
                if sandbox_path in resolved_p.parents or resolved_p == sandbox_path:
                    # Filter ignored files
                    # We check relative path parts to be safe
                    rel_path = p.relative_to(sandbox_path)
                    
                    if not include_ignored:
                        # Check each component of the relative path
                        # e.g. "node_modules/package.json" -> node_modules is in ignore_dirs
                        should_skip = False
                        if p.name.startswith(".") and p.name != ".": # Ignore hidden files/dirs if not explicitly requested? 
                            # Wait, .gitignore, .env might be useful. 
                            # Let's rely on explicit ignore list for now.
                            pass
                        
                        for part in rel_path.parts:
                            if part in settings.ignore_dirs:
                                should_skip = True
                                break
                        
                        if p.suffix in settings.ignore_extensions:
                            should_skip = True
                            
                        if should_skip:
                            continue

                    relative_paths.append(str(rel_path))
            except Exception:
                continue
                
        return FileLists(files="\n".join(relative_paths))

    try:
        return await asyncio.to_thread(_list)
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        # Return error message in files field so agent sees it
        if isinstance(e, ToolExecutionError):
            return FileLists(files=f"Error: {e}")
        return FileLists(files=f"Error listing files: {e}")

async def read_file(path: str) -> FileContent:
    """Read a file from the sandbox."""
    try:
        safe_path = _resolve_sandbox_path(path)
        if not safe_path.is_file():
            raise ToolExecutionError("read_file", f"'{path}' is not a file or does not exist.")

        def _read() -> FileContent:
            with open(safe_path, 'r', encoding='utf-8') as f:
                return FileContent(content=f.read())

        return await asyncio.to_thread(_read)
    except Exception as e:
        logger.error(f"Error reading file '{path}': {e}")
        return FileContent(content=f"Error reading file: {e}")

async def write_file(path: str, content: str, append: bool = False) -> WriteFileResult:
    """Write content to a file."""
    try:
        safe_path = _resolve_sandbox_path(path)

        def _write() -> WriteFileResult:
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            mode = 'a' if append else 'w'
            with open(safe_path, mode, encoding='utf-8') as f:
                f.write(content)
            return WriteFileResult(write_result=f"File '{path}' written successfully.")

        return await asyncio.to_thread(_write)
    except Exception as e:
        logger.error(f"Error writing file '{path}': {e}")
        return WriteFileResult(write_result=f"Error writing file: {e}")

async def apply_patch(path: str, patch_content: str, dry_run: bool = False) -> WriteFileResult:
    """Apply a unidiff patch."""
    try:
        safe_path = _resolve_sandbox_path(path)

        if not safe_path.is_file():
            return WriteFileResult(write_result=f"Error: '{path}' is not a file.")

        def _apply() -> WriteFileResult:
            patch_text = patch_content.strip()
            # Remove markdown code blocks if present
            if patch_text.startswith("```"):
                patch_text = "\n".join(
                    line for line in patch_text.splitlines()
                    if not line.strip().startswith("```")
                )

            with open(safe_path, "r", encoding="utf-8") as f:
                original_lines = f.readlines()

            patch = PatchSet(io.StringIO(patch_text))
            if len(patch) != 1:
                return WriteFileResult(write_result="Error: Patch must modify exactly one file.")

            patched_file = patch[0]
            
            new_lines = []
            src_idx = 0

            for hunk in patched_file:
                while src_idx < hunk.source_start - 1:
                    if src_idx < len(original_lines):
                        new_lines.append(original_lines[src_idx])
                    src_idx += 1

                for line in hunk:
                    if line.is_context or line.is_added:
                        new_lines.append(line.value)
                    if not line.is_added:
                        src_idx += 1

            if src_idx < len(original_lines):
                new_lines.extend(original_lines[src_idx:])

            if dry_run:
                return WriteFileResult(write_result=f"Dry run: Patch can be applied to '{path}'.")

            with open(safe_path, "w", encoding="utf-8") as f:
                f.write("".join(new_lines))
            
            return WriteFileResult(write_result=f"Patch successfully applied to '{path}'.")

        return await asyncio.to_thread(_apply)
    except Exception as e:
        logger.error(f"Error applying patch to '{path}': {e}")
        return WriteFileResult(write_result=f"Error applying patch: {e}")

async def delete_file(path: str, dry_run: bool = False) -> WriteFileResult:
    """Delete a single file."""
    try:
        safe_path = _resolve_sandbox_path(path)
        
        if not safe_path.exists():
             return WriteFileResult(write_result=f"Error: File '{path}' does not exist.")
        if not safe_path.is_file():
             return WriteFileResult(write_result=f"Error: '{path}' is not a file.")

        if dry_run:
            return WriteFileResult(write_result=f"Dry run: File '{path}' would be deleted.")

        def _delete() -> WriteFileResult:
            os.remove(safe_path)
            return WriteFileResult(write_result=f"File '{path}' deleted successfully.")

        return await asyncio.to_thread(_delete)
    except Exception as e:
        logger.error(f"Error deleting file '{path}': {e}")
        return WriteFileResult(write_result=f"Error deleting file: {e}")

async def delete_directory(path: str, dry_run: bool = False) -> WriteFileResult:
    """Delete a directory recursively."""
    try:
        safe_path = _resolve_sandbox_path(path)
        
        # Prevent deleting root sandbox
        if safe_path == settings.sandbox_dir.resolve():
             return WriteFileResult(write_result="Error: Cannot delete the root sandbox directory.")

        if not safe_path.exists():
             return WriteFileResult(write_result=f"Error: Directory '{path}' does not exist.")
        if not safe_path.is_dir():
             return WriteFileResult(write_result=f"Error: '{path}' is not a directory.")

        if dry_run:
            return WriteFileResult(write_result=f"Dry run: Directory '{path}' would be deleted.")

        def _delete() -> WriteFileResult:
            shutil.rmtree(safe_path)
            return WriteFileResult(write_result=f"Directory '{path}' deleted successfully.")

        return await asyncio.to_thread(_delete)
    except Exception as e:
        logger.error(f"Error deleting directory '{path}': {e}")
        return WriteFileResult(write_result=f"Error deleting directory: {e}")
