# Agent 面试题实战 Demo 集合

> 本项目将 Agent 面试高频题与 LangChain/LangGraph 实战 Demo 一一对应。
> 帮助你从"背概念"到"写得出"。

---

## 使用方式

```bash
cd agent_interview_demos
python 01_react_agent.py        # ReAct 范式
python 02_tool_calling.py       # 工具调用
python 03_agent_memory.py       # Agent 记忆
python 04_agent_rag.py          # RAG in Agent
python 05_multi_agent.py        # Multi-Agent 协作
python 06_tool_error_handling.py # 工具调用失败处理
python 07_agent_evaluation.py   # Agent 评估
python 08_langgraph_workflow.py # LangGraph 工作流
python 09_chain_vs_agent.py     # Chain vs Agent
```

**前置条件：** 配置 `.env` 文件（复制 `.env.example`，填入 LLM API Key）

---

## 面试题 ↔ Demo 映射表

| 编号 | 面试题 | 技术点 | Demo 文件 | 来源平台 |
|------|--------|--------|----------|---------|
| 01 | **什么是 ReAct 范式？它的优缺点？** | ReAct (Reason+Act)、Thought-Action-Observation 循环 | [01_react_agent.py](01_react_agent.py) | 微信/小红书/X |
| 02 | **Agent 如何选择工具 / Function Calling 的实现机制？** | Tool Schema、工具注册、动态路由 | [02_tool_calling.py](02_tool_calling.py) | 微信/小红书/X |
| 03 | **Agent 的记忆机制如何实现？** | 短期记忆、长期记忆、MemGPT 分层 | [03_agent_memory.py](03_agent_memory.py) | 微信/小红书/X |
| 04 | **RAG 在 Agent 中的应用？向量数据库为什么重要？** | RAG、ChromaDB、混合检索 | [04_agent_rag.py](04_agent_rag.py) | 微信/小红书/X |
| 05 | **Multi-Agent 协作常见模式？** | LangGraph Supervisor、Agent 通信、任务编排 | [05_multi_agent.py](05_multi_agent.py) | 微信/小红书/X |
| 06 | **Agent 工具调用失败怎么处理？** | 重试策略、降级、超时处理 | [06_tool_error_handling.py](06_tool_error_handling.py) | 微信/小红书 |
| 07 | **如何评估 Agent 的效果？** | Eval 体系、准确率、召回率、成功率 | [07_agent_evaluation.py](07_agent_evaluation.py) | 微信/X |
| 08 | **Plan-and-Execute 模式 / LangGraph 工作流** | Plan-Execute、状态图、条件分支 | [08_langgraph_workflow.py](08_langgraph_workflow.py) | 微信/小红书 |
| 09 | **Chain 和 Agent 的区别？LangChain 核心抽象？** | Chain vs Agent、LCEL、Runnable | [09_chain_vs_agent.py](09_chain_vs_agent.py) | 微信 |

---

## 面试题来源

| 文件 | 来源平台 |
|------|---------|
| [Agent面试题整理.md](/Users/caicongyang/code/ai-agent-demo/Agent面试题整理.md) | X/Twitter |
| [Agent面试题整理-微信公众号.md](/Users/caicongyang/code/ai-agent-demo/Agent面试题整理-微信公众号.md) | 微信公众号 |
| [Agent面试题整理-小红书.md](/Users/caicongyang/code/ai-agent-demo/Agent面试题整理-小红书.md) | 小红书 |

---

## 🌐 爬虫 / RAG / GraphRAG / AgenticRAG 专题

> 2026-07-04 增补。配合 [Agent面试题整理-爬虫_RAG_GraphRAG专题.md](/Agent面试题整理-爬虫_RAG_GraphRAG专题.md)

### 新增 Demo

```bash
python 10_web_crawler_agent.py    # AI Agent 友好的爬虫 (Crawl4AI 风格)
python 11_graph_rag.py            # GraphRAG：实体-关系图 + 社区检测
python 12_agentic_rag.py         # Agentic RAG：LangGraph 自决策检索
```

**Demo 10** — AI Agent 友好的爬虫：自适应抓取（覆盖度/一致性/饱和度评估何时停）、多层内容过滤（Pruning / BM25 / LLM Content Filter）、干净 Markdown 输出。零 LLM 依赖可离线跑。

**Demo 11** — GraphRAG：实体抽取（LLM / Mock 双模式）、BFS 邻域查询 + 标签传播社区检测、子图遍历 + 向量兜底（混合搜索）。展示"多跳推理 / 全局总结"两类查询。

**Demo 12** — Agentic RAG：LangGraph StateGraph + MemorySaver checkpoint + 三工具路由器（vector / graph / web）+ Verify 触发 Reflective Loop。展示"自主决定查什么 / 查几次"。

| Demo | 覆盖 Q | 重点 |
|------|--------|------|
| 10  Web Crawler Agent | Q59, Q60, Q61 | 自适应爬虫、多级过滤、Markdown 输出 |
| 11  GraphRAG | Q62, Q71, Q72, Q73, Q74 | 实体-关系、社区检测、子图遍历 |
| 12  Agentic RAG | Q75, Q76, Q77, Q78 | LangGraph 编排、Reflective Loop |

### 专题与第 4 章 Demo 的关系
- **Demo 04 (Classic RAG)** 仍是基础 RAG 知识点的入口
- **Demo 11 (GraphRAG)** 在 Demo 04 之上叠加"实体-关系"层
- **Demo 12 (Agentic RAG)** 用 LangGraph 取代 Demo 04 的固定流水线

> 三者互补，不要重复写 demo。
