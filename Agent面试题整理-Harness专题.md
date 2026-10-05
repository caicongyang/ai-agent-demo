# Agent 面试题整理 — Harness Engineering 专题

> 数据来源：X/Twitter、微信公众号、小红书（via OpenCLI）
> 整理日期：2026-06-26

---

## 一、Harness 是什么？

### 核心公式

```
Agent = Model + Harness
```

**Harness = 模型之外的"驾驭层"**，让 Agent 不只是调 API，而是能稳定、可控地完成任务。

### Harness 的两层含义

来源：[@9hills](https://x.com/i/status/2053708571817513159) (X/Twitter)

1. **Harness Workflow** — Agent 的**工作流方法论**（研究→需求→设计→开发→验证闭环）
2. **Harness Infra** — Agent 的**基础设施**（沙盒、Skills、Tooling）

> Infra 的目标是保证 Workflow 的落地。

### Harness 包含什么

来源：小红书 @程序员流年 | 👍 153

Harness 是一套围绕 Agent 的**工程化驾驭体系**，包括：
- Prompt — 提示词
- Tool — 工具集
- Memory — 记忆
- Skill — 能力模块
- Agent Loop — 执行循环
- Trace — 全链路追踪（知道 Agent 做了什么）
- Eval — 评估体系（知道做得好不好）
- Replay — 问题复现
- Bad Case 分析 — 定位优化点

---

## 二、Harness 面试题（小红书）

来源：小红书 @程序员流年 | 👍 153

1. **Harness Engineering 和普通工程化测试有什么区别？**
2. **为什么 Harness 要去记录完整 Trace？**
3. **如何设计高质量的 Agent 评测任务集？**
4. **LLM Judge 在 Harness 中可靠吗？如何使用？**
5. **如何处理 Agent 输出的不确定性？同一个用例每次结果不完全一样怎么办？**
6. **Harness Engineering 的最大工程难点是什么？**
7. **如何判断一个 Agent Harness 是否成熟？**

---

## 三、Harness Linter 面试题

来源：小红书 @也许能耕耘token | 👍 315

### 面试官：Harness 的 Linter 怎么设计？

**答案：Linter + 审计 Agent 双轨机制**

**Linter 的三层架构：**

1. **L1 代码级**：ESLint + 自定义规则，检查代码规范
2. **L2 架构级**：自定义 Linter，检查是否违反分层架构
3. **L3 行为级**：LLM 审计 Agent，检查 Agent 行为是否合理

**关键设计：错误信息要指导性**

❌ 差的报错：`Error: Architecture violation`（Agent 看不懂）
✅ 好的报错：
```
禁止直接修改 Core 层
位置：src/core/user_service.py
原因：Core 层是稳定层
修复：请在 src/service/ 下创建对应 Service 类
示例：参考 src/service/order_service.py
```

**加分回答金句：**
> Linter 是给 Agent 装上的红绿灯，不是限制它，而是让它知道什么时候该停、什么时候该走。

---

## 四、DeepSeek Harness 岗位面试

来源：[@tianyi](https://x.com/i/status/2068652453797724562) (X/Twitter) DeepSeek Harness 团队负责人

### 招聘岗位

| 岗位 | 类型 | 核心要求 |
|------|------|---------|
| Harness 研究员 | 实习/全职 | 研究 Agent 工程化方法论 |
| Harness 工程师 | 全职/实习 | 构建 Agent 工程化基础设施 |
| Harness 产品经理 | 限全职 | Agent 产品设计与用户研究 |

### 面试流程
- 1 轮笔试 + 3 轮面试（终面由崔添翼亲自主持）

### 面试考察重点

来源：[@runes_leo](https://x.com/i/status/2070424435316695186) (X/Twitter)

面试要讲清楚的 6 件事：
1. 你真实做过什么任务
2. Agent 到底在哪一步断
3. 怎么判断它不是"看起来完成了"
4. 结果怎么验证
5. Worker 输出怎么写回
6. 个人 Workflow 怎么抽象成别人也能用的产品

### DeepSeek Harness PM 面试要求

来源：[@BoxMrChen](https://x.com/i/status/2055512625052553641) (X/Twitter)

- 深度使用过 Claude Code、Cowork、Codex、Cursor 等产品
- 理解 LLM API、KV Cache、Agent Loop、Tool Use、Reasoning、Planning、Skills、MCP、Memory、Subagent、Multi-Agent
- 对 Prompt Engineering、**Context Engineering、Harness Engineering** 有第一手实践
- 能够设计系统性收集数据的方法（问卷、访谈、A/B测试、灰度测试）

---

## 五、Harness Engineering 面试专题（微信公众号）

### 1. Agent Harness 的五大组件

来源：微信公众号《华为 Agent 实习面试》

面试标准回答：
> "我们的 Harness 包括任务集、运行器、工具环境、轨迹记录和评测器。每个组件都对 Agent 的稳定执行至关重要。"

### 2. Harness 全栈面试题

来源：微信公众号《Harness全栈-Eval-Agent-RL-Test》（Staff 面试）

Staff 级别 Harness 面试需覆盖：
- Eval 体系设计
- Agent 编排架构
- RL（强化学习）与 Agent 的关系
- Test 策略（CI/CD 集成）

### 3. Harness Engineering 分水岭

来源：微信公众号《聊聊 Harness Engineering》

> 还在 "prompt 写好点 agent 就能干活" 的认知阶段 vs 已经进入 Harness 工程化阶段 —— 这是 2026 年 Agent 工程的分水岭。

---

## 六、Anthropic 长任务 Agent 的 Harness 实践

来源：[@yibie](https://x.com/i/status/2069917331455987731) (X/Twitter)

Anthropic 工程师解决"Agent 跨多 context window 持续工作"的方案：

**两阶段架构：**
1. **初始化 Agent** — 第一次运行时搭环境、生成 feature list
2. **编码 Agent** — 每个 session 增量推进，完成单个 feature

**四种失败模式及修复：**
1. 一口气干太多 → 拆成 feature list，每次只做一个
2. 留下烂摊子 → 要求 git commit + progress 文件
3. 过早宣布完成 → JSON feature list 明确标记
4. 没真正验证就标记完成 → 要求用浏览器自动化工具端到端测试

**核心思想：** 把 "project state" 从 Agent 脑子里移出来，放到结构化文件里。Agent 成为 feature 处理器，不是环境侦探。

---

*本文档由 OpenCLI 搜索整理生成，仅供参考。*

