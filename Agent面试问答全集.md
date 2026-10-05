# Agent 面试问答全集

> 基于 X/Twitter、微信公众号、小红书三平台真实面经整理。
> 每道题均附面试级回答，部分配实战 Demo 链接。
> 整理日期：2026-06-26

---

## 一、Agent 基础概念

### Q1：什么是 AI Agent？它与传统程序的区别？

**回答：**

AI Agent 是一种能够**自主感知环境、做出决策并采取行动**的智能系统。它的核心公式是：

```
Agent = LLM（大脑）+ Tools（手脚）+ Memory（记忆）
```

与传统程序的关键区别：

| 维度 | 传统程序 | AI Agent |
|------|---------|----------|
| **执行方式** | 预定义逻辑，逐行执行 | 自主决策，动态规划路径 |
| **灵活性** | 只能处理预知场景 | 能处理未知场景 |
| **工具使用** | 硬编码调用 | LLM 动态选择工具 |
| **容错能力** | 遇到异常直接崩溃 | 能自我修复、重试、降级 |
| **记忆** | 无状态或简单状态 | 分层记忆（短期+长期） |

> → 实战 Demo: [Demo 01: ReAct 范式](agent_interview_demos/01_react_agent.py) 展示了 Agent 的自主决策循环

---

### Q2：Agent 的核心组件有哪些？

**回答：**

Agent 由四大核心组件构成：

1. **LLM（推理引擎）** — 大脑，负责理解、推理、决策
2. **Tools（工具集）** — 手脚，负责执行具体操作（搜索、计算、API 调用）
3. **Memory（记忆模块）** — 存储上下文和经验（短期 + 长期）
4. **Planner（规划器）** — 制定执行计划（ReAct / Plan-and-Execute）

```
用户输入 → [LLM 推理] → [规划器拆解任务]
                ↓
         [工具调度] ←→ [记忆检索]
                ↓
         [结果综合] → 最终输出
```

> → 实战 Demo: [Demo 01-09 完整体系](agent_interview_demos/README.md)

---

### Q3：Agent 与 LLM 调用的区别？

**回答：**

| 对比项 | 纯 LLM 调用 | Agent |
|--------|------------|-------|
| **输出** | 一次性文本生成 | 多步骤推理+行动+观察循环 |
| **工具** | 不调用外部工具 | 动态选择并调用工具 |
| **状态** | 无状态（或有简单对话历史） | 有状态（规划+记忆+执行上下文） |
| **决策** | 用户引导 | 自主决策 |
| **适用** | 翻译、摘要、文案生成 | 搜索、分析、多步骤复杂任务 |

---

## 二、ReAct 范式

### Q4：什么是 ReAct 范式？它的工作原理？优缺点？

**回答：**

ReAct = **Rea**soning + **Act**ing，是 Agent 最主流的设计模式。

**工作原理：**
```
[用户问题]
    ↓
Thought（思考）: 分析问题，决定下一步做什么
    ↓
Action（行动）: 调用工具执行
    ↓
Observation（观察）: 获取工具返回结果
    ↓
[继续思考或给出最终答案]
```

**优点：**
- 可解释性强（每一步都有思考过程）
- 能纠错（观察结果可以纠正下一步推理）
- 能利用外部工具扩展能力边界

**缺点：**
- Token 消耗大
- 延迟高（多步循环多次 LLM 调用）
- 复杂任务可能陷入死循环（需 max_iterations 限制）

> → 实战 Demo: [Demo 01: ReAct 范式](agent_interview_demos/01_react_agent.py) 包含 LangChain Agent + LangGraph 手写两种实现

---

## 三、工具调用 / Function Calling

### Q5：Agent 如何选择工具？Function Calling 是怎么设计的？

**回答：**

工具选择的核心流程：

```
① 定义 Tool Schema（name, description, parameters）
② Agent 启动时注册所有工具到工具列表
③ LLM 根据用户意图 + 工具 description 匹配
④ LLM 输出结构化 tool_call（工具名 + 参数）
⑤ 运行时调度执行，结果返回给 LLM
```

**关键设计原则：**
- **description 越精确，选择越准确** — 这是最重要的因素
- 使用 Pydantic 定义输入参数的 Schema
- 工具数量多时要分层加载（渐进式披露）

> → 实战 Demo: [Demo 02: 工具调用](agent_interview_demos/02_tool_calling.py) 包含 @tool 装饰器、Pydantic Schema、手写 Tool Router 三种方式

---

### Q6：如何保证 Agent 调用工具的可靠性？

**回答：**

从三个层面保障：

1. **语法层面**：利用 JSON Mode 或 Pydantic 强类型约束
2. **逻辑层面**：高风险操作引入人工确认（Human-in-the-Loop）
3. **重试逻辑**：参数不合法时，将报错信息返回给 LLM，让其自我修复（Self-heal）

> → 实战 Demo: [Demo 06: 错误处理](agent_interview_demos/06_tool_error_handling.py)

---

### Q7：工具调用失败怎么办？什么错误该重试？什么不该重试？降级策略？

**回答：**

**错误分类：**

| 错误类型 | 是否重试 | 策略 |
|---------|---------|------|
| 网络超时 (Timeout) | ✅ 重试 | 指数退避，最多3次 |
| 频率限制 (Rate Limit) | ✅ 重试 | 退避等待，最多2次 |
| 服务不可用 (503) | ✅ 重试 | 切换备用服务，最多2次 |
| 参数错误 (ValueError) | ❌ 不重试 | 返回报错给LLM重新规划 |
| 权限不足 (Permission) | ❌ 不重试 | 返回错误，人工介入 |

**重试策略（指数退避）：**
```
等待时间 = min(1s × 2^重试次数, 30s) × (1 + random × 0.5)
```

**降级策略：**
- 主 API 超时 → 备用 API
- 搜索不可用 → 本地缓存
- 全部失败 → 返回清晰错误信息，建议人工介入

> → 实战 Demo: [Demo 06: 错误处理](agent_interview_demos/06_tool_error_handling.py) 包含完整的 RetryableToolWrapper + FallbackStrategy

---

## 四、记忆机制

### Q8：Agent 的记忆机制是怎么做的？有哪些记忆类型？

**回答：**

三层记忆架构：

```
① 感觉记忆（Sensory Memory）
   — 原始输入缓存，毫秒级保留

② 短期记忆（Short-term Memory）
   — 当前会话的对话历史
   — 实现：ConversationBufferMemory
   — 限制：LLM 上下文窗口大小

③ 长期记忆（Long-term Memory）
   — 跨会话的知识和经验
   — 实现：向量数据库（ChromaDB / Pinecone）
   — 检索：RAG + Embedding
```

**MemGPT 分层架构（面试加分）：**
- Tier 1 (HBM)：模型上下文窗口内的活跃信息
- Tier 2 (DRAM)：外部向量存储，按需检索
- Tier 3 (SSD)：归档存储，冷数据

> → 实战 Demo: [Demo 03: Agent 记忆](agent_interview_demos/03_agent_memory.py) 包含 BufferMemory、SummaryMemory、LangGraph 持久化、ChromaDB 长期记忆

---

### Q9：如何处理多轮对话中的"状态爆炸"和"上下文溢出"？

**回答：**

三种策略：

1. **State Schema**：定义严格的状态结构（如 TypedDict），只保存核心变量
2. **Trim Strategy**：按语义重要性保留（System Prompt + 最近N轮 + 当前目标）
3. **Summary Buffer**：旧对话浓缩为摘要，放入 Context 头部

> → 实战 Demo: [Demo 03: 记忆机制](agent_interview_demos/03_agent_memory.py) 中的 SummaryMemory 实现

---

## 五、RAG 与向量数据库

### Q10：什么是 RAG？Agent 如何结合 RAG？

**回答：**

RAG = **R**etrieval-**A**ugmented **G**eneration（检索增强生成）

**工作原理：**
```
① Indexing: 文档分块 → Embedding → 存入向量数据库
② Retrieval: 用户查询 → Embedding → 相似度搜索 → Top-K
③ Generation: 检索结果 + 查询 → LLM → 生成回答
```

**Agent 结合 RAG 的三种方式：**
1. **RAG 作为 Agent 的工具**（推荐）— Agent 需要知识时主动调用
2. **RAG 作为 Agent 的长期记忆** — 存储和检索历史经验
3. **RAG 结果作为推理上下文** — 规划阶段自动注入

