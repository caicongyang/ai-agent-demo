"""
面试题：AI Agent 友好的爬虫与网页解析
========================================

来源：小红书《开源智能爬虫框架：Crawl4AI 快速入门》、微信 /《LangChain 进阶 | 用 Crawl4AI 装"爬虫大脑"》、《零代码 AgentBrowser》

问题域（对应 Agent 面试问答全集 - 十九 - 爬虫 / RAG）：
  - Q59：AI Agent 友好的爬虫 vs 传统爬虫
  - Q60：AI Agent 必备的爬虫能力 / 工具栈
  - Q61：如何设计 LLM-friendly 的网页解析与反爬策略

面试回答要点：
  - 传统爬虫面向 HTML 标签：CSS / XPath 选择器脆弱
  - AI 爬虫面向语义：
      1) 输出干净 Markdown（Crawl4AI fit_markdown）
      2) 自适应抓取：覆盖度 / 一致性 / 饱和度 评估何时停
      3) 多级过滤器：PruningContentFilter / BM25ContentFilter / LLMContentFilter
  - AI Agent 把"抓取"变成"工具"：load_webpage(url) -> clean markdown -> chunk -> embed
  - 反爬：UA 轮换、限速、代理池、robots.txt 遵守

技术栈：requests + BeautifulSoup + 自适应 parser + LangChain Document + Chroma 向量库
"""

from __future__ import annotations

import os
import re
import time
import hashlib
import logging
import urllib.parse
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()
log = logging.getLogger("crawler_agent")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")


# ─── 1. 核心数据结构 ────────────────────────────────

@dataclass
class CrawlResult:
    """单次抓取结果"""
    url: str
    title: str
    clean_text: str
    markdown: str
    links: List[str] = field(default_factory=list)
    content_hash: str = ""
    fetched_at: str = ""

    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = hashlib.sha256(self.clean_text.encode()).hexdigest()[:12]
        if not self.fetched_at:
            self.fetched_at = datetime.now().isoformat()


# ─── 2. 自适应爬虫：覆盖度 / 一致性 / 饱和度评估 ──────────

class AdaptiveCrawler:
    """
    灵感来源：Crawl4AI 的 AdaptiveCrawler
    核心思想：滚动抓取过程中实时计算三个指标，达到阈值后自动停止。

    - Coverage：累计拿到的主题（关键词）数 vs 期望主题数
    - Consistency：相邻 batch 抓到的内容重合度
    - Saturation：   新增信息的边际收益（每个新 batch 带来的 new_ratio）
    """

    def __init__(self, query: str, max_pages: int = 20,
                 saturation_threshold: float = 0.15):
        self.query = query
        self.query_keywords = set(self._extract_keywords(query))
        self.max_pages = max_pages
        self.saturation_threshold = saturation_threshold

        self.visited: Dict[str, CrawlResult] = {}
        self.seen_phrases: set = set()

    @staticmethod
    def _extract_keywords(query: str) -> List[str]:
        """极简中文/英文分词：按空格 & 常见停用词切"""
        stop = {"the", "a", "an", "of", "in", "to", "is", "and", "or", "的", "了", "是", "在"}
        tokens = re.split(r"\s+|[，。？、]", query.lower())
        return [t for t in tokens if t and t not in stop and len(t) > 1]

    def should_stop(self, batch_new_ratio: float, batch_size: int) -> bool:
        """判断是否到达饱和度"""
        if len(self.visited) >= self.max_pages:
            log.info("[STOP] 已达 max_pages=%d", self.max_pages)
            return True
        if batch_size == 0:
            return True
        if batch_new_ratio < self.saturation_threshold and len(self.visited) > 5:
            log.info("[STOP] 饱和度 %.2f < 阈值 %.2f", batch_new_ratio, self.saturation_threshold)
            return True
        return False

    def compute_coverage(self) -> float:
        """已抓取内容覆盖 query 关键词比例"""
        if not self.query_keywords:
            return 1.0
        all_text = " ".join(r.clean_text for r in self.visited.values())
        hit = sum(1 for kw in self.query_keywords if kw in all_text.lower())
        return hit / len(self.query_keywords)

    def compute_saturation(self, recent_texts: List[str]) -> float:
        """新文本中的新短语比例（越低越饱和）"""
        all_phrases = set()
        for t in recent_texts:
            phrases = set(re.findall(r"\b[\u4e00-\u9fa5]{2,}\b", t))
            all_phrases.update(phrases)
        new = all_phrases - self.seen_phrases
        ratio = len(new) / max(len(all_phrases), 1)
        self.seen_phrases.update(all_phrases)
        return ratio


