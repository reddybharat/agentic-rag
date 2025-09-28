from typing import TypedDict, List, Annotated, Sequence, Union
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class RAGAgentState(TypedDict):
    """
    Represents the state of the agent in the state graph.
    """
    files_uploaded: List[str]
    query: str
    answer: str
    data_ingested: bool
    status: str
    messages: Annotated[Sequence[Union[BaseMessage, dict]], add_messages]
    rewrite: bool
    finish: bool