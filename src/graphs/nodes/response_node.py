from typing import Dict, TypedDict, List
from langgraph.graph import StateGraph
from src.graphs.type import RAGAgentState
from src.utils.llm_runner import LLM

def response_node(state: RAGAgentState) -> RAGAgentState:
    """
    A node that returns a response to the user query provided.
    """
    llm = LLM()
    state['answer'] = llm.generate_response(state['query'])

    return state