# ─── 3. 内容过滤器（多层） ────────────────────────────

class ContentFilter:
    """基础接口：输入原始文本，输出保留的文本块"""

    def filter(self, text: str) -> str:  # noqa
        raise NotImplementedError


class PruningFilter(ContentFilter):
    """按文本 / 链接密度评分：去除导航、广告、菜单"""

    NOISE_PATTERNS = [
        r"^.*(导航|菜单|登录|注册|订阅|广告|推广).*$",
        r"^\s*$",
        r"^\s*(Copyright|©|All Rights Reserved).*$",
        r"^\s*(分享到|扫码|微信扫一扫).*$",
    ]

    def filter(self, text: str) -> str:
        lines = text.split("\n")
        kept = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if any(re.match(p, line, re.IGNORECASE) for p in self.NOISE_PATTERNS):
                continue
            # 链接密度：链接数 / 字符数
            link_count = line.count("http")
            if len(line) > 20 and link_count / max(len(line), 1) > 0.05:
                continue
            kept.append(line)
        return "\n".join(kept)


class BM25ContentFilter(ContentFilter):
    """按 query 相关性过滤（BM25 简化版）"""

    def __init__(self, query: str, top_ratio: float = 0.6):
        self.query_terms = set(re.findall(r"\b\w{2,}\b", query.lower()))
        self.top_ratio = top_ratio

    @staticmethod
    def _score(text: str, terms: set) -> float:
        text_lower = text.lower()
        if not terms:
            return 1.0
        hit = sum(1 for t in terms if t in text_lower)
        length_norm = max(len(text_lower.split()), 1)
        return hit / length_norm * 10

    def filter(self, text: str) -> str:
        paragraphs = [p for p in text.split("\n\n") if p.strip()]
        scored = [(self._score(p, self.query_terms), p) for p in paragraphs]
        scored.sort(reverse=True)
        keep_count = max(1, int(len(scored) * self.top_ratio))
        kept = [p for _, p in scored[:keep_count]]
        return "\n\n".join(kept)


# ─── 4. Web Fetcher（兼容真实 / 模拟数据） ──────────────

class WebFetcher:
    """爬取单页；优先 requests，失败则用内置演示数据"""

    def __init__(self, user_agent: str = "Mozilla/5.0 (AgentBot; crawl4ai-style)",
                 delay_seconds: float = 0.5):
        self.user_agent = user_agent
        self.delay = delay_seconds

    def fetch(self, url: str, retries: int = 2) -> Optional[CrawlResult]:
        for attempt in range(retries):
            try:
                import requests
                from bs4 import BeautifulSoup
                resp = requests.get(
                    url,
                    headers={"User-Agent": self.user_agent},
                    timeout=10,
                )
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                title = (soup.title.string if soup.title and soup.title.string else url).strip()
                for tag in soup(["script", "style", "nav", "footer", "aside"]):
                    tag.decompose()
                body = soup.get_text(separator="\n", strip=True)
                links = [a["href"] for a in soup.find_all("a", href=True)]
                time.sleep(self.delay)
                md = self._to_markdown(soup, body)
                return CrawlResult(url=url, title=title, clean_text=body, markdown=md, links=links)
            except Exception as e:
                log.warning("fetch %s attempt %d failed: %s", url, attempt + 1, e)
                time.sleep(self.delay)
        return None

    @staticmethod
    def _to_markdown(soup, body: str) -> str:
        """粗糙的 HTML -> Markdown：根据 heading 标签"""
        from bs4 import BeautifulSoup
        if not isinstance(soup, BeautifulSoup):
            return body
        lines = []
        for el in soup.find_all(["h1", "h2", "h3", "p", "li"]):
            txt = el.get_text(strip=True)
            if not txt:
                continue
            tag = el.name
            if tag == "h1":
                lines.append(f"# {txt}")
            elif tag == "h2":
                lines.append(f"## {txt}")
            elif tag == "h3":
                lines.append(f"## {txt}")
            elif tag == "li":
                lines.append(f"- {txt}")
            else:
                lines.append(txt)
        return "\n\n".join(lines)