> → 实战 Demo: [Demo 04: RAG in Agent](agent_interview_demos/04_agent_rag.py) 包含基本 RAG、MMR 检索、混合搜索

---

### Q11：为什么向量数据库在 Agent 面试中如此重要？

**回答：**

向量数据库是 RAG 的核心基础设施，它负责**语义检索**（理解意图而非关键词匹配）。

**为什么重要：**
- 支持大规模知识管理（百万级文档毫秒级响应）
- 语义搜索准确率远超关键词搜索
- 支持增量更新（动态知识库）
- 多模态支持（文本、图片、代码均可向量化）

**常见对比：**

| 数据库 | 场景 | 特点 |
|-------|------|------|
| ChromaDB | 原型/小规模 | 轻量、本地部署 |
| Pinecone | 生产级 | 全托管、高性能 |
| Milvus | 大规模 | 分布式、云原生 |
| FAISS | 离线检索 | Meta 开源、GPU 加速 |

---

### Q12：RAG 系统如何评测？有哪些评测维度？

**回答：**

| 维度 | 指标 | 说明 |
|------|------|------|
| 检索精度 | Recall@K, MRR | 检索结果是否包含正确答案 |
| 生成质量 | 准确率、完整性 | LLM 回答是否正确、完整 |
| 相关度 | NDCG | 排序结果与查询的相关程度 |
| 延迟 | P50/P99 | 从查询到返回的时间 |
| 鲁棒性 | 异常覆盖率 | 边界场景是否稳定 |

> → 实战 Demo: [Demo 07: Agent 评估](agent_interview_demos/07_agent_evaluation.py)

---

## 六、Multi-Agent 系统

### Q13：Multi-Agent 协作常见模式有哪些？

**回答：**

四种常见模式：

1. **监督者模式（Supervisor）** — 中心化调度
   ```
   Supervisor Agent → Worker A / Worker B / Worker C
   ```

2. **竞拍模式（Auction）** — 市场化分配
   ```
   Task 广播 → Agents 竞标 → 最优者执行
   ```

3. **流水线模式（Pipeline）** — 阶段化处理
   ```
   Stage1 Agent → Stage2 Agent → Stage3 Agent
   ```

4. **共享工作空间模式** — 去中心化协作
   ```
   Agents ↔ Shared Workspace（黑板模式）
   ```

**选型建议：**
- 确定性任务 → 监督者模式
- 竞争性任务 → 竞拍模式
- 流程性任务 → 流水线模式
- 创意性任务 → 共享工作空间

> → 实战 Demo: [Demo 05: Multi-Agent](agent_interview_demos/05_multi_agent.py) 包含 Supervisor Pattern、Agent 通信协议、Shared Workspace

---

### Q14：子 Agent 之间怎么通信？

**回答：**

四种通信方式：

| 方式 | 描述 | 适用场景 |
|------|------|---------|
| 直接消息 | 点对点发送 | 确定性通信 |
| 广播 | 一对多通知 | 状态变更通知 |
| 共享状态 | 工作空间/黑板模式 | 协作文档 |
| 消息队列 | 异步解耦 | 大规模系统 |

> → 实战 Demo: [Demo 05: 通信协议](agent_interview_demos/05_multi_agent.py) 实现了完整的 Message 结构和 CommunicationProtocol

---

### Q15：如何防止 Multi-Agent 互相调用停不下来？

**回答：**

1. **最大迭代限制**：给每个 Agent 设置 max_iterations
2. **超时控制**：单次 Agent 调用超时中断
3. **监督者裁决**：Supervisor 判断是否终止
4. **循环检测**：检测重复的调用模式并中断
5. **人工介入**：关键节点需人工确认

---

## 七、Plan-and-Execute

### Q16：什么是 Plan-and-Execute？和 ReAct 的区别？

**回答：**

**Plan-and-Execute**：先制定完整计划，再逐步执行。

```
[用户目标] → [Planner 制定计划] → [Executor 逐步执行] → [Checker 检查结果]
                                      ↑                        |
                                      └────── 需要调整 ────────┘
```

**与 ReAct 的区别：**

| 维度 | Plan-and-Execute | ReAct |
|------|-----------------|-------|
| **规划时机** | 先规划再执行 | 边想边做 |
| **适用场景** | 步骤已知的结构化任务 | 未知探索性任务 |
| **灵活性** | 低（计划固定） | 高（动态调整） |
| **Token 消耗** | 相对低 | 较高 |
| **可预测性** | 高 | 低 |

> → 实战 Demo: [Demo 08: LangGraph 工作流](agent_interview_demos/08_langgraph_workflow.py) 包含 Plan-Execute + 条件分支

---

## 八、LangChain / LangGraph

### Q17：LangChain 的核心抽象是什么？

**回答：**

五大核心模块：

```
① Model I/O     — 模型输入输出（Prompt Template, Output Parser）
② Retrieval     — 检索（Document Loader, Text Splitter, Vector Store, Retriever）
③ Chain         — 链（LCEL 声明式组合）
④ Agent         — 智能体（ReAct, Tool Calling）
⑤ Callback      — 回调（日志, 监控, LangSmith 追踪）
```

**LCEL（LangChain Expression Language）：**
```python
# | 操作符声明式组合
chain = prompt | model | output_parser

# 并行执行
parallel = RunnableParallel(task1=chain1, task2=chain2)

# 数据流转换
chain = {"context": RunnablePassthrough()} | prompt | model | parser
```

> → 实战 Demo: [Demo 09: Chain vs Agent](agent_interview_demos/09_chain_vs_agent.py) 包含 LCEL、RunnableParallel、RunnablePassthrough

---

### Q18：Chain 和 Agent 的区别？怎么选型？

**回答：**

| 维度 | Chain | Agent |
|------|-------|-------|
| 决策方式 | 预定义流程 | 动态决策 |
| 灵活性 | 低（固定步骤） | 高（LLM 自主选择） |
| Token 消耗 | 低 | 高 |
| 调试难度 | 易 | 难 |

**选型原则：**
- **用 Chain**：翻译、分类、提取、格式转换（确定性强）
- **用 Agent**：搜索、推理、多工具协作（不确定性强）
- **生产最佳实践**：70% Chain + 20% Agent + 10% Human-in-the-Loop

> → 实战 Demo: [Demo 09: 对比分析](agent_interview_demos/09_chain_vs_agent.py)

---

### Q19：什么是 LangGraph？节点和边与传统工作流有何不同？

**回答：**

LangGraph 是 LangChain 的图框架，用于构建有状态的 Agent 工作流。

**与传统工作流的区别：**

1. **边可以是条件边** — 由 LLM 输出决定下一步走向
2. **支持循环** — Agent 可以不断尝试直到成功
3. **状态持久化** — Checkpointer 支持断点续跑
4. **支持人工介入** — interrupt 机制

```python
# LangGraph 核心结构
builder = StateGraph(StateType)
builder.add_node("planner", planner_func)
builder.add_node("executor", executor_func)
builder.add_conditional_edges("checker", should_continue)
builder.compile()
```

> → 实战 Demo: [Demo 08: LangGraph 工作流](agent_interview_demos/08_langgraph_workflow.py)

---

### Q20：AgentExecutor 的工作原理？

**回答：**

AgentExecutor 是 Agent 的执行引擎，核心循环：

```
① 接收用户输入
② LLM 推理 → 决定是调用工具还是直接回答
③ 若调用工具：执行工具 → 将结果返回给 LLM
④ 重复②③直到 LLM 决定直接回答或达到 max_iterations
⑤ 返回最终输出
```

---

## 九、MCP 协议

### Q21：什么是 MCP 协议？

**回答：**

MCP = **M**odel **C**ontext **P**rotocol，是模型与外部工具交互的**统一协议标准**。

类比理解：MCP 是 AI 界的 **USB 接口** — 无论什么设备和主机，只要遵守 USB 协议就能互通。

**核心价值：**
- 标准化工具定义和调用方式
- 减少重复集成工作
- 工具可发现、可组合
- 支持权限控制和安全审计

> 项目已内置 `langchain-mcp-adapters` 支持 MCP 集成

---

## 十、Agent 评估

### Q22：如何评估 Agent 的效果？

**回答：**

五维度评估体系：

