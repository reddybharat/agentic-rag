from typing import Dict, TypedDict, List
from langgraph.graph import StateGraph

class AgentState(TypedDict):
    """
    Represents the state of the agent in the state graph.
    """
    query: str
    answer: str