# ─── 5. Crawler Agent：把爬虫封装成 LangChain 工具 ────────

class CrawlerAgent:
    """高层封装：用户给 query，自动调度自适应爬虫 + 过滤 + 切片，可灌入 RAG"""

    def __init__(self, fetcher: Optional[WebFetcher] = None):
        self.fetcher = fetcher or WebFetcher()
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=80)
        self.results: List[CrawlResult] = []

    def crawl_and_index(self, urls: List[str], query: str) -> List[Document]:
        """
        主入口：从 urls 抓取、按 query 过滤、切分，返回 LangChain Document 列表
        """
        ac = AdaptiveCrawler(query=query)
        pruning = PruningFilter()
        bm25 = BM25ContentFilter(query=query)

        for url in urls:
            if len(ac.visited) >= ac.max_pages:
                break
            result = self.fetcher.fetch(url)
            if result is None:
                continue
            # Step 1: 清洗噪声
            cleaned = pruning.filter(result.clean_text)
            # Step 2: 按相关性筛段落
            cleaned = bm25.filter(cleaned)
            result.clean_text = cleaned
            ac.visited[url] = result
            self.results.append(result)

            # 计算 batch 内 saturation
            recent = [r.clean_text for r in list(ac.visited.values())[-3:]]
            ratio = ac.compute_saturation(recent)
            if ac.should_stop(ratio, batch_size=len(recent)):
                break

        coverage = ac.compute_coverage()
        log.info("Crawled %d pages, coverage=%.2f", len(ac.visited), coverage)

        # Step 3: 转 LangChain Document & 切分
        docs: List[Document] = []
        for r in ac.visited.values():
            chunks = self.splitter.split_text(r.markdown or r.clean_text)
            for i, c in enumerate(chunks):
                docs.append(Document(
                    page_content=c,
                    metadata={
                        "url": r.url,
                        "title": r.title,
                        "chunk_id": f"{r.content_hash}-{i}",
                        "fetched_at": r.fetched_at,
                    },
                ))
        return docs

    def to_rag(self, docs: List[Document]) -> Optional["Chroma"]:
        """可选：把结果直接灌进 Chroma 向量库"""
        try:
            from langchain_openai import OpenAIEmbeddings
            from langchain_chroma import Chroma
        except ImportError:
            log.warning("langchain_openai / langchain_chroma 未安装")
            return None
        api_key = os.getenv("EMBEDDING_API_KEY") or os.getenv("LLM_API_KEY") or ""
        if not api_key or api_key == "your-llm-api-key":
            log.info("未配置真实 API key，跳过 Chroma 写入（演示模式）")
            return None
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=api_key,
            base_url=os.getenv("EMBEDDING_BASE_URL") or os.getenv("LLM_BASE_URL") or None,
        )
        return Chroma.from_documents(docs, embeddings, collection_name="web_crawler")


# ─── 6. 演示（无需联网 / 无需 API Key 也能跑） ──────────

DEMO_URLS = [
    "https://example.com/graph-rag-intro",
    "https://example.com/agentic-rag-overview",
]


def run_demo():
    """演示：跑一次 crawl + filter + chunk，不依赖 LLM API"""
    agent = CrawlerAgent(fetcher=WebFetcher())
    # 用离线 mock 替换真实 fetcher，方便离线演示
    agent.fetcher = _MockFetcher()
    docs = agent.crawl_and_index(DEMO_URLS, query="GraphRAG 实体抽取 多跳推理")
    print(f"\n✅ 抓取并切分得到 {len(docs)} 个 Document")
    for d in docs[:3]:
        print("─" * 60)
        print(f"URL: {d.metadata['url']}")
        print(f"Title: {d.metadata['title']}")
        print(f"Content snippet: {d.page_content[:200]}…")


