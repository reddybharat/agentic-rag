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
    
@tool
def add_test(input_str: str):
    """
    Adds two numbers together.

    Args:
        input_str (str): A string containing two numbers to add, e.g., "5 + 3" or "a: 5, b: 3"

    Returns:
        str: The sum of the two numbers.
    """
    print(f"[TOOL] add_test called with input: {input_str}")
    try:
        # Parse the input string to extract numbers
        # Handle different formats: "5 + 3", "a: 5, b: 3", "5, 3", etc.
        import re
        
        # Extract all numbers from the string
        numbers = re.findall(r'\d+', input_str)
        if len(numbers) >= 2:
            a = int(numbers[0])
            b = int(numbers[1])
            result = a + b
            return f"The sum of {a} + {b} is: {result}"
        else:
            return f"Error: Could not find two numbers in the input '{input_str}'. Please provide two numbers to add."
    except Exception as e:
        print(f"[TOOL] Addition error: {e}")
        return f"Error performing addition: {str(e)}"