| 维度 | 指标 | 说明 |
|------|------|------|
| 任务完成率 | Success Rate | Agent 成功完成任务的占比 |
| 工具准确率 | Tool Selection Accuracy | 正确选择工具的比率 |
| Token 效率 | Tokens per Task | 完成任务消耗的 Token 数 |
| 响应延迟 | P50/P99 Latency | 从输入到输出的时间 |
| 鲁棒性 | Error Recovery Rate | 异常场景下的自愈能力 |

**评估方法论：**
- **离线评估**：构造测试集，自动化跑分
- **在线评估**：A/B 测试，用户反馈
- **LLM-as-Judge**：用更强模型评估输出质量
- **人工评估**：抽样标注

> → 实战 Demo: [Demo 07: Agent 评估](agent_interview_demos/07_agent_evaluation.py) 包含完整的 Eval Framework

---

## 十一、系统设计

### Q23：Agent 怎么加载海量技能？

**回答：**

核心问题：200 个工具全塞进 Prompt，Token 能超 10 万，模型选择准确率从 95% 掉到 41%。

**解决方案：渐进式披露（分层加载）**

```
第一层：技能名 + 一句话描述（几十个 Token）
       让模型知道有什么工具
       
第二层：用户提出具体需求后，再加载完整操作说明
       包含参数格式、调用方式
       
第三层：碰到报错或复杂任务，再查详细文档或知识库
```

**效果：** 比全量加载省 85%~95% 的 Token

**落地难点：**
1. 第一层信息要写准 → 用轻量模型先做工具分类
2. 每切一层都有加载延迟 → 用提示词缓存（成本降 45~80%，响应快 13~31%）
3. 技能卸载后模型忘记进度 → 单独建记忆模块记当前任务状态

> → 实战 Demo: [Demo 02: Tool Router](agent_interview_demos/02_tool_calling.py)

---

### Q24：多用户同时调用 API，任务一多就卡死，怎么设计？

**回答：**

高并发 Agent 架构设计：

```
[Gateway] → [Rate Limiter] → [Task Queue] → [Worker Pool]
    ↑                            ↓
    └────── [Cache] ← [Result Store]
```

关键点：
1. **无状态化**：Agent 实例不保存状态，状态存外部存储
2. **连接池**：复用 API 连接，避免频繁创建
3. **限流**：令牌桶/漏桶算法控制请求速率
4. **缓存**：高频查询结果缓存
5. **异步处理**：非阻塞 I/O，任务队列削峰

---

## 十二、安全与对齐

### Q25：Agent 的安全风险有哪些？如何防护？

**回答：**

| 风险 | 描述 | 防护措施 |
|------|------|---------|
| Prompt 注入 | 恶意输入操纵 Agent 行为 | 输入过滤、指令隔离 |
| 工具滥用 | Agent 在未经授权时调用高危工具 | 权限分级、人工确认 |
| 数据泄露 | 敏感信息通过工具调用泄露 | 输出过滤、脱敏处理 |
| 权限逃逸 | Agent 绕过安全限制 | 沙箱执行、最小权限原则 |

---

## 十三、场景题实战

### Q26：字节场景题 — 用户跨 Session 如何保证上下文连贯？

**回答：**

1. **UserID + SessionID** 双重标识，跨会话关联
2. **长期记忆**：每次对话结束，将关键信息存入向量数据库
3. **主题识别**：自动识别用户话题，即使跨 Session 也能关联
4. **渐进式摘要**：旧会话逐层压缩，保留核心信息

---

### Q27：字节场景题 — 长时间任务如何减少用户等待？

**回答：**

1. **SSE/WebSocket 流式推送**：边生成边推送，首字时延降到最低
2. **进度反馈**：实时报告当前步骤和进度百分比
3. **异步执行**：后台执行任务，用户可以先做其他事
4. **预加载**：预测用户下一步需求，提前准备

---

### Q28：蜜雪冰城 LLM Engineer 经典场景题

**场景题1：** 400B 模型跨区域 serving，首 Token < 80ms

参考答案：
- PD 分离，Frontend 用 SGLang
- RadixAttention（高频 KV cache 走 trie 复用）
- KVCache-centric 架构：Tier1 HBM + Tier2 DRAM
- Speculative Decoding（按地区训练 draft model）

**场景题2：** 用户说 "I miss my school days, something cheap and sweet like back then"

参考答案：不够，必须 Multi-Agent：
- Memory Agent：学生时代 nostalgia RAG
- Store Agent：原料库存 + 制作速度
- Brand Agent：输出品牌风格话术
- 训练：GRPO + offline RL
- Reward 设计：下单 +10，说 "this reminds me of my childhood" +30

---

## 十四、各厂面经汇总

### 快手 AI Agent 开发一面（25题·速查）

| # | 题目 | 对应知识点 | 对应 Demo |
|---|------|-----------|----------|
| 1 | 为什么引入父子索引？ | RAG 分层检索 | [Demo 04](agent_interview_demos/04_agent_rag.py) |
| 2 | 为什么引入 BM25？ | 混合搜索：语义+关键词 | [Demo 04](agent_interview_demos/04_agent_rag.py) |
| 3 | Rerank 后返回几个块？ | 重排序策略 | [Demo 04](agent_interview_demos/04_agent_rag.py) |
| 5 | 上下文工程怎么设计？ | Context Engineering | [Demo 02](agent_interview_demos/02_tool_calling.py) |
| 6 | 记忆机制怎么做？ | Memory 分层架构 | [Demo 03](agent_interview_demos/03_agent_memory.py) |
| 7 | Function Calling 怎么设计？ | Tool Schema + Router | [Demo 02](agent_interview_demos/02_tool_calling.py) |
| 8 | 任务规划怎么做？ | ReAct / Plan-and-Execute | [Demo 01](agent_interview_demos/01_react_agent.py) [Demo 08](agent_interview_demos/08_langgraph_workflow.py) |
| 9 | Prompt 注入防御？ | Agent 安全 | 安全组件 |
| 18 | RAG 系统如何评测？ | 评估体系 | [Demo 07](agent_interview_demos/07_agent_evaluation.py) |

### 字节跳动 Agent 开发岗二面（20题·速查）

| # | 题目 | 对应知识点 | 对应 Demo |
|---|------|-----------|----------|
| 1 | LangGraph 还是自研？为什么？ | 框架选型 | [Demo 08](agent_interview_demos/08_langgraph_workflow.py) |
| 2 | 单 Agent 还是多 Agent？ | 架构设计 | [Demo 05](agent_interview_demos/05_multi_agent.py) |
| 8 | Agent 效果怎么评估？ | Eval 体系 | [Demo 07](agent_interview_demos/07_agent_evaluation.py) |
| 12 | 推理优化做了哪些？ | continuous batching / KV Cache / vLLM | 推理优化 |
| 17 | Self-Attention 原理？ | QKV 三个向量 | 基础理论 |

### 携程 Agent 开发二面（30题·速查）

| # | 题目 | 对应知识点 | 对应 Demo |
|---|------|-----------|----------|
| 1-3 | Agent 架构设计 | LangGraph / Master-Sub | [Demo 08](agent_interview_demos/08_langgraph_workflow.py) |
| 7-13 | 评测体系与 Badcase | Eval + Prompt 调优 | [Demo 07](agent_interview_demos/07_agent_evaluation.py) |
| 16-20 | 推理优化与工程落地 | vLLM / continuous batching | 工程实践 |

---

*本文档将面试题、回答、实战 Demo 三者串联。每个 Demo 文件独立可运行，详见 `agent_interview_demos/README.md`。*

---

## 十五、CLAUDE.md / AGENTS.md / System Prompt

### Q29：CLAUDE.md / AGENTS.md 是什么？它的作用是什么？

**回答：**

CLAUDE.md（GitHub 通用项目）或 AGENTS.md（Codex 项目）是放在项目根目录的配置文件，AI Coding Agent 启动时自动读取，相当于项目的**员工手册**。

**作用：**
- 定义代码风格和规范
- 指定构建/测试命令
- 设定工作流和验证方式
- 设置停止条件（什么情况必须问人）

> 核心理念：不是让 AI 更聪明，而是让 AI 更受控。

**模板结构：**
```markdown
# AGENTS.md

## Project Rules
- Read the relevant files before editing.
- Keep changes limited to the user's request.
- Do not refactor unrelated code.

## Workflow
Before editing: restate goal → list files → list risks → explain verification
While editing: minimal change → preserve behavior → stop if scope grows
After editing: summarize changes → report verification → mention risks

## Verification
- npm test | pytest | cargo test | browser screenshot

## Stop Conditions
- need new dependencies | modify DB schema | conflict with existing code
```

