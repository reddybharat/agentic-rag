from typing import Dict, TypedDict, List
from src.graphs.type import RAGAgentState
from src.graphs.nodes.response_node import response_node
from langgraph.graph import StateGraph, START, END

def _build_base_graph():
    """Build and return the base state graph with only summarizer and categorizer nodes."""
    builder = StateGraph(RAGAgentState)
    builder.add_node("response", response_node)

    builder.add_edge(START, "response")
    builder.add_edge("response", END)
    return builder

def build_graph():
    builder = _build_base_graph()
    return builder.compile()