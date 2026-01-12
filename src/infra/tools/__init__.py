"""
Tool registry.
"""
from .external.weather import get_current_weather, WEATHER_TOOL_SCHEMA
from .external.fx import get_exchange_rate, FX_TOOL_SCHEMA
from .external.wiki import get_wikipedia_summary, WIKI_TOOL_SCHEMA
from .external.timez import get_timezone_time, TIMEZ_TOOL_SCHEMA

from .filesystem import (
    read_file, list_files, write_file, apply_patch, delete_file, delete_directory,
    LIST_FILES_TOOL_SCHEMA, READ_FILE_TOOL_SCHEMA, WRITE_FILE_TOOL_SCHEMA, 
    APPLY_PATCH_TOOL_SCHEMA, DELETE_FILE_TOOL_SCHEMA, DELETE_DIRECTORY_TOOL_SCHEMA
)
from .code_analysis import (
    search_in_files, run_pytest, 
    SEARCH_IN_FILE_TOOL_SCHEMA, RUN_PYTEST_TOOL_SCHEMA
)

ALL_TOOLS = [
    WEATHER_TOOL_SCHEMA,
    FX_TOOL_SCHEMA,
    WIKI_TOOL_SCHEMA,
    TIMEZ_TOOL_SCHEMA,
    LIST_FILES_TOOL_SCHEMA,
    READ_FILE_TOOL_SCHEMA,
    WRITE_FILE_TOOL_SCHEMA,
    APPLY_PATCH_TOOL_SCHEMA,
    DELETE_FILE_TOOL_SCHEMA,
    DELETE_DIRECTORY_TOOL_SCHEMA,
    SEARCH_IN_FILE_TOOL_SCHEMA,
    RUN_PYTEST_TOOL_SCHEMA,
]

TOOL_FUNCTIONS = {
    "get_current_weather": get_current_weather,
    "get_exchange_rate": get_exchange_rate,
    "get_wikipedia_summary": get_wikipedia_summary,
    "get_timezone_time": get_timezone_time,
    "read_file": read_file,
    "list_files": list_files,
    "write_file": write_file,
    "apply_patch": apply_patch,
    "delete_file": delete_file,
    "delete_directory": delete_directory,
    "search_in_files": search_in_files,
    "run_pytest": run_pytest,
}
