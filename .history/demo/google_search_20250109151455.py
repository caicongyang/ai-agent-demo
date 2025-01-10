from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langchain_community.utilities import SerpAPIWrapper
from langchain_community.tools import GooglePlacesTool
os.environ["SERPAPI_API_KEY"] = "XXXXX"
os.environ["GPLACES_API_KEY"] = "XXXXX"
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
model = ChatVertexAI(model="gemini-1.5-flash-001")
tools = [search, places]
query = "Who did the Texas Longhorns play in football last week? What is the 
address of the other team's stadium?"
agent = create_react_agent(model, tools)
input = {"messages": [("human", query)]}
for s in agent.stream(input, stream_mode="values"):
message = s["messages"][-1]
if isinstance(message, tuple):
 print(message)
else:
 message.pretty_print()