"""
面试题：GraphRAG（基于知识图谱的检索增强）
==========================================

来源：小红书《大模型面试必背！GraphRAG 核心考点》、微信 /《智谱数开一面：GraphRAG 用过吗？》、《全局 GraphRAG 知识图谱详解》

问题域（对应 Agent 面试问答全集 - 十九 - 爬虫 / RAG）：
  - Q71：GraphRAG 与传统 RAG 的核心区别
  - Q72：GraphRAG 工作流程（索引 / 查询）
  - Q73：何时必须用 GraphRAG 而不是普通 RAG
  - Q74：GraphRAG 工业级 9 大避坑

面试回答要点：
  - 数据组织：传统 RAG 是文本切片；GraphRAG 是实体-关系三元组
  - 工作流程：LLM 抽取实体/关系 → 建图 → Leiden 社区检测 → 社区摘要
  - 查询类型：全局总结（用社区摘要）/ 局部查询（1-2 跳子图 + 向量兜底）
  - 选型场景：组织关系、供应链、审批链、依赖分析、多跳推理
  - 避坑：小模型抽取 / 实体对齐 / Schema 收敛 / 语义剪枝 / 混合检索

技术栈：LangChain + NetworkX（图）+ Chroma（向量兜底）+ 自实现 GraphRAGPipeline
"""

from __future__ import annotations

import os
import re
import json
import math
import random
from typing import List, Dict, Tuple, Optional, Set
from collections import defaultdict
from dataclasses import dataclass, field

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()


# ─── 1. 图节点 / 边 ────────────────────────────────

@dataclass
class Entity:
    """图谱实体节点"""
    id: str
    name: str
    type: str                          # Person / Org / Product / Tech ...
    description: str = ""
    source_doc_ids: List[str] = field(default_factory=list)


@dataclass
class Relation:
    """图谱关系边"""
    source: str                        # entity id
    target: str
    relation: str                      # 关系类型
    weight: float = 1.0
    evidence: str = ""                 # 支撑证据


@dataclass
class Community:
    """社区（Leiden / Louvain 聚类）"""
    id: int
    entities: List[str]
    summary: str = ""
    level: int = 0


# ─── 2. 实体 / 关系抽取（LLM / 离线 Mock 双模式） ──────────