### Q30：CLAUDE.md、Memory、RAG 三者是什么关系？

**回答：**

| 机制 | 定位 | 持久性 | 触发方式 | 类比 |
|------|------|--------|---------|------|
| CLAUDE.md | 静态项目规则 | 文件持久 | 每次对话自动加载 | 员工手册 |
| Memory | 动态交互记忆 | 跨会话持久 | 对话中积累更新 | 工作笔记 |
| RAG | 按需知识检索 | 外部知识库 | 需要时才调用 | 查询文档 |

**加载优先级：**
```
System Prompt（每次都有）→ CLAUDE.md（级别规则）
    → Rules（条件触发）→ Skills（按需加载）→ RAG（需要时检索）
```

### Q31：System Prompt 和 CLAUDE.md 有什么区别？怎么设计 System Prompt？

**回答：**

| 维度 | System Prompt | CLAUDE.md |
|------|--------------|-----------|
| 作用域 | Agent 的角色、性格、边界 | 项目的工程规范 |
| 内容 | "你是谁" "注意事项" 输出格式 | 代码风格、构建命令、验证方式 |
| 位置 | 对话启动时注入 | 项目根目录文件 |
| 持久性 | 对话级别 | 项目级别 |
| 修改频率 | 每次对话可调 | 项目生命周期内相对稳定 |

**System Prompt 设计原则：**
1. **精简精准** — 不是大 Prompt，是精准约束
2. **角色定义** — 清楚说明 Agent 是谁
3. **能力边界** — 明确能做什么、不能做什么
4. **行为约束** — 什么情况下必须停下来
5. **输出规范** — 格式、语气、风格

### Q32：Anthropic Steering Claude Code 的 7 大操控技巧是什么？

**回答：**

Anthropic 官方指南《Steering Claude Code》：

1. **CLAUDE.md** — 项目取扱说明书（build命令、目录结构、团队规范）
2. **Rules（规则）** — 条件触发的约束文件（只匹配特定路径时激活）
3. **Skills（技能）** — 按需加载的能力包（被调用时才启动）
4. **Subagents（子代理）** — 独立处理子任务，只返回结果
5. **Hooks（钩子）** — 保存后自动 Lint、结束后 Slack 通知
6. **Output Styles** — 改变输出风格（最强权限，慎用）
7. **System Prompt 追记** — 启动时注入本次对话规则（Token 节约）

### Q33：上百个 Skills 如何不爆上下文？

**回答：**

核心方案：**渐进式披露**（同海量技能加载策略）

```
① 第一层：Skill 名 + 一句话描述（几十 Token）
         让模型知道有什么能力可用

② 第二层：用户选择/触发后，加载完整 Skill 说明
         包含操作步骤、参数格式

③ 第三层：复杂任务或报错时，查详细文档/知识库
```

效果：比全量加载省 85%~95% 的 Token。

### Q34：Claude Code 的上下文管理策略有哪些？

**回答：**

1. **分层加载**：System Prompt → CLAUDE.md → Rules → Skills → RAG
2. **上下文裁剪**（Trim）：按语义重要性保留核心内容，丢弃低价值信息
3. **摘要压缩**：多轮对话后自动压缩为摘要
4. **Token 预算管理**：设定 Token 上限，超出时触发裁剪
5. **按需检索**：RAG 方式只在需要时才加载外部知识

### Q35：面试问题 "Claude Code 你用到什么程度？" 怎么回答？

**回答：**

从以下维度展示你的使用深度：

1. **基础配置**：CLAUDE.md / AGENTS.md 编写项目规范
2. **Skill 扩展**：自定义 Skills，按需加载专项能力
3. **MCP 集成**：通过 MCP 协议连接外部工具和数据库
4. **工作流自动化**：Hooks 实现保存后自动检查、测试
5. **多 Agent 协作**：Subagents 并行处理多任务
6. **上下文管理**：System Prompt 优化 + Rules 条件加载
7. **工程化实践**：spec.md / tasks.md / checklist.md 三件套

### Q36：5 种 Agent Skill 设计模式是什么？

**回答：**

1. **模板模式** — 预定义操作流程（如「部署检查清单」）
2. **反转模式** — Agent 扮演面试官/审查者角色来验证输出
3. **链式模式** — 多个 Skill 串联（分析 → 生成 → 检查）
4. **分支模式** — 根据上下文条件选择不同 Skill
5. **循环模式** — 迭代优化的 Skill（不断 refine）

### Q37：andrej-karpathy-skills 的 4 条铁律？

**回答：**

GitHub 11万+ Stars 的最佳实践：

1. **先思考再编码**：不准做假设，模糊就提问，困惑立刻停下
2. **简约至上**：只写最小可工作代码，不做过度抽象
3. **手术式修改**：只改要求的部分，不重构邻居代码
4. **目标驱动执行**：先写成功标准，每步都要可验证

---

*本篇章为 CLAUDE.md / AGENTS.md / System Prompt 专题。完整面试题库涵盖 14 大章节。*

---

## 十六、Agent 评估（Eval）深度专题

### Q38：为什么 Agent 的 Eval 比普通模型难得多？

**回答：**

| 维度 | 普通模型 Eval | Agent Eval |
|------|-------------|-----------|
| 评估对象 | 输入→输出的固定映射 | 动态执行过程（多路径） |
| 评估维度 | 单一输出准确性 | 轨迹 + 结果 + 鲁棒性 |
| 中间步骤 | 不关心中间过程 | 中间步骤对错很关键 |
| 稳定性 | 容易复现 | 同一任务可能走完全不同的路径 |

> 核心矛盾：**结果对不代表过程对，过程对也不等于结果一定对。**

举例：Agent 查融资信息，答案对了。但如果是搜索关键词质量差、碰巧搜到了？下次还能稳定吗？

### Q39：你们线上 Agent 的评估体系是怎么设计的？（满分回答）

**回答：**

> 我们的评估分三个层次：
>
> 1. **轨迹评估**（Trajectory Eval）—— 看执行路径的合理性。Agent 每一步的思考、工具选择和调用是否合理。
> 2. **结果评估**（Outcome Eval）—— 看最终输出的准确性。任务是否真正完成。
> 3. **鲁棒性评估**（Robustness Eval）—— 看边界场景下的稳定性。换一个问法、换一个场景是否还能稳定？

**配套机制：**
- 测试集按**任务类型分层构建**，同时从线上真实流量采样补充长尾场景
- 标注侧用 **LLM-as-Judge** 初筛 + 人工复核，定期校准 judge 一致性
- 线上配合**步骤级日志**和**异常模式告警**，形成「离线 Eval + 线上监控」闭环

> 踩坑经验：早期只看结果准确率，忽视了轨迹评估。线下 90% 准确率的任务，换个场景立刻崩，因为 Agent 是"猜"对的，不是真正推理出来的。

> → 实战 Demo: [Demo 07: Agent 评估](agent_interview_demos/07_agent_evaluation.py)

### Q40："准确率"是怎么定义的？任务完成怎么判断？

**回答：**

准确率不能笼统地说，必须分层定义：

1. **端到端准确率**：最终结果是否正确（需人工标注或 LLM-as-Judge）
2. **工具选择准确率**：Agent 选择的工具是否正确
3. **轨迹准确率**：执行路径是否符合预期
4. **部分正确率**：部分子任务完成的比例

**任务完成的判断方式：**
- 结构化任务：比对预期输出（确定性）
- 开放式任务：LLM-as-Judge 打分 + 人工抽样复核
- 多步任务：每步独立打分 + 最终结果综合

### Q41：Agent 评估的三层模型是什么？

**回答：**

Agent = Model + Harness。三层评估模型：

1. **🧠 推理层（Reasoning）** → 计划质量
   - 指标：计划完整性、步骤合理性、时间估算准确度

2. **🔧 行动层（Action）** → 工具调用准确性
   - 指标：工具选择准确率、参数正确率、重试次数

3. **📊 执行层（Execution）** → 端到端任务完成
   - 指标：完成率、任务耗时、Token 消耗

### Q42：Agent 评测的四大维度是什么？（PM 面试版）

**回答：**

1. **能力维度** — "能不能"做到？
   - 任务完成率、工具选择准确率

