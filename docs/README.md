# Agent Bot (Level 2)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Architecture](https://img.shields.io/badge/Architecture-Skills--First-green)
![Status](https://img.shields.io/badge/Status-Active-success)

Agent Bot (Level 2) 是一个基于 **Skills-First Architecture** 的智能编码助手。它不仅仅是一个简单的聊天机器人，更是一个能够理解复杂意图、自主规划任务、执行代码操作并自我修正的 AI Agent。

该项目采用了类似 Claude Code 的工作流（Plan -> Implement -> Reflect -> Iterate），通过 **Orchestrator** 协调 **Planner** (规划)、**Executor** (执行) 和 **Critic** (审查) 三大核心组件，为开发者提供强大的自动化辅助能力。

---

## 📖 核心功能 (Core Features)

*   **智能规划 (Smart Planning)**: 理解模糊的高层需求，将其拆解为有序的、可执行的步骤。
*   **技能驱动 (Skills-Based)**: 封装了文件操作、代码搜索、测试运行等高层能力，而非低级的 API 调用。
*   **流式交互 (Streaming UI)**: 全链路支持 Markdown 流式输出，提供即时、美观的终端交互体验。
*   **自我修正 (Self-Correction)**: 内置 Critic 角色，自动审查执行结果并提出修改建议。
*   **安全沙箱 (Sandboxed)**: 所有文件操作均限制在安全目录内，并自动过滤敏感或无关文件（如 `.git`, `node_modules`）。

---

## 🚀 快速开始 (Quick Start)

### 1. 环境要求

*   Python 3.10 或更高版本
*   [uv](https://github.com/astral-sh/uv) (推荐的项目管理工具)

### 2. 安装与配置

我们强烈推荐使用 `uv` 进行依赖管理和环境配置。

```bash
# 1. 克隆项目
git clone https://github.com/yourusername/Agent_Bot_l2.git
cd Agent_Bot_l2

# 2. 创建并激活虚拟环境 (使用 uv)
uv venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# 3. 安装依赖
uv pip install -r requirements.txt
```

### 3. 配置环境变量

在项目根目录创建 `.env` 文件（参考 `.env.example`）：

```ini
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1  # 可选，支持兼容 OpenAI 接口的模型
OPENAI_MODEL_NAME=gpt-4o                   # 可选
```

### 4. 运行 Agent

启动交互式 CLI：

```bash
python main.py
```

---

## 💡 使用指南 (Usage Guide)

Agent 支持两种交互模式，系统会自动根据输入内容进行判断：

### 1. 快速通道 (Fast Path)
适用于无需复杂操作的直接问答。
> **User**: "解释一下 Python 的 GIL 是什么？"
> **Agent**: (直接流式输出解释)

### 2. 复杂任务 (Complex Path)
涉及文件操作、代码分析或多步骤执行的任务。系统会自动进入规划模式。
> **User**: "分析当前项目结构，并在 README.md 中生成一个概要。"
> **Agent**:
> 1.  **Architect**: 生成 Markdown 格式的执行计划（流式显示）。
> 2.  **Executor**: 调用 `ExploreProject` 技能扫描文件。
> 3.  **Executor**: 调用 `EditFile` 技能更新 README。
> 4.  **Critic**: 审查操作结果。

### 可用技能 (Available Skills)

| 技能名称 | 描述 |
| :--- | :--- |
| `ExploreProject` | 智能探索项目结构，自动过滤噪音文件。 |
| `ViewFile` | 读取并展示文件内容。 |
| `SearchCode` | 使用正则模式全局搜索代码。 |
| `EditFile` | 创建、覆盖或追加内容到文件。 |
| `DeleteResource` | 删除文件或目录（需谨慎）。 |
| `RunTests` | 运行 pytest 测试套件并返回报告。 |

---

## 📂 项目结构 (Project Structure)

```
src/
├── core/               # 核心智能体逻辑
│   ├── skills/         # Skill 定义与注册 (High-Level 能力封装)
│   ├── planner.py      # 规划器：负责任务拆解
│   ├── executor.py     # 执行器：负责调用 Skills
│   ├── critic.py       # 审查器：负责结果验收
│   ├── orchestrator.py # 编排器：管理 Agent 协作流程
│   └── analyzer.py     # 分析器：意图识别与路由
├── infra/              # 基础设施层
│   ├── tools/          # 底层原子工具 (文件系统、代码分析等)
│   └── mcp/            # MCP (Model Context Protocol) 适配器
└── interface/          # 交互层
    └── ui/             # 基于 Rich 的高性能终端 UI
```

---

## 🛠️ 贡献指南 (Contributing)

欢迎扩展 Agent Bot 的能力！

### 如何新增 Skill

1.  **定义**: 在 `src/core/skills/definitions.py` 中继承 `Skill` 基类，实现 `execute` 方法。
2.  **注册**: 在 `src/core/skills/registry.py` 中将新 Skill 加入注册表。
3.  **验证**: 运行 Agent，通过自然语言指令测试新能力。

### 提交规范

*   请确保代码通过 pylint 检查。
*   新增功能需附带相应的测试用例（如适用）。
*   提交 PR 前请更新相关文档。

---

## ❓ 常见问题 (FAQ)

**Q: 为什么 Agent 有时会拒绝执行删除操作？**
A: `DeleteResource` 是一个敏感操作。如果 Critic 认为删除操作可能导致数据丢失且未得到充分理由，它可能会阻止执行。请在指令中明确说明删除的原因。

**Q: 如何查看详细的调试日志？**
A: 系统默认将详细日志输出到 `stderr` 或日志文件，而将干净的交互界面保留在 `stdout`。你可以重定向 stderr 来查看底层通信细节。

**Q: 支持哪些大模型？**
A: 理论上支持所有兼容 OpenAI Chat Completion API 的模型（如 GPT-4, Claude 3.5 Sonnet via wrapper, DeepSeek 等）。建议使用推理能力较强的模型以获得最佳体验。
