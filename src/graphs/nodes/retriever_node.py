from src.graphs.type import RAGAgentState
from src.utils.data_ingest import IngestData
from src.utils.retriever import Retriever
from src.helpers.history_summarizer import summarize_chat_history
from langchain_core.messages import AIMessage, HumanMessage

def retriever_node(state: RAGAgentState) -> RAGAgentState:
    """
    A node that creates a retriever to get data from the vectorDB
    """
    print("[RETRIEVER NODE] 🚀 Node hit")
    print(f"[RETRIEVER NODE DEBUG] Original query: {state['query']}")
    print(f"[RETRIEVER NODE DEBUG] Current messages count: {len(state.get('messages', []))}")
    
    result = ""
    new_messages = ""
    try:
        # Summarize chat history for context
        print("[RETRIEVER NODE DEBUG] Starting history summarization...")
        history_summary = summarize_chat_history(state.get("messages", []))
        print(f"[RETRIEVER NODE] History summary: {history_summary}")
        
        # Enhance query with history context
        enhanced_query = state["query"]
        if history_summary and history_summary != "This is a new conversation with no previous history.":
            enhanced_query = f"Context from previous conversation: {history_summary}\n\nCurrent query: {state['query']}"
            print(f"[RETRIEVER NODE DEBUG] Enhanced query created with history context")
            print(f"[RETRIEVER NODE DEBUG] Enhanced query length: {len(enhanced_query)} characters")
        else:
            print("[RETRIEVER NODE DEBUG] No history context added (new conversation or no summary)")
        
        print(f"[RETRIEVER NODE DEBUG] Final query to use: {enhanced_query}")
        
        db = IngestData().load_chroma_collection("devuser")
        print("[RETRIEVER NODE DEBUG] Running retriever with enhanced query...")
        result = Retriever().run_retriever_node(enhanced_query, db, 5)
        print(f"[RETRIEVER NODE DEBUG] Retriever result length: {len(result) if result else 0} characters")
        
        # Prepare new messages to append
        new_messages = [
            HumanMessage(content=state["query"]),
            AIMessage(content=result)
        ]
        print(f"[RETRIEVER NODE DEBUG] Created {len(new_messages)} new messages")

    except Exception as e:
        print(f"[RETRIEVER NODE] Error: {str(e)}")
        print(f"[RETRIEVER NODE DEBUG] Exception details: {type(e).__name__}: {str(e)}")
        state['status'] = "Error"

    print(f"[RETRIEVER NODE DEBUG] Updating state with {len(new_messages)} new messages")
    state["messages"] = state["messages"] + new_messages
    state["answer"] = result
    print(f"[RETRIEVER NODE DEBUG] Final messages count: {len(state['messages'])}")
    return state