2. **体验维度** — "好不好"用？
   - 响应速度（P50/P99）、交互流畅度

3. **可靠与安全维度** — "可不可靠"？
   - 稳定性、安全性、异常处理

4. **业务与价值维度** — "有没有用"？
   - 业务转化率、用户满意度 NPV、ROI

### Q43：大模型能力评测指标有哪些？（面试高频）

**回答：**

❌ 错误回答：**"用户反馈……"**（太笼统，面试官直接摇头）

✅ 正确回答分三类：

| 类别 | 指标 | 说明 |
|------|------|------|
| 离线通用指标 | Accuracy / F1 / BLEU / ROUGE / VES | 模型能力基准 |
| Agent 特有指标 | 任务完成率、工具准确率、轨迹合理性 | Agent 系统质量 |
| 在线业务指标 | 用户满意度、留存率、业务转化率 | 实际业务价值 |

加分项：提 DeepEval / LangSmith / RAGChecker 等工具

### Q44：如何评估 Agentic RAG 系统的准确性？

**回答：**

需从两个维度分离评估：

1. **检索质量**：Recall@K、MRR、NDCG
2. **生成质量**：答案准确性、幻觉率、Faithfulness

评估方法：
- 构造 Ground Truth 测试集
- LLM-as-a-Judge（用更强模型打分）
- RAGChecker 等专用评估框架

### Q45：Eval 在面试中怎么讲才加分？

**回答：**

面试中讲 Evaluation 必须包含三要素：

1. **Why** — 为什么要做？（从 toy demo 到 engineering 生产）
2. **How** — 分几层做？（fault isolation 故障隔离，每层独立指标）
3. **Launch** — 怎么推上线？（golden test cases + CI 集成 + 线上追踪）

**加分金句：**
> "我用 DeepEval 在 CI 里做了 LLM 回归测试"
> "只要能用 tests/evals 明确定义「什么叫 working」，Agent 就能接管剩下 90% 的工作"

> → 实战 Demo: [Demo 07: Agent 评估](agent_interview_demos/07_agent_evaluation.py) 包含完整的 Eval Framework、LLM-as-Judge、自动化跑分

---

*本篇章为 Agent 评估（Eval）深度专题。完整面试题库涵盖 16 章节、45 道问答。*

---

## 十七、Harness Engineering

### Q46：什么是 Harness？Agent = Model + Harness 怎么理解？

**回答：**

```
Agent = Model + Harness
```

Harness 是**模型之外的"驾驭层"**。模型是地基，Harness 是上层工程系统，让 Agent 从 "能调 API" 到 "能稳定完成任务"。

**Harness 包含：**
- **方法论层**：Prompt、Agent Loop、Workflow
- **工具层**：Tool、Skill、MCP、Sandbox
- **可观测层**：Trace（全链路追踪）、Eval（评估）、Replay（问题复现）
- **约束层**：Linter（行为检查）、Guardrails（安全围栏）

> 类比：Harness 是马鞍和缰绳，Model 是马。没 Harness，马到处乱跑。

### Q47：Harness = Workflow + Infra 怎么理解？

**回答：**

来源：@9hills (X/Twitter)

1. **Harness Workflow** — 工作流方法论
   - 研究→需求→设计→开发→验证闭环
   - 关注 Agent 怎么组织、怎么协作、怎么推进

2. **Harness Infra** — 基础设施
   - Sandbox（沙盒环境）
   - Skills（能力模块）
   - Tooling（工具链管理）
   - CI/CD 集成

> Infra 的目标是保证 Workflow 的落地。

### Q48：Harness Engineering 和普通工程化测试有什么区别？

**回答：**

| 维度 | 普通测试 | Harness Engineering |
|------|---------|-------------------|
| 测试对象 | 确定性代码 | 非确定性 Agent 行为 |
| 验证方式 | 固定输入→输出 | 轨迹+结果+鲁棒性多层次 |
| 可复现性 | 100% 复现 | 需 Replay 机制 |
| 工具链 | 单元测试/UAT | Trace + Eval + Linter + Judge |
| 优化闭环 | Bug→Fix | BadCase→定位组件→优化Prompt/Tool/Loop |

### Q49：Agent 输出不确定怎么办？同一用例每次结果不同？

**回答：**

1. **多次运行取统计** — 同一 case 跑 N 次，看成功率而非单次结果
2. **轨迹评估优先** — 不只看结果对错，更看执行路径是否合理
3. **LLM-as-Judge** — 用更强的模型评估输出质量
4. **容忍度设置** — 定义什么叫 "可接受的不一致"
5. **分层标记** — 确定性任务严格要求，创意性任务放宽标准

### Q50：Harness 的 Linter 怎么设计？

**回答：**

**双轨验证机制：**
- L1 确定性 Linter：代码/规则校验（ESLint、架构规则）→ 处理 80% 问题
- L2 LLM 审计 Agent：智能判断边缘情况 → 处理 20% 问题

**三层架构：**
1. L1 代码级 — ESLint + 自定义规则
2. L2 架构级 — 自定义 Linter（分层架构、接口约束）
3. L3 行为级 — LLM 审计 Agent（行为合理性检查）

**关键设计：** 报错要带修复指导
```
❌ 差的：Error: Architecture violation
✅ 好的：禁止修改 Core 层 | 位置: xxx | 原因: xxx | 修复: 参考 xxx
```

> Linter 是给 Agent 装的红绿灯，让它知道什么时候该停、什么时候该走。

### Q51：面试面 Harness 岗，要准备哪些问题？

**回答：**

面试官考察的 6 个维度：

1. **做过什么任务** — 有真实项目经验
2. **Agent 在哪断** — 能定位问题根因，不只是 "效果不好"
3. **怎么判断完成** — 有量化的完成标准，不是 "看起来对了"
4. **结果验证** — 有 Eval 体系、有测试用例
5. **输出怎么回写** — Worker 产出如何整合
6. **Workflow 可复用** — 个人方法能抽象成别人也能用的产品

**DeepSeek Harness 面试流程：** 1 轮笔试 + 3 轮面试（终面负责人主持）

### Q52：Anthropic 长任务 Agent 的 Harness 经验是什么？

**回答：**

两阶段架构解决 "Agent 跨多 context window 持续工作"：

1. **初始化 Agent** — 搭环境、生成 feature list（200+ features）
2. **编码 Agent** — 每个 session 做一个 feature，留下交接信息

**四种关键设计：**
- Feature list：每次只做一个
- Git commit + progress 文件：防止烂摊子
- JSON feature list：禁止删改测试、禁止过早标记完成
- 浏览器自动化 E2E：真实验证

> 核心思想：把 "project state" 从 Agent 脑子里移出来，放到结构化文件里。

---

*本篇章为 Harness Engineering 专题。完整面试题库涵盖 17 章节、52 道问答。*

---

## 十八、Context Engineering（上下文工程）

### Q53：什么是 Context Engineering？和 Prompt Engineering 有什么区别？

**回答：**

> Prompt Engineering = 模型被提问时，**怎么被提问**（措辞优化）
> Context Engineering = 模型被提问时，**已经知道什么**（知识环境构建）

| 维度 | Prompt Engineering | Context Engineering |
|------|-------------------|-------------------|
| 关注点 | 怎么问 | 有什么 |
| 操作对象 | 单条提示词 | 整个上下文窗口 |
| 服务对象 | 普通用户 | 开发者/Agent 构建者 |
| 技术栈 | few-shot, CoT | RAG, Memory, 裁剪, 分层注入 |
| 时间跨度 | 单次对话 | 跨会话、长期积累 |

**一句话总结：** PE 是你告诉模型的那句话，CE 是模型在听到那句话之前就已经知道的一切。

### Q54：Context Engineering 包含哪些组件？

**回答：**

六大核心组件：

1. **组装（Assembly）** — 哪些信息该进入上下文，优先级排序
2. **裁剪（Trimming）** — 丢弃低价值信息，保留核心内容
3. **注入（Injection）** — 什么时候动态注入（System Prompt / 按需）
4. **隔离（Isolation）** — 多租户/多任务上下文的隔离策略
5. **记忆（Memory）** — 跨会话如何保持和检索
6. **监控（Monitoring）** — Token 预算、上下文利用率追踪

> 核心理念：**多数 AI Agent 的失败，并非模型能力的失败，而是上下文工程的失败。**

