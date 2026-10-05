# 爬虫 + RAG + GraphRAG + AgenticRAG 面试题整理

> 跨 X/Twitter、微信公众号、小红书三平台的爬取与检索增强生成专题面试题。
> 整理日期：2026-07-04

---

## 目录

- 一、爬虫与 LLM 友好的数据采集
- 二、Classic RAG / Naive RAG
- 三、Advanced RAG / Modular RAG
- 四、GraphRAG 知识图谱检索
- 五、Agentic RAG 智能体化检索
- 六、向量数据库与 Embedding
- 七、RAG 评估与幻觉抑制
- 八、来源索引

---

## 一、爬虫与 LLM 友好的数据采集

### 1.1 普通爬虫和 "AI Agent 友好的爬虫" 有什么区别？
*来源：小红书 / 汤圆键盘坏了不能写论文 -《开源智能爬虫框架：Crawl4AI的快速入门》*

传统爬虫的痛点：
- 脆弱的选择器（CSS / XPath）：网站一改版，所有选择器全作废
- 动态加载 / JS 交互：永远点不完的 "加载更多"
- 抽样 "黑盒"：滚雪球抽样该滚到第几层无法判断
- 语料噪声：HTML 含广告 / 导航，洗数据耗费 80% 时间

AI 友好的爬虫范式（Crawl4AI 为代表）：
- 用 `LLMExtractionStrategy` + Pydantic Schema "描述" 你想要的数据（如 `{作者, 标题, 摘要}`），LLM 自己 "理解" 非结构化网页
- `AdaptiveCrawler` 围绕研究问题实时评估：覆盖度 (Coverage)、一致性 (Consistency)、饱和度 (Saturation)，模型判断 "饱和" 就自动停止
- 多层过滤器：
  - `PruningContentFilter`：基于文本 / 链接密度评分
  - `BM25ContentFilter`：基于查询相关性过滤
  - `LLMContentFilter`：基于 LLM 指令的 "外科手术式" 提取
- 输出干净的 `fit_markdown`，可直接灌进 RAG

> 一句话：传统爬虫面向 HTML 标签体力活，AI 爬虫面向语义与目标脑力活。

### 1.2 Agent 必备的爬虫能力 / 工具栈？
*来源：微信公众号 /《LangChain进阶 | 用Crawl4AI给AI Agent装"爬虫大脑"》、零代码 AgentBrowser*

| 工具 | 用法 |
|------|------|
| `requests` + `BeautifulSoup` | 静态 HTML 抓取 + 选择器解析 |
| `playwright` / `pyppeteer` | JS 动态页面 / 交互 |
| `Crawl4AI` | LLM 友好抓取，自动输出 Markdown |
| `Jina Reader` / `Firecrawl` | 把网页转 LLM 原生可读格式 |
| `SerpAPI` / `Bing Search API` | 搜索引擎结果 API |
| `AgentBrowser` | Agent 自动生成元素引用 ID，自动交互 |
| MCP Server (web-fetch) | 通过 MCP 协议暴露网页抓取工具 |

设计原则：
- 输出格式优先 Markdown（结构化 + 节省 Token）
- 内置反爬对抗（UA 轮换、限速、代理池）
- 失败重试 + 指数退避
- 增量抓取（基于 ETag / Last-Modified）

### 1.3 Cloudflare / 付费爬虫时代对 Agent 意味着什么？
*来源：微信 /《Cloudflare给AI爬虫装上收费闸门》、《07·02 - AI 午报》*

- Cloudflare 已上线 AI 爬虫付费闸门，区分传统搜索爬虫 / AI 训练爬虫 / Agent 爬虫三类
- 法律上：网站可借 `robots.txt` 屏蔽 AI 训练抓取
- 工程上：Agent 需要支付、按规范爬取（UA 标识 User-Agent）
- 业务上：未来 Agent 服务方需提供 robots / 付费 API

---

## 二、Classic RAG / Naive RAG

