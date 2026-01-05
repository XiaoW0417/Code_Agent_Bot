
class AgentError(Exception):
    """Agent相关的基础异常类"""
    pass

class ConfigError(AgentError):
    """配置相关错误"""
    pass

class ToolError(AgentError):
    """工具相关错误"""
    pass

class ToolNotFoundError(ToolError):
    """工具未找到"""
    def __init__(self, tool_name: str):
        super().__init__(f"工具'{tool_name}'未找到")

class ToolExecutionError(ToolError):
    """执行工具时发生错误"""
    def __init__(self, tool_name: str, error_msg: str):
        super().__init__(f"执行工具'{tool_name}'时发生错误， 错误：'{error_msg}'")
    
class ModelResponseError(AgentError):
    """模型回复相关错误"""
    pass
