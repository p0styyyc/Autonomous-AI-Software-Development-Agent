# 🤖 Mini Background Coding Agent

> 用户输入自然语言需求 → 多个 AI Agent 自动协作 → 生成可运行的代码项目。

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.3+-green.svg)](https://langchain-ai.github.io/langgraph/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-92%20passed-brightgreen.svg)](backend/)

---

## 📖 目录

- [项目概述](#项目概述)
- [技术架构](#技术架构)
- [Agent 工作流程](#agent-工作流程)
- [功能说明](#功能说明)
- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [API 文档](#api-文档)
- [安全设计](#安全设计)
- [测试](#测试)
- [项目难点](#项目难点)
- [后续优化方向](#后续优化方向)

---

## 项目概述

Mini Background Coding Agent 对标 GitHub Copilot Workspace / Devin / OpenHands 的核心理念，使用 **LangGraph + LangChain** 实现多 Agent 协作的代码生成流水线。

**一句话描述：** 用户输入自然语言需求 → 4 个 AI Agent 自动协作（规划→编码→执行→审查）→ 生成可运行的代码项目。

### 项目定位

这是一个**求职作品集项目**，目标岗位：**AI 应用工程师**。项目展示了以下能力：

| 维度 | 展示内容 |
|------|---------|
| **LLM 工程化** | LangGraph 状态图编排、Tool Calling、多 Provider 适配 |
| **多 Agent 协作** | Planner → Coder → Executor → Reviewer 流水线 |
| **安全设计** | Docker 沙箱隔离执行、5 层安全防护 |
| **全栈能力** | FastAPI + WebSocket + React + TypeScript + Docker |
| **工程规范** | 92 个单元测试、类型注解、Pydantic 校验、异步编程 |

---

## 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                   Frontend (React 18)                    │
│  ChatWindow │ StepProgress │ FileTree │ CodeBlock       │
│              WebSocket / REST API                        │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────┐
│                  Backend (FastAPI)                       │
│  ┌─────────────────────────────────────────────────┐    │
│  │         LangGraph Orchestrator                   │    │
│  │                                                  │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐      │    │
│  │  │ PLANNER  │─▶│  CODER   │─▶│ EXECUTOR │      │    │
│  │  │  Agent   │  │  Agent   │  │  Agent   │      │    │
│  │  └──────────┘  └──────────┘  └────┬─────┘      │    │
│  │       ▲                           │             │    │
│  │       │       ┌──────────┐        │             │    │
│  │       └───────│ REVIEWER │◀───────┘             │    │
│  │               │  Agent   │                       │    │
│  │               └──────────┘                       │    │
│  └─────────────────────────────────────────────────┘    │
│  Tool System: FileCreate │ FileRead │ FileModify        │
│               PythonExec │ TestRunner                   │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────┐
│              Docker Sandbox (Isolation)                   │
│  python:3.11-slim │ no-network │ read-only │ 512MB cap   │
└─────────────────────────────────────────────────────────┘
```

### 技术栈

| 层级 | 技术 | 选型理由 |
|------|------|---------|
| **Agent 编排** | LangGraph 0.3+ | 显式状态图、条件路由、检查点 |
| **LLM 框架** | LangChain 0.3+ | Tool Calling、统一模型抽象 |
| **后端** | Python 3.11+ / FastAPI | 异步原生、WebSocket、自动 OpenAPI |
| **前端** | React 18 / TypeScript / Tailwind | 现代组件化、类型安全 |
| **沙箱** | Docker SDK | 内核级隔离、资源限制 |
| **LLM** | OpenAI / DeepSeek | 双 Provider 工厂模式 |

---

## Agent 工作流程

```
用户: "帮我创建一个 Python 天气查询 API"

    ┌──────────────────────────────────────────────────┐
    │  1. PLANNER Agent  (gpt-4o-mini, temp=0.3)       │
    │     分析需求 → 拆分步骤 → 结构化 JSON 计划        │
    │     ↓                                             │
    │     Step 1: 创建项目骨架 (main.py, requirements)  │
    │     Step 2: 实现 /health 端点                     │
    │     Step 3: 实现 /weather?city=beijing            │
    └──────────────────────┬───────────────────────────┘
                           │
    ┌──────────────────────▼───────────────────────────┐
    │  2. CODER Agent  (gpt-4o, temp=0, Tool Calling)   │
    │     file_read → 了解现有代码                       │
    │     file_create → 创建新文件                       │
    │     file_modify → 修改已有文件                     │
    └──────────────────────┬───────────────────────────┘
                           │
    ┌──────────────────────▼───────────────────────────┐
    │  3. EXECUTOR Agent  (Docker Sandbox)              │
    │     docker run → python main.py                   │
    │     收集 stdout / stderr / exit_code              │
    └──────────────────────┬───────────────────────────┘
                           │
    ┌──────────────────────▼───────────────────────────┐
    │  4. REVIEWER Agent  (gpt-4o-mini, temp=0)         │
    │     5 维评分: 功能/质量/安全/性能/可读            │
    │     Pass? → 下一步 / Fail? → 重试 (最多 3 次)     │
    └──────────────────────┬───────────────────────────┘
                           │
    ┌──────────────────────▼───────────────────────────┐
    │  📊 Final Report                                  │
    │     所有步骤结果汇总 + 文件清单 + 审查建议        │
    └──────────────────────────────────────────────────┘
```

### 条件路由

```
Reviewer 判定:
  ✅ Pass 且有下一步  → next_step → Coder (继续)
  ✅ Pass 且全部完成  → finalize  → 生成报告
  ❌ Fail 且 retry<3  → retry     → Coder (重试)
  ❌ Fail 且 retry=3  → next_step → 跳过当前步骤
```

---

## 功能说明

### 已实现功能

- [x] **自然语言需求理解** — Planner Agent 自动分析并拆分步骤
- [x] **自动代码生成** — Coding Agent 通过 Tool Calling 创建/修改文件
- [x] **Docker 沙箱执行** — 5 层安全隔离：无网络/只读/去特权/内存限制/超时
- [x] **自动测试运行** — TestRunnerTool 在沙箱中运行 pytest
- [x] **代码质量审查** — Reviewer Agent 5 维评分 + 修改建议
- [x] **失败重试** — 审查不通过自动重试（最多 3 次）
- [x] **WebSocket 实时推送** — 前端实时展示 Agent 思考和执行过程
- [x] **文件树查看** — 侧边栏展示生成的文件，点击查看内容
- [x] **多 LLM 支持** — OpenAI / DeepSeek 工厂模式切换
- [x] **Docker Compose 部署** — 一键启动前后端

### API 端点

```
POST   /api/v1/task/create            — 创建编程任务
GET    /api/v1/task/{id}              — 查询任务状态
GET    /api/v1/task/{id}/files        — 获取文件列表
GET    /api/v1/task/{id}/file/{path}  — 获取文件内容
DELETE /api/v1/task/{id}              — 删除任务
WS     /api/v1/task/{id}/stream       — WebSocket 实时事件流
GET    /health                         — 健康检查
```

---

## 快速开始

### 前提条件

- Python 3.11+
- Node.js 18+
- Docker (可选，用于沙箱执行。没有则降级为 dry-run 模式)

### 1. 克隆项目

```bash
git clone https://github.com/your-username/mini-background-agent.git
cd mini-background-agent
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，至少填入一个 API Key:
#   OPENAI_API_KEY=sk-...
#   DEEPSEEK_API_KEY=sk-...
```

### 3. 启动后端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 5. 打开浏览器

访问 **http://localhost:5173**，输入你的编程需求。

### Docker 一键部署

```bash
docker-compose -f docker/docker-compose.yml up -d
# 前端: http://localhost:3000
# 后端: http://localhost:8000
# API 文档: http://localhost:8000/docs
```

---

## 项目结构

```
mini-background-agent/
├── README.md                        # 项目文档
├── LICENSE                          # MIT
├── .gitignore
├── .env.example                     # 环境变量模板
│
├── backend/                         # Python 后端
│   ├── pyproject.toml              # 项目配置 (ruff/mypy/pytest)
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py                 # FastAPI 入口
│   │   ├── config.py               # 配置管理 (pydantic-settings)
│   │   ├── api/                    # REST + WebSocket API
│   │   ├── core/                   # 核心模块
│   │   │   ├── llm.py              # LLM 工厂 (OpenAI/DeepSeek)
│   │   │   ├── state.py            # LangGraph AgentState
│   │   │   └── orchestrator.py     # LangGraph 编排器 ★
│   │   ├── agents/                 # 4 个 Agent
│   │   │   ├── planner.py          # 需求分析 + 步骤拆解
│   │   │   ├── coder.py            # 代码生成 (Tool Calling)
│   │   │   ├── executor.py         # Docker 沙箱执行
│   │   │   └── reviewer.py         # 5维质量审查
│   │   ├── tools/                  # Agent 工具系统
│   │   │   ├── file_create.py      # 文件创建 (防路径遍历)
│   │   │   ├── file_read.py        # 文件读取 (行范围)
│   │   │   ├── file_modify.py      # 文件修改 (4种操作)
│   │   │   ├── python_exec.py      # Docker 沙箱执行
│   │   │   ├── test_runner.py      # 测试运行器
│   │   │   └── registry.py         # Tool 注册表 (按角色分发)
│   │   ├── models/                 # Pydantic 数据模型
│   │   └── services/               # 服务层
│   │       ├── workspace.py        # 工作区管理
│   │       ├── event_bus.py        # 事件总线 (Pub/Sub)
│   │       └── task_store.py       # 任务状态存储
│   └── tests/                      # 92 个单元/集成测试
│
├── frontend/                        # React 前端
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatWindow.tsx      # 主聊天界面
│   │   │   ├── MessageBubble.tsx   # 智能消息渲染
│   │   │   ├── StepProgress.tsx    # 步骤进度条
│   │   │   ├── FileTree.tsx        # 文件树
│   │   │   ├── CodeBlock.tsx       # 代码块
│   │   │   └── ReportCard.tsx      # 最终报告
│   │   ├── hooks/                  # WebSocket + Task Hooks
│   │   ├── types/                  # TypeScript 类型
│   │   └── utils/                  # API 客户端
│   └── ...
│
├── docker/                          # Docker 部署
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── Dockerfile.sandbox
│   ├── docker-compose.yml
│   └── nginx.conf
│
└── docs/
    └── ARCHITECTURE.md              # 详细架构设计文档
```

---

## 安全设计

代码执行使用 **Docker 容器隔离**，非 subprocess。5 层防护：

```
Layer 1: Container Isolation   容器级隔离，非进程级
Layer 2: Network Disabled      network_mode=none，无法外连
Layer 3: Read-Only Rootfs      read_only=True + tmpfs /tmp
Layer 4: Privilege Drop        cap_drop=ALL + no-new-privileges
Layer 5: Resource Limits       512MB 内存 / 1 CPU / 30s 超时
```

文件操作防护：所有路径使用 `resolve()` + `is_relative_to()` 防路径遍历。

---

## 测试

```bash
cd backend
python -m pytest tests/ -v
```

```
tests/test_tools/      29 tests  — FileCreate/Read/Modify/Exec/Registry
tests/test_agents/     26 tests  — Planner/Coder/Executor/Reviewer
tests/test_services/   24 tests  — Workspace/EventBus/Orchestrator
tests/test_api/        13 tests  — REST API 集成测试
─────────────────────────────────────────────────────
Total:                 92 tests  ✅ 0 failures
```

---

## 项目难点

### 1. LLM 输出不可靠

**问题：** LLM 可能返回非 JSON、markdown 包裹的 JSON、甚至纯文本。
**解决：** 实现了 `_extract_json()` 函数处理 4 种输出格式，加字段默认值补全，JSON 解析失败时降级而非崩溃。

### 2. Agent 间信息传递

**问题：** 4 个 Agent 需要共享任务状态、代码变更、执行结果。
**解决：** 使用 LangGraph `AgentState` (TypedDict) 作为单一状态源，每个 Node 读写同一 State。

### 3. 失败死循环

**问题：** Coder → Executor → Reviewer 循环中可能无限重试。
**解决：** 最大 3 次重试 + 超限自动 skip + Reviewer 异常时默认 pass。

### 4. Docker 沙箱安全

**问题：** AI 生成的代码不可信，可能包含恶意操作。
**解决：** 5 层 Docker 安全隔离 + 降级 dry-run 模式（Docker 不可用时只预览不执行）。

---

## 后续优化方向

- [ ] **Human-in-the-Loop** — Reviewer fail 时暂停等待人工决定
- [ ] **LangSmith 集成** — LLM 调用链路追踪和性能监控
- [ ] **GitHub 集成** — 自动创建 PR、管理 Issue
- [ ] **增量修改** — 大项目只传文件摘要给 LLM，减少 token 消耗
- [ ] **Prompt 版本管理** — 将 Prompt 抽离为独立文件，支持 A/B 测试
- [ ] **Redis 替换** — EventBus 从内存升级到 Redis，支持多进程
- [ ] **SQLite → PostgreSQL** — 任务持久化升级
- [ ] **流式输出** — LLM streaming 提升用户体验
- [ ] **Sandbox 预热** — 预启动容器减少执行延迟
- [ ] **多语言支持** — 扩展到 JavaScript/TypeScript/Go 项目生成

---

## 贡献

欢迎 Issue 和 PR！请先阅读 [ARCHITECTURE.md](docs/ARCHITECTURE.md) 了解设计细节。

## 许可证

MIT License — 详见 [LICENSE](LICENSE) 文件。

---

<p align="center">
  <sub>Python · FastAPI · LangGraph · React · Docker</sub>
</p>