### 2.1 什么是 RAG？它解决了大模型的什么问题？
*来源：微信 /《RAG基础入门 | 面试高频问题 (2026 版)》、《AIGC 大模型面试高频考点-RAG篇》、小红书 / 小瑜的AI实战笔记*

定义：
> RAG = Retrieval-Augmented Generation，检索增强生成。由 2 部分构成：一是离线对异构数据进行数据工程处理成知识并存储在知识库中，二是基于用户检索在线召回知识后辅助大模型生成更可靠的答案。

解决的核心问题：
1. **知识截止**：模型不知道训练截止后的新信息
2. **私有数据**：模型不知道企业 / 业务 / 个人文档
3. **幻觉**：减少模型编造答案
4. **可追溯**：回答可附带引用，便于审查

> RAG 系统评估需关注**检索、生成一致性及系统整体性能**。通过 Recall、Precision、Faithfulness 等指标，结合人工评测，确保系统稳定、准确、可复现。

### 2.2 Naive RAG 流程？为什么面试官嫌弃它？
*来源：微信公众号 /《RAG基础入门》2026版、GC.《大模型岗位面试题系列图文 第四集 Rag知识库》、《大厂面试必考：RAG 怎么答才能让面试官觉得你"深不可测"》*

Naive RAG = `embedding → 向量库 → top-k 召回 → 拼到 prompt → LLM 生成`

但它的失败模式也很经典：
| 失败模式 | 表现 |
|----------|------|
| 召回失败 (Missed Retrieval) | 真正相关的 chunk 没召回来 |
| 召回错误 (Low Precision) | 召回的 chunk 多数不相关 |
| 截断 (Truncation) | 长文档切碎后丢失上下文 |
| 整合失败 | 多 chunk 信息冲突 / 冗余 |
| 生成失败 | LLM 编造 / 没引用证据 |
| 过度依赖 | LLM 用已有知识覆盖检索内容 |

> 面试官频繁追问的核心点：Naive RAG 三大缺陷——**检索质量差、生成不忠实、缺乏评估体系**。

### 2.3 RAG 的五代演进
*来源：小红书 / 白梦猿《【AI八股文】RAG进阶优化：从 Naive RAG 到 Agentic RAG》*

| 代际 | 名称 | 关键创新 |
|------|------|----------|
| 1 | Naive RAG | 简单的 embedding + top-k + prompt |
| 2 | Advanced RAG | Query Rewrite、HyDE、Hybrid Search、Rerank、Small-to-Big |
| 3 | Modular RAG | 各模块（路由 / 检索 / 重排 / 生成）可插拔重组 |
| 4 | GraphRAG | 实体 + 关系知识图谱 + 社区检测 + 全局视角 |
| 5 | Agentic RAG | Agent 自主决定 "要不要检索 / 查哪个 / 查几次"，并能调用工具 + 验证证据 |

2026 年生产级 RAG 须混合检索 + Graph 推理 + Agent 决策，结合 Contextual Retrieval、Late Chunking 等技术。

---

## 三、Advanced RAG / Modular RAG

### 3.1 Retrieval 五大优化手段
*来源：小红书 / Orlando Liu《进阶RAG学习笔记》、永远天真《RRF融合+重排序》*

| 优化 | 解决什么 |
|------|----------|
| **Query Rewrite** | 用户口语化提问 vs 文档专业术语鸿沟 |
| **Multi-Query + RAG-Fusion** | 单一查询召回不全，多视角融合 |
| **HyDE (Hypothetical Document Embeddings)** | 先让 LLM 生成假设答案，再拿假设答案去检索 |
| **Hybrid Search (BM25 + Vector)** | 关键词和语义互补 |
| **Cross-Encoder Rerank** | 在 top-K 候选上精细语义重排 |

补充查询构建场景：
- 关系型数据库 → Text-to-SQL
- 图数据库 → Text-to-Cypher
- 向量数据库 → Self-Query Retriever（生成 metadata filter）

### 3.2 路由 (Routing) 是什么？为什么是 Modular RAG 的关键？
*来源：小红书 / Orlando Liu《进阶RAG学习笔记》*

