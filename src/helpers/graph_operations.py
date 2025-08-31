from typing import Dict, List, Optional
from uuid import uuid4
from src.graphs.builder import build_graph
from src.graphs.type import RAGAgentState
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from src.helpers.summarizer import serialize_messages

# Global checkpointer for all sessions (same as in the API)
checkpointer = MemorySaver()

def start_new_chat(query: str, web_search: bool, messages: List, file_paths: List[str]) -> Dict:
    """
    Start a new chat session - equivalent to /start API endpoint
    
    Args:
        query: The initial query
        web_search: Whether to enable web search
        messages: List of previous messages
        file_paths: List of uploaded file paths
    
    Returns:
        Dict containing thread_id and state
    """
    thread_id = str(uuid4())
    state: RAGAgentState = {
        "files_uploaded": file_paths,
        "query": query,
        "answer": "",
        "data_ingested": False,
        "status": "",
        "messages": messages,
        "web_search": web_search,
        "rewrite": False,
        "finish": False,
    }
    
    print(f"[HELPER] Starting new chat session with thread_id: {thread_id}")
    graph = build_graph(checkpointer)
    result = graph.invoke(state, config={"configurable": {"thread_id": thread_id}})
    
    return {"thread_id": thread_id, "state": result}

def continue_chat(thread_id: str, query: str, web_search: bool, messages: List, 
                  file_paths: List[str], data_ingested: bool, status: str) -> Dict:
    """
    Continue an existing chat session - equivalent to /continue API endpoint
    
    Args:
        thread_id: The thread ID to continue
        query: The new query
        web_search: Whether web search is enabled
        messages: List of previous messages
        file_paths: List of uploaded file paths
        data_ingested: Whether data has been ingested
        status: Current status
    
    Returns:
        Dict containing thread_id and state
    """
    print(f"[HELPER] Continuing chat session with thread_id: {thread_id}")
    
    # Ensure all required state variables are present
    state = {
        "finish": False,
        "web_search": web_search,
        "query": query,
        "answer": "",
        "messages": messages,
        "status": status,
        "data_ingested": data_ingested,
        "files_uploaded": file_paths,
    }
    
    graph = build_graph(checkpointer)
    result = graph.invoke(
        Command(resume={
            "query": state.get('query'),
            "web_search": state.get('web_search'),
            "messages": state.get('messages', []),
            "status": state.get('status'),
            "data_ingested": state.get('data_ingested'),
            "files_uploaded": state.get('files_uploaded'),
            "finish": state.get('finish'),
        }),
        config={"configurable": {"thread_id": thread_id}}
    )
    
    return {"thread_id": thread_id, "state": result}

def finish_chat(thread_id: str) -> Dict:
    """
    Finish a chat session - equivalent to /finish API endpoint
    
    Args:
        thread_id: The thread ID to finish
    
    Returns:
        Dict containing thread_id and state
    """
    print(f"[HELPER] Finishing chat session with thread_id: {thread_id}")
    
    graph = build_graph(checkpointer)
    result = graph.invoke(
        Command(resume={"finish": True}), 
        config={"configurable": {"thread_id": thread_id}}
    )
    
    return {"thread_id": thread_id, "state": result}
