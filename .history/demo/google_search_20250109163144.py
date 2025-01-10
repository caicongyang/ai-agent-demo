from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langchain_community.utilities import SerpAPIWrapper
from langchain_community.tools import GooglePlacesTool
from langchain_google_vertexai import ChatVertexAI
from openai import OpenAI
import os

# 设置 API Key
os.environ["SERPAPI_API_KEY"] = "57b1783f5dc4bc650cda6d21b06d2a1d5cbf571da23ac1c5230741e2e1c52c09"
os.environ["GPLACES_API_KEY"] = "57b1783f5dc4bc650cda6d21b06d2a1d5cbf571da23ac1c5230741e2e1c52c09"

# 创建 DeepSeek 客户端
deepseek_client = OpenAI(
    api_key="sk-00acc077d0d34f43a21910049163d796",
    base_url="https://api.deepseek.com"
)

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

# 创建代理
tools = [search, places]
agent = create_react_agent(
    ChatVertexAI(model_name="gemini-1.5-flash-001"), 
    tools
)

# 定义查询
query = ("Who did the Texas Longhorns play in football last week? What is the "
         "address of the other team's stadium?")

# 执行代理
input = {"messages": [("human", query)]}
for s in agent.stream(input, stream_mode="values"):
    message = s["messages"][-1]
    if isinstance(message, tuple):
        print(message)
    else:
        message.pretty_print()