### Q55：面试官问"你的上下文工程策略是什么"，怎么回答？

**回答：**

> 我们的上下文工程策略包含四个层面：
>
> 1. **静态层（CLAUDE.md / AGENTS.md）** — 项目规则、编码规范、构建命令，每次对话必加载
> 2. **动态层（Memory + RAG）** — 当前任务状态、检索到的相关知识
> 3. **预算层** — Token 预算管理，超出阈值触发裁剪和摘要压缩
> 4. **隔离层** — 多租户、多任务场景下的上下文隔离
>
> 实践中最关键的是裁剪策略：按信息重要性分层，System Prompt > 当前任务 > 历史摘要 > 原始对话。

### Q56：上下文工程和 Harness 是什么关系？

**回答：**

> Harness = 上下文工程 + 架构约束 + 知识 Memory + 技术债梳理

来源：字节火山引擎 @vista8

Context Engineering 是 Harness 的核心组成部分：
- Harness 提供的是**整体工程框架**
- Context Engineering 负责的是框架中的**信息层**
- 两者配合：Harness 定义"怎么做"，CE 定义"知道什么"

### Q57：Loop Engineering 中，上下文（Context）为什么是最先失控的变量？

**回答：**

Agent 在循环执行中，上下文是第一个变量：

1. **每轮推理都消耗 Token** — 上下文窗口有上限
2. **信息积累不可逆** — 旧信息占着位置但可能已经无用
3. **信息质量递减** — 越往后 LLM 注意力越分散

**解决方案：**
- 设置 Token 预算预警线（80% 触发裁剪）
- 优先级列表：System Prompt > 核心约束 > 当前目标 > 历史摘要 > 原始记录
- 每 N 轮自动压缩历史为摘要

### Q58：简历写"精通 Prompt"，面试官怎么看？

**回答：**

面试官的内心 OS：
> 把 PE 和 CE 混为一谈 → 说明只在写 prompt 这一层工作过
> 没有管理过 Agent 的上下文生命周期
> 不理解上下文窗口预算、裁剪策略、分层注入

**正确姿势：** 简历和面试中区分 PE 和 CE：
- "擅长 Prompt Engineering（指令优化） 和 Context Engineering（上下文管理）"
- 能说清楚两者的区别和技术栈

---


---

## 十九、爬虫 + RAG + GraphRAG + AgenticRAG

### Q59：AI Agent 友好的爬虫 vs 传统爬虫区别？

**回答：**

> 核心差异：**面向 HTML 标签 → 面向语义与目标**

| 维度 | 传统爬虫 | AI Agent 友好爬虫 |
|------|---------|----------------|
| 选择器 | 脆弱 CSS / XPath | LLM+Pydantic Schema |
| 输出 | HTML 噪声大 | 干净 Markdown |
| 抽样 | 滚雪球无停止条件 | 自适应：覆盖率 / 一致性 / 饱和度 |
| 过滤 | 规则黑名单 | Pruning / BM25 / LLMContent Filter |
| 集成 | 手工塞 | LangChain Tool / MCP Server |

> 一句话：传统爬虫是体力活，AI 友好爬虫是脑力活。

**核心趋势**：Cloudflare 已对 AI 爬虫分类（搜索爬虫 / AI 训练爬虫 / Agent 爬虫），Agent 爬虫可能需付费；robots.txt 可屏蔽 AI 训练抓取。

> → 实战 Demo: [Demo 10: AI Agent 友好的爬虫](agent_interview_demos/10_web_crawler_agent.py) — Crawl4AI 风格自适应爬虫 + 多层内容过滤

---

### Q60：AI Agent 必备的爬虫能力 / 工具栈？

**回答：**

```
              ┌─ 静态 (requests + BS4)
              ├─ 动态 (playwright / pyppeteer)
抓取引擎 ─────┼─ LLM-friendly (Crawl4AI / Jina Reader / Firecrawl)
              ├─ Agent 自驱动 (AgentBrowser / Browser-Use)
              └─ 协议层 (MCP Server: web-fetch)
```

**反爬对抗 4 要素：**
1. UA 轮换（区分 bot 标识）
2. 频率控制（限速 / 退避）
3. 代理池
4. robots.txt 遵守

**输出格式优先级**：Markdown（结构化 + 节省 Token，Agent 友好） > HTML > 纯文本。

> → 实战 Demo: [Demo 10](agent_interview_demos/10_web_crawler_agent.py) 内部实现了 WebFetcher + Pruning/BM25 双层 Filter + Markdown 输出

---

### Q61：Agentic 时代的爬虫为什么变了？

**回答：**

**三个根本性变化：**

1. **法律层**：robots.txt 可以选择性屏蔽 "AI 训练爬虫"，但允许 "Agent 爬虫"（参考 Google-Extended 标签）
2. **工程层**：爬虫从 "HTML 解析器" 变成 "LangChain Tool" —— Agent 可以决定**何时抓 + 抓哪个 + 是否值得**
3. **商业层**：Cloudflare 等 CDN 已上线 AI Crawl 付费闸门，未来可能形成 "抓取收费 / 越权封锁" 双层格局

**对 Agent 设计的影响：**
- 把爬虫封装为 Tool，并通过 MCP 协议暴露
- 缓存层必备，避免重复抓取
- 失败重试 + 指数退避 + 抓取成本熔断

---

### Q62：什么是 RAG？它解决了大模型的什么问题？

**回答：**

> **RAG = Retrieval-Augmented Generation，检索增强生成。**

解决四个核心问题：
1. **知识截止**：模型不知道训练截止后的新信息
2. **私有数据**：模型不知道企业业务 / 内部文档
3. **幻觉**：减少模型编造答案
4. **可追溯**：回答可附带引用

**一句话本质**：RAG 把 "凭印象回答" 变成 "带资料回答"，让 AI 从黑盒变成可审计白盒。

> → 实战 Demo: [Demo 04: RAG 在 Agent 中的应用](agent_interview_demos/04_agent_rag.py) 已实现 Chroma 向量库 + 多种检索策略

---

### Q63：Naive RAG 的工作流程与失败模式？

**回答：**

**Naive RAG 流程**（固定流水线）：
```
文档 → split → embed → 向量库
                        ↓
query → embed → top-k 检索 → context → prompt → LLM 生成
```

**六大失败模式：**

| 模式 | 表现 | 解法 |
|------|------|------|
| 召回失败 | 真正相关 chunk 没召回来 | Hybrid Search / 扩大 top-k |
| 召回错误 | 召回的多不相关 | Reranker |
| 截断失败 | 长文档切碎丢上下文 | 父子索引 / Late Chunking |
| 整合失败 | 多 chunk 信息冲突 | Adaptive RAG / Agentic |
| 生成失败 | 模型编造 | 强制引用 + Self-RAG |
| 过度依赖 | LLM 用既有知识覆盖 | "I don't know" 拒答能力 |

> 面试官常追问：**"Naive RAG 三大缺陷——检索质量差、生成不忠实、缺乏评估体系"**。

---

### Q64：RAG 的五代演进

**回答：**

| 代际 | 名称 | 关键创新 |
|------|------|----------|
| 1 | **Naive RAG** | 简单 embedding + top-k |
| 2 | **Advanced RAG** | Query Rewrite / HyDE / Hybrid Search / Rerank |
| 3 | **Modular RAG** | 路由 + 检索 + 重排 + 生成 模块可重组 |
| 4 | **GraphRAG** | 实体-关系知识图谱 + 社区检测 + 全局视角 |
| 5 | **Agentic RAG** | Agent 自主决定检索 + 工具 + 验证 |

**2026 年生产级 RAG 标配**：
- 混合检索（向量 + BM25）
- GraphRAG 增强（图推理 + 全局总结）
- Agentic RAG（自主决策 + 校验闭环）
- Contextual Retrieval / Late Chunking（Anthropic 提出的高精度分块）

---

### Q65：Advanced RAG 的五大核心优化

**回答：**

| 优化 | 解决什么 | 工具 |
|------|----------|------|
| **Query Rewrite** | 用户口语 vs 文档专业术语 | LLM 改写 query |
| **Multi-Query + RAG-Fusion** | 单一 query 召回不全 | 3-5 个相似 query + RRF 融合 |
| **HyDE** | query vs doc 维度差 | LLM 生成假设答案再去检索 |
| **Hybrid Search** | 关键词 vs 语义互补 | BM25 + 向量 |
| **Cross-Encoder Rerank** | top-K 精排 | ms-marco / BGE-reranker |

