#!/usr/bin/env python3
"""
测试 Azure OpenAI 连接
"""

import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

# 加载环境变量
load_dotenv()

def test_azure_openai():
    """测试 Azure OpenAI 连接"""
    print("🧪 测试 Azure OpenAI 连接")
    print("=" * 40)
    
    # 检查环境变量
    required_vars = [
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT", 
        "AZURE_OPENAI_API_VERSION"
    ]
    
    print("🔍 检查环境变量:")
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # 隐藏敏感信息
            if "KEY" in var:
                display_value = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
            else:
                display_value = value
            print(f"  ✅ {var}: {display_value}")
        else:
            print(f"  ❌ {var}: 未设置")
            missing_vars.append(var)
    
    # 检查模型名称 (新版本简化配置)
    model_name = os.getenv("AZURE_OPENAI_MODEL") or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME") or "gpt-4"
    print(f"  🤖 模型: {model_name}")
    
    if missing_vars:
        print(f"\n❌ 缺少环境变量: {', '.join(missing_vars)}")
        return False
    
    # 测试连接
    print(f"\n🔗 测试连接...")
    try:
        # 使用新版本的简化配置
        llm = AzureChatOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            model=model_name,  # 使用 model 参数
            temperature=0
        )
        print("✅ 客户端创建成功")
        
        # 发送测试消息
        print("💬 发送测试消息...")
        response = llm.invoke("Hello, this is a test message. Please respond with 'Test successful'.")
        print(f"✅ 响应成功: {response.content}")
        
        return True
        
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        
        # 提供详细的错误分析
        error_str = str(e)
        if "404" in error_str:
            print("\n💡 404错误通常意味着:")
            print("  1. 部署名称 (AZURE_OPENAI_DEPLOYMENT_NAME) 错误")
            print("  2. 端点URL格式错误")
            print("  3. API版本不匹配")
        elif "401" in error_str:
            print("\n💡 401错误通常意味着:")
            print("  1. API密钥错误或已过期")
            print("  2. 权限不足")
        elif "403" in error_str:
            print("\n💡 403错误通常意味着:")
            print("  1. 配额已用完")
            print("  2. 地区限制")
        
        print(f"\n🔧 请检查Azure门户中的配置:")
        print("  1. 资源名称和部署名称")
        print("  2. API密钥是否正确")
        print("  3. 端点URL是否完整")
        
        return False

if __name__ == "__main__":
    success = test_azure_openai()
    if success:
        print("\n🎉 Azure OpenAI 连接测试成功!")
        print("现在可以运行 MCP 演示了")
    else:
        print("\n❌ Azure OpenAI 连接测试失败")
        print("请修复上述问题后重试")
