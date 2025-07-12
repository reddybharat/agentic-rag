from typing import Dict, TypedDict, List
from src.graphs.type import RAGAgentState
from src.graphs.nodes.ingestor_node import ingestor_node
from src.graphs.nodes.retriever_node import retriever_node
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph import StateGraph, START, END
from src.tools import web_search_tool


def _build_base_graph():
    """Build and return the base state graph with ingestor and retriever nodes."""
    builder = StateGraph(RAGAgentState)
    #Tools
    tools = [web_search_tool]

    #Nodes
    builder.add_node("ingestor", ingestor_node)
    builder.add_node("retriever", retriever_node)
    builder.add_node("toolbox", ToolNode(tools))

    #Graph Edges
    builder.add_edge(START, "ingestor")
    builder.add_edge("ingestor", "retriever")
    # builder.add_conditional_edges("retriever", tools_condition)
    builder.add_edge("retriever", END)
    return builder

def build_graph():
    builder = _build_base_graph()
    return builder.compile()