**实战经验（OpenAI 公开案例）**：只用 Rerank + 父子 chunk + 强制引用，就把准确率从 45% 提到 95%。

> → 实战 Demo: [Demo 04](agent_interview_demos/04_agent_rag.py) 已实现 MMR、ContextualCompression、混合搜索

---

### Q66：RRF 融合 + Reranker 为什么是企业级 RAG 标准链路？

**回答：**

**问题**：多路检索结果量纲不同（向量是 0-1 余弦，BM25 是 TF-IDF，MCP 没有分数），无法直接合并。

**RRF (Reciprocal Rank Fusion)** 公式：
```
rrf_score(d) = Σ weight_i / (k + rank_i(d))
```

- 用排名代替分数解决量纲不一致
- k 默认 60（平滑常数），防止第一名垄断
- 实战调参：vector=1.0, HyDE=0.9, MCP=0.7

**Reranker 为什么必须？**
- RRF 按"投票排名"粒度粗
- Cross-Encoder 对 (query, chunk) 做精准二分类打分
- 慢，必须只在 RRF 后的 top-K 上跑
- **GPU 记得设 batch_size**，否则 100 chunk 重排 3+ 秒

> → 实战 Demo: [Demo 12: Agentic RAG](agent_interview_demos/12_agentic_rag.py) 内置简易 Reranker 节点

---

### Q67：Chunk 切片：常见分块方法与实战经验

**回答：**

| 类型 | 切法 | 适用 |
|------|------|------|
| 固定长度 | 按字符 / Token | 通用文本 |
| 段落 / 句子 | 按 `\n\n` / `。` | 结构化叙述 |
| 滑动窗口 | chunk_size + overlap | 长文本保持上下文 |
| 结构化 (Markdown/HTML) | 按 heading / 标签 | 富文档 |
| 语义切片 | 按 embedding 相似度断点 | 主题多变 |
| 父子切片 | Small-to-Big | 法律 / 论文 |
| Late Chunking | tokenize 带上下文分别 embed | 高精度长文档 |

**避坑 3 条**：
- 中文优先按句号 + overlap (10-20%)
- 表格 / 图片 / 代码块不切碎
- 父子索引：索引用小 chunk，召回返回父 chunk

---

### Q68：Routing（路由）在 Modular RAG 中为什么关键？

**回答：**

**两种路由**：
1. **Logical Routing**：LLM 分类，例 "销售额" → 关系库 / "专业术语" → 向量库
2. **Semantic Routing**：query 向量与各数据源 / Prompt 向量匹配，自动路由

**没路由的代价**：每个数据源都拼一份 context，Token 必爆。

**典型架构**：
```
query → Logical 分类
       → 数学题 → 关系库 (Text-to-SQL)
       → 法律问题 → 法律向量库
       → 一般问答 → 通用向量库
```

---

### Q69：Self-RAG / CRAG / Adaptive-RAG / Agentic RAG 核心差异

**回答：**

| 范式 | 反思位置 | 触发方式 |
|------|----------|----------|
| **CRAG (Corrective RAG)** | 检索后、生成前 | 检索后外部纠错 |
| **Adaptive-RAG** | 检索前 | 检索前问题路由 |
| **Self-RAG** | 生成过程内部 | reflection tokens：`[Retrieve]` `[IsRel]` `[IsSup]` `[IsUse]` |
| **Agentic RAG** | 流程外 | LangGraph + Tool + Reflective Loop |

**Self-RAG 工作机制**：
- 模型遇到 `[Retrieve]` token 决定检索
- 检索多篇后并行生成候选
- 每个候选附带 reflection token（document relevance / support / quality）
- beam search 把 reflection 概率纳入打分

**关键差异**：
- CRAG/Adaptive-RAG 是 **"外部模块控制生成"**
- Self-RAG 是 **"模型在生成过程中实时质疑自己"**
- Agentic RAG 是 **"模型驱动工具循环"**

> → 实战 Demo: [Demo 12: Agentic RAG](agent_interview_demos/12_agentic_rag.py) 内置 Reflective Loop

---

### Q70：Claude Code 为什么用 Grep 不用 Code RAG？

**回答：**

**Code RAG 的失败模式**：
- 函数定义 / 调用经常跨文件
- 代码 RAG 索引跟不上代码更新
- 局部代码片段不足以解决逻辑问题

**Claude Code 方案 (Agentic Search)**：
- 模型自己驱动 Glob / Grep 工具
- 每步只抓必要文件 / 函数
- 每次搜索基于上一步动态调整
- RAG 仅作为"代码库语义搜索"辅助

> **关键洞察**：RAG 不是被淘汰，而是从"替代工具调用"变成"辅助工具调用"。

> → 设计参考: [Demo 12](agent_interview_demos/12_agentic_rag.py) 中 `WebSearchTool` 即用类似模式

---

### Q71：GraphRAG 和传统 RAG 的核心区别？

**回答：**

> **关键答：数据组织形式不同！**
> 传统 RAG = "文本片段检索"
> GraphRAG = "实体-关系结构化图谱检索"

| 维度 | Classic RAG | GraphRAG |
|------|-------------|----------|
| 数据形式 | 文本切片 | 实体-关系-三元组 |
| 检索粒度 | chunk 相似度 | 子图路径 / 社区摘要 |
| 擅长 | 单步语义匹配 | 多跳推理 / 全局总结 |
| 数据组织 | 扁平行式 | 图结构 + 社区聚类 |
| 命中率 | 段落级 | 实体级 + 关系级 |
| 案例 | "找某段文字" | "A 公司 → 供应链 B → 违规担保 C" |

> → 实战 Demo: [Demo 11: GraphRAG](agent_interview_demos/11_graph_rag.py) 包含完整实体抽取 → 建图 → 社区检测 → 子图查询

---

### Q72：GraphRAG 工作流程？

**回答：**

**索引阶段：**
```
原始文档 → LLM 抽取实体 / 关系 (三元组) → 构建知识图谱
        → Leiden / Louvain 社区检测 → 生成社区摘要
```

**查询阶段：**
```
用户提问 → 判断问题类型
        ├─ 全局总结 → 检索社区摘要 → LLM 综合
        └─ 实体查询 → 图上 1-2 跳路径 + 向量兜底 → Reranker → 生成
```

**关键细节**：
- 社区检测用 Leiden（比 Louvain 稳定）
- 子图用 YAML/Markdown 喂 LLM（Token 密度更高）
- 兜底必须用向量检索，因为图不擅长模糊语义

> → 实战 Demo: [Demo 11](agent_interview_demos/11_graph_rag.py) 自实现标签传播 + 社区摘要 + 子图 BFS

---

### Q73：何时必须用 GraphRAG？

**回答：**

| 场景 | 该用什么 |
|------|----------|
| FAQ / 政策查询 / 产品手册 | Classic RAG |
| 组织关系 / 供应链 / 审批链 | **GraphRAG** |
| 依赖分析 / 影响范围 | **GraphRAG** |
| 多跳推理 / 全局总结 | **GraphRAG** |
| 跨系统调查 / 归因分析 / 路径不确定 | **Agentic RAG** |

**回答模板**：
> "我先看答案在哪一类问题域：
> - 段落级 → Classic RAG 就够
> - 多跳推理 → 上 GraphRAG
> - 路径不确定 → 让 Agentic RAG 自己挑"

> → 实战 Demo: [Demo 11](agent_interview_demos/11_graph_rag.py) 内置 `_is_global_question` 自动判断走全局 vs 子图查询

---

### Q74：GraphRAG 工业级 9 大避坑

**回答：**

| # | 坑 | 解决 |
|---|----|------|
| 1 | 原生 GraphRAG 全量重构代价大 | LightRAG / FalkorDB 增量索引 |
| 2 | GPT-4 抽取成本爆炸 | 微调 Qwen2.5-IE 等 7B/3B |
| 3 | 实体对齐失败（"马云" vs "Jack Ma"） | Embedding + LLM 二次清洗 + 社区检测 |
| 4 | Schema-Free 抽取关系爆炸 | 先自由跑 + 再固化 Schema |
| 5 | 2-Hop 邻居一股脑塞 LLM | 语义剪枝：Query vs 边属性相似度 |
| 6 | 子图用自然语言塞 LLM | 改 YAML / Markdown 列表 |
| 7 | Graph 替代 Vector | 错！两者互补，RRF 融合 |
| 8 | 没有数据血缘 | 边刻 Source Doc ID + Chunk ID |
| 9 | 图片 Base64 入图库 | 对象存储 + 向量存 Embedding + 图存元数据 |

