# Azure OpenAI 配置指南

本指南将帮助您配置项目以使用 Microsoft Azure OpenAI 服务。

## 前提条件

1. 拥有 Azure 账户
2. 已启用 Azure OpenAI 服务访问权限
3. 已完成项目的基本环境设置

## 步骤 1：创建 Azure OpenAI 资源

1. 登录 [Azure 门户](https://portal.azure.com/)
2. 点击 "创建资源"
3. 搜索 "OpenAI" 并选择 "Azure OpenAI"
4. 填写以下信息：
   - **订阅**：选择您的 Azure 订阅
   - **资源组**：创建新的或选择现有的资源组
   - **区域**：选择支持 OpenAI 的区域（如 East US、West Europe 等）
   - **名称**：为您的资源命名（如 `my-openai-resource`）
   - **定价层**：选择适合的定价层

## 步骤 2：部署模型

1. 在 Azure OpenAI 资源中，导航到 "模型部署"
2. 点击 "创建新部署"
3. 选择要部署的模型：
   - **GPT-4**：用于聊天和文本生成
   - **GPT-3.5-turbo**：更经济的聊天选项
   - **text-embedding-ada-002**：用于嵌入向量（如果需要）

4. 为每个部署指定名称（记住这些名称，稍后配置时需要）

## 步骤 3：获取配置信息

1. 在 Azure OpenAI 资源中，导航到 "密钥和终结点"
2. 复制以下信息：
   - **密钥 1** 或 **密钥 2**
   - **终结点**

## 步骤 4：配置环境变量

创建或更新您的 `.env` 文件：

```bash
# Azure OpenAI 配置
AZURE_OPENAI_API_KEY=your-azure-openai-api-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# 模型配置
MODEL=azure_openai/gpt-4

# 可选：如果部署名称与模型名称不同
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=your-gpt4-deployment-name
AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME=your-embedding-deployment-name
```

### 配置说明

- **AZURE_OPENAI_API_KEY**：从 Azure 门户获取的 API 密钥
- **AZURE_OPENAI_ENDPOINT**：您的 Azure OpenAI 资源终结点
- **AZURE_OPENAI_API_VERSION**：API 版本，建议使用最新稳定版本
- **MODEL**：使用 `azure_openai/` 前缀指定 Azure OpenAI 模型
- **部署名称**：如果您的部署名称与标准模型名称不同，请设置这些变量

## 步骤 5：验证配置

运行以下命令验证配置是否正确：

```bash
# 激活虚拟环境
source .venv/bin/activate  # macOS/Linux
# 或 .venv\Scripts\activate  # Windows

# 验证 Azure OpenAI 连接
python -c "
from langchain.chat_models import init_chat_model
import os
from dotenv import load_dotenv

load_dotenv()
model = init_chat_model('azure_openai/gpt-4')
print('Azure OpenAI 配置成功！')
"
```

## 常见问题

### Q: 如何选择合适的区域？
A: 选择距离您最近且支持所需模型的区域。常用区域包括：
- East US
- West Europe  
- Canada East
- Australia East

### Q: 为什么我无法访问某些模型？
A: 一些模型（如 GPT-4）需要申请访问权限。请在 Azure OpenAI Studio 中申请访问。

### Q: 如何监控使用量和成本？
A: 在 Azure 门户中，您可以在 "成本管理 + 计费" 部分监控使用情况。

### Q: 部署名称和模型名称有什么区别？
A: 部署名称是您在 Azure 中为模型部署指定的自定义名称，而模型名称是 OpenAI 的标准模型名称（如 gpt-4）。

## 支持的模型

### 聊天模型
- `azure_openai/gpt-4`
- `azure_openai/gpt-35-turbo`
- `azure_openai/gpt-4-32k`（如果可用）

### 嵌入模型
- `azure_openai/text-embedding-ada-002`
- `azure_openai/text-embedding-3-small`
- `azure_openai/text-embedding-3-large`

## 安全最佳实践

1. **不要在代码中硬编码 API 密钥**
2. **使用环境变量存储敏感信息**
3. **定期轮换 API 密钥**
4. **设置适当的访问控制和权限**
5. **监控异常使用模式**

## 故障排除

如果遇到问题，请检查：

1. **API 密钥是否正确**：确保复制了完整的密钥
2. **终结点 URL 是否正确**：应以 `https://` 开头，以 `.openai.azure.com/` 结尾
3. **模型是否已部署**：确保在 Azure 中已成功部署所需模型
4. **区域是否支持**：某些模型可能在特定区域不可用
5. **配额是否足够**：检查是否达到了使用配额限制

需要更多帮助，请参考 [Azure OpenAI 官方文档](https://learn.microsoft.com/azure/ai-services/openai/)。