class EntityExtractor:
    """
    从一段文本抽取 (entity, entity, relation) 三元组
    真实场景用 LLM；演示场景用基于规则的 mock
    """

    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm

    def extract(self, text: str, doc_id: str) -> Tuple[List[Entity], List[Relation]]:
        if self.use_llm:
            return self._extract_llm(text, doc_id)
        return self._extract_mock(text, doc_id)

    def _extract_llm(self, text: str, doc_id: str) -> Tuple[List[Entity], List[Relation]]:
        """真实场景：调用 LLM 返回严格 JSON 三元组（生产环境按 token 节流）"""
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.prompts import ChatPromptTemplate
        except ImportError:
            return [], []
        api_key = os.getenv("LLM_API_KEY") or ""
        if not api_key or api_key == "your-llm-api-key":
            return self._extract_mock(text, doc_id)  # 降级

        llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=api_key,
            base_url=os.getenv("LLM_BASE_URL") or None,
            temperature=0,
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "你是知识图谱构建助手。从文本中提取实体和关系三元组，"
             "输出严格 JSON："
             "{\"entities\":[{\"name\":\"...\",\"type\":\"...\"}],"
             "\"relations\":[{\"source\":\"...\",\"target\":\"...\",\"relation\":\"...\"}]}"
             "无 JSON 外的文字，最多 8 个实体 / 8 个关系。"),
            ("human", "{text}")
        ])
        chain = prompt | llm
        try:
            resp = chain.invoke({"text": text[:1500]}).content
            data = json.loads(resp[resp.find("{"):resp.rfind("}") + 1])
            entities = [Entity(id=e["name"], name=e["name"], type=e.get("type", "Unknown"),
                               source_doc_ids=[doc_id]) for e in data.get("entities", [])]
            relations = [Relation(source=r["source"], target=r["target"],
                                  relation=r["relation"], evidence=text[:100]) for r in data.get("relations", [])]
            return entities, relations
        except Exception:
            return self._extract_mock(text, doc_id)

    @staticmethod
    def _normalize(name: str) -> str:
        """实体对齐：去前后空格 / 简单同义替换"""
        return name.strip().replace("公司", "").replace("（", "(").replace("）", ")")

    def _extract_mock(self, text: str, doc_id: str) -> Tuple[List[Entity], List[Relation]]:
        """
        离线 Mock：使用正则匹配中文专有名词，构建一些 demo 三元组
        用于无 LLM API Key 时也能跑通整个 GraphRAG 链路
        """
        # 简易规则：从 demo 文本识别常见实体
        patterns = {
            "Org": [r"([A-Z][a-zA-Z0-9]+公司|[A-Z][a-zA-Z]+ Inc\.?|\w+集团|阿里|字节|微软|腾讯|百度|英伟达)"],
            "Person": [r"(马斯克|黄仁勋|雷军|库克|张一鸣|Jack Ma|Sam Altman)"],
            "Tech": [r"(GraphRAG|AgenticRAG|LangGraph|LangChain|RAG|LLM)"],
            "Product": [r"(Crawl4AI|Firecrawl|Ragent AI|Claude Code|GPT-4o|Qwen)"],
        }
        entities: Dict[str, Entity] = {}
        for etype, regs in patterns.items():
            for reg in regs:
                for m in re.finditer(reg, text):
                    name = self._normalize(m.group(1))
                    if name and name not in entities:
                        entities[name] = Entity(id=name, name=name, type=etype, source_doc_ids=[doc_id])

        # 简易关系：实体共现 + 距离 < 100 字符
        relations = []
        ent_list = list(entities.keys())
        for i, a in enumerate(ent_list):
            for b in ent_list[i + 1:]:
                if a == b:
                    continue
                # 检测共现
                if a in text and b in text:
                    idx_a = text.find(a)
                    idx_b = text.find(b)
                    if abs(idx_a - idx_b) < 100:
                        relations.append(Relation(
                            source=a,
                            target=b,
                            relation="相关",
                            weight=1.0 / (abs(idx_a - idx_b) + 1),
                            evidence=text[max(0, min(idx_a, idx_b) - 10):max(idx_a, idx_b) + len(b) + 10],
                        ))
        return list(entities.values()), relations


# ─── 3. 图构建 + Leiden 简版（贪心模块度 / 标签传播） ──────