> → 实战 Demo: [Demo 11](agent_interview_demos/11_graph_rag.py) 已实现实体对齐（`_normalize`）和子图剪枝（邻居距离排序）

---

### Q75：什么是 Agentic RAG？和 Naive RAG 区别

**回答：**

> **关键答**：Agentic RAG 不是 "更高级的 RAG"，而是**让检索从固定流程变成了智能决策**。

| 维度 | Naive/Classic RAG | Agentic RAG |
|------|-------------------|--------------|
| 检索触发 | 必然 1 次 | 模型判断 "需不需要" |
| 检索次数 | 固定 1 次 | 模型决定几次 |
| 工具调用 | 无 | 可调用 SQL / Graph / Web |
| 验证 | 无 | 模型验证证据是否充足 |
| 适合 | FAQ / 简单问答 | 企业知识库 / 论文分析 / 客服工单 |

> 一句话：**Agentic RAG 不是让模型"多查一点资料"，而是让模型学会"如何使用资料"。**

> → 实战 Demo: [Demo 12: Agentic RAG](agent_interview_demos/12_agentic_rag.py) 演示了自主决策 → Reflective Loop → Verify 闭环

---

### Q76：Self-RAG、CRAG、Corrective RAG 的核心差异

**回答：**

| 范式 | 反思位置 | 触发方式 | 训练成本 |
|------|----------|----------|----------|
| **CRAG** | 检索之后、生成之前 | 检索后做外部纠错 | 无（流程级） |
| **Adaptive-RAG** | 检索之前 | 检索前做问题路由 | 无（流程级） |
| **Self-RAG** | 生成过程内部 | reflection tokens 内嵌 | 高（必须训练） |
| **Agentic RAG** | 流程外 | LangGraph 编排 | 无（流程级） |

**Self-RAG 三大代价**：
- 必须专门训练
- reflection tokens 会频繁触发检索，延迟高
- 判断能力继承 GPT-4 标注偏差

> **实战选择**：无训练预算 / 想快速上线 → 选 Agentic RAG；论文 / 学术研究 → 选 Self-RAG；老系统改造 → 加 CRAG。

---

### Q77：Agentic RAG 的 LangGraph 实现思路

**回答：**

**最小化图**：
```
[Router] → [Step(Node: vector/graph/web/rerank/generate/verify)] → ... → [Finish] → END
```

**Demo 12 的实现关键**：
1. **Router**：根据问题关键词判断 `qtype=local / multi_hop / global`，生成 `plan = [vector_rag, rerank, generate, verify, ...]`
2. **Step Dispatcher**：单一节点根据 `plan[plan_idx]` 决定执行哪一个动作
3. **Verify 触发 Reflective Loop**：校验不通过时往 plan 追加新轮 `[vector_rag, rerank, generate, verify]`
4. **MemorySaver checkpoint**：支持人工介入与时间旅行回放

**关键工程经验**：
- 工具白名单（防止 Agent 越权）
- max_iterations 熔断（防止死循环）
- Verify 节点既统计引用数，又调用 LLM-as-Judge

> → 实战 Demo: [Demo 12](agent_interview_demos/12_agentic_rag.py) 完整可跑

---

### Q78：Agentic RAG 项目经验怎么讲？

**回答：**

**万能四段论**：

```text
1. 场景：企业级多租户 / 高 QPS / 合规要求
2. 架构：Hybrid Search + Cross-Encoder Rerank + LangGraph 编排
   → Router (qtype) → Tools(vector/graph/web) → Reranker → Generator → Verifier
3. 关键设计：
   - 工具白名单 + Reflective Loop（避免死循环 + 幻觉）
   - 强制输出 [N] 引用 + LLM-as-Judge 双重校验
   - max_iterations 熔断 + 时间旅行（人工介入）
4. 评估指标：
   - Faithfulness / Context Precision / Answer Relevancy
   - LLM-as-Judge + 人工抽检
   - 日志回放 + A/B 测试
```

**加分点**：
- 提到 Ragent AI / RAGFlow 等开源项目
- 提到 GraphRAG + Agentic RAG 的融合（graph 提供 entity 索引，agentic 提供决策）
- 提到 Self-RAG 的反思 token 思想（reflection tokens）
- 提到 Claude Code 的"agentic search"经验（用工具而非 RAG 替代）

> → 综合演示: [Demo 12](agent_interview_demos/12_agentic_rag.py) + [Demo 11](agent_interview_demos/11_graph_rag.py) 构成完整答案

---

### Q59-Q78 速查表

| Q编号 | 主题 | 关键答案 | Demo |
|------|------|---------|------|
| Q59 | AI 友好爬虫 vs 传统 | 面向语义 vs 标签 | [Demo 10](agent_interview_demos/10_web_crawler_agent.py) |
| Q60 | Agent 必备爬虫栈 | requests + Crawl4AI + MCP | [Demo 10](agent_interview_demos/10_web_crawler_agent.py) |
| Q61 | Agentic 时代爬虫变化 | CDN 分类 + 协议化 | [Demo 10](agent_interview_demos/10_web_crawler_agent.py) |
| Q62 | 什么是 RAG | 检索增强生成 | [Demo 04](agent_interview_demos/04_agent_rag.py) |
| Q63 | Naive RAG 失败模式 | 召回/生成/截断/整合 | [Demo 04](agent_interview_demos/04_agent_rag.py) |
| Q64 | RAG 五代演进 | Naive→Advanced→Modular→Graph→Agentic | [Demo 11](agent_interview_demos/11_graph_rag.py) + [Demo 12](agent_interview_demos/12_agentic_rag.py) |
| Q65 | Advanced RAG 5大优化 | Query Rewrite / HyDE / Multi-Query | [Demo 12](agent_interview_demos/12_agentic_rag.py) |
| Q66 | RRF + Reranker | 排名融合 + Cross-Encoder | [Demo 12](agent_interview_demos/12_agentic_rag.py) |
| Q67 | Chunk 切片 | 滑动 / 结构化 / 父子 / Late | [Demo 04](agent_interview_demos/04_agent_rag.py) |
| Q68 | 路由在 Modular RAG | Logical / Semantic | [Demo 12](agent_interview_demos/12_agentic_rag.py) |
| Q69 | Self-RAG/CRAG/Adaptive/Agentic | 反思位置差异 | [Demo 12](agent_interview_demos/12_agentic_rag.py) |
| Q70 | Claude Code 为什么不用 Code RAG | Agentic Search 替代 | [Demo 12](agent_interview_demos/12_agentic_rag.py) |
| Q71 | GraphRAG vs RAG | 数据形式不同 | [Demo 11](agent_interview_demos/11_graph_rag.py) |
| Q72 | GraphRAG 工作流程 | 索引+查询两阶段 | [Demo 11](agent_interview_demos/11_graph_rag.py) |
| Q73 | 何时用 GraphRAG | 多跳 / 全局 | [Demo 11](agent_interview_demos/11_graph_rag.py) |
| Q74 | GraphRAG 9 大避坑 | 小模型抽取 / 实体对齐 | [Demo 11](agent_interview_demos/11_graph_rag.py) |
| Q75 | 什么是 Agentic RAG | 自主决策检索 | [Demo 12](agent_interview_demos/12_agentic_rag.py) |
| Q76 | Self-RAG/CRAG/Agentic 差异 | 反思位置 | [Demo 12](agent_interview_demos/12_agentic_rag.py) |
| Q77 | Agentic RAG LangGraph 实现 | Router→Step→Verify | [Demo 12](agent_interview_demos/12_agentic_rag.py) |
| Q78 | Agentic RAG 项目经验 | 四段论 | [Demo 12](agent_interview_demos/12_agentic_rag.py) |

---

> *本篇章为爬虫 / RAG / GraphRAG / AgenticRAG 专题。完整面试题库涵盖 19 章节、78 道问答。*
> 本章节 Q59-Q78 共 20 题，对应新增 3 个 Demo (10/11/12)，覆盖了从数据采集到检索增强再到智能体化决策的完整链路。*
