"""
面试题：Agentic RAG（智能体化检索）— LangGraph 实现
====================================================

来源：小红书 / Antique《面试官问：什么是 Agentic RAG？》、鹿桃桃《从0到1学RAG Self-RAG详解》、
      微信 /《三十九：Agentic RAG》、《Claude Code 为何只用 Grep、不碰 Code RAG》

问题域（对应 Agent 面试问答全集 - 十九 - 爬虫 / RAG）：
  - Q75：什么是 Agentic RAG？和 Naive/Classic RAG 区别
  - Q76：Self-RAG / CRAG / Adaptive-RAG / Agentic RAG 核心差异
  - Q77：Agentic RAG 的 LangGraph 实现思路
  - Q78：Agentic RAG 项目经验怎么讲

面试回答要点：
  - 核心变化：把固定流水线变成自主决策（要不要查 / 查哪个 / 查几次）
  - Self-RAG 引入 reflection tokens：[Retrieve] [IsRel] [IsSup] [IsUse]
  - Agentic RAG 走 LangGraph：Router → Tool → Reranker → Generator → Verifier → (回退) → Output
  - 与 GraphRAG / RAG 是互补关系，不是替代

技术栈：LangGraph StateGraph + 自实现 Router/Tool/Reranker/Verifier 节点 + MemorySaver checkpoint
"""

from __future__ import annotations

import os
from typing import List, Dict, TypedDict
from typing_extensions import Annotated
from operator import add
from datetime import datetime

from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()


# ─── 1. 状态 ────────────────────────────────────────

class AgenticRAGState(TypedDict):
    question: str
    question_type: str                          # local / multi_hop / global
    plan: List[str]                             # 待执行的步骤名列表
    plan_idx: int                               # 当前执行到的索引
    retrieved_docs: List[Dict]                  # 所有检索文档
    reranked_docs: List[Dict]                   # 重排后
    draft_answer: str                           # 候选答案
    verification: Dict                          # {has_evidence, is_unsupported, ...}
    final_answer: str                           # 最终答案
    iterations: int                             # 反思循环计数
    max_iterations: int                         # 上限
    history: Annotated[List[str], add]


# ─── 2. 三个工具：向量 / 图 / Web ───────────────────────

class VectorRAGTool:
    """向量检索工具（Classic RAG 风格）"""
    name = "vector_rag"

    DOCS = [
        {"id": "d1", "text": "GraphRAG 通过 LLM 抽取实体和关系，构建知识图谱，支持多跳推理。"},
        {"id": "d2", "text": "Self-RAG 引入 reflection tokens，让模型在生成 token 时判断 '要不要检索' / '证据是否支撑'。"},
        {"id": "d3", "text": "Agentic RAG 让模型自主决定要查什么、查几次、怎么查。"},
        {"id": "d4", "text": "LangGraph 是 LangChain 公司的图框架，适合编排多步骤 / 条件分支 / 循环 / 人工介入的 Agent 工作流。"},
        {"id": "d5", "text": "RRF 融合（Reciprocal Rank Fusion）用排名代替分数解决多路检索量纲不一致问题。"},
        {"id": "d6", "text": "Crawl4AI 是一个 LLM 友好的爬虫框架，输出干净 Markdown 是 RAG 的高质量数据源。"},
        {"id": "d7", "text": "嵌入式模型把文本转稠密向量，余弦相似度检索；HNSW 是工业界最主流的 ANN 索引。"},
        {"id": "d8", "text": "Cross-Encoder Reranker 比向量检索更精准，但更慢，常用于 top-K 重排。"},
    ]

    def __call__(self, query: str, k: int = 3) -> List[Dict]:
        q_words = set(query.lower().split())
        scored = []
        for d in self.DOCS:
            text_words = set(d["text"].lower().split())
            overlap = len(q_words & text_words) / max(len(q_words | text_words), 1)
            scored.append((overlap, d))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"source": "vector", **d, "score": s} for s, d in scored[:k] if s > 0]


