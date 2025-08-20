"""
LLM Web Agent 配置模块
"""

import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


@dataclass
class LLMConfig:
    """LLM 配置"""
    api_key: str
    model_name: str = "gpt-4"
    temperature: float = 0.1
    max_tokens: Optional[int] = None
    base_url: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> "LLMConfig":
        """从环境变量创建配置"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 环境变量未设置")
        
        return cls(
            api_key=api_key,
            model_name=os.getenv("OPENAI_MODEL", "gpt-4"),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.1")),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS")) if os.getenv("OPENAI_MAX_TOKENS") else None,
            base_url=os.getenv("OPENAI_BASE_URL")
        )


@dataclass
class MCPConfig:
    """MCP 服务器配置"""
    server_url: str = "ws://localhost:8080"
    server_port: int = 8080
    timeout: int = 30
    
    @classmethod
    def from_env(cls) -> "MCPConfig":
        """从环境变量创建配置"""
        return cls(
            server_url=os.getenv("MCP_SERVER_URL", "ws://localhost:8080"),
            server_port=int(os.getenv("MCP_SERVER_PORT", "8080")),
            timeout=int(os.getenv("MCP_TIMEOUT", "30"))
        )


@dataclass 
class BrowserConfig:
    """浏览器配置"""
    headless: bool = False
    timeout: int = 30000
    viewport_width: int = 1280
    viewport_height: int = 720
    user_agent: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> "BrowserConfig":
        """从环境变量创建配置"""
        return cls(
            headless=os.getenv("BROWSER_HEADLESS", "false").lower() == "true",
            timeout=int(os.getenv("BROWSER_TIMEOUT", "30000")),
            viewport_width=int(os.getenv("BROWSER_WIDTH", "1280")),
            viewport_height=int(os.getenv("BROWSER_HEIGHT", "720")),
            user_agent=os.getenv("BROWSER_USER_AGENT")
        )


@dataclass
class LogConfig:
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> "LogConfig":
        """从环境变量创建配置"""
        return cls(
            level=os.getenv("LOG_LEVEL", "INFO"),
            format=os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            file_path=os.getenv("LOG_FILE")
        )


@dataclass
class AgentConfig:
    """代理配置"""
    max_iterations: int = 10
    early_stopping_method: str = "generate"
    verbose: bool = True
    memory_type: str = "buffer"
    
    @classmethod
    def from_env(cls) -> "AgentConfig":
        """从环境变量创建配置"""
        return cls(
            max_iterations=int(os.getenv("AGENT_MAX_ITERATIONS", "10")),
            early_stopping_method=os.getenv("AGENT_EARLY_STOPPING", "generate"),
            verbose=os.getenv("AGENT_VERBOSE", "true").lower() == "true",
            memory_type=os.getenv("AGENT_MEMORY_TYPE", "buffer")
        )


class Config:
    """主配置类"""
    
    def __init__(self):
        self.llm = LLMConfig.from_env()
        self.mcp = MCPConfig.from_env()
        self.browser = BrowserConfig.from_env()
        self.log = LogConfig.from_env()
        self.agent = AgentConfig.from_env()
    
    def validate(self) -> bool:
        """验证配置"""
        try:
            # 验证 LLM 配置
            if not self.llm.api_key:
                raise ValueError("OpenAI API Key 未设置")
            
            # 验证端口范围
            if not (1 <= self.mcp.server_port <= 65535):
                raise ValueError(f"MCP 服务器端口无效: {self.mcp.server_port}")
            
            # 验证超时值
            if self.mcp.timeout <= 0:
                raise ValueError(f"MCP 超时值无效: {self.mcp.timeout}")
            
            if self.browser.timeout <= 0:
                raise ValueError(f"浏览器超时值无效: {self.browser.timeout}")
            
            # 验证视口大小
            if self.browser.viewport_width <= 0 or self.browser.viewport_height <= 0:
                raise ValueError("浏览器视口大小无效")
            
            # 验证日志级别
            valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            if self.log.level.upper() not in valid_log_levels:
                raise ValueError(f"无效的日志级别: {self.log.level}")
            
            # 验证代理配置
            if self.agent.max_iterations <= 0:
                raise ValueError("代理最大迭代次数必须大于0")
            
            return True
            
        except ValueError as e:
            print(f"配置验证失败: {e}")
            return False
    
    def print_config(self):
        """打印配置信息"""
        print("📋 当前配置:")
        print("-" * 40)
        print(f"LLM 模型: {self.llm.model_name}")
        print(f"LLM 温度: {self.llm.temperature}")
        print(f"MCP 服务器: {self.mcp.server_url}")
        print(f"浏览器无头模式: {self.browser.headless}")
        print(f"浏览器视口: {self.browser.viewport_width}x{self.browser.viewport_height}")
        print(f"日志级别: {self.log.level}")
        print(f"代理最大迭代: {self.agent.max_iterations}")
        print("-" * 40)


# 全局配置实例
config = Config()


def load_config() -> Config:
    """加载配置"""
    global config
    config = Config()
    
    if not config.validate():
        raise RuntimeError("配置验证失败")
    
    return config


def get_config() -> Config:
    """获取配置"""
    return config


if __name__ == "__main__":
    # 测试配置
    try:
        cfg = load_config()
        cfg.print_config()
        print("✅ 配置验证通过")
    except Exception as e:
        print(f"❌ 配置错误: {e}")