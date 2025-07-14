from typing import Dict, TypedDict, List, Literal
from src.graphs.type import RAGAgentState
from src.graphs.nodes.ingestor_node import ingestor_node
from src.graphs.nodes.retriever_node import retriever_node
from src.graphs.nodes.search_node import search_node
# from src.graphs.nodes.agent_node import agent_node

from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph import StateGraph, START, END
from src.tools.web_search_tool import tavily_search_tool
from src.tools.retriever_tool import retriever_tool



def search_tool_condition(state: RAGAgentState) -> Literal["web_search", "vector_search"]:
    if state["web_search"]:
        return "web_search"
    else:
        return "vector_search"


def _build_base_graph():
    """Build and return the base state graph with ingestor and retriever nodes."""
    builder = StateGraph(RAGAgentState)
    #Tools
    tools = [tavily_search_tool]

    #Nodes
    builder.add_node("ingestor", ingestor_node)
    # builder.add_node("agent", agent_node)
    builder.add_node("retriever", retriever_node)
    builder.add_node("search", search_node)

    # builder.add_node("tools", ToolNode(tools))

    #Graph Edges
    builder.add_edge(START, "ingestor")

    builder.add_conditional_edges(
        "ingestor",
        search_tool_condition,
        {
            "web_search": "search", 
            "vector_search": "retriever", 
        },
    )

    # builder.add_edge("retriever", "generator")
    # builder.add_conditional_edges("generator", tools_condition)
    builder.add_edge("search", END)
    builder.add_edge("retriever", END)

    return builder

def build_graph():
    builder = _build_base_graph()
    return builder.compile()