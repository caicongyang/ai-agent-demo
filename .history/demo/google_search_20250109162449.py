from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool, StructuredTool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_community.utilities import SerpAPIWrapper
from langchain_community.tools import GooglePlacesTool
from openai import OpenAI
from pydantic import Field, ConfigDict, BaseModel
import os

os.environ["SERPAPI_API_KEY"] = "57b1783f5dc4bc650cda6d21b06d2a1d5cbf571da23ac1c5230741e2e1c52c09"
os.environ["GPLACES_API_KEY"] = "57b1783f5dc4bc650cda6d21b06d2a1d5cbf571da23ac1c5230741e2e1c52c09"

deepseek_client = OpenAI(
    api_key="sk-00acc077d0d34f43a21910049163d796",
    base_url="https://api.deepseek.com"
)

class DeepSeekModel(BaseChatModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    client: OpenAI = Field(...)
    model_name: str = "deepseek-chat"

    def __init__(self, client, model="deepseek-chat"):
        super().__init__(
            client=client, 
            model_name=model
        )

    def _generate(self, messages, stop=None, **kwargs):
        # 转换 LangChain 消息为 OpenAI 格式
        openai_messages = [
            {"role": "user" if msg.type == "human" else msg.type, "content": msg.content} 
            for msg in messages
        ]

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=openai_messages,
            stop=stop,
            **kwargs
        )
        
        ai_message = AIMessage(
            content=response.choices[0].message.content,
            tool_calls=response.choices[0].message.tool_calls
        )
        return {"messages": [ai_message]}

    async def _agenerate(self, messages, stop=None, **kwargs):
        return self._generate(messages, stop, **kwargs)

    def bind_tools(self, tools, **kwargs):
        # 确保工具是 StructuredTool 类型
        structured_tools = [
            StructuredTool.from_function(
                func=tool.func,
                name=tool.name,
                description=tool.description
            ) if not isinstance(tool, StructuredTool) else tool 
            for tool in tools
        ]
        return self.bind(tools=structured_tools, **kwargs)

    @property
    def _llm_type(self):
        return "deepseek"

# 使用 Pydantic 定义工具的输入模型
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

# 使用 bind_tools 绑定工具
model_with_tools = DeepSeekModel(deepseek_client).bind_tools([search, places])

query = ("Who did the Texas Longhorns play in football last week? What is the "
         "address of the other team's stadium?")

# 创建代理
agent = create_react_agent(model_with_tools, [search, places])

# 准备输入消息
input = {"messages": [
    SystemMessage(content="You are a helpful assistant that can search for information."),
    HumanMessage(content=query)
]}

# 流式处理响应
for s in agent.stream(input, stream_mode="values"):
    message = s["messages"][-1]
    if isinstance(message, tuple):
        print(message)
    else:
        print(message.content)
        if message.tool_calls:
            print("Tool Calls:", message.tool_calls)