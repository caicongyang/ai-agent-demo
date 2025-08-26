#!/usr/bin/env python3
"""
测试 Azure OpenAI 配置的脚本

运行此脚本来验证您的 Azure OpenAI 配置是否正确设置。
"""

import os
import sys
from dotenv import load_dotenv

def test_azure_openai_config():
    """测试 Azure OpenAI 配置"""
    
    # 加载环境变量
    load_dotenv()
    
    print("🔍 检查 Azure OpenAI 环境变量...")
    
    # 检查必需的环境变量
    required_vars = [
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_VERSION"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
        else:
            print(f"✅ {var}: 已设置")
    
    if missing_vars:
        print(f"❌ 缺少以下环境变量: {', '.join(missing_vars)}")
        print("请在 .env 文件中设置这些变量。")
        return False
    
    # 检查模型配置
    model = os.getenv("MODEL")
    if not model:
        print("⚠️  警告: 未设置 MODEL 环境变量，将使用默认模型")
    elif model.startswith("azure_openai/"):
        print(f"✅ MODEL: {model} (Azure OpenAI)")
    else:
        print(f"ℹ️  MODEL: {model} (非 Azure OpenAI)")
    
    print("\n🧪 测试 LangChain 集成...")
    
    try:
        from langchain.chat_models import init_chat_model
        
        # 测试 Azure OpenAI 模型初始化
        if model and model.startswith("azure_openai/"):
            print(f"正在初始化模型: {model}")
            chat_model = init_chat_model(model)
            print("✅ Azure OpenAI 模型初始化成功!")
            
            # 测试简单的调用
            print("\n🔄 测试模型调用...")
            response = chat_model.invoke("Hello! This is a test message.")
            print(f"✅ 模型响应: {response.content[:100]}...")
            
        else:
            print("ℹ️  当前配置未使用 Azure OpenAI 模型，跳过测试")
            
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("请确保安装了所需的依赖包")
        return False
    except Exception as e:
        print(f"❌ 模型测试失败: {e}")
        print("请检查您的 Azure OpenAI 配置是否正确")
        return False
    
    print("\n✅ 所有测试通过! Azure OpenAI 配置正确。")
    return True

def show_config_template():
    """显示配置模板"""
    print("\n📋 Azure OpenAI 配置模板 (.env 文件):")
    print("-" * 50)
    print("""# Azure OpenAI 配置
AZURE_OPENAI_API_KEY=your-azure-openai-api-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# 模型配置
MODEL=azure_openai/gpt-4

# 可选：自定义部署名称
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=your-gpt4-deployment-name
AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME=your-embedding-deployment-name

# 用户配置
USER_ID=default""")
    print("-" * 50)

if __name__ == "__main__":
    print("🚀 Azure OpenAI 配置测试工具")
    print("=" * 40)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--template":
        show_config_template()
        sys.exit(0)
    
    success = test_azure_openai_config()
    
    if not success:
        print("\n💡 提示: 运行 'python test_azure_config.py --template' 查看配置模板")
        print("📖 详细配置指南: ./AZURE_SETUP_zh.md")
        sys.exit(1)
    
    print("\n🎉 配置测试完成!")