两种路由：
1. **Logical Routing**：LLM 分类，把 "销售额" 路由到关系库，把 "专业术语" 路由到向量库
2. **Semantic Routing**：查询向量与各数据源 / Prompt 向量匹配，自动将医疗、法律等专业问题路由到对应领域向量库

> 没有路由，每个数据源都会拼一份上下文，Token 爆掉；有了路由，每个查询只问对的人。

### 3.3 Chunk 策略：常见分块方法与避坑
*来源：小红书 / 安浩夕《RAG 切片切不对，检索全白费》、马诚《RAGFlow 提供的 11 种文档切片方法》、曚曚《超级干货 RAG攻克切片难题》、赛博玄烨《chucking 的几种方式》*

常见切片方法：
| 类型 | 切法 | 适用 |
|------|------|------|
| 固定长度 | 按字符 / Token 数 | 通用文本 |
| 段落 / 句子 | 按 `\n\n` / `。` 切 | 结构化叙述 |
| 滑动窗口 (Overlap) | chunk_size + chunk_overlap | 长文本保持上下文 |
| 结构化 (Markdown/HTML) | 按 heading / 标签 | 富文档 |
| 语义切片 | 按 embedding 相似度断点 | 主题多变的文档 |
| 父子切片 | Small-to-Big：索引小块、返回大块 | 法律 / 论文 |
| Late Chunking | 先把整篇 tokenize，带上下文分别 embed | 高精度长文档 |

实战经验：
- chunk_size 默认 256~512，重叠 10~20%
- 中文文档优先按句号切 + overlap
- 表格 / 图片 / 代码块尽量不切碎
- 父子索引：chunk 索引用 "小块"，检索后返回 "父块" 拼接

### 3.4 RRF + Reranker：企业级 RAG 的标准链路
*来源：小红书 / 永远天真《RRF融合+重排序，面试官说这就是企业级RAG》*

为什么要 RRF 融合？
- 向量检索返回 0-1 的余弦
- BM25 返回 BM25 score
- MCP 搜索根本没有相似度分数
- 直接相加量纲混乱

RRF 公式：`rrf_score = weight / (k + rank)`
- 用排名代替分数解决量纲问题
- 默认 `k=60`，防止第一名垄断
- 调参经验：`weight 向量=1.0、HyDE=0.9、MCP=0.7`
- 每路取 top-20，融合后再去重

为什么要 Reranker？
- RRF 融合按 "投票排名" 来排序，粒度太粗
- 用 Cross-Encoder 对 (query, chunk) 做精准二分类打分
- 但 Cross-Encoder 慢，所以只在 RRF 后的 top-K 上跑

> 踩坑：模型上 GPU 后一定要设 `batch_size`，否则 100 chunk 重排要 3 秒多。

### 3.5 OpenAI 把 RAG 准确率从 45% 提到 95% 的核心做法
*来源：小红书 / 发光的卡罗《OpenAI 如何将 RAG 的准确率由 45% 提升至...》*

技术细节：
1. **滑动窗口 + 父子 chunk**：建索引用小 chunk，召回用其父级 chunk 补充上下文
2. **Rerank 模型**：对 top-K 候选做精细重排
3. **Prompt 压缩 + 引用强制**：让 LLM 引用 chunk ID，防止幻觉
4. **评测闭环**：每改动都跑 Recall@K / Faithfulness 自动评测

### 3.6 Agentic Search vs RAG：Claude Code 为什么用 Grep？
*来源：微信 / 《Claude Code 为什么"只用 Grep、不碰 Code RAG"?》*

核心观点：传统 Code RAG 的失败模式：
- 函数定义 / 调用 / 实现常常跨多个文件
- 代码 RAG 索引跟不上代码更新
- 局部代码片段不足以解决逻辑问题

Claude Code 的方案：
- 用 Agentic Search，由模型自己驱动 Glob / Grep 工具
- 每步只抓必要的几个文件 / 函数
- 每次搜索都基于上一步的结果动态调整
- 保留 RAG 价值但仅用于 "代码库层面的语义搜索"，不用它替代工具调用

