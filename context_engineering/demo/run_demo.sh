#!/bin/bash

# LangGraph 上下文工程演示运行脚本

echo "🚀 LangGraph 上下文工程演示"
echo "=============================="
echo ""

# 检查 Python 版本
python_version=$(python3 --version 2>/dev/null)
if [ $? -ne 0 ]; then
    echo "❌ 错误：未找到 Python3"
    exit 1
fi
echo "✅ Python 版本：$python_version"

# 检查依赖包
echo "📦 检查依赖包..."
if ! python3 -c "import langgraph" 2>/dev/null; then
    echo "❌ 未安装 langgraph，正在安装依赖包..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ 依赖包安装失败"
        exit 1
    fi
else
    echo "✅ 依赖包已安装"
fi

# 检查环境变量
if [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  警告：未设置 API Keys，运行时会提示输入"
fi

echo ""
echo "选择要运行的演示："
echo "1. 完整演示 (complete_context_engineering_demo.py)"
echo "2. 简化演示 (simple_demo.py)"  
echo "3. 写入上下文演示 (write_context_demo.py)"
echo ""

read -p "请输入选择 (1-3): " choice

case $choice in
    1)
        echo "🚀 运行完整演示..."
        python3 complete_context_engineering_demo.py
        ;;
    2)
        echo "🚀 运行简化演示..."
        python3 simple_demo.py
        ;;
    3)
        echo "🚀 运行写入上下文演示..."
        python3 write_context_demo.py
        ;;
    *)
        echo "❌ 无效选择，默认运行简化演示..."
        python3 simple_demo.py
        ;;
esac

echo ""
echo "✨ 演示完成！"
