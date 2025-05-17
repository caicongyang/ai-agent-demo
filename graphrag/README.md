# GraphRAG 最小演示

这是一个基于 LlamaIndex 概念的 GraphRAG（基于图的检索增强生成）最小演示。

## 什么是 GraphRAG？

GraphRAG 结合了知识图谱与检索增强生成（RAG），以提升大语言模型（LLM）的响应能力。其流程如下：

1. 从文档中抽取实体和关系
2. 根据抽取的信息构建知识图谱
3. 利用知识图谱为问答提供结构化上下文

## 本演示的特点

本仓库包含两个演示：

### 1. 简单内存版演示（`graphrag_demo.py`）
- 纯内存实现（无需 Neo4j）
- 使用 LLM 从文本中抽取实体和关系
- 构建基础知识图谱
- 提供简单的查询引擎，基于图谱回答问题

### 2. 基于 Neo4j 的演示（`graphrag_neo4j_demo.py`）
- 集成 Neo4j 图数据库
- 使用 LlamaIndex 的 Neo4jPropertyGraphStore
- 演示如何结合外部图数据库使用 PropertyGraphIndex
- 更贴近 LlamaIndex 官方文档的实现方式

## 环境搭建

1. 安装依赖包：
   ```
   pip install -r requirements.txt
   ```

2. 基于 `env.example` 文件创建 `.env` 文件：
   ```
   cp env.example .env
   ```

3. 在 `.env` 文件中填写你的 OpenAI API Key

4. （如需运行 Neo4j 演示）配置 Neo4j：
   
   **方式一：推荐使用 Docker Compose**
   ```
   docker-compose up -d
   ```
   
   **方式二：直接使用 Docker**
   ```
   docker run \
     -p 7474:7474 -p 7687:7687 \
     -v $PWD/neo4j/data:/data -v $PWD/neo4j/plugins:/plugins \
     --name neo4j-apoc \
     -e NEO4J_AUTH=neo4j/password \
     -e NEO4J_apoc_export_file_enabled=true \
     -e NEO4J_apoc_import_file_enabled=true \
     -e NEO4J_apoc_import_file_use__neo4j__config=true \
     -e NEO4JLABS_PLUGINS=["apoc"] \
     neo4j:latest
   ```
   
   然后：
   - 在浏览器中打开 http://localhost:7474/
   - 使用默认账号密码 neo4j/password 登录
   - 首次登录会要求修改密码
   - 在 `.env` 文件中更新你的新密码

## 如何运行演示

### 简单内存版演示

```
python graphrag_demo.py
```

### 基于 Neo4j 的演示

```
python graphrag_neo4j_demo.py
```

两个演示都会：
1. 初始化 GraphRAG 组件
2. 处理示例文档
3. 抽取实体和关系
4. 构建知识图谱
5. 基于图谱回答示例问题

## 关键组件说明

1. **GraphRAGExtractor**：从文本中抽取实体和关系
2. **GraphRAGStore**：存储知识图谱（内存或 Neo4j）
3. **GraphRAGQueryEngine**：利用知识图谱回答问题

## 进阶建议

如需更高级的实现，可考虑：
- 实现高级社区发现算法
- 增加基于向量的检索能力
- 集成向量数据库，实现混合检索
- 自定义图遍历策略

## 了解更多

想了解更多 GraphRAG 相关内容，请参考：
- [LlamaIndex GraphRAG 官方文档](https://docs.llamaindex.ai/en/stable/examples/cookbooks/GraphRAG_v2/) 