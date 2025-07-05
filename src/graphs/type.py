from typing import Dict, TypedDict, List

class RAGAgentState(TypedDict):
    """
    Represents the state of the agent in the state graph.
    """
    query: str
    answer: str