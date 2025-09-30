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
    
    result = ""
    new_messages = []
    try:
        # Summarize chat history for context
        history_summary = summarize_chat_history(state.get("messages", []))
        
        # Enhance query with history context
        enhanced_query = state["query"]
        if history_summary and history_summary != "This is a new conversation with no previous history.":
            enhanced_query = f"Context from previous conversation: {history_summary}\n\nCurrent query: {state['query']}"
        
        try:
            db = IngestData().load_chroma_collection("agentic-rag")
            
            result = Retriever().run_retriever_node(enhanced_query, db, 5)
            
        except Exception as db_error:
            print(f"[RETRIEVER NODE] Database error: {str(db_error)}")
            print(f"[RETRIEVER NODE] Error type: {type(db_error)}")
            result = "I couldn't find any relevant information in the uploaded documents. Please make sure documents have been uploaded and processed correctly."
        
        # Prepare new messages to append
        new_messages = [
            HumanMessage(content=state["query"]),
            AIMessage(content=result)
        ]

    except Exception as e:
        print(f"[RETRIEVER NODE] Error: {str(e)}")
        state['status'] = "Error"

    state["messages"] = state["messages"] + new_messages
    state["answer"] = result
    return state