> 关键洞察：**RAG 不是被淘汰了，而是从"替代工具调用"变成"辅助工具调用"**。

---

## 四、GraphRAG 知识图谱检索

### 4.1 GraphRAG 和传统 RAG 的核心区别？
*来源：小红书 / 大模型学习狗《大模型面试必背！GraphRAG 核心考点》、丁师兄大模型《什么场景下必须用 GraphRAG？而不是 RAG？》*

> **关键答：数据组织形式不同！传统 RAG 是"文本片段检索"，GraphRAG 是"实体-关系结构化图谱检索"，多跳推理和关联挖掘能力碾压前者**。

| 维度 | Classic RAG | GraphRAG |
|------|-------------|----------|
| 数据形式 | 文本切片 | 实体-关系-三元组 |
| 检索粒度 | chunk 相似度 | 子图路径 / 社区摘要 |
| 擅长 | 单步语义匹配 | 多跳推理 / 全局总结 |
| 数据组织 | 扁平行式 | 图结构 + 社区聚类 |
| 命中案例 | "找某段文字" | "A 公司 → 供应链 B → 违规担保 C" |

### 4.2 GraphRAG 的工作流程？
*来源：大模型学习狗（小红书）、微信 / 《从知识图谱到 GraphRAG》、《三十八：GraphRAG》*

**索引阶段：**
```
原始文档 → LLM 抽取实体 / 关系 (三元组) → 构建知识图谱 (Neo4j / NetworkX)
        → Leiden / Louvain 社区检测 → 生成社区摘要
```

**查询阶段：**
```
用户提问 → 判断问题类型 (全局总结 vs 实体查询)
        → 全局：检索社区摘要 → LLM 综合
        → 局部：图上走 1-2 跳路径 + 向量兜底 → Reranker 排序
        → 结构化信息喂给 LLM 生成
```

> 面试加分：在 GraphRAG 上混合检索 "向量兜底"，因为 GraphRAG 不擅长模糊语义召回。

### 4.3 何时必须用 GraphRAG？
*来源：小红书 / Hp-AI宝藏库《一文看懂三种 RAG 架构》、丁师兄大模型*

| 场景 | 该用什么 |
|------|----------|
| FAQ / 政策查询 / 产品手册 | Classic RAG |
| 组织关系 / 供应链 / 审批链 | GraphRAG |
| 依赖分析 / 影响范围 | GraphRAG |
| 跨系统调查 / 归因分析 / 路径不确定 | Agentic RAG |

> 一句话：Classic RAG 找资料，Graph RAG 找关系，Agentic RAG 决定下一步。

### 4.4 GraphRAG 的工业级 9 条避坑
*来源：小红书 / 红鲤鱼与胖头鱼《什么是 GraphRAG？知识图谱如何增强 RAG》*

| # | 坑 | 解决 |
|---|----|------|
| 1 | 原生 GraphRAG 必须全量重构，T+0 实时性差 | 改用 LightRAG / FalkorDB 增量索引 |
| 2 | 用 GPT-4 跑全量实体抽取，成本爆炸 | 微调 7B / 3B（如 Qwen2.5-IE），效果接近，成本 1/50 |
| 3 | 实体对齐失败，"马云" 和 "Jack Ma" 不合并 | Embedding 相似度 + LLM 二次清洗 + 社区检测 |
| 4 | Schema-Free 抽取导致关系类型爆炸 | 先自由跑 + 再固化 Schema |
| 5 | 2-Hop 邻居一股脑塞 LLM，Token 爆 | 语义剪枝：计算 Query 与边属性相似度 |
| 6 | 子图用自然语言塞给 LLM | 改用 YAML / Markdown 列表，结构化提示更省 Token |
| 7 | Graph 替代 Vector | 错！两者互补，Vector 模糊 + Graph 精准，RRF 融合 |
| 8 | 没有数据血缘 | 边必须刻 Source Doc ID + Chunk ID，否则增量更新灾难 |
| 9 | 图片 Base64 入图数据库 | 对象存储存原图 + 向量库存 Embedding + 图库存元数据 |