class GraphBuilder:
    """
    用 NetworkX 替代 Neo4j（演示场景）
    实战大图请用 Neo4j / FalkorDB / TuGraph
    """

    def __init__(self):
        self.graph: Dict[str, Set[str]] = defaultdict(set)   # adjacency (无向)
        self.entities: Dict[str, Entity] = {}
        self.relations: List[Relation] = []

    def add_relation(self, rel: Relation):
        self.graph[rel.source].add(rel.target)
        self.graph[rel.target].add(rel.source)
        self.relations.append(rel)

    def add_entity(self, e: Entity):
        if e.id not in self.entities:
            self.entities[e.id] = e
            _ = self.graph[e.id]

    @staticmethod
    def _label_propagation(graph: Dict[str, Set[str]], max_iter: int = 30) -> Dict[str, int]:
        """轻量社区检测：标签传播算法"""
        nodes = list(graph.keys())
        labels = {n: i for i, n in enumerate(nodes)}
        random.seed(42)
        for _ in range(max_iter):
            changed = False
            random.shuffle(nodes)
            for n in nodes:
                if not graph[n]:
                    continue
                # 邻居中标签最多的
                neighbor_labels = defaultdict(int)
                for nb in graph[n]:
                    neighbor_labels[labels[nb]] += 1
                best = max(neighbor_labels, key=neighbor_labels.get)
                if best != labels[n]:
                    labels[n] = best
                    changed = True
            if not changed:
                break
        # 重新映射社区 ID 为 0-based 紧凑
        unique_labels = list(set(labels.values()))
        remap = {l: i for i, l in enumerate(unique_labels)}
        return {n: remap[l] for n, l in labels.items()}

    def detect_communities(self) -> List[Community]:
        labels = self._label_propagation(self.graph)
        grouped: Dict[int, List[str]] = defaultdict(list)
        for n, c in labels.items():
            grouped[c].append(n)
        return [Community(id=i, entities=ents) for i, ents in grouped.items()]

    def community_summary(self, community: Community) -> str:
        """社区摘要：拼接实体类型 + 边数量 + 抽样关系（生产用 LLM 生成）"""
        ents = [self.entities[n] for n in community.entities if n in self.entities]
        type_count: Dict[str, int] = defaultdict(int)
        for e in ents:
            type_count[e.type] += 1
        rels = [r for r in self.relations
                if r.source in community.entities and r.target in community.entities]
        return (
            f"社区 #{community.id}（{len(ents)} 实体）："
            f"{dict(type_count)}；"
            f"{len(rels)} 条关系；"
            f"如 " + "、".join(f"{r.source}—{r.relation}->{r.target}" for r in rels[:3])
        )

    def neighbors_within_hops(self, entity: str, max_hops: int = 2) -> List[Tuple[str, int]]:
        """BFS 获取 1~2 跳邻居 + 距离"""
        seen: Dict[str, int] = {entity: 0}
        frontier = [entity]
        for _ in range(max_hops):
            nxt = []
            for n in frontier:
                for nb in self.graph[n]:
                    if nb not in seen:
                        seen[nb] = seen[n] + 1
                        nxt.append(nb)
            if not nxt:
                break
            frontier = nxt
        return [(n, d) for n, d in sorted(seen.items(), key=lambda x: x[1])]


# ─── 4. GraphRAG Pipeline ────────────────────────────

