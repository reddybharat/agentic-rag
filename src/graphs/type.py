from typing import Dict, TypedDict, List

class RAGAgentState(TypedDict):
    """
    Represents the state of the agent in the state graph.
    """
    files_uploaded: List[str]
    query: str
    answer: str
    data_ingested: bool