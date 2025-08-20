"""
MCP Web Automation - 基于官方 MCP Python SDK 的简洁网页自动化工具

核心组件:
- DirectMCPClient: 直接使用官方 MCP SDK 的客户端
- WebAutomationTasks: 网页自动化任务集合
- MCPWebService: Flask API 服务中使用的 MCP 服务
- Config: 配置管理

使用示例:
    from crawl.simple_llm_crawler import DirectMCPClient
    
    client = DirectMCPClient()
    await client.connect_to_playwright()
    await client.navigate("https://example.com")
    await client.take_screenshot("test.png")
    await client.close()

或者使用高级封装:
    from crawl.mcp_integration_example import WebScrapingService
    
    service = WebScrapingService()
    await service.initialize()
    results = await service.scrape_multiple_sites(["https://example.com"])
    await service.cleanup()
"""

from .simple_llm_crawler import DirectMCPClient, WebAutomationTasks
from .mcp_integration_example import WebScrapingService, MCPWebAutomation
from .flask_mcp_integration import MCPWebService
from .amazon_scraper_with_llm import AmazonScraperWithLLM, LLMTaskPlanner, ScrapingTask, ProductInfo
from .config import Config, load_config, get_config

__version__ = "2.1.0"
__author__ = "AI Agent Demo"

__all__ = [
    "DirectMCPClient",
    "WebAutomationTasks", 
    "WebScrapingService",
    "MCPWebAutomation",
    "MCPWebService",
    "AmazonScraperWithLLM",
    "LLMTaskPlanner",
    "ScrapingTask",
    "ProductInfo",
    "Config",
    "load_config",
    "get_config"
]