### 4.5 微软 GraphRAG vs LightRAG vs FalkorDB
*来源：小红书 / 红鲤鱼与胖头鱼*

| 方案 | 优势 | 劣势 |
|------|------|------|
| 微软 GraphRAG | 社区摘要强 | 全量重构代价大，T+0 实时差 |
| LightRAG | 增量索引、低成本 | 社区摘要质量略弱 |
| FalkorDB | 高性能图数据库 | 部署复杂，需 Redis |

### 4.6 自建 GraphRAG 的工程经验
*来源：小红书 / 寻找意义《被面试官问爆的 GraphRAG，我把它搭出来了》*

真实案例：
```
老板问：A 公司投资了哪些做 AI 的初创公司？
- Classic RAG：搜到 10 篇提到 A 公司的文章，翻半天理不清关系
- GraphRAG：直接在图里走投资关系路径，几秒钟出答案
```

构建实战要点：
1. **省钱两步走**：先用 spaCy 粗筛，再送大模型精抽，省 60% 成本
2. **多跳查准提升**：GraphRAG 78% vs 传统 RAG 52%
3. **响应时间**：2.5 秒以内
4. **不要梭哈**：简单问题普通 RAG，复杂推理上 GraphRAG

### 4.7 智谱数开一面原题
*来源：微信 / 《智谱数开一面：GraphRAG用过吗？和 RAG 到底有什么区别？》*

面试官高频追问：
1. 你的业务为什么不用 Naive RAG？
2. GraphRAG 怎么抽取实体？怎么对齐？怎么更新？
3. 用了哪款图数据库？Neo4j / JanusGraph / FalkorDB？为啥？
4. 怎么评估 GraphRAG 的效果？和向量检索能 A/B 吗？
5. LightRAG 和 GraphRAG 区别？增量索引怎么做的？

---

## 五、Agentic RAG 智能体化检索

### 5.1 什么是 Agentic RAG？
*来源：小红书 / Antique《面试官问：什么是Agentic RAG？》、微信 /《三十九：Agentic RAG》*

> 很多人以为 Agentic RAG 只是 "更高级的 RAG"，其实它真正的变化是**让检索从固定流程变成了智能决策**。

对比：
| 维度 | Naive/Classic RAG | Agentic RAG |
|------|-------------------|--------------|
| 检索触发 | 必然 | 模型判断 "需不需要" |
| 检索次数 | 固定 1 次 | 模型决定几次 |
| 工具调用 | 无 | 可调用 SQL / Graph / Web |
| 验证 | 无 | 模型验证证据是否充足 |
| 适合 | FAQ / 简单问答 | 企业知识库 / 论文分析 / 客服工单 / 数据分析 |

> 一句话：**Agentic RAG 不是让模型 "多查一点资料"，而是让模型学会 "如何使用资料"**。

### 5.2 Self-RAG、CRAG、Corrective RAG 的核心差异
*来源：小红书 / 鹿桃桃《从0到1学RAG（五）Self-RAG详解》、硅谷刘老师《Self-RAG vs CRAG 对比》*

| 范式 | 反思位置 | 触发方式 |
|------|----------|----------|
| **CRAG (Corrective RAG)** | 检索之后、生成之前 | 检索后做外部纠错，重写 query 后再检索 |
| **Adaptive RAG** | 检索之前 | 检索前做问题路由 |
| **Self-RAG** | 生成过程内部 | 模型在生成 token 的同时输出 `[Retrieve]` / `[IsRel]` / `[IsSup]` / `[IsUse]` reflection tokens |

Self-RAG 工作机制：
- 模型先决定要不要检索（`[Retrieve]` token）
- 检索到多篇文档，模型并行生成候选段落
- 每个候选都附带 "文档是否相关 / 内容是否有支撑 / 答案质量如何" 等判断
- 最后 segment-level beam search，把 reflection token 概率纳入打分