class GraphRAGTool:
    """图检索工具（实体-关系查询）"""
    name = "graph_rag"

    GRAPH = {
        "GraphRAG":  {"公司": ["微软"], "技术": ["知识图谱", "Leiden"], "用于": ["多跳推理"]},
        "Self-RAG":  {"是": ["reflection token"], "用到": ["[Retrieve]"], "对比": ["CRAG"]},
        "AgenticRAG": {"优势": ["自主决策"], "实现": ["LangGraph"], "对比": ["Naive RAG"]},
        "LangGraph": {"属于": ["LangChain"], "适用": ["Agent", "工作流"]},
        "Crawl4AI":  {"类型": ["爬虫框架"], "特点": ["LLM-friendly", "输出 Markdown"]},
        "英伟达":     {"是": ["公司"], "创始人": ["黄仁勋"]},
        "OpenAI":    {"是": ["公司"], "CEO": ["Sam Altman"]},
    }

    def __call__(self, query: str, k: int = 3) -> List[Dict]:
        results: List[Dict] = []
        for entity, relations in self.GRAPH.items():
            if entity.lower() in query.lower() or query.lower() in entity.lower():
                items = [f"{entity} — {rel} → {tgt}" for rel, targets in relations.items() for tgt in targets]
                results.append({
                    "source": "graph",
                    "id": f"g-{entity}",
                    "text": f"{entity} 的关系网络：" + "；".join(items[:5]),
                    "score": 1.0,
                })
        if not results and any(kw in query for kw in ["总结", "综述", "全景"]):
            results.append({
                "source": "graph",
                "id": "g-overview",
                "text": "全局视图：RAG 五代 = Naive→Advanced→Modular→GraphRAG→Agentic RAG",
                "score": 0.8,
            })
        return results[:k]


class WebSearchTool:
    """联网搜索工具（演示用，真实请接 SerpAPI / Tavily）"""
    name = "web_search"

    def __call__(self, query: str, k: int = 3) -> List[Dict]:
        return [{
            "source": "web",
            "id": "w-stub",
            "text": f"[Mock 联网结果] 关于 '{query}' 的最新公开信息（演示模式无网络）",
            "score": 0.5,
        }]


TOOLS = {"vector_rag": VectorRAGTool(), "graph_rag": GraphRAGTool(), "web_search": WebSearchTool()}


# ─── 3. Agentic RAG 节点 ────────────────────────────

