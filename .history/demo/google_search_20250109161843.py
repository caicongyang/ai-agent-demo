from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_community.utilities import SerpAPIWrapper
from langchain_community.tools import GooglePlacesTool
from openai import OpenAI
import os

os.environ["SERPAPI_API_KEY"] = "57b1783f5dc4bc650cda6d21b06d2a1d5cbf571da23ac1c5230741e2e1c52c09"
os.environ["GPLACES_API_KEY"] = "57b1783f5dc4bc650cda6d21b06d2a1d5cbf571da23ac1c5230741e2e1c52c09"

deepseek_client = OpenAI(
    api_key="sk-00acc077d0d34f43a21910049163d796",
    base_url="https://api.deepseek.com"
)

class DeepSeekModel(BaseChatModel):
    def __init__(self, client, model="deepseek-chat"):
        super().__init__()
        self.client = client
        self.model = model

    def _generate(self, messages, stop=None, **kwargs):
        # 转换 LangChain 消息为 OpenAI 格式
        openai_messages = [
            {"role": msg.type, "content": msg.content} 
            for msg in messages
        ]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
            stop=stop
        )
        
        ai_message = AIMessage(content=response.choices[0].message.content)
        return {"messages": [ai_message]}

    async def _agenerate(self, messages, stop=None, **kwargs):
        return self._generate(messages, stop, **kwargs)

    def bind_tools(self, tools, **kwargs):
        # 添加 bind_tools 方法以兼容 LangChain
        return self

    @property
    def _llm_type(self):
        return "deepseek"

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

model = DeepSeekModel(deepseek_client)
tools = [search, places]
query = ("Who did the Texas Longhorns play in football last week? What is the "
         "address of the other team's stadium?")

agent = create_react_agent(model, tools)
input = {"messages": [HumanMessage(content=query)]}

for s in agent.stream(input, stream_mode="values"):
    message = s["messages"][-1]
    if isinstance(message, tuple):
        print(message)
    else:
        print(message.content)