关键差异：
- CRAG/Adaptive-RAG 是 "外部模块控制生成"
- Self-RAG 是 "模型在生成过程中实时质疑自己"
- Self-RAG 适合事实准确性要求高 / 长文本 / 多轮补充知识
- 代价：必须专门训练，reflection tokens 会频繁触发检索和多路径生成，推理延迟高

### 5.3 Agentic RAG 的 LangGraph 实现思路
*来源：微信 /《Claude Code 为什么"只用 Grep、不碰 Code RAG"》、Ragent AI 开源项目*

典型图：
```
[Query]
   ↓
[Router]   -- 判断需要哪个数据源
   ↓                ↓
[向量检索] / [Graph 检索] / [Web 检索]
   ↓
[Reranker]  -- 融合排序
   ↓
[Generator] -- 引用证据生成
   ↓
[Verifier]  -- 校验引用是否支撑结论
   ↓ (不支撑)
   ↓ (返回 Router 重查)
   ↓ (支撑)
[Output]
```

### 5.4 Agentic RAG 项目经验怎么讲？
*来源：微信 /《耗时半年我开源了一套企业级 RAG 智能体：Ragent AI》、《AI 午报: Claude Fable 5 恢复》*

项目回答模板：
1. **业务场景**：企业级 / 多租户 / 高 QPS
2. **架构选型**：GraphRAG + Hybrid Search + Cross-Encoder Rerank
3. **Agent 决策**：Tool Router + Reflective Loop + 工具白名单
4. **评估**：Faithfulness / Recall@K / LLM-as-Judge
5. **坑**：向量召回幻觉、实体对齐、对抗 prompt 注入
6. **落地数据**：检索准确率 / 响应时间 / 成本下降

### 5.5 Claude Fable 5 / AI 午报：Agent 时代下的 RAG 走向
*来源：微信 /《07·02 - AI 午报: Claude Fable 5 恢复，AI 爬虫与算力分发进入计费时代》*

- Claude Code 这类 Agent 偏向 "agentic search"，由模型驱动工具调用而非全套 RAG 索引
- RAG 不是被淘汰，而是从 "替代搜索" 变成 "辅助决策"
- 工程上：Agentic RAG + Tool Use 走向统一接口（MCP）

---

## 六、向量数据库与 Embedding

### 6.1 Embedding 为什么能做语义检索？
*来源：小红书 / 薯条Coding《面试被问"什么是Embedding"答不上来？》、AI旅行者《Embedding 凭啥能做语义检索？》*

流程：
```
文本 → 切分 → 向量化 (Embedding) → 存入向量库 → 用户查询 → 向量化 → 相似度检索 (ANN) → 返回相关文档
```

6 个核心要点：
1. **是什么**：把文本变成定长稠密向量，语义近的在向量空间里距离也近
2. **为啥用余弦**：向量模长受文本长度影响，余弦只看方向不看长度
3. **怎么快**：百万级用 ANN 索引（HNSW 最主流、IVF 聚类分桶）
4. **怎么省内存**：PQ / SQ 量化
5. **混合检索**：稠密 + 稀疏 (BM25) 互补
6. **评估**：用相关性数据集做 Recall@K

### 6.2 主流 Embedding 模型怎么选？
*来源：小红书 / Agent_KK《RAG Embedding 到底怎么选？》、海龟老师《一文说清，什么是 Embedding？如何选模型》、六哥聊AI《面试官：如何判断一个 Embedding 的质量？》*

| 模型 | 维度 | 优势 |
|------|------|------|
| OpenAI text-embedding-3-small | 1536 | 通用、多语言平衡 |
| BAAI/bge-large-zh | 1024 | 中文效果好 |
| m3e-large | 1024 | 中文多任务 |
| BGE-M3 | 1024 | 多语言 + 多粒度 + 多功能 |
| Cohere embed-v3 | 1024 | 检索 + 分类 |
| Qwen3-Embedding | 1024 | 多语言 SOTA |

