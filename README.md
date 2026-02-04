# Code Agent Bot

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue)
![React](https://img.shields.io/badge/React-18+-61DAFB)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688)
![License](https://img.shields.io/badge/License-MIT-green)

**Code Agent Bot** 是一个生产就绪的 AI 编码助手，采用 **Plan -> Execute -> Reflect -> Iterate** 工作流，为开发者提供强大的自动化辅助能力。

## 核心特性

- **智能规划**: 理解模糊需求，自动拆解为可执行步骤
- **技能驱动**: 高层能力封装（文件操作、代码搜索、测试运行）
- **自我修正**: Critic 审查机制自动修复执行错误
- **流式输出**: 全链路 Markdown 流式渲染
- **安全沙箱**: 文件操作限制在安全目录内
- **现代化 UI**: 响应式 Web 界面，暗黑极客风格
- **用户认证**: JWT 认证，会话持久化
- **数据分析**: Token 使用量追踪和统计

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+

### Docker 部署 (推荐)

```bash
# 克隆项目
git clone https://github.com/yourusername/agent-bot.git
cd agent-bot

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 OpenAI API Key

# 启动服务
docker-compose up -d

# 访问 http://localhost:8000
```

### 本地开发

```bash
# 安装后端依赖
pip install -e ".[dev]"

# 安装前端依赖
cd frontend && npm install && cd ..

# 配置环境变量
cp .env.example .env

# 启动后端
uvicorn src.api.app:app --reload

# 启动前端 (新终端)
cd frontend && npm run dev
```

## API 文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 主要端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/auth/register` | POST | 用户注册 |
| `/api/v1/auth/login` | POST | 用户登录 |
| `/api/v1/auth/me` | GET | 获取当前用户 |
| `/api/v1/sessions` | GET/POST | 会话管理 |
| `/api/v1/chat/stream` | POST | 流式对话 |
| `/health` | GET | 健康检查 |

## 可用技能

| 技能名称 | 描述 |
|----------|------|
| `ExploreProject` | 智能探索项目结构 |
| `ViewFile` | 读取文件内容 |
| `SearchCode` | 正则搜索代码 |
| `EditFile` | 编辑文件 |
| `DeleteResource` | 删除资源 |
| `RunTests` | 运行测试 |

## 测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行带覆盖率的测试
pytest tests/ -v --cov=src --cov-report=html
```

## 项目结构

```
agent-bot/
├── src/
│   ├── api/            # FastAPI 应用
│   ├── core/           # 核心业务逻辑
│   ├── infra/          # 基础设施
│   └── interface/      # 交互界面
├── frontend/           # React 前端
├── tests/              # 测试套件
├── docker-compose.yml  # Docker 编排
└── pyproject.toml      # 项目配置
```

## 安全特性

- JWT 认证（Access Token + Refresh Token）
- 密码 PBKDF2 哈希
- 文件沙箱隔离
- SQL 注入防护
- CORS 配置
- 请求验证

## 许可证

MIT License