class GraphRAGPipeline:
    """索引 + 查询两阶段"""

    def __init__(self, use_llm: bool = False):
        self.extractor = EntityExtractor(use_llm=use_llm)
        self.builder = GraphBuilder()
        self.communities: List[Community] = []
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=80)
        # 兜底向量检索 (Hybrid Search 必备)
        self.vectorstore = None
        self._init_vectorstore()

    def _init_vectorstore(self):
        try:
            from langchain_openai import OpenAIEmbeddings
            from langchain_chroma import Chroma
        except ImportError:
            return
        api_key = os.getenv("EMBEDDING_API_KEY") or os.getenv("LLM_API_KEY") or ""
        if not api_key or api_key == "your-llm-api-key":
            return
        self._emb_fn = lambda texts: OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=api_key,
            base_url=os.getenv("EMBEDDING_BASE_URL") or os.getenv("LLM_BASE_URL") or None,
        ).embed_documents(texts)
        self._Chroma = Chroma

    # ── 索引阶段 ─────────────────────────────
    def index_documents(self, docs: List[Document]) -> None:
        for i, doc in enumerate(docs):
            doc_id = f"doc-{i}"
            text = doc.page_content
            chunks = self.splitter.split_text(text)
            for chunk in chunks:
                entities, relations = self.extractor.extract(chunk, doc_id)
                for e in entities:
                    self.builder.add_entity(e)
                for r in relations:
                    self.builder.add_relation(r)

        # 社区检测
        self.communities = self.builder.detect_communities()
        # 社区摘要
        for c in self.communities:
            c.summary = self.builder.community_summary(c)

        # 兜底向量库
        try:
            if hasattr(self, "_emb_fn") and self._emb_fn:
                from langchain_chroma import Chroma
                self.vectorstore = Chroma.from_documents(
                    docs,
                    embedding=OpenAIEmbeddings(  # noqa
                        model="text-embedding-3-small",
                        openai_api_key=os.getenv("EMBEDDING_API_KEY") or os.getenv("LLM_API_KEY"),
                        base_url=os.getenv("EMBEDDING_BASE_URL") or os.getenv("LLM_BASE_URL") or None,
                    ),
                    collection_name="graph_rag_fallback",
                )
        except Exception:
            pass

    # ── 查询阶段 ─────────────────────────────
    def query(self, question: str, top_k: int = 5) -> Dict[str, any]:
        """
        自适应选择：
          - 全局型问题（"总结"/"整体"/"全景"）→ 社区摘要排序
          - 实体型问题（具体公司/技术）→ 子图遍历 + 向量兜底
        """
        if self._is_global_question(question):
            contexts = self._global_query(question, top_k)
            answer = self._synthesize_global(question, contexts)
        else:
            contexts = self._local_query(question, top_k)
            answer = self._synthesize_local(question, contexts)
        return {"question": question, "answer": answer, "contexts": contexts}

    @staticmethod
    def _is_global_question(q: str) -> bool:
        return any(k in q for k in ["总结", "综述", "全景", "整体", "总览", "概览", "全部关系"])

    def _global_query(self, q: str, top_k: int) -> List[str]:
        # 简单按社区 entity 数排序；实战可用 embedding 匹配 query vs summary
        ranked = sorted(self.communities, key=lambda c: len(c.entities), reverse=True)
        return [c.summary for c in ranked[:top_k]]

    def _local_query(self, q: str, top_k: int) -> List[Dict]:
        # 1) 找种子实体：先匹配名字 / 再退化到向量相似度（兜底）
        seeds: List[str] = []
        for ent in self.builder.entities.values():
            if ent.name.lower() in q.lower() or q.lower() in ent.name.lower():
                seeds.append(ent.name)
                break
        if not seeds and self.vectorstore is not None:
            try:
                docs = self.vectorstore.similarity_search(q, k=1)
                if docs:
                    seed_hint = EntityExtractor._normalize(docs[0].page_content[:30])
                    seeds = [s for s in self.builder.entities if s in seed_hint][:1] or list(self.builder.entities)[:1]
            except Exception:
                pass

        # 2) 1-2 跳子图
        contexts: List[Dict] = []
        if seeds:
            for s in seeds[:2]:
                for entity, hops in self.builder.neighbors_within_hops(s, max_hops=2):
                    rels = [r for r in self.builder.relations
                            if {r.source, r.target} == {s, entity} or r.source == entity or r.target == entity]
                    contexts.append({
                        "entity": entity,
                        "hops": hops,
                        "relations": [r.__dict__ for r in rels[:3]],
                    })
                    if len(contexts) >= top_k:
                        break

        # 3) Vector RAG 兜底
        if self.vectorstore is not None:
            try:
                extra = self.vectorstore.similarity_search(q, k=top_k)
                for e in extra:
                    contexts.append({"doc_snippet": e.page_content, "meta": e.metadata})
            except Exception:
                pass
        return contexts

    @staticmethod
    def _synthesize_global(q: str, summaries: List[str]) -> str:
        return f"【全局视角】{q}\n" + "\n".join(f"- {s}" for s in summaries)

    @staticmethod
    def _synthesize_local(q: str, contexts: List[Dict]) -> str:
        lines = [f"【子图 + 向量兜底】{q}", ""]
        for c in contexts:
            if "entity" in c:
                lines.append(f"实体 {c['entity']}（距种子 {c['hops']} 跳）：")
                for r in c["relations"]:
                    lines.append(f"  - {r['source']} —{r['relation']}→ {r['target']}")
            elif "doc_snippet" in c:
                lines.append(f"相关文档：{c['doc_snippet'][:120]}…")
        return "\n".join(lines)


# ─── 5. Demo 数据 ──────────────────────────────────

