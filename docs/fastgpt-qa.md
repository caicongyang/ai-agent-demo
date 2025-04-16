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