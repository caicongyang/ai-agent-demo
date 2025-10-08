#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from WXPublisher import WeixinRenderer
import mistune

# 创建测试用的 Markdown 内容
test_md = '''
# 🚀 LangGraph 完整指南

## 📌 PDF 文档解析

PDF 文档解析有两种方式：

### 🔧 高级 PDF 解析

- 检测文件类型（通过文件扩展名）
- 根据文件类型调用对应的解析器
- 将解析结果转换为 LangChain Document 对象
- 返回 Document 对象列表供后续处理

### ⚡ 快速 PDF 解析（当高级解析失败时）

- 使用 UnstructuredPaddlePDFLoader 加载 PDF
- 该加载器使用 PyMuPDF (fitz) 库提取文本内容
- 以页为单位提取文本并创建 Document 对象

整体解析流程如下：

1. 检测文件类型（通过文件扩展名）
2. 根据文件类型调用对应的解析器
3. 将解析结果转换为 LangChain Document 对象
4. 返回 Document 对象列表供后续处理

💡 这是一个提示信息，展示特殊样式！

⚠️ 注意：请确保正确配置环境变量。

> 这是一个引用块，用于展示重要信息。

```python
def hello_world():
    print("Hello, WeChat!")
    return "success"
```

---

**重要内容**会被特别标记，*斜体内容*也有特殊样式。

[📚 查看文档](https://docs.example.com) | [🔗 GitHub](https://github.com/example)
'''

def main():
    print('开始生成HTML文件...')
    
    # 创建渲染器并转换
    renderer = WeixinRenderer()
    parser = mistune.create_markdown(renderer=renderer, plugins=['table', 'strikethrough', 'footnotes'])
    html_content = parser(test_md)
    
    print('HTML 转换完成')
    
    # 创建完整的HTML文档
    full_html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>微信公众号样式测试</title>
    <style>
        body {{
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
    </style>
</head>
<body>
    {html_content}
</body>
</html>'''
    
    # 保存到文件
    with open('wx_style_test.html', 'w', encoding='utf-8') as f:
        f.write(full_html)
    
    print('✅ HTML文件已保存为: wx_style_test.html')
    print('📁 可以用浏览器打开查看效果')

if __name__ == '__main__':
    main()
