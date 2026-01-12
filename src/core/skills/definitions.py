"""
Concrete Skill Implementations.
Wraps infra.tools into high-level Skills.
"""
from typing import Any, Dict, List
import json

from src.core.skills.base import Skill
from src.infra.tools import filesystem, code_analysis

class ExploreProject(Skill):
    name = "ExploreProject"
    description = (
        "Explore the project structure by listing files. "
        "Use this to understand the directory layout or find specific files. "
        "Automatically ignores common clutter (node_modules, venv, etc)."
    )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path_pattern": {
                    "type": "string",
                    "description": "Glob pattern to list (e.g. 'src/**/*.py'). Default: '**/*'",
                    "default": "**/*"
                }
            },
            "required": []
        }

    async def execute(self, path_pattern: str = "**/*") -> Any:
        # Maps to filesystem.list_files
        # Note: We enforce include_ignored=False for high-level skill
        return await filesystem.list_files(pattern=path_pattern, include_ignored=False)


class ViewFile(Skill):
    name = "ViewFile"
    description = (
        "Read the content of a specific file. "
        "Use this when you need to examine code or configuration details."
    )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to read (relative to project root)."
                }
            },
            "required": ["file_path"]
        }

    async def execute(self, file_path: str) -> Any:
        return await filesystem.read_file(path=file_path)


class SearchCode(Skill):
    name = "SearchCode"
    description = (
        "Search for a text pattern (regex) across the project codebase. "
        "Useful for finding usages of a function, variable, or error message."
    )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regex pattern to search for."
                },
                "file_filter": {
                    "type": "string",
                    "description": "Glob pattern to limit search scope (e.g. 'src/*.py').",
                    "default": "**/*"
                }
            },
            "required": ["pattern"]
        }

    async def execute(self, pattern: str, file_filter: str = "**/*") -> Any:
        return await code_analysis.search_in_files(
            query=pattern, 
            file_pattern=file_filter, 
            include_ignored=False
        )


class EditFile(Skill):
    name = "EditFile"
    description = (
        "Modify a file by replacing its content or appending to it. "
        "For complex partial edits, consider reading the file first to ensure context."
    )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to edit."
                },
                "new_content": {
                    "type": "string",
                    "description": "The new content for the file."
                },
                "operation": {
                    "type": "string",
                    "enum": ["overwrite", "append"],
                    "description": "Edit mode: 'overwrite' replaces entire file, 'append' adds to end.",
                    "default": "overwrite"
                }
            },
            "required": ["file_path", "new_content"]
        }

    async def execute(self, file_path: str, new_content: str, operation: str = "overwrite") -> Any:
        is_append = (operation == "append")
        return await filesystem.write_file(path=file_path, content=new_content, append=is_append)

class DeleteResource(Skill):
    name = "DeleteResource"
    description = (
        "Delete a file or directory. "
        "Use this to remove temporary files or cleanup resources. "
        "Be careful as this operation is irreversible."
    )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file or directory to delete."
                }
            },
            "required": ["path"]
        }

    async def execute(self, path: str) -> Any:
        # Try deleting as file first
        result = await filesystem.delete_file(path=path)
        
        # If it fails because it's not a file (likely a directory), try delete_directory
        if "is not a file" in result.get("write_result", ""):
            return await filesystem.delete_directory(path=path)
            
        return result

class RunTests(Skill):
    name = "RunTests"
    description = (
        "Run the project's test suite (pytest). "
        "Use this to verify changes or check for regressions."
    )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "test_args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional arguments for pytest (e.g. ['-k', 'test_auth']).",
                    "default": []
                }
            },
            "required": []
        }

    async def execute(self, test_args: List[str] = []) -> Any:
        return await code_analysis.run_pytest(args=test_args)
