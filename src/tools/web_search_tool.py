from langchain_tavily import TavilySearch
from langchain_core.tools import tool
from src.graphs.type import RAGAgentState

# Initialize Tavily Search Tool
@tool
def tavily_search_tool(query: str) -> str:
    """
    Performs web search using Tavily Search API.
    
    Returns:
        TavilySearch: A configured Tavily search tool instance with max_results=3
        and topic set to "general" for broad search capabilities.
    """
    print("[TOOL] tavily_search_tool called")
    return TavilySearch(
        max_results=3,
        topic=query,
    )