DEMO_DOCS = [
    Document(
        page_content=(
            "GraphRAG 是微软在 2024 年开源的 RAG 增强方案。它通过 LLM 从文档中抽取实体和关系，"
            "构建知识图谱，然后用 Leiden 算法做社区检测，生成社区摘要。"
            "在多跳推理（如 药物A → 副作用B → 禁忌人群C）场景下，效果显著优于传统 RAG。"
            "微软公司的 GraphRAG 项目在 GitHub 上获得了数万 Star。"
        ),
        metadata={"source": "demo-doc-1"},
    ),
    Document(
        page_content=(
            "AgenticRAG 让模型自主决定要查什么、查几次、怎么查。"
            "LangGraph 是 LangChain 的图框架，适合编排 Agentic RAG 的工作流。"
            "英伟达 (NVIDIA) 在生成式 AI 芯片领域占据主导地位，黄仁勋是公司创始人。"
            "阿里、字节、腾讯都在公司内部评测 Agentic RAG。"
        ),
        metadata={"source": "demo-doc-2"},
    ),
    Document(
        page_content=(
            "黄仁勋 (Jensen Huang) 领导的英伟达为 OpenAI 提供了大量 GPU。"
            "Sam Altman 是 OpenAI 的 CEO，他多次公开提到 Agentic RAG 的重要性。"
            "LangChain 和 LangGraph 都是 LangChain AI 公司的开源框架。"
        ),
        metadata={"source": "demo-doc-3"},
    ),
]


# ─── 6. 面试 Q&A ───────────────────────────────────

INTERVIEW_QAS = """
=== Q71：GraphRAG 与传统 RAG 的核心区别 ===
A:
- 核心答：数据组织形式不同
- 传统 RAG = 文本片段检索；GraphRAG = 实体-关系结构化图谱检索
- 多跳推理 GraphRAG 碾压 RAG（如药物-疾病-副作用的关联案例）

=== Q72：GraphRAG 工作流程 ===
A:
索引阶段：数据 → LLM 抽取实体/关系 (三元组) → 构建知识图谱 → Leiden 社区检测 → 生成社区摘要
查询阶段：
  - 全局总结 → 检索社区摘要 → LLM 综合
  - 实体查询 → 图遍历 1-2 跳 + 向量兜底 → Reranker → 生成

=== Q73：何时必须用 GraphRAG ===
A:
- 组织关系 / 供应链 / 审批链 / 依赖分析 → GraphRAG
- 多跳推理 / 全局总结 → GraphRAG
- FAQ / 政策查询 / 简单问答 → Classic RAG
- 路径不确定 / 跨系统调查 → Agentic RAG

=== Q74：GraphRAG 工业级 9 大避坑 ===
A:
1) 原生 GraphRAG 全量重构代价大 → LightRAG / FalkorDB 增量索引
2) GPT-4 抽取成本爆炸 → 微调 Qwen2.5-IE 等 7B/3B 小模型
3) 实体对齐失败 → Embedding + LLM 二次清洗 + 社区检测
4) Schema-Free 抽取关系爆炸 → 先自由跑 + 再固化 Schema
5) 2-Hop 邻居一股脑塞 LLM → 语义剪枝
6) 子图自然语言塞 LLM → 改 YAML / Markdown 列表
7) Graph 替代 Vector → 错！两者互补，RRF 融合
8) 没有数据血缘 → 边刻 Source Doc ID + Chunk ID
9) 图片 Base64 入图库 → 对象存储 + 向量存 Embedding + 图存元数据
"""


# ─── 7. 演示 ───────────────────────────────────────

def run_demo():
    print("\n" + "=" * 60)
    print("Demo 11: GraphRAG 离线 Mock 演示")
    print("=" * 60)

    pipe = GraphRAGPipeline(use_llm=False)
    pipe.index_documents(DEMO_DOCS)

    print(f"\n📊 索引结果")
    print(f"- 实体数: {len(pipe.builder.entities)}")
    print(f"- 关系数: {len(pipe.builder.relations)}")
    print(f"- 社区数: {len(pipe.communities)}")

    print(f"\n🔍 全局查询")
    r1 = pipe.query("GraphRAG 和 RAG 的整体关系总结")
    print(r1["answer"][:400])

    print(f"\n🔍 实体查询")
    r2 = pipe.query("黄仁勋 关联到哪些公司")
    print(r2["answer"][:600])


if __name__ == "__main__":
    print(INTERVIEW_QAS)
    run_demo()
