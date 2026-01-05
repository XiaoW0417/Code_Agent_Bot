from .client import AgentClient
from .config import settings
from .errors import AgentError

import asyncio
import logging

# 必须先设置日志，再导入其他模块，以确保所有模块的日志格式统一
from .logging_setup import setup_logging
setup_logging()

logger = logging.getLogger(__name__)

async def main():
    """命令行交互主程序"""
    print("欢迎使用多工具聊天机器人！输入 'exit' 或 'quit' 结束对话。")

    if not settings.openai_api_key:
        logger.error("错误: API Key 环境变量未设置。")
        print("\n请在 .env 文件中设置你的 API Key (OPENAI_API_KEY)。")
        return

    try:
        agent_client = AgentClient()
    except ValueError as e:
        logger.error(e)
        return

    while True:
        try:
            user_input = input("> ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit"]:
                print("再见！")
                break

            response = await agent_client.chat(user_input)
            print(f"\n🤖: {response}\n")

        except AgentError as e:
            logger.error(f"发生应用错误: {e}", exc_info=True)
            print(f"\n🤖: 抱歉，处理你的请求时遇到了问题: {e}\n")
        except (KeyboardInterrupt, EOFError):
            print("\n再见！")
            break
        except Exception as e:
            logger.critical(f"发生未预期的严重错误: {e}", exc_info=True)
            print(f"\n🤖: 抱歉，系统遇到了一个严重错误，对话已结束。\n")
            break

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # 在 asyncio.run 之外再捕获一次，确保 Ctrl+C 能干净地退出
        print("\n程序已终止。")