评估 Embedding 质量：
- 用相关性标注数据集（如 BEIR / CMRC / T2Ranking）
- 计算 Recall@K / NDCG@10 / MRR
- 关注中文、长文本、对称 vs 非对称任务差异

### 6.3 向量数据库技术内幕
*来源：小红书 / AI旅行者、顺丰"向量数据库 DBA"岗位面试攻略*

| 索引 | 复杂度 | 适用规模 | 召回率 |
|------|--------|----------|--------|
| 暴力 (Flat) | O(N) | <10k | 100% |
| IVF | O(√N) | 100k-10M | ~95% |
| HNSW | O(log N) | <100M | ~99% |
| PQ / SQ 量化 | -- | >100M | ~95% |

> 工程经验：HNSW 是工业界默认；量化通常是把内存压 4-10 倍。

### 6.4 向量数据库 DBA 岗面经核心
*来源：小红书 / 顺丰"向量数据库 DBA"面试攻略、小鹏汽车向量数据库 DBA*

高频考点：
- HNSW 与 IVF 的差异、各自优缺点
- 量化（PQ/SQ）原理和适用场景
- 元数据过滤（pre-filter / post-filter）
- 分布式方案（分片、副本、一致性）
- 向量召回与传统 SQL 的融合（Hybrid Search）
- 千万 / 亿级数据的索引构建耗时

---

## 七、RAG 评估与幻觉抑制

### 7.1 RAG 评估要测哪些指标？
*来源：小红书 / 闭眼拿下大模型 offer《面试官问：RAG 的评估体系怎么做？》、小哲讲大模型《如何真正抑制大模型幻觉》*

| 维度 | 指标 |
|------|------|
| 检索 | Recall@K、MRR、NDCG、Hit Rate |
| 生成 | Faithfulness、Answer Relevancy |
| 幻觉 | Context Precision、Context Recall |
| 工程 | Latency、Token 成本、QPS、可用性 |
| 业务 | CSAT、人工抽检合格率 |

评估方法：
- 自动指标：BLEU、ROUGE、BertScore
- LLM-as-Judge：GPT-4 评分（注意偏差）
- 人工评测：金标准

### 7.2 RAG 如何真正抑制大模型幻觉？
*来源：小红书 / 小哲讲大模型*

> 面试如果只答 "改 Prompt" 就太浅了。真实抑制幻觉需要**分层防线**：

```
事实性幻觉：模型编造不存在的事实
   ↓
忠实性幻觉：模型回答与检索文档不一致
   ↓
工程防御 (按层级)：
  1. 检索层：扩大召回 (混合检索 + Rerank)
  2. 生成层：prompt 强制引用 + 拒答能力
  3. 校验层：双重核对 (LLM-as-Judge + 事实核查)
```

工程具体动作：
- 强制要求 LLM 输出 `[Doc-id, Sentence]` 引用
- 对置信度低的结果拒答 "我不知道"
- Self-RAG 反思 token 让模型自己判断证据是否支撑
- 关键事实用 NLI 模型做交叉验证

### 7.3 "RAG 不就是调一下 API 吗？" 怎么怼回去？
*来源：微信 / 《面试官："RAG 不就是调一下 API 吗？"，我怼回去："20 万字全塞进 Prompt，你确定？"》*

逻辑反驳：
1. 上下文窗口有上限：20 万字塞不进 prompt
2. 单纯 prompt 是 "无差别投喂"，RAG 是 "按需供给"
3. RAG 有完整的评估体系，Prompt 拼接没有
4. RAG 可追溯、可解释，Prompt 不行
5. RAG 节省成本（不用每次都塞全量）

---

## 八、来源索引

