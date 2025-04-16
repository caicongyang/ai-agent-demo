# FastGPT 文档解析系统

FastGPT 支持多种文档格式的解析，包括 PDF、Word、Excel、PowerPoint 等。本文档详细介绍了各类文档的解析方式和技术实现。

## 支持的文档类型

FastGPT 目前支持以下文档类型：
- PDF (.pdf)
- Word (.docx)
- Excel (.xlsx)
- PowerPoint (.pptx)
- CSV (.csv)
- HTML (.html)
- Markdown (.md)
- 纯文本 (.txt)

## 解析系统架构

文档解析系统主要集中在 `packages/service/worker/readFile` 目录下，采用模块化设计，为每种文件类型提供专门的解析器。

### 核心流程

1. 接收文件 buffer 和文件类型
2. 根据文件扩展名分发到对应的解析器
3. 解析器处理文件并返回标准格式的结果
4. 处理结果传递给后续的文本分析和 AI 处理模块

## PDF 文档解析

FastGPT 提供三种方式解析 PDF：

### 1. 系统默认解析方式

使用 PDF.js 库进行解析，代码位于 `packages/service/worker/readFile/extension/pdf.ts`：

- 逐页处理 PDF，提取文本内容
- 过滤页眉页脚(通过位置信息判断)
- 处理段落结束标记和换行符
- 合并所有页面内容

### 2. 自定义 PDF 解析服务

可以配置外部服务来解析 PDF：

- 配置外部服务 URL 和认证 token
- 通过 FormData 发送 PDF 文件
- 接收处理结果并进行图像处理
- 支持提取文档中的图像

### 3. Doc2x 解析服务

使用专业的 Doc2x 服务解析复杂 PDF：

- 预上传、上传文件、轮询结果的多步骤流程
- 处理复杂表格和图像
- 转换 HTML 表格为 Markdown 格式
- 保留文档结构和排版

## Word 文档 (DOCX) 解析

Word 文档解析代码位于 `packages/service/worker/readFile/extension/docx.ts`：

- 使用 mammoth 库将 docx 转换为 HTML
- 处理文档中的图像，提取为 base64 并存储
- 调用 html2md 将 HTML 转换为 Markdown 格式
- 保留文档结构和格式

## Excel 文档 (XLSX) 解析

Excel 文档解析代码位于 `packages/service/worker/readFile/extension/xlsx.ts`：

- 使用 node-xlsx 库解析 Excel 文件
- 针对多个工作表进行处理，逐表转换
- 首先转换为 CSV 格式
- 再转换为 Markdown 表格格式，保留表头和内容
- 处理特殊字符(如换行符)

## PowerPoint 文档 (PPTX) 解析

PowerPoint 文档解析代码位于：
- `packages/service/worker/readFile/extension/pptx.ts`
- `packages/service/worker/readFile/parseOffice.ts`

解析流程：
- 将 PPTX 文件解压缩，提取 XML 内容
- 使用正则表达式识别幻灯片内容文件
- 解析 XML 格式，提取文本节点内容
- 合并所有幻灯片的文本

## HTML 和 Markdown 转换

系统使用 TurndownService 进行 HTML 到 Markdown 的转换，代码位于 `packages/service/worker/htmlStr2Md/utils.ts`：

- 处理图像、表格和样式
- 保留文档结构
- 支持 GFM (GitHub Flavored Markdown)

## 图像处理

在解析过程中，系统会处理文档中的图像：

- 提取文档中的图像为 base64 格式
- 生成唯一 ID 链接图像和文本
- 支持各种图像格式

## 表格处理

系统对表格有特殊处理：

- HTML 表格转换为 Markdown 表格
- 保留表头和内容
- 处理合并单元格
- 对 Excel 和 CSV 文件的表格进行专门处理

## 输出格式

所有解析器返回统一的标准格式结果：

```typescript
type ReadFileResponse = {
  rawText: string;     // 原始文本内容
  formatText?: string; // 格式化后的文本(如Markdown)
  imageList?: ImageType[]; // 文档中的图像列表
};
```

## 技术实现要点

1. **模块化设计**：每种文件类型有独立的解析器
2. **统一输出格式**：标准化的返回结果便于后续处理
3. **可扩展性**：支持接入外部服务进行解析
4. **图像和表格处理**：保留更多原始文档信息
5. **文本格式化**：将不同格式统一转换为 Markdown 

## 复杂数据公式的解析

FastGPT 在处理 PDF 中的复杂数学公式和数据公式时采用了多种技术手段：

### 公式解析方法

1. **基础文本提取**：
   - 对于简单的内联公式，PDF.js 可以提取基本文本内容
   - 系统会尝试保留公式的原始格式

2. **Doc2x 高级解析**：
   - 复杂数学公式主要依赖 Doc2x 服务进行处理
   - Doc2x 能够识别 LaTeX 格式的数学表达式
   - 处理后的公式会以 LaTeX 格式保留在文本中

3. **特殊公式处理**：
   - 系统会识别并保留 `$formula$` 格式的 LaTeX 表达式
   - 对于复杂公式，会进行特殊的后处理

### 公式标记处理

FastGPT 在 Doc2x 处理过程中会进行以下格式转换：

