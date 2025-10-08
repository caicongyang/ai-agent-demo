#!/usr/bin/env python3
"""
简单的数学 MCP 服务器
提供基本的数学计算功能
"""

import asyncio
from mcp.server.fastmcp import FastMCP

# 创建 MCP 服务器
mcp = FastMCP("Simple Math Server")

@mcp.tool()
def add(a: int, b: int) -> int:
    """将两个整数相加"""
    result = a + b
    print(f"📊 计算: {a} + {b} = {result}")
    return result

@mcp.tool()
def multiply(a: int, b: int) -> int:
    """将两个整数相乘"""
    result = a * b
    print(f"📊 计算: {a} × {b} = {result}")
    return result

@mcp.tool()
def calculate_area(length: float, width: float) -> float:
    """计算矩形面积"""
    area = length * width
    print(f"📊 计算矩形面积: {length} × {width} = {area} 平方米")
    return area

@mcp.tool()
def fibonacci(n: int) -> list:
    """生成斐波那契数列的前n项"""
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]
    
    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i-1] + fib[i-2])
    
    print(f"📊 生成斐波那契数列前 {n} 项: {fib}")
    return fib

@mcp.tool()
def power(base: int, exponent: int) -> int:
    """计算幂次方"""
    result = base ** exponent
    print(f"📊 计算: {base}^{exponent} = {result}")
    return result

if __name__ == "__main__":
    print("🚀 启动数学 MCP 服务器...")
    mcp.run()
