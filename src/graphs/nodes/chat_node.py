from src.graphs.type import RAGAgentState
from src.graphs.nodes.retriever_node import retriever_node
from src.graphs.nodes.search_node import search_agent_node
from langgraph.types import interrupt

# Chat node for routing user queries to the appropriate node and maintaining chat history
def chat_node(state: RAGAgentState) -> RAGAgentState:
    """
    Chat node that routes the user query to either the search or retriever node based on the web_search flag,
    and maintains the chat history in the state. Pauses for HITL after processing.
    """
    print("[CHAT NODE] 🚀 Node hit")

    result = interrupt({})
    state["finish"] = result.get("finish", False)
    state["query"] = result.get("query", "")
    state["web_search"] = result.get("web_search", True)

    return state
