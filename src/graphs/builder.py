from typing import Dict, TypedDict, List, Literal
from src.graphs.type import RAGAgentState
from src.graphs.nodes.ingestor_node import ingestor_node
from src.graphs.nodes.retriever_node import retriever_node
from src.graphs.nodes.search_node import search_agent_node
from src.graphs.nodes.rewrite_node import rewrite
from src.graphs.nodes.chat_node import chat_node
from src.graphs.nodes.router_node import router_agent_node
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

def chat_routing_condition(state: RAGAgentState) -> Literal["continue", "end"]:
    """Route based on finish flag and web_search flag"""
    finish_flag = state.get('finish', False)

    if finish_flag:
        print("[GRAPH] 🛑 FINISH FLAG DETECTED - ending graph")
        return "end"
    else:
        print("[GRAPH] ➡️ Continuing conversation - proceeding to router agent")
        return "continue"

def _build_base_graph():
    """Build and return the base state graph with ingestor and retriever nodes."""
    builder = StateGraph(RAGAgentState)

    #Nodes
    builder.add_node("ingestor", ingestor_node)
    builder.add_node("router agent", router_agent_node)
    builder.add_node("rewrite", rewrite)
    builder.add_node("continue chat", chat_node)

    #Graph Edges
    builder.add_edge(START, "ingestor")
    builder.add_edge("ingestor", "router agent")
    builder.add_edge("router agent", "rewrite")
    builder.add_edge("rewrite", "continue chat")
    builder.add_conditional_edges(
        "continue chat", 
        chat_routing_condition,
        {
            "continue": "router agent", 
            "end": END,
        },
    )
    
    return builder

def build_graph(checkpointer):
    builder = _build_base_graph()
    return builder.compile(
        checkpointer=checkpointer,
    )