# Mini Background Coding Agent — 架构设计文档

> 版本: v1.0 | 日期: 2026-07-19 | 作者: AI Application Engineer

---

## 目录

1. [项目概述](#1-项目概述)
2. [系统架构](#2-系统架构)
3. [技术选型](#3-技术选型)
4. [Agent 流程设计](#4-agent-流程设计)
5. [数据流设计](#5-数据流设计)
6. [安全架构](#6-安全架构)
7. [目录结构](#7-目录结构)
8. [API 设计](#8-api-设计)
9. [开发路线图](#9-开发路线图)

---

## 1. 项目概述

### 1.1 项目定位

Mini Background Coding Agent 是一个**简化但完整**的自主编程 Agent 系统，对标 GitHub Copilot Workspace / Devin / OpenHands 的核心理念，使用 LangGraph + LangChain 实现多 Agent 协作的代码生成流水线。

**一句话描述：** 用户输入自然语言需求 → 多个 AI Agent 自动协作 → 生成可运行的代码项目。

### 1.2 核心价值（面试亮点）

| 维度 | 价值 |
|------|------|
| **多 Agent 协作** | 展示了 Planner → Coder → Executor → Reviewer 的流水线设计能力 |
| **LLM 工程化** | LangGraph 状态图 + LangChain Tool Calling，非简单 API 调用 |
| **安全设计** | Docker 沙箱隔离执行，企业级安全思维 |
| **全栈能力** | FastAPI 后端 + React 前端 + Docker 部署 |
| **工程规范** | 类型注解、Pydantic 校验、异步编程、依赖注入 |

### 1.3 用户故事

```
作为 开发者
我想 用自然语言描述一个编程需求
以便 Agent 自动生成、测试并交付可运行代码

场景示例:
  "帮我创建一个 Python Flask API，包含 /health 和 /weather?city=beijing 两个接口"
```

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │   Chat Window  │  File Tree  │  Execution Output    │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │ WebSocket / HTTP                    │
└─────────────────────────┼───────────────────────────────────┘
                          │
┌─────────────────────────┼───────────────────────────────────┐
│                  Backend (FastAPI)                           │
│                         │                                     │
│  ┌──────────────────────┼──────────────────────────────┐    │
│  │              API Layer (Routers)                     │    │
│  │  POST /task/create   WS /task/{id}/stream            │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │                                     │
│  ┌──────────────────────┼──────────────────────────────┐    │
│  │           Orchestrator (LangGraph)                   │    │
│  │                                                      │    │
│  │   ┌──────────┐   ┌──────────┐   ┌──────────┐       │    │
│  │   │ PLANNER  │──▶│  CODER   │──▶│EXECUTOR  │       │    │
│  │   │  Agent   │   │  Agent   │   │  Agent   │       │    │
│  │   └──────────┘   └──────────┘   └─────┬────┘       │    │
│  │        ▲                               │            │    │
│  │        │          ┌──────────┐         │            │    │
│  │        └──────────│ REVIEWER │◀────────┘            │    │
│  │                   │  Agent   │                       │    │
│  │                   └──────────┘                       │    │
│  └──────────────────────────────────────────────────────┘    │
│                         │                                     │
│  ┌──────────────────────┼──────────────────────────────┐    │
│  │               Tool System                            │    │
│  │  FileCreate │ FileRead │ FileModify │ PythonExec    │    │
│  │  TestRunner │ ShellCmd  │ WebSearch  │ CodeAnalysis  │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │                                     │
└─────────────────────────┼───────────────────────────────────┘
                          │
┌─────────────────────────┼───────────────────────────────────┐
│              Docker Sandbox (Execution)                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  python:3.11-slim Container                           │   │
│  │  - 只读挂载项目文件                                     │   │
│  │  - 网络隔离                                            │   │
│  │  - 内存限制 512MB                                      │   │
│  │  - CPU 限制 1核                                        │   │
│  │  - 超时 30s                                            │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 架构决策记录 (ADR)

#### ADR-001: 为什么用 LangGraph 而不是纯 LangChain？

- **状态管理**: LangGraph 提供显式的 StateGraph，适合多步骤 Agent 流水线
- **条件路由**: 支持根据执行结果动态决定下一步（如执行失败→修复循环）
- **可观测性**: 每个 Node 的执行状态可追踪，便于前端展示
- **检查点**: 支持状态持久化，可恢复中断的任务

#### ADR-002: 为什么用 Docker 沙箱而不是 subprocess？

- **安全**: subprocess 可逃逸，Docker 提供内核级隔离
- **环境一致性**: 每次执行从相同镜像启动，避免环境污染
- **资源限制**: Docker 原生支持内存/CPU/网络限制
- **面试价值**: 展示安全意识和 DevOps 能力

#### ADR-003: 为什么用 WebSocket 而不是 SSE？

- **双向通信**: Agent 执行过程中需要发送进度，WebSocket 更灵活
- **连接效率**: 单个连接复用，减少握手开销
- **但保留 HTTP**: 简单操作（创建任务、查询状态）使用 REST API

---

## 3. 技术选型

### 3.1 后端技术栈

| 技术 | 版本 | 选型理由 |
|------|------|----------|
| Python | 3.11+ | LangChain/LangGraph 最佳支持版本 |
| FastAPI | 0.115+ | 异步原生、自动 OpenAPI、WebSocket 支持 |
| LangGraph | 0.3+ | Agent 状态图编排 |
| LangChain | 0.3+ | LLM 抽象层、Tool 定义 |
| Pydantic | 2.x | 数据校验（FastAPI 内置） |
| Docker SDK | 7.x | Python 操作 Docker 容器 |
| Redis | 7.x | WebSocket 消息广播、任务状态缓存 |
| SQLite | 3.x | 任务历史持久化（轻量，零配置） |
| pytest | 8.x | 测试框架 |

### 3.2 前端技术栈

| 技术 | 版本 | 选型理由 |
|------|------|----------|
| React | 18.x | 生态成熟，面试认可度高 |
| TypeScript | 5.x | 类型安全 |
| Tailwind CSS | 3.x | 快速开发，现代风格 |
| Vite | 5.x | 极速 HMR |
| React Markdown | 9.x | 渲染 Agent 输出（代码块高亮） |
| xterm.js | 5.x | 终端输出展示 |

### 3.3 LLM 支持矩阵

| Provider | 模型 | 用途 |
|----------|------|------|
| OpenAI | gpt-4o / gpt-4o-mini | 主力推理（Planner + Coder） |
| DeepSeek | deepseek-chat / deepseek-coder | 性价比替代（Coder + Reviewer） |

```python
# 统一的 LLM 工厂模式
from enum import Enum
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek  # 社区包或自定义

class LLMProvider(Enum):
    OPENAI = "openai"
    DEEPSEEK = "deepseek"

def create_llm(
    provider: LLMProvider,
    model: str | None = None,
    temperature: float = 0.1,
) -> BaseChatModel:
    """LLM 工厂：统一创建不同 provider 的模型实例"""
    ...
```

---

## 4. Agent 流程设计

### 4.1 LangGraph 状态图

```
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   PLANNER   │  分析需求 → 产出 Step[]
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
              ┌─────│    CODER    │◀─────────────┐
              │     └──────┬──────┘              │
              │            │                      │
              │     ┌──────▼──────┐              │
              │     │  EXECUTOR   │  运行代码     │
              │     └──────┬──────┘              │
              │            │                      │
              │     ┌──────▼──────┐              │
              │     │  REVIEWER   │  检查结果     │
              │     └──────┬──────┘              │
              │            │                      │
              │     ┌──────▼──────┐              │
              │     │  CONDITION  │              │
              │     └──┬──────┬───┘              │
              │        │ PASS │ FAIL             │
              │        │      └──────────────────┘
              │   ┌────▼────┐    (retry ≤ 3)
              │   │  NEXT   │
              │   │  STEP?  │── yes ──▶ CODER
              │   └────┬────┘
              │        │ no
              │   ┌────▼────┐
              │   │FINALIZE │  生成报告
              │   └────┬────┘
              │        │
              └────────┘ (loop for each step)
                    ┌──▼──┐
                    │ END │
                    └─────┘
```

### 4.2 Agent 定义

#### Planner Agent

```python
class PlannerAgent:
    """
    输入: 用户自然语言需求
    输出: 结构化的执行计划
    
    Prompt 策略: Chain-of-Thought + Structured Output
    """
    
    system_prompt = """你是一位资深软件架构师。分析用户需求并制定开发计划。

规则:
1. 将需求拆分为 3-7 个可独立执行的步骤
2. 每个步骤产出具体文件或修改
3. 按依赖关系排序
4. 预估每个步骤的复杂度 (1-5)

输出格式 (JSON):
{
  "task_summary": "一句话概述",
  "tech_stack": {"language": "python", "framework": "flask", ...},
  "steps": [
    {
      "id": 1,
      "description": "创建项目目录结构",
      "files_to_create": ["main.py", "requirements.txt"],
      "files_to_modify": [],
      "expected_output": "可运行的基础项目骨架",
      "complexity": 2,
      "depends_on": []
    },
    ...
  ],
  "estimated_total_time": "3分钟"
}
"""
```

#### Coding Agent

```python
class CodingAgent:
    """
    输入: 单个 Step + 项目当前状态
    输出: 代码变更 (create/modify/delete)
    
    Prompt 策略: Few-shot + Tool Calling
    """
    
    tools = [
        FileCreateTool(),
        FileReadTool(),
        FileModifyTool(),
    ]
    
    system_prompt = """你是一位高级软件工程师。根据任务步骤生成高质量代码。

代码规范:
- Python: 类型注解, docstring, 遵循 PEP 8
- 错误处理: 所有外部调用需要 try/except
- 日志: 使用 logging 而非 print
- 安全: 不硬编码密钥, 使用环境变量
"""
```

#### Execution Agent

```python
class ExecutionAgent:
    """
    输入: 代码变更结果
    输出: 执行结果 (stdout, stderr, exit_code)
    
    安全: 所有代码在 Docker 沙箱中执行
    """
    
    def execute(self, code: str, files: dict[str, str]) -> ExecutionResult:
        # 1. 创建临时目录
        # 2. 写入文件
        # 3. 启动 Docker 容器
        # 4. 挂载临时目录到容器
        # 5. 执行代码
        # 6. 收集输出
        # 7. 清理容器和临时文件
```

#### Review Agent

```python
class ReviewAgent:
    """
    输入: 代码 + 执行结果
    输出: ReviewResult (pass/fail + 修改建议)
    
    检查维度:
    - 功能正确性: 输出是否符合预期
    - 代码质量: 命名、结构、注释
    - 安全性: SQL注入、XSS、路径遍历
    - 性能: 明显的性能问题
    """
```

### 4.3 状态定义

```python
from typing import TypedDict, NotRequired
from langgraph.graph import StateGraph

class AgentState(TypedDict):
    # 任务信息
    task_id: str
    user_request: str
    
    # 计划
    plan: list[Step] | None
    current_step_index: int
    
    # 代码
    workspace_path: str
    files_created: list[str]
    files_modified: list[str]
    
    # 执行
    execution_result: ExecutionResult | None
    
    # 审查
    review_result: ReviewResult | None
    retry_count: int
    max_retries: int
    
    # 最终输出
    final_report: str | None
    status: str  # pending | planning | coding | executing | reviewing | done | failed
    error_message: str | None
```

---

## 5. 数据流设计

### 5.1 请求生命周期

```
用户                 前端               后端                Agent              Docker
 │                   │                  │                   │                   │
 │  "创建天气API"    │                  │                   │                   │
 │──────────────────▶│                  │                   │                   │
 │                   │  POST /task      │                   │                   │
 │                   │─────────────────▶│                   │                   │
 │                   │                  │  task_id          │                   │
 │                   │◀─────────────────│                   │                   │
 │                   │                  │                   │                   │
 │                   │  WS /task/{id}   │                   │                   │
 │                   │◀═════════════════│                   │                   │
 │                   │                  │  Orchestrator     │                   │
 │                   │                  │──────────────────▶│                   │
 │                   │                  │                   │                   │
 │                   │                  │  Planner          │                   │
 │                   │                  │◀──────────────────│                   │
 │                   │  event: planning │                   │                   │
 │                   │◀═════════════════│                   │                   │
 │                   │                  │                   │                   │
 │                   │                  │  Coder (step 1)   │                   │
 │                   │                  │◀──────────────────│                   │
 │                   │  event: coding   │                   │                   │
 │                   │◀═════════════════│                   │                   │
 │                   │                  │                   │                   │
 │                   │                  │  Executor         │                   │
 │                   │                  │◀──────────────────│                   │
 │                   │                  │                   │  docker run       │
 │                   │                  │                   │──────────────────▶│
 │                   │                  │                   │  stdout/stderr    │
 │                   │                  │                   │◀──────────────────│
 │                   │  event: exec_ok  │                   │                   │
 │                   │◀═════════════════│                   │                   │
 │                   │                  │                   │                   │
 │                   │                  │  Reviewer         │                   │
 │                   │                  │◀──────────────────│                   │
 │                   │  event: pass     │                   │                   │
 │                   │◀═════════════════│                   │                   │
 │                   │                  │                   │                   │
 │                   │  ... step 2, 3   │                   │                   │
 │                   │                  │                   │                   │
 │                   │  event: done     │                   │                   │
 │                   │◀═════════════════│                   │                   │
```

### 5.2 WebSocket 事件类型

```python
class WSEvent(BaseModel):
    type: Literal[
        "task_started",
        "planning",
        "plan_ready",
        "step_started",
        "coding",
        "code_generated",
        "executing",
        "execution_success",
        "execution_error",
        "reviewing",
        "review_pass",
        "review_fail",
        "retry",
        "task_completed",
        "task_failed",
        "error",
    ]
    data: dict
    timestamp: str
```

---

## 6. 安全架构

### 6.1 威胁模型

```
信任边界:
  User Input ──▶ [Untrusted] ──▶ Backend Validation ──▶ [Trusted]
  
  敏感操作边界:
  Code Execution ──▶ [Docker Sandbox] ──▶ Result ──▶ [Host]
```

### 6.2 安全措施清单

| 层级 | 措施 | 实现方式 |
|------|------|----------|
| **输入层** | Prompt Injection 防护 | 输入长度限制、敏感词过滤 |
| **应用层** | API Key 保护 | 环境变量 + Secret 管理，绝不在代码中硬编码 |
| **执行层** | Docker 沙箱 | no-network, read-only rootfs, memory limit, timeout |
| **文件层** | 路径遍历防护 | 所有文件操作限制在 workspace 内 |
| **输出层** | 输出过滤 | 不返回系统路径、环境变量等敏感信息 |

### 6.3 Docker 沙箱配置

```python
SANDBOX_CONFIG = {
    "image": "python:3.11-slim",
    "mem_limit": "512m",
    "cpu_limit": 1.0,
    "timeout": 30,  # 秒
    "network_disabled": True,
    "read_only": True,
    "tmpfs": {"/tmp": "size=64m"},
    "volumes": {
        # 只读挂载项目文件
        "/workspace": {"bind": "/sandbox/workspace", "mode": "ro"},
        # 可写输出目录
        "/output": {"bind": "/sandbox/output", "mode": "rw"},
    },
    "security_opt": ["no-new-privileges"],
    "cap_drop": ["ALL"],
}
```

---

## 7. 目录结构

```
mini-background-agent/
│
├── README.md                    # 项目主文档
├── LICENSE                      # MIT
├── .gitignore
├── .env.example                 # 环境变量模板
│
├── backend/                     # Python 后端
│   ├── pyproject.toml          # 项目元数据 + 依赖
│   ├── requirements.txt        # 锁定版本
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI 应用入口
│   │   ├── config.py           # 配置管理 (pydantic-settings)
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── router.py       # 路由注册
│   │   │   ├── task.py         # POST /task/create
│   │   │   └── ws.py           # WS /task/{id}/stream
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py # LangGraph 编排器
│   │   │   ├── state.py        # AgentState 定义
│   │   │   └── llm.py          # LLM 工厂
│   │   │
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── base.py         # Agent 基类
│   │   │   ├── planner.py      # Planner Agent
│   │   │   ├── coder.py        # Coding Agent
│   │   │   ├── executor.py     # Execution Agent
│   │   │   └── reviewer.py     # Review Agent
│   │   │
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── base.py         # Tool 基类
│   │   │   ├── file_create.py
│   │   │   ├── file_read.py
│   │   │   ├── file_modify.py
│   │   │   ├── python_exec.py  # Docker Sandbox
│   │   │   ├── test_runner.py
│   │   │   └── registry.py     # Tool 注册表
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── task.py         # Task, Step, Plan 模型
│   │   │   ├── ws_event.py     # WebSocket 事件模型
│   │   │   └── tool.py         # Tool 输入输出模型
│   │   │
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── workspace.py    # 工作区管理
│   │       ├── sandbox.py      # Docker 沙箱管理
│   │       └── event_bus.py    # 事件总线 (Redis)
│   │
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_planner.py
│       ├── test_coder.py
│       ├── test_executor.py
│       ├── test_reviewer.py
│       ├── test_orchestrator.py
│       └── test_tools/
│           ├── test_file_create.py
│           ├── test_file_modify.py
│           └── test_python_exec.py
│
├── frontend/                    # React 前端
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── index.html
│   │
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   │
│   │   ├── components/
│   │   │   ├── ChatWindow.tsx      # 聊天窗口
│   │   │   ├── MessageBubble.tsx   # 消息气泡
│   │   │   ├── CodeBlock.tsx       # 代码块渲染
│   │   │   ├── StepProgress.tsx    # 步骤进度条
│   │   │   ├── FileTree.tsx        # 文件树
│   │   │   ├── ExecutionOutput.tsx # 终端输出
│   │   │   └── ReportCard.tsx      # 最终报告卡片
│   │   │
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts
│   │   │   └── useTask.ts
│   │   │
│   │   ├── types/
│   │   │   └── index.ts
│   │   │
│   │   └── utils/
│   │       └── api.ts
│   │
│   └── public/
│       └── favicon.svg
│
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── Dockerfile.sandbox        # 沙箱镜像
│   └── docker-compose.yml
│
└── docs/
    ├── ARCHITECTURE.md           # 本文档
    ├── API.md                    # API 文档
    └── screenshots/              # 截图
        └── .gitkeep
```

---

## 8. API 设计

### 8.1 REST API

```
POST   /api/v1/task/create     — 创建任务
GET    /api/v1/task/{id}       — 查询任务状态
GET    /api/v1/task/{id}/files — 获取生成的文件列表
GET    /api/v1/task/{id}/file/{path} — 获取单个文件内容
DELETE /api/v1/task/{id}       — 删除任务及文件
WS     /api/v1/task/{id}/stream — WebSocket 实时流
```

### 8.2 请求/响应示例

```json
// POST /api/v1/task/create
{
  "request": "帮我创建一个Python天气查询API，包含 /health 和 /weather?city=beijing",
  "provider": "openai",
  "model": "gpt-4o-mini"
}

// Response
{
  "task_id": "abc-123",
  "status": "planning",
  "created_at": "2026-07-19T10:00:00Z"
}
```

---

## 9. 开发路线图

### Phase 1: 核心骨架 (Day 1)

- [x] 项目目录创建
- [ ] `backend/app/config.py` — 配置管理
- [ ] `backend/app/main.py` — FastAPI 入口
- [ ] `backend/app/core/llm.py` — LLM 工厂
- [ ] `backend/app/core/state.py` — AgentState 定义
- [ ] `backend/app/models/` — 数据模型
- [ ] `.env.example` + `.gitignore`

### Phase 2: 工具系统 (Day 2)

- [ ] `backend/app/tools/base.py` — Tool 基类
- [ ] `backend/app/tools/file_create.py`
- [ ] `backend/app/tools/file_read.py`
- [ ] `backend/app/tools/file_modify.py`
- [ ] `backend/app/tools/python_exec.py` — Docker 沙箱
- [ ] `backend/app/tools/registry.py` — Tool 注册表
- [ ] 单元测试

### Phase 3: Agent 实现 (Day 3-4)

- [ ] `backend/app/agents/base.py` — Agent 基类
- [ ] `backend/app/agents/planner.py`
- [ ] `backend/app/agents/coder.py`
- [ ] `backend/app/agents/executor.py`
- [ ] `backend/app/agents/reviewer.py`
- [ ] 单元测试

### Phase 4: 编排层 (Day 5)

- [ ] `backend/app/core/orchestrator.py` — LangGraph 状态图
- [ ] `backend/app/services/workspace.py`
- [ ] `backend/app/services/sandbox.py`
- [ ] `backend/app/services/event_bus.py`
- [ ] 集成测试

### Phase 5: API + WebSocket (Day 6)

- [ ] `backend/app/api/task.py`
- [ ] `backend/app/api/ws.py`
- [ ] 端到端测试

### Phase 6: 前端 (Day 7-8)

- [ ] Vite + React + Tailwind 初始化
- [ ] `ChatWindow` 组件
- [ ] `StepProgress` 组件
- [ ] `CodeBlock` 组件
- [ ] `FileTree` 组件
- [ ] WebSocket 集成

### Phase 7: 文档 + 部署 (Day 9-10)

- [ ] Docker Compose 一键部署
- [ ] README 完整文档
- [ ] Demo GIF 录制
- [ ] GitHub 发布

---

## 附录 A: 面试提问预测

| 可能的面试问题 | 你的回答要点 |
|---------------|-------------|
| 为什么不用 LangChain 默认 Agent？ | LangGraph 提供更精细的状态控制和条件路由，适合多步骤工程流水线 |
| 如何处理 LLM 输出不稳定？ | Pydantic 校验 + Retry + Fallback 策略 |
| Docker 沙箱如何保证安全？ | no-network, read-only rootfs, cap_drop ALL, memory limit, timeout |
| 如何处理大项目？ | 只传递相关文件摘要给 LLM，不传全量代码；文件树剪枝 |
| Agent 之间的信息如何传递？ | LangGraph State 对象，每个 Node 读写同一 State |

---

## 附录 B: 性能预估

| 操作 | 预估耗时 |
|------|----------|
| Planner (分析需求) | 3-5s |
| Coder (生成一个文件) | 5-10s |
| Executor (Docker 启动+执行) | 3-8s |
| Reviewer (检查代码) | 3-5s |
| **典型任务总计** | **30-60s** |
