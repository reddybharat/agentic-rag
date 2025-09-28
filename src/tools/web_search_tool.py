from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain_community.tools import DuckDuckGoSearchResults

import os
from dotenv import load_dotenv
load_dotenv()

# Initialize Tavily Search Tool
@tool
def tavily_search_tool(query: str):
    """
    Performs web search using Tavily Search API.
    
    Args:
        query: The search query to look up on the web
        
    Returns:
        str: Search results from Tavily
    """
    print(f"[TOOL] tavily_search_tool called with query: {query}")

    tavily_search = TavilySearch(
        tavily_api_key=os.getenv("TAVILY_API_KEY"),
        max_results=7,
        topic="general",
    )
    
    try:
        results = tavily_search.invoke(query)
        return str(results)
    except Exception as e:
        print(f"[TOOL] Tavily search error: {e}")
        return f"Error performing search: {str(e)}"

@tool
def duckduckgo_search_tool(query: str):
    """
    Performs web search using DuckDuckGo API.
    
    Args:
        query: The search query to look up on the web
        
    Returns:
        str: Search results from DuckDuckGo
    """
    print(f"[TOOL] duckduckgo_search_tool called with query: {query}")
    
    try:
        wrapper = DuckDuckGoSearchAPIWrapper(region="in-en", time="d", max_results=3)
        search_tool = DuckDuckGoSearchResults(
            api_wrapper=wrapper,
            source="news",
            output_format="json",
        )
        
        results = search_tool.invoke(query)
        return str(results)
    except Exception as e:
        print(f"[TOOL] DuckDuckGo search error: {e}")
        return f"Error performing search: {str(e)}"