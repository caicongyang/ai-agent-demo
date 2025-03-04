import os
from typing import Any, List, Optional
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.tools import tool, StructuredTool
from langchain_community.utilities import SerpAPIWrapper
from langchain_community.tools import GooglePlacesTool
from openai import OpenAI
from pydantic import Field, BaseModel
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 设置 API Key
os.environ["SERPAPI_API_KEY"] = os.getenv("SERPAPI_API_KEY")
os.environ["GPLACES_API_KEY"] = os.getenv("GOOGLE_PLACES_API_KEY")

class DeepSeekChatModel(BaseChatModel):
    """
    A custom chat model using DeepSeek API
    """
    client: OpenAI = Field(default=None)
    model_name: str = Field(default="deepseek-chat")

    def __init__(self):
        super().__init__()
        object.__setattr__(self, 'client', OpenAI(
            api_key=os.getenv("LLM_API_KEY"), 
            base_url=os.getenv("LLM_BASE_URL")
        ))
        object.__setattr__(self, 'model_name', "deepseek-chat")

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """
        Generate a chat response using DeepSeek API
        """
        # 转换消息为 OpenAI 格式
        openai_messages = [
            {"role": "user" if msg.type == "human" else msg.type, "content": msg.content}
            for msg in messages
        ]

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=openai_messages,
            stop=stop
        )
        
        # 创建 AIMessage
        message = AIMessage(
            content=response.choices[0].message.content,
            response_metadata={
                "model": self.model_name,
                "finish_reason": response.choices[0].finish_reason
            }
        )

        # 创建 ChatGeneration 和 ChatResult
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])

    def bind_tools(self, tools, **kwargs):
        """
        Bind tools to the model
        """
        # 将工具转换为 StructuredTool
        structured_tools = [
            StructuredTool.from_function(
                func=tool.func,
                name=tool.name,
                description=tool.description
            ) if not isinstance(tool, StructuredTool) else tool 
            for tool in tools
        ]
        
        # 返回模型本身，允许工具绑定
        return self

    @property
    def _llm_type(self) -> str:
        """
        Unique identifier for the LLM type
        """
        return "deepseek"

    @property
    def _identifying_params(self) -> dict:
        """
        Get the identifying parameters
        """
        return {
            "model_name": self.model_name
        }

# 定义工具的输入模型
class SearchInput(BaseModel):
    query: str

class PlacesInput(BaseModel):
    query: str

# 使用 StructuredTool 创建工具
def search_func(query: str) -> str:
    """Use the SerpAPI to run a Google Search."""
    search = SerpAPIWrapper()
    return search.run(query)

def places_func(query: str) -> str:
    """Use the Google Places API to run a Google Places Query."""
    places = GooglePlacesTool()
    return places.run(query)

search = StructuredTool.from_function(
    func=search_func,
    name="search",
    description="Use the SerpAPI to run a Google Search.",
    args_schema=SearchInput
)

places = StructuredTool.from_function(
    func=places_func,
    name="places",
    description="Use the Google Places API to run a Google Places Query.",
    args_schema=PlacesInput
)

# 创建 DeepSeek 模型
deepseek_model = DeepSeekChatModel()

# 创建代理
from langgraph.prebuilt import create_react_agent
tools = [search, places]
agent = create_react_agent(deepseek_model, tools)

# 定义查询
query = ("Who did the Texas Longhorns play in football last week? What is the "
         "address of the other team's stadium?")

# 执行代理
input = {"messages": [HumanMessage(content=query)]}
for s in agent.stream(input, stream_mode="values"):
    message = s["messages"][-1]
    if isinstance(message, tuple):
        print(message)
    else:
        print(message.content)