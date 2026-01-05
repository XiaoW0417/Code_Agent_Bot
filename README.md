# Aget Bot

## 笔记
### dataclass
```python
from dataclasses import dataclass
'''十分简洁，可直接print(Settings实例)、初始化'''
@dataclass
class Settings():
    a: str | None
    b: int | None
```

### load_dotenv
```python
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path='.env') # 把.env里面的内容以键值对的方式写入os.env中
key = os.getenv('key')          # 可直接通过os.getenv取出相应的值
```

### 定义异常基类
```python
class AgentError(Exception):             # 定义基类继承Exception，通过往父类的__init__传字符串，打印出来的字符串即为传入的字符
    def __init__(self, tool_name: str):
        super().__init__(f"Agent Error with '{tool_name}'") 
try:
    if xx:
        raise AgentError('search_tool')
except AgentError as e:
    print(e)
```

## httpx
内置异步函数，更加现代化

## Typing
```python
from typing import Literal, TypedDict, cast
Literal: 限制变量只能是几个特定的值
TypedDict: 用来给字典定义结构。
cast: 欺骗 / 强制类型检查器的工具。
```

## openai 库
```python
from openai import AsyncOpenAI

self.client = AsyncOpenAI(             # 这一步是创建了一个异步类，用于发送消息
    api_key = openai_key,              # 在创建时指定 key 和 url
    base_url = setting.openai_base_url
)

response = await self.client.chat.completions.create(
    model = model,                     # 在这一步指定模型、消息  tool相关的为可选
    messages = messages,               # 注意是await
    tools = tool_schemas,
    tool_choice = "auto"
)
response_message = response.choices[0].message    # 其中response_message.tool_calls能拿到tool的name和相关args, 此时
tool_call = response_message.tool_calls           # tool和response只有其中一个，另外一个为None, 用于判断是否需要tool_call
reponse = response_message.content                # 上下文本质是通过一个Messages列表来维护的

```

