# Agent 面试题整理 — CLAUDE.md / AGENTS.md / System Prompt

> 数据来源：X/Twitter、微信公众号、小红书（via OpenCLI）
> 专题：AI Coding Agent 配置、上下文工程、System Prompt 管理
> 整理日期：2026-06-26

---

## 一、CLAUDE.md / AGENTS.md 专题

### 1. AGENTS.md 的作用和结构

来源：[@mashi2003_mashi](https://x.com/i/status/2070033604097515972) (X/Twitter)

> AGENTS.md 的作用不是让 AI 更聪明，而是让 AI 更受控。

**AGENTS.md 四大模块：**

1. **Project Rules**（项目规则）
   - 先读相关文件，再编辑
   - 只改用户要求的内容
   - 不做无关重构
   - 匹配现有代码风格
   - 不经确认不新增依赖

2. **Workflow**（工作流）
   - 改代码前：复述目标 → 列出改动文件 → 说明风险 → 说明验证方式
   - 改代码中：做最小有用改动 → 保留现有行为 → 范围变大就停下来问人
   - 改代码后：总结改动 → 报告验证命令 → 说明未跑的测试 → 说明残余风险

3. **Verification**（验证）
   - 项目级验证命令（npm test、pytest、cargo test）
   - 按场景定制（前端改动必须截图、后端改动跑 API 测试）

4. **Stop Conditions**（停止条件）
   - 需要新增依赖
   - 需要改数据库 schema
   - 需求和代码现状冲突
   - 需要大范围重构
   - 测试失败但原因不明确
   - 可能影响用户数据或权限

### 2. andrej-karpathy-skills：4条铁律

来源：[@AYi_AInotes](https://x.com/i/status/2051321729843069037) (X/Twitter)

GitHub 11万+ Stars 的 CLAUDE.md 文件：

1. **先思考再编码**：不准默默做假设，模糊就提问，困惑立刻停下
2. **简约至上**：只写最小可工作代码，不准搞没人要的抽象和灵活性
3. **手术式修改**：只碰要求的部分，不准顺便重构邻居代码
4. **目标驱动执行**：先写成功标准，每一步都要可验证

### 3. Anthropic Steering Claude Code：7大操控技巧

来源：[@_moto___](https://x.com/i/status/2068819331811868713) (X/Twitter)

Anthropic 官方指南《Steering Claude Code》提出的 7 大技巧：

1. **CLAUDE.md** — 项目的"取扱说明书"。build命令、目录结构、团队规范
2. **Rules（规则）** — 条件触发的约束文件。只匹配特定路径时激活
3. **Skills（技能）** — 按需加载的能力包。被调用时才启动，轻量
4. **Subagents（子代理）** — 独立处理子任务，只返回结果
5. **Hooks（钩子）** — 自动触发：「保存后必Lint」「结束后Slack通知」
6. **Output Styles** — 改变 Claude 的行为风格（最强权限，慎用）
7. **System Prompt 追记** — 启动时注入「本次对话的规则」，Token 节约

### 4. CLAUDE.md 让编程错误率降至 3%

来源：小红书 @来杯凉白开 | 👍 731

12 条规则将 AI 编程错误率从常规水平降低至 3%。

### 5. CLAUDE.md 的 12 条规则

来源：小红书 @来杯凉白开 | 👍 731

12 条高效规则涵盖代码风格、错误处理、测试策略、依赖管理等。

---

## 二、System Prompt 专题

### 1. System Prompt 不是大 Prompt

来源：小红书 @上交-余学长 | 2026-06-24

核心观点：System Prompt 的关键是**精简精准**，而非堆砌。目标是定义 Agent 的角色、边界和行为规则，而不是把所有业务逻辑都写进去。

**System Prompt 设计原则：**
- 角色定义：清楚说明 Agent 是谁
- 能力边界：明确能做什么、不能做什么
- 行为约束：什么情况下必须停下来
- 输出规范：格式、语气、风格

### 2. 面试问题：上百个 Skills 如何不爆上下文？

来源：小红书 @阿东玩AI | 👍 255

核心考点：Skills 的按需加载策略（渐进式披露）

- 第一层：Skill 名称 + 简短描述（几行文本）
- 第二层：用户选择后加载完整 Skill 说明
- 第三层：复杂任务时查询详细文档

### 3. CLAUDE.md、Memory、RAG 三者关系

来源：小红书 @大模型一粟

三者定位和关系：

| 机制 | 作用 | 类比 |
|------|------|------|
| CLAUDE.md | 静态项目规则（每次对话都加载） | 员工手册 |
| Memory | 动态交互记忆（跨会话持久化） | 工作笔记 |
| RAG | 按需知识检索（需要时才调用） | 查阅文档 |

---

## 三、Claude Code 面试专版

### 1. 面试题："Claude Code 你用到什么程度？"

来源：微信公众号《面试官冷笑："Claude Code你用到什么程度？"》

关键回答结构：
- CLAUDE.md 配置（项目规则、工作流、验证）
- Skills 扩展机制（按需加载能力）
- MCP 集成（连接外部工具）
- Hooks 自动化（保存后自动 Lint / 测试）
- Subagents 并行处理（多任务协作）
- System Prompt 管理（上下文优化）
- spec.md / tasks.md / checklist.md 三件套

### 2. 面试题：Claude Code 的上下文管理策略有哪些？

来源：小红书 @Corgi写代码 | 2026-06-02

考察点：
- 上下文裁剪策略（Trim Strategy）
- CLAUDE.md 角色（静态规则始终在上下文中）
- Memory vs RAG 的区别
- 分层加载（System Prompt → Rules → Skills → RAG）
- Token 预算管理

### 3. 面试题：Claude Code 的检索是怎么做的？

来源：小红书 @算法狗 | 👍 360 | 2026-04-24

考察点：
- Claude Code 如何从项目文件中检索相关上下文
- 文件索引机制
- 语义搜索 vs grep
- RAG in Agent 的具体实现

### 4. 面试题：Claude Code 的上下文裁剪

来源：小红书 @风起的大模型笔记 | 2026-05-19

考察点：
- 上下文裁剪的时机和策略
- 如何判断哪些内容可以丢弃
- 裁剪后的信息恢复机制

### 5. Claude Code 生态系统全览

来源：微信公众号《Claude Code 生态系统全览:超越代码生成》

涵盖：
- CLAUDE.md 定期评审和优化
- 配置模板库建设
- 社区验证过的配置复用
- Prompt 工程原则（结构化、统一结构）

---

## 四、Skill 设计模式专题

### 1. 每个开发者都应掌握的 5 种 Agent 技能设计模式

来源：微信公众号 | 2026-03-19

**5 种设计模式：**

1. **模板模式** — 预定义操作流程（如「部署检查清单」）
2. **反转模式** — Agent 扮演面试官/审查者角色来验证输出
3. **链式模式** — 多个 Skill 串联（先分析、再生成、最后检查）
4. **分支模式** — 根据上下文选择不同 Skill
5. **循环模式** — 迭代优化的 Skill（不断 refine）

### 2. Google 发布的 5 个 Agent Skill 设计模式

来源：微信公众号《继Anthropic之后,Google发布5个常用的Agent Skill设计模式》

- 不把复杂工作流塞进 system prompt
- 用正确的结构模式拆分工作流
- Agent 变成面试官的反直觉设计

---

## 五、面试高频问题-AI Coding 专题

来源：小红书 @努力转型agent💪 | 2026-06-22

AI Coding 相关高频面试题：

1. **Vibe Coding 是什么？和传统开发有什么区别？**
2. **CLAUDE.md / AGENTS.md 怎么写？项目结构和最佳实践？**
3. **System Prompt 如何设计和优化？**
4. **Skills 的架构和加载机制？**
5. **如何处理 AI 编程中的代码质量问题和幻觉？**

---

## 六、Claude Claude Certified Architect

来源：[@VincentLogic](https://x.com/i/status/2070018959508996533) (X/Twitter)

**官方 10 周备考路线：**

| 周 | 内容 |
|----|------|
| 1 | Messages API、模型选择、JSON 输出 |
| 2 | Prompt Engineering、XML、few-shot |
| 3 | Tool Use、Schema、错误处理 |
| 4 | 客服 Agent + Eval |
| 5 | 长上下文、PDF、Prompt Caching、成本控制 |
| 6 | 文档抽取系统 |
| 7 | MCP Server 开发 |
| 8 | Claude Code、CLAUDE.md、Hooks、Skills |
| 9 | 整理作品集 |
| 10 | 模拟考试 + 查漏补缺 |

---

## 七、Google DESIGN.md

来源：[@Gorden_Sun](https://x.com/i/status/2046947310631035017) (X/Twitter)

Google 开源的 **DESIGN.md**：Agent 的设计系统规范
- 读完就能持续按品牌规范生成 UI
- 跨工具、跨项目复用

---

*本文档由 OpenCLI 搜索 X/Twitter、微信、小红书整理生成，仅供参考。*
