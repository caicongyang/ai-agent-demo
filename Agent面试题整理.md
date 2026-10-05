# Agent 面试题整理

> 数据来源：X/Twitter (via OpenCLI)
> 整理日期：2026-06-26

---

## 一、面试官视角的 Agent 面试观察

### 1. Agent 工程师面试现状

来源：[@object_nullll](https://x.com/i/status/2061412751445266741)

> 这几天面试 Agent 工程师下来，有一半的面试的都是本硕期间发过 AI 周边论文的，剩下的一半才是 Java 后端或者前端转来的。
>
> 比起 AI 正规军，前后端这批很多人没有对 Agent/RAG 进行 eval 的意识，很多项目停在"能跑了"，想法可能还行，但是问不出指标。

**关键点：** 面试 Agent 工程师时，面试官非常看重候选人对 Agent 系统的 **评估（Eval）** 能力——不能只是"能跑"，要有量化指标意识。

---

### 2. AI Agent 岗位面试题

来源：[@seclink](https://x.com/i/status/2056565600026071277)

判断一个人用 AI 和 Agent 到了什么水平，最有效的方式是看 **它有没有摸到 AI 的边界**。以下是 AI Agent 岗位面试必须问的两道题：

**题 1：在实现 AI Agent 开发新应用时，需要注意哪些事情，以避免和减少返工的可能性？**

**题 2：现在什么类别的任务适合人来实现，什么类别的任务适合借助 AI Agent 来发挥实现？**

**核心考察点：** 候选人是否理解 AI 当前的能力边界，而不只是把 Agent 吹成万能工具。

---

### 3. AI 面试中的诚信观察

来源：[@frxiaobei](https://x.com/i/status/1991183076224024968)

> 面试候选人，技术能力基本没问题，但演示 Agent 作品时误操作，满屏密密麻麻的面经直接"自爆"。

**启示：** 面试中诚信比能力更重要。能力是可以补的，但诚信掉下去就补不回来了。

---

## 二、Agent 技术面试高频知识点

### 1. 核心知识体系

综合多个面试经验帖，Agent 岗位面试主要考察以下方面：

#### 基础理论
- **RAG（检索增强生成）**：原理、架构、优化
- **Agent 架构设计**：单 Agent vs Multi-Agent
- **Prompt Engineering**：系统提示词设计技巧
- **Function Calling / Tool Use**：工具调用机制
- **Memory 机制**：短期记忆、长期记忆（MemGPT 分层 memory）

#### 工程实践
- **LangGraph / LangChain**：Agent 编排框架
- **MCP（Model Context Protocol）**：模型上下文协议
- **Context Engineering**：上下文工程
- **Eval（评估体系）**：Agent 系统的评估指标与方法
- **Safety（安全）**：Agent 安全防护
- **Post-training**：训练后优化（RLHF、GRPO 等）

#### 系统设计（Agent 场景）
- 多租户数据隔离设计
- 实时搜索系统设计
- 自主编码 Agent 设计
- Agent 生产级部署架构

---

### 2. OpenAI 面试参考

来源：[Alisa Liu (alisawuffles)](https://x.com/i/status/2069981005587329447) — 拿到 OpenAI Research Scientist offer

#### OpenAI 面试主要考察内容：

| 考察类型 | 内容 | 频率 |
|---------|------|------|
| **ML Coding** | 用 PyTorch 实现架构、decoding 策略、Transformer 等 | 最高频 |
| **General Coding** | LeetCode 风格题目 | 高频 |
| **Technical Discussion** | 实验设计讨论 + 快速概念问答（positional encoding、parallelism、PPO vs GRPO 等） | 高频 |
| **Research Discussion** | 讲自己的项目、insight 和未来方向 | 中频 |
| **Behavioral** | 把经历整理成故事 | 有准备即可 |
| **Math + Job Talk** | 聚焦自己最核心的方向 | 视岗位而定 |

#### 关键技能点：
- Transformer 实现要练到 **muscle memory**
- 面试时需要 **关闭 AI 辅助** 练习 coding（真实面试时必须自己写）
- 面试当天必须睡够觉

#### 建议的学习资源：
1. Stanford CS336《Language Modeling from Scratch》
2. The Illustrated GPT-2 (Jalammar)
3. Self-Attention & Transformers (CS224n)
4. CS231n Backpropagation
5. Introduction to Policy Gradient for LMs
6. Lightweight Guide to GRPO and RL principles
7. How to Scale Your Model (JAX scaling book)
8. LeetCode（常规 + ML 相关题）

---

### 3. Agent 面试趣题：蜜雪冰城 LLM Engineer 面经

来源：[@wangray](https://x.com/i/status/2050246059717517352)

一道非常经典的场景题：

**系统设计题：** 400B 模型跨区域 serving，首 Token < 80ms

**参考答案要点：**
- PD 分离，Frontend 用 SGLang
- RadixAttention（高频 SKU KV cache 走 trie 复用）
- KVCache-centric 架构：Tier1 HBM + Tier2 DRAM
- Speculative Decoding（按地区训练 draft model）
- Sugar-aware Token Trie（限定输出范围）

**第二题：** 用户说 "I miss my school days, something cheap and sweet like back then"，单 agent 够吗？

**参考答案：** 不够，必须 **Multi-Agent + Agent RL**
- Memory Agent：学生时代 nostalgia RAG
- Store Agent：原料库存 + 制作速度
- Brand Agent：输出品牌风格话术
- 训练：GRPO + offline RL
- Reward 设计：下单 +10，说 "this reminds me of my childhood" +30

---

### 4. AgentGuide 开源项目

来源：[@Wood_rif](https://x.com/i/status/2069795102709678148)

推荐的开源项目 AgentGuide，覆盖 Agent 开发面试完整路径：

```
Agent 开发路线 → LangGraph 实战 → 高级 RAG → MCP
→ Context Engineering → Eval → Safety → Post-training
→ 面试题库 → 简历项目
```

GitHub 地址：https://github.com/（搜索 AgentGuide）

---

### 5. AI System Design Guide

来源：[@GitHub_Daily](https://x.com/i/status/2060209546157773060)

GitHub 项目，包含：
- **110 道面试真题** 和答题框架
- **20 个真实案例**（自主编码 Agent、多租户数据隔离、实时搜索系统等）
- 架构图 + 完整方案
- AI 评估深度指南
- 角色转型路线图

涵盖核心技术栈：
- RAG 架构
- Agent 智能体
- 多租户隔离
- 大模型选型

---

## 三、Agent 面试准备建议

### 1. 必读文章（来自社区推荐）

来源：[@HiTw93](https://x.com/i/status/2067851910464565374) — 被认为是"AI 岗位面试准备必读"

1. **你不知道的 Claude Code**：架构、治理与工程实践
2. **你不知道的 Agent**：原理、架构与工程实践
3. **你不知道的大模型训练**：原理、路径与新实践
4. **你不知道的 AI Coding**：非技术人的上手、场景与实战
5. **你不知道的 GEO**：AI 可见性的原理、实践与取舍
6. **你不知道的具身智能**：从小机器狗到 Optimus

### 2. 学习路径推荐

结合 Alisa Liu 的经验，推荐以下学习路径：

```
① 建立广度
   └─ Stanford CS336《Language Modeling from Scratch》
   
② 深度突破（逐个概念）
   └─ 读 blog + paper
   └─ 和 AI 对话加深理解
   └─ 从零实现代码
   
③ 针对性复习
   └─ 准备 Behavioral 故事
   └─ 研究岗位方向突击
```

### 3. 优秀 GitHub 项目推荐

| 项目 | 内容 | 适合人群 |
|------|------|---------|
| AgentGuide | Agent 开发路线 + 面试题库 + 简历项目 | 转岗/求职者 |
| AI System Design Guide | 110 道面试真题 + 20 个真实案例 | 系统设计准备 |
| hello-agents | Agentic RL + SFT + GRPO | 硬核技能学习 |
| autoresearch | AI Agent 自动推进研究 | 研究导向 |

---

## 四、社区热议观点

### Agent 行业的现实挑战

来源：[@dashen9999](https://x.com/i/status/2070046837562880271)

某头部 Agent 公司从业者的观点：

1. **Token 成本**：利润大头被 AI 公司赚走，使用本地模型和开源模型控制成本仍困难
2. **准确率**：复杂 workflow 调用多层 AI，好功能 90% 准确率，差的只有 80%，客户不可接受
3. **问题边界**：多少人工就有多少智能，开发测试工作量巨大

### 后端的转型差距

来源：[@object_nullll](https://x.com/i/status/2061412751445266741)

前后端转 Agent 的常见问题：
- 缺乏 **Eval** 意识
- 项目停留在"能跑了"的阶段
- 想法可以但问不出指标

### 面试加分项：在项目中放 AGENTS.md

来源：[@mashi2003_mashi](https://x.com/i/status/2070033604097515972)

面试官视角：如果候选人的 GitHub 项目中有合理的 AGENTS.md（项目规则 + 工作流 + 验证方式 + 停止条件），说明对 AI Agent 的理解是工程级别的。

---

## 五、总结

Agent 面试的核心考察维度：

| 维度 | 考察点 |
|------|--------|
| **能力边界认知** | 是否理解 AI 能做什么、不能做什么 |
| **系统评估能力** | 是否有 Eval 意识、能量化指标 |
| **工程落地能力** | 能否从"能跑"到"能上线" |
| **架构设计能力** | Multi-Agent、Memory、Tool Use 设计 |
| **底层理解** | Transformer、RL、GRPO 原理 |
| **编程基本功** | 手写 ML 代码、算法能力 |

---

*本文档由 OpenCLI 搜索 X/Twitter 整理生成，仅供参考。*

---



---

## 六、X/Twitter 面试题目实录

以下是从 X/Twitter 搜索结果中提取的真实面试题目和面试官观察。

### 面试官视角的真实考题

**来源：@seclink — AI Agent 岗位面试题**

> 判断一个人用 AI 和 Agent 到了什么水平，最有效的方式是看它有没有摸到 AI 的边界。

AI Agent 岗位面试必须问的两道题：

**题1：** 在实现 AI Agent 开发新应用时，需要注意哪些事情，以避免和减少返工的可能性？

**题2：** 现在什么类别的任务适合人来实现，什么类别的任务适合借助 AI Agent 来发挥实现？

### 面试观察中的考察点

**来源：@object_nullll — Agent 工程师面试观察**

面试 Agent 工程师时的关键考察点：
1. 有没有对 Agent/RAG 进行 **Eval** 的意识
2. 项目是否停在"能跑了"的阶段
3. 想法能不能转化为可量化的指标
4. 对 RAG、Tool Use、Memory 的基础理解

### OpenAI Research Scientist 面试题型

**来源：@alisawuffles (Alisa Liu)**

OpenAI 面试主要考察内容：

| 考察类型 | 内容 | 频率 |
|---------|------|------|
| ML Coding | 用 PyTorch 实现架构、decoding 策略、Transformer | 最高频 |
| General Coding | LeetCode 风格题目 | 高频 |
| Technical Discussion | 实验设计、positional encoding、PPO vs GRPO | 高频 |
| Research Discussion | 项目、insight、未来方向 | 中频 |
| Behavioral | 经历整理 | 有准备即可 |

### 蜜雪冰城 LLM Engineer 经典场景题

**来源：@wangray**

**场景题1：** 400B 模型跨区域 serving，首 Token < 80ms，如何设计？

**场景题2：** 用户说 "I miss my school days, something cheap and sweet like back then"，单 Agent 够吗？

### 面试官判断标准

**来源：@randyloop — 面试时如何判断程序员的能力**

面试时会着重了解的维度：
1. **对业务的理解** — 是否能给 AI 足够的业务场景上下文
2. **对技术栈的理解** — 是否能让 AI 在特定技术栈中稳定发挥
3. **对架构的理解** — 是否能设计好工程架构，让 AI 在其中行动

### 面试加分项

**来源：@mashi2003_mashi**

在项目中放 AGENTS.md 是面试加分项，包含：
1. Project Rules — 基本规则
2. Workflow — 改代码前/中/后流程
3. Verification — 验证方式
4. Stop Conditions — 什么情况必须停下来问人

---

## 七

每道面试题均配有基于本项目技术栈（LangChain + LangGraph）的实战 Demo。

| 面试题 | 回答要点 | 对应 Demo |
|--------|---------|----------|
| **Agent 工程师的核心能力是什么？** | 不是会搭 Agent，而是能做 Eval（评估）。能回答"指标是多少"而不是"能跑了"。 | [Demo 07: Agent 评估体系](agent_interview_demos/07_agent_evaluation.py) |
| **在实现 AI Agent 时，如何避免返工？** | ① 做好技术选型（Chain vs Agent）② 定义清晰的 Tool Schema ③ 设计 Error Handling ④ 先做 Eval 再上线 | [Demo 09: Chain vs Agent](agent_interview_demos/09_chain_vs_agent.py) [Demo 06: 错误处理](agent_interview_demos/06_tool_error_handling.py) |
| **什么适合人做，什么适合 Agent 做？** | 人做：战略决策、边界判断、创意设计。Agent 做：信息检索、重复执行、多步推理。关键是理解 AI 的能力边界。 | [Demo 02: 工具调用](agent_interview_demos/02_tool_calling.py) |
| **什么是 ReAct 范式？** | Reasoning + Acting 交替进行，Thought → Action → Observation 循环。优势是可解释、可纠错；劣势是 Token 消耗大。 | [Demo 01: ReAct 范式](agent_interview_demos/01_react_agent.py) |
| **Agent 记忆机制如何实现？** | 三层架构：感觉记忆（原始输入）→ 短期记忆（对话历史）→ 长期记忆（向量数据库）。MemGPT 有 Tier1/2/3 分层。 | [Demo 03: Agent 记忆](agent_interview_demos/03_agent_memory.py) |
| **RAG 在 Agent 中怎么用？** | Agent 把 RAG 当工具调用。核心是 Chunk 策略 + Embedding + 向量检索 + 混合搜索。 | [Demo 04: RAG in Agent](agent_interview_demos/04_agent_rag.py) |
| **Multi-Agent 有哪些协作模式？** | 四种：监督者模式、竞拍模式、流水线模式、共享工作空间。通信方式包括直接消息、广播、共享状态。 | [Demo 05: Multi-Agent 协作](agent_interview_demos/05_multi_agent.py) |
| **工具调用失败怎么处理？** | 按错误类型分类：可重试（超时/限流）用指数退避；不可重试（参数错/权限）返回错误给 LLM 重新规划。 | [Demo 06: 错误处理](agent_interview_demos/06_tool_error_handling.py) |
| **Plan-and-Execute 是什么？** | 先规划再执行，适合结构化任务。与 ReAct 区别：ReAct 边想边做，Plan-Execute 先想好再做。 | [Demo 08: LangGraph 工作流](agent_interview_demos/08_langgraph_workflow.py) |
| **Chain 和 Agent 有什么区别？** | Chain 是固定流水线，确定性强；Agent 是动态决策，灵活性强。确定性任务用 Chain，探索性任务用 Agent。 | [Demo 09: Chain vs Agent](agent_interview_demos/09_chain_vs_agent.py) |

> 💡 所有 Demo 在 `agent_interview_demos/` 目录下，每个文件独立可运行。
> 详细映射见 [agent_interview_demos/README.md](agent_interview_demos/README.md)

