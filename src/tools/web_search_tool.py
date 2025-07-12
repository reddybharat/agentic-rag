from langchain_tavily import TavilySearch
from langchain_core.tools import tool

# Initialize Tavily Search Tool
@tool
def tavily_search_tool():
    return TavilySearch(
        max_results=3,
        topic="general",
    )