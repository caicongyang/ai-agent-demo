#!/usr/bin/env python3
"""
多轮对话上下文工程演示启动脚本
简化版本，专门用于演示多轮对话和上下文操作日志
"""

import os
import sys

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    """主函数"""
    try:
        # 导入演示模块
        from complete_context_engineering_demo import run_complete_demo
        
        # 运行演示
        print("🚀 启动多轮对话上下文工程演示...")
        result, store = run_complete_demo()
        
        print("\n" + "="*60)
        print("✨ 演示成功完成！")
        print(f"📊 完成了 {result.get('conversation_round', 1)} 轮对话")
        print(f"🛠️  执行了 {len(result.get('tool_results', []))} 次工具调用")
        print(f"📝 记录了 {len(result.get('context_operations_log', []))} 个上下文操作")
        print("="*60)
        
        return True
        
    except KeyboardInterrupt:
        print("\n❌ 演示被用户中断")
        return False
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {str(e)}")
        print("请检查环境配置和依赖包是否正确安装。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