class _MockFetcher:
    """离线演示用 fetcher：返回示例数据，不联网"""

    MOCK_PAGES = [
        {
            "url": "https://example.com/graph-rag-intro",
            "title": "GraphRAG 入门：实体抽取与社区检测",
            "body": (
                "导航 首页 文档 博客 关于\n"
                "GraphRAG 入门：实体抽取与社区检测\n\n"
                "GraphRAG 通过 LLM 抽取实体和关系三元组，构建知识图谱。\n"
                "抽取阶段使用 LLM 提取 SPOT 实体（人物/公司/事件）。\n"
                "再聚类出社区，生成社区摘要，方便全局总结。\n"
                "传统 RAG 在多跳推理时召回差，GraphRAG 能沿关系路径走 2 跳。\n"
                "广告：加入 AI 训练营 扫码立即报名\n"
                "© 2026 Example Inc. All Rights Reserved.\n"
            ),
            "links": ["https://example.com/agentic-rag-overview"],
        },
        {
            "url": "https://example.com/agentic-rag-overview",
            "title": "Agentic RAG 让模型学会如何使用资料",
            "body": (
                "导航 首页 文档 博客 关于\n"
                "Agentic RAG 让模型学会如何使用资料\n\n"
                "传统 RAG 是 检索-生成 的固定流水线。\n"
                "Agentic RAG 让模型自主决定查什么、查几次、怎么查，必要时还能调用工具。\n"
                "Self-RAG 引入 reflection tokens，让模型边生成边反思证据是否支撑。\n"
                "订阅获取最新 AI 资讯\n"
            ),
            "links": [],
        },
    ]

    def fetch(self, url: str, retries: int = 1) -> CrawlResult:
        for m in self.MOCK_PAGES:
            if m["url"] == url:
                md = self._to_md(m["body"])
                return CrawlResult(url=url, title=m["title"], clean_text=m["body"], markdown=md, links=m["links"])
        return None

    @staticmethod
    def _to_md(body: str) -> str:
        md = re.sub(r"^(导航 首页 文档 博客 关于|广告.*|©.*|订阅.*)$", "", body, flags=re.MULTILINE)
        return md.strip()


# ─── 7. 面试 Q&A（文件内自带速查） ──────────────────────

INTERVIEW_QAS = """
=== Q59：AI Agent 友好的爬虫 vs 传统爬虫 区别 ===
A:
- 传统：CSS 选择器脆弱、网站改版全挂；只输出 HTML 噪声大
- AI 友好：
  1) 干净 Markdown 输出（Crawl4AI fit_markdown）
  2) 自适应抓取：覆盖度/一致性/饱和度 评估何时停
  3) LLMContentFilter / BM25ContentFilter / PruningContentFilter

=== Q60：AI Agent 必备的爬虫能力 / 工具栈 ===
A:
- 静态：requests + BeautifulSoup
- 动态：playwright / pyppeteer
- LLM-friendly：Crawl4AI / Jina Reader / Firecrawl
- 反爬：UA 轮换、限速、代理池、robots.txt 遵守
- 协议层：MCP Server (web-fetch) 标准化暴露

=== Q61：Agent 时代下爬虫的根本变化 ===
A:
- 从面向 HTML 标签 → 面向语义与目标
- Cloudflare 已经分类（传统爬虫 / AI 训练爬虫 / Agent 爬虫），Agent 爬虫需付费
- 法律上 robots.txt 可屏蔽 AI 训练抓取
- 工程上：将爬虫封装为 LangChain 工具，让 Agent 自主调度
"""


if __name__ == "__main__":
    print("=" * 60)
    print("Demo 10: AI Agent 友好的爬虫（Crawl4AI 范式）")
    print("=" * 60)
    print(INTERVIEW_QAS)
    print("\n--- 离线演示（无需联网 / API Key） ---")
    run_demo()
    print("\n💡 完整使用：在 .env 配置 LLM_API_KEY 后, run `crawler.to_rag(docs)` 灌入向量库")