```javascript
// 调整带标签的公式格式
.replace(/\$(.+?)\s+\\tag\{(.+?)\}\$/g, '$$$1 \\qquad \\qquad ($2)$$')

// 修正下标处理
.replace(/\\text\{([^}]*?)(\b\w+)_(\w+\b)([^}]*?)\}/g, '\\text{$1$2\\_$3$4}')
```

### 图像化公式处理

对于无法直接以文本形式提取的复杂公式：

1. 系统会将公式作为图像提取
2. 为图像生成唯一 ID
3. 在文本中通过图像引用保留公式
4. 最终可以通过图像呈现复杂公式

### 集成方式

复杂公式的处理主要集成在 PDF 解析流程中，特别是在 Doc2x 服务的后处理部分：

- 位于 `packages/service/common/file/read/utils.ts` 文件中
- 作为 `parsePdfFromDoc2x` 函数的一部分
- 通过正则表达式和字符串替换实现格式转换

总体而言，FastGPT 对复杂数学公式的处理采用了文本提取和图像提取相结合的方式，对于特别复杂的公式主要依赖外部专业服务（如 Doc2x）进行解析。

## 文档召回优化技术

FastGPT 在文档召回方面采用了多种先进技术和优化方法，大幅提升了检索的准确性和相关性。

### 1. 多查询检索技术

FastGPT 实现了多查询策略来提高召回效果：

#### 查询扩展 (Query Extension)

通过 AI 生成多个与原始查询语义相关但表达不同的查询变体：

- 使用 LLM 模型分析原始问题并生成多个相关查询
- 根据历史对话上下文消除指代不明确的问题
- 自动过滤重复或高度相似的查询
- 查询扩展实现在 `packages/service/core/ai/functions/queryExtension.ts`

示例：当用户查询"怎么解决"时，系统可能会扩展为：
- "Nginx报错'no connection'如何解决？"
- "造成'no connection'报错的原因"
- "Nginx提示'no connection'，要怎么办？"

#### 多查询结果合并

使用 RRF (Reciprocal Rank Fusion) 算法合并多个查询的结果：

- 为不同查询结果根据排名分配分数
- 同一文档在多个查询中出现时，分数会累加
- 最终根据累计分数重新排序
- 实现在 `packages/global/core/dataset/search/utils.ts` 中的 `datasetSearchResultConcat` 函数

### 2. 混合检索策略

同时使用多种检索方法并智能融合结果：

#### 向量检索 (Embedding Search)

- 使用先进的嵌入模型将查询和文档转换为向量
- 通过向量相似度计算找到语义相关的文档
- 支持 PostgreSQL 和 Milvus 等向量数据库

#### 全文检索 (Full-Text Search)

- 使用 MongoDB 的全文索引功能
- 通过结巴分词优化中文检索效果
- 提高对关键词匹配的精确度

#### 动态权重调整

- 允许设置向量检索和全文检索的权重比例
- 通过 `embeddingWeight` 参数动态调整两种方法的影响
- 使用 RRF 算法智能合并两种检索结果

### 3. 重排序技术 (ReRank)

通过额外的相关性评估模型对初步检索结果进行更精确的排序：

- 使用专门的重排序模型评估查询与文档的相关性
- 每个文档获得一个相关性分数
- 与基础检索结果通过 RRF 算法融合
- 实现在 `packages/service/core/ai/rerank/index.ts`

### 4. 深度 RAG 技术

FastGPT 实现了递归式的检索增强技术：

- 分析初步检索结果，生成更精确的后续查询
- 多轮次递归检索，不断优化结果质量
- 通过 `deepRagSearch` 功能实现，支持设置最大递归次数
- 可以设置相关背景信息引导搜索方向

### 5. 过滤和去重机制

为提高结果质量，FastGPT 实现了多种过滤机制：

#### 相似度过滤

- 通过 `similarity` 参数设置最低相似度阈值
- 根据不同搜索模式应用不同的相似度计算

#### 内容去重

- 对检索结果进行智能去重
- 删除标点符号和空格后比较文本内容
- 使用哈希函数加速比较过程
- 实现在 `searchDatasetData` 函数中的 `filterSameDataResults`

#### 元数据过滤

- 支持通过文档的元数据信息进行过滤
- 可以指定集合级别的过滤条件
- 允许高级用户使用 JSON 格式定义复杂的过滤规则

### 6. RRF 融合算法

FastGPT 使用 Reciprocal Rank Fusion (RRF) 算法智能融合多种来源的搜索结果：

- 为每个文档分配一个 RRF 分数：`score = 1 / (k + rank)`
- 将多个结果列表中同一文档的分数累加
- 根据累计分数重新排序
- `k` 值可以调整以控制排名影响程度
- 实现在 `datasetSearchResultConcat` 函数中

### 技术亮点总结

1. **多层次优化**：从查询生成、多种检索方法、重排序到深度 RAG，全方位提升召回质量
2. **智能结果融合**：使用 RRF 算法高效合并多来源结果
3. **自适应权重**：允许调整不同检索方法和重排序的权重
4. **灵活配置**：提供丰富的参数，适应不同场景需求
5. **去重和过滤**：通过多种机制保证结果的多样性和质量

这些技术的组合使 FastGPT 能够在海量文档中快速找到最相关的内容，大幅提升了 RAG 应用的效果和用户体验。 