class AgenticRAGAgent:
    def __init__(self, max_iterations: int = 2):
        self.max_iter = max_iterations

    # ── Node: Router ────────────────────────────
    def router(self, state: AgenticRAGState) -> AgenticRAGState:
        q = state["question"]
        if any(k in q for k in ["总结", "整体", "全景", "概览"]):
            qtype = "global"
            plan = ["graph_rag", "vector_rag", "rerank", "generate", "verify"]
        elif any(k in q for k in ["关系", "多跳", "关联", "链路"]):
            qtype = "multi_hop"
            plan = ["graph_rag", "vector_rag", "rerank", "generate", "verify"]
        else:
            qtype = "local"
            plan = ["vector_rag", "rerank", "generate", "verify"]
        return {
            "question_type": qtype,
            "plan": plan,
            "plan_idx": 0,
            "iterations": 0,
            "max_iterations": self.max_iter,
            "history": [f"[Router] qtype={qtype}, plan={plan}"],
        }

    # ── Node: Step Dispatcher（路由到下一个节点） ─────
    def step_dispatch(self, state: AgenticRAGState) -> AgenticRAGState:
        """把当前 plan[plan_idx] 的步骤执行掉，然后 plan_idx 推进"""
        step = state["plan"][state["plan_idx"]]
        history = [f"[{step}] start"]
        if step in TOOLS:
            docs = TOOLS[step](state["question"], k=3)
            history.append(f"[{step}] returned {len(docs)} docs")
            return {
                "retrieved_docs": state["retrieved_docs"] + docs,
                "plan_idx": state["plan_idx"] + 1,
                "history": history,
            }
        if step == "rerank":
            return self._rerank_inline(state, history)
        if step == "generate":
            return self._generate_inline(state, history)
        if step == "verify":
            return self._verify_inline(state, history)
        # unknown step
        return {"plan_idx": state["plan_idx"] + 1, "history": history}

    def _rerank_inline(self, state: AgenticRAGState, history: List[str]) -> AgenticRAGState:
        q = state["question"].lower()
        q_words = set(q.split())
        docs = state["retrieved_docs"]
        if not docs:
            history.append("[Reranker] no docs")
            return {"reranked_docs": [], "plan_idx": state["plan_idx"] + 1, "history": history}
        def score(d):
            text_words = set(d["text"].lower().split())
            return len(q_words & text_words) / max(len(q_words | text_words), 1) + d.get("score", 0) * 0.3
        reranked = sorted(docs, key=score, reverse=True)[:3]
        history.append(f"[Reranker] top={len(reranked)}")
        return {"reranked_docs": reranked, "plan_idx": state["plan_idx"] + 1, "history": history}

    def _generate_inline(self, state: AgenticRAGState, history: List[str]) -> AgenticRAGState:
        docs = state.get("reranked_docs") or state["retrieved_docs"]
        if not docs:
            draft = "[Generator] 未检索到文档，无法生成。"
        else:
            ctx = "\n".join(f"- [{d.get('source','?')}] {d['text']}" for d in docs)
            draft = f"[{state['question_type']}] {state['question']}\n\n引用：\n{ctx}\n\n（演示模式直接拼接，未调用 LLM）"
        history.append(f"[Generator] draft={len(draft)} chars")
        return {"draft_answer": draft, "plan_idx": state["plan_idx"] + 1, "history": history}

    def _verify_inline(self, state: AgenticRAGState, history: List[str]) -> AgenticRAGState:
        draft = state["draft_answer"]
        has_evidence = bool(state.get("reranked_docs") or state["retrieved_docs"])
        is_unsupported = ("未知" in draft) or (not has_evidence)
        verification = {
            "has_evidence": has_evidence,
            "is_unsupported": is_unsupported,
            "checked_at": datetime.now().isoformat(),
        }
        history.append(f"[Verifier] {verification}")
        iterations = state["iterations"]
        if is_unsupported and iterations + 1 < state["max_iterations"]:
            # 再追加一段 "vector_rag, rerank, generate, verify" 重新尝试
            new_plan = state["plan"] + ["vector_rag", "rerank", "generate", "verify"]
            return {
                "verification": verification,
                "plan": new_plan,
                "plan_idx": state["plan_idx"] + 1,
                "iterations": iterations + 1,
                "history": history,
            }
        return {
            "final_answer": draft,
            "verification": verification,
            "plan_idx": state["plan_idx"] + 1,
            "iterations": iterations + 1,
            "history": history,
        }


# ─── 4. 图构建（清晰版本） ────────────────────────────

def build_graph() -> any:
    agent = AgenticRAGAgent()
    g = StateGraph(AgenticRAGState)

    # 三个节点：router / step / output（router 在 verify 后被重新调用时使用）
    g.add_node("router", agent.router)
    g.add_node("step", agent.step_dispatch)
    # 终点节点：把 final_answer 拷贝到一个稳定的输出（可选）
    g.add_node("finish", lambda s: {"history": [f"[Finish] answer ready ({len(s.get('final_answer','') or s.get('draft_answer',''))} chars)"]})

    def after_router(state):
        return "step"

    def after_step(state):
        if state["plan_idx"] >= len(state["plan"]):
            return "finish"
        return "step"

    def after_finish(state):
        return END

    g.add_edge(START, "router")
    g.add_conditional_edges("router", after_router, {"step": "step"})
    g.add_conditional_edges("step", after_step, {"step": "step", "finish": "finish"})
    g.add_conditional_edges("finish", after_finish, {END: END})

    return g.compile(checkpointer=MemorySaver())


