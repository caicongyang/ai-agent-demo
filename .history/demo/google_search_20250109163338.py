from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_community.utilities import SerpAPIWrapper
from langchain_community.tools import GooglePlacesTool
from openai import OpenAI
import os

# 设置 API Key
os.environ["SERPAPI_API_KEY"] = "57b1783f5dc4bc650cda6d21b06d2a1d5cbf571da23ac1c5230741e2e1c52c09"
os.environ["GPLACES_API_KEY"] = "57b1783f5dc4bc650cda6d21b06d2a1d5cbf571da23ac1c5230741e2e1c52c09"

class DeepSeekChatModel(BaseChatModel):
    def __init__(self, api_key, base_url="https://api.deepseek.com", model="deepseek-chat"):
        super().__init__()
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model = model

    def _generate(self, messages, stop=None, **kwargs):
        # 转换消息为 OpenAI 格式
        openai_messages = [
            {"role": "user" if msg.type == "human" else msg.type, "content": msg.content}
            for msg in messages
        ]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
            stop=stop
        )
        
        ai_message = AIMessage(content=response.choices[0].message.content)
        return {"messages": [ai_message]}

    def bind_tools(self, tools, **kwargs):
        # 添加 bind_tools 方法以兼容 LangChain
        return self

    @property
    def _llm_type(self):
        # 添加 _llm_type 属性
        return "deepseek"

# 定义工具
@tool
def search(query: str):
    """Use the SerpAPI to run a Google Search."""
    search = SerpAPIWrapper()
    return search.run(query)

@tool
def places(query: str):
    """Use the Google Places API to run a Google Places Query."""
    places = GooglePlacesTool()
    return places.run(query)

# 创建 DeepSeek 模型
deepseek_model = DeepSeekChatModel(
    api_key="sk-00acc077d0d34f43a21910049163d796"
)

# 创建代理
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