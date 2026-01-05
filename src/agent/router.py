import json
import logging
from typing import Any

from .errors import ToolNotFoundError, ToolExecutionError
from .tools import ALL_TOOLS, TOOL_FUNCTIONS

logger = logging.getLogger(__name__)

class Router:
    def __init__(self,):
        self.tools = ALL_TOOLS
        self.functions = TOOL_FUNCTIONS

    def get_tool_schemas(self) -> list[dict]:
        return self.tools

    async def call_tool(self, tool_name: str, arguments_json: str) -> Any:
        logger.info(f"准备调用工具: {tool_name}，参数: {arguments_json}")

        if tool_name not in self.functions:
            logger.error(f"尝试调用一个未知的工具: {tool_name}")
            raise ToolNotFoundError(tool_name)
        
        try:
            arguments = json.loads(arguments_json)
            if not isinstance(arguments, dict):
                raise ValueError("参数必须是一个 JSON 对象。")
        except (json.JSONDecodeError, ValueError) as e:
            error_msg = f"解析工具 '{tool_name}' 的参数失败: {e}. 原始参数: '{arguments_json}'"
            logger.error(error_msg)
            # 将解析错误包装成工具执行错误，方便上层统一处理
            raise ToolExecutionError(tool_name=tool_name, error_msg=error_msg)

        # 获取目标函数
        tool_function = self.functions.get(tool_name)

        # 调用函数
        try:
            result = await tool_function(**arguments)
            logger.info(f"工具 '{tool_name}' 执行成功，返回: {result}")
            return result
        except TypeError as e:
            # 捕获参数不匹配等 TypeError
            error_msg = f"调用工具 '{tool_name}' 时参数不匹配: {e}"
            logger.error(error_msg)
            raise ToolExecutionError(tool_name=tool_name, error_msg=error_msg)
        except ToolExecutionError:
            # 如果工具内部已经抛出了 ToolExecutionError，直接向上传递
            raise
        except Exception as e:
            # 捕获其他所有未预期的异常
            error_msg = f"执行工具 '{tool_name}' 时发生未知错误: {e}"
            logger.error(error_msg, exc_info=True)
            raise ToolExecutionError(tool_name=tool_name, error_msg=error_msg)
    
router = Router()
