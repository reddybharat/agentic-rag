from typing import Dict, TypedDict, List, Literal
from src.graphs.type import RAGAgentState
from src.graphs.nodes.ingestor_node import ingestor_node
from src.graphs.nodes.retriever_node import retriever_node
from src.graphs.nodes.search_node import search_agent_node
from src.graphs.nodes.rewrite_node import rewrite
from src.graphs.nodes.chat_node import chat_node
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

def is_web_search(state: RAGAgentState) -> Literal["web_search", "vector_search"]:
    web_search_flag = state.get("web_search", False)
    if web_search_flag:
        print("[GRAPH] ➡️ Routing to web_search")
        return "web_search"
    else:
        print("[GRAPH] ➡️ Routing to vector_search")
        return "vector_search"


# def should_finish_condition(state: RAGAgentState) -> Literal["continue", "end"]:
#     finish_flag = state.get('finish', False)
#     if finish_flag:
#         print("[GRAPH] Finishing conversation - ending graph")
#         return "end"
#     else:
#         print("[GRAPH] Continuing conversation - proceeding to chat")
#         return "continue"

def chat_routing_condition(state: RAGAgentState) -> Literal["web_search", "vector_search", "end"]:
    """Route based on finish flag and web_search flag"""
    finish_flag = state.get('finish', False)
    web_search_flag = state.get('web_search', False)
    
    if finish_flag:
        print("[GRAPH] 🛑 FINISH FLAG DETECTED - ending graph")
        return "end"
    elif web_search_flag:
        print("[GRAPH] ➡️ Continuing conversation - proceeding to web_search")
        return "web_search"
    else:
        print("[GRAPH] ➡️ Continuing conversation - proceeding to vector_search")
        return "vector_search"

def _build_base_graph():
    """Build and return the base state graph with ingestor and retriever nodes."""
    builder = StateGraph(RAGAgentState)


    #Nodes
    builder.add_node("ingestor", ingestor_node)
    # builder.add_node("agent", agent_node)
    builder.add_node("retriever", retriever_node)
    builder.add_node("search", search_agent_node)
    builder.add_node("rewrite", rewrite)
    builder.add_node("chat", chat_node)

    #Graph Edges

    builder.add_conditional_edges(
        START,
        is_web_search,
        {
            "web_search": "search", 
            "vector_search": "ingestor", 
        },
    )

    builder.add_edge("ingestor", "retriever")


    # Remove conditional edge; add normal edge from 'search' to 'rewrite'
    builder.add_edge("search", "rewrite")
    builder.add_edge("retriever", "rewrite")
    
    # Always go from rewrite to chat
    builder.add_edge("rewrite", "chat")
    
    #Chat node conditionally routes to search, retriever, or END
    builder.add_conditional_edges(
        "chat", 
        chat_routing_condition,
        {
            "web_search": "search", 
            "vector_search": "retriever", 
            "end": END,
        },
    )
    
    return builder

def build_graph(checkpointer):
    builder = _build_base_graph()
    return builder.compile(
        checkpointer=checkpointer,
    )