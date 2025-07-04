from typing import Dict, TypedDict, List
from basic.type import AgentState
from basic.nodes import response_node
from langgraph.graph import StateGraph, START, END

def _build_base_graph():
    """Build and return the base state graph with only summarizer and categorizer nodes."""
    builder = StateGraph(AgentState)
    builder.add_node("response", response_node)

    builder.add_edge(START, "response")
    builder.add_edge("response", END)
    return builder

def build_graph():
    builder = _build_base_graph()
    return builder.compile()

# def _build_base_graph():
#     """Build and return the base state graph with only summarizer and categorizer nodes."""
#     builder = StateGraph(SummaryState)
#     builder.add_edge(START, "summarizer")
#     builder.add_node("summarizer", summarizer_node)
#     builder.add_node("categorizer", categorizer_node)
#     builder.add_edge("summarizer", "categorizer")
#     builder.add_edge("categorizer", END)
#     return builder

