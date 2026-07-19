# 刘皓

**AI应用工程师** — LLM应用开发 / AI Agent工程 / 大模型应用开发

📧 1281741407@qq.com | 🔗 [github.com/p0styyyc](https://github.com/p0styyyc) | 📍 广州

---

## 技术能力

**LLM应用** — LangGraph · LangChain · Agent架构设计 · Tool Calling · Prompt Engineering · Multi-Agent协作 · RAG基础

**后端开发** — Python 3.11+ · FastAPI · WebSocket · RESTful API · Pydantic · 异步编程 · Docker SDK

**工程工具** — Git · Docker · Docker Compose · pytest · ruff · mypy · Linux

**前端（辅助）** — React 18 · TypeScript · Tailwind CSS

---

## 项目经历

### Autonomous AI Software Development Agent
*个人作品集项目 · 70+ 文件 · 92 测试 | 2026.06*

> 对标 GitHub Copilot Workspace / Devin 理念，从零构建完整多Agent自主编程系统。用户输入自然语言需求后，系统自动完成 **需求理解 → 任务规划 → 代码生成 → 沙箱执行 → 质量审查** 的完整闭环。

- **Agent编排**：基于 LangGraph StateGraph 构建 Planner → Coder → Executor → Reviewer 四Agent流水线，TypedDict 单一状态源实现 Agent 间信息传递，条件路由实现自主决策循环（通过→继续 / 失败→重试 / 超限→跳过）
- **LLM工程化**：工厂模式适配 OpenAI / DeepSeek 双 Provider，不同 Agent 分配不同模型与温度参数。实现多格式 JSON 提取 + 字段补全 + 降级策略，解决 LLM 输出不可靠问题
- **Tool Calling体系**：实现 5 个定制 LangChain Tool，Registry 模式 + 角色最小权限分发。Docker 沙箱 5 层安全隔离：容器级隔离 · 网络禁用 · 只读根文件系统 · cap_drop=ALL · 512MB/30s 限制
- **实时通信**：基于 asyncio.Queue 的 Pub/Sub 事件总线，WebSocket 推送 13 种 Agent 事件，支持历史事件补发 + 心跳保活
- **前端可视化**：React 18 + TypeScript + Tailwind CSS，步骤进度条、文件树、代码高亮、最终报告。Docker Compose 一键部署

**技术栈**：`Python` `FastAPI` `LangGraph` `LangChain` `React 18` `TypeScript` `Docker` `pytest` `WebSocket` `Pydantic`

---

## 教育经历

**广东药科大学** — 电子信息工程 · 本科 | 2026届

---

## 个人优势

- **全链路AI工程能力**：独立完成 Agent架构设计 → LLM编排 → Tool Calling → 前后端开发 → Docker部署的完整闭环
- **工程化思维**：92 个单元/集成测试 · 全量类型注解 · Pydantic 校验 · 错误降级策略 · 安全防护机制 · ADR 架构决策记录
- **技术广度与深度**：从 LLM 应用到全栈开发到容器化部署，理解每层工作原理而非停留在调用层面