### 小红书
1. 大模型学习狗《大模型面试必背！GraphRAG 核心考点》`/explore/692dc1e2`
2. 寻找意义《被面试官问爆的 GraphRAG，我把它搭出来了》`/explore/6a20de3d`
3. 闭眼拿下大模型 offer《面试官问：RAG 的评估体系怎么做？》`/explore/6969f0eb`
4. Hp-AI 宝藏库《一文看懂三种 RAG 架构》`/explore/6a08700e`
5. 程序员不鸭《03｜RAG（AIAgent 面试八股文）②》`/explore/6a2f6ab0`
6. 丁师兄大模型《什么场景下必须用 GraphRAG？而不是 RAG？》`/explore/694ea503`
7. 白梦猿《RAG进阶优化：从 Naive RAG 到 Agentic》`/explore/6a2814e9`
8. 红鲤鱼与胖头鱼《什么是 GraphRAG？知识图谱如何增强 RAG》`/explore/69723cf3`
9. Antique《面试官问：什么是 Agentic RAG？》`/explore/6a081661`
10. 代码不蓝《Agent 面试题 - RAG 篇（持续更新中）》`/explore/69e476e6`
11. 薯条Coding《面试被问"什么是Embedding"答不上来？》`/explore/6a37ad80`
12. AI旅行者《Embedding 凭啥能做语义检索？全解》`/explore/6a3c9a04`
13. 小哲讲大模型《RAG 面试题：如何真正抑制大模型幻觉》`/explore/6a475b02`
14. 后端仔玩 AI Agent《Agent 面试 5 道必考题》`/explore/6a467a71`
15. 小瑜的AI实战笔记《12个关于 RAG 的面试题详解》`/explore/695b9815`
16. 鹿桃桃的 AI 百宝箱《从0到1学RAG（五）Self-RAG 详解》`/explore/6a046a60`
17. Orlando Liu《进阶 RAG 学习笔记》`/explore/697da1cf`
18. 永远天真《RRF 融合 + 重排序，面试官说这就是企业级 RAG》`/explore/6a43b1e8`
19. 汤圆键盘坏了不能写论文《开源智能爬虫框架：Crawl4AI的快速入门》`/explore/691544f3`
20. AI 算法面试《GraphRAG 在大厂核心组的落地方案》`/explore/68472364`

### 微信公众号
1. 《Agent 与 RAG 面试突围手册》总览
2. 《RAG 基础入门 | 面试高频问题 (2026 版)》
3. 《大模型岗位面试题系列图文 第四集 Rag 知识库》
4. 《【AIGC】大模型面试高频考点 - RAG 篇》
5. 《【AIGC】大模型面试高频考点 - RAG 中 Embedding 模型选型》
6. 《大厂面试必考：RAG 怎么答才能让面试官觉得你"深不可测"？》
7. 《从一道大厂面试题谈起：如何处理 RAG 中用户提问与文档间的"语义鸿沟"》
8. 《面试官："RAG 不就是调一下 API 吗？" 我怼回去："20 万字全塞进 Prompt，你确定？"》
9. 《【每日一道 AI 测试面试题 -04】RAG 怎么测》
10. 《LangChain 进阶 | 用 Crawl4AI 给 AI Agent 装"爬虫大脑"》
11. 《零代码！用 AgentBrowser 搭建 AI 爬虫》
12. 《全局 GraphRAG、知识图谱与实体解析详解》
13. 《Graph RAG：当 RAG 遇上知识图谱》
14. 《从知识图谱到 GraphRAG：工作原理、核心优势与应用场景全景图》
15. 《智谱数开一面：GraphRAG 用过吗？和 RAG 到底有什么区别？》
16. 《三十八：GraphRAG》
17. 《三十九：Agentic RAG》
18. 《AI 午报: Claude Fable 5 恢复，AI 爬虫与算力分发进入计费时代》
19. 《Claude Code 为什么"只用 Grep、不碰 Code RAG"？》
20. 《耗时半年，我开源了一套企业级 RAG 智能体：Ragent AI》

### X / Twitter
- X 搜索两次因 stale page identity 失败，仅获取摘要标题（多数为英文 RAG / GraphRAG 教程与论文）。后续可补充：`graphrag interview`、`RAG benchmark twitter`、`LangChain retrieval`。