# ─── 5. 面试 Q&A ───────────────────────────────────

INTERVIEW_QAS = """
=== Q75：什么是 Agentic RAG？和 Naive/Classic RAG 区别 ===
A:
- 不是"更高级的 RAG"，而是让检索从固定流程变成智能决策
- 传统 RAG：提问 → 检索 → 塞 prompt → 回答（固定）
- Agentic RAG：模型自主决定查什么 / 怎么查 / 查几次 / 是否调用工具 / 验证证据
- 适合：企业知识库 / 论文分析 / 客服工单 / 数据分析
- 一句话：让模型学会"如何使用资料"而不是"多查一点资料"

=== Q76：Self-RAG / CRAG / Adaptive-RAG / Agentic RAG 差异 ===
A:
- CRAG (Corrective RAG)：检索后做外部纠错
- Adaptive-RAG：检索前做问题路由
- Self-RAG：把判断能力推进到生成过程内部（用 reflection tokens：[Retrieve] [IsRel] [IsSup] [IsUse]）
- Agentic RAG：用 LangGraph 把路由 → 检索 → 重排 → 生成 → 校验 编排成一个图
- 关键：Self-RAG 是"模型自己质疑自己"，Agentic RAG 是"模型驱动工具循环"

=== Q77：Agentic RAG 的 LangGraph 实现思路 ===
A:
最小图：Router → Step(Tool/Rerank/Generate/Verify) → Step → ... → Finish
- Router: 根据问题判断 qtype (global/local/multi_hop)，生成计划
- Step: 根据 plan[plan_idx] 决定执行 vector/graph/web/rerank/generate/verify
- Verify 不通过：自动往 plan 后追加一轮"vector_rag → rerank → generate → verify"
- Verify 通过或达 max_iterations：进入 Finish 节点 → END

=== Q78：Agentic RAG 项目经验怎么讲 ===
A:
四段论：
1. 场景：企业级多租户 / 高 QPS
2. 架构：Hybrid Search + Cross-Encoder Rerank + LangGraph 编排
3. 工具白名单 + Reflective Loop：避免死循环 / 幻觉
4. 评估：Faithfulness / Recall@K / LLM-as-Judge + 日志回放
"""


# ─── 6. 演示 ────────────────────────────────────────

def run_demo(question: str = "Agentic RAG 与 Self-RAG 的核心区别是什么？"):
    print("\n" + "=" * 60)
    print("Demo 12: Agentic RAG LangGraph 演示")
    print("=" * 60)
    print(f"Question: {question}")

    graph = build_graph()
    initial_state: AgenticRAGState = {
        "question": question,
        "question_type": "",
        "plan": [],
        "plan_idx": 0,
        "retrieved_docs": [],
        "reranked_docs": [],
        "draft_answer": "",
        "verification": {},
        "final_answer": "",
        "iterations": 0,
        "max_iterations": 2,
        "history": [],
    }
    config = {"configurable": {"thread_id": "demo-12"}}
    final_state: AgenticRAGState = graph.invoke(initial_state, config=config)  # type: ignore

    print("\n📋 调度历史：")
    for h in final_state.get("history", []):
        print(f"  {h}")

    print(f"\n📊 迭代次数：{final_state.get('iterations')}/{final_state.get('max_iterations')}")
    print(f"📊 检索总数：{len(final_state.get('retrieved_docs', []))}")

    print("\n✅ 校验结果：")
    v = final_state.get("verification", {})
    print(f"  has_evidence={v.get('has_evidence')}  is_unsupported={v.get('is_unsupported')}")

    print("\n💡 最终答案：")
    print(final_state.get("final_answer") or final_state.get("draft_answer"))


if __name__ == "__main__":
    print(INTERVIEW_QAS)
    run_demo()
