from fastapi import APIRouter, Request, HTTPException
from src.graphs.builder import build_graph
from src.graphs.type import RAGAgentState
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from uuid import uuid4

router = APIRouter()

# Global checkpointer for all sessions
checkpointer = MemorySaver()



# --- Start a new session ---
@router.post("/start")
async def start_graph(request: Request):
    body = await request.json()
    thread_id = str(uuid4())
    state: RAGAgentState = {
        "files_uploaded": body.get("files_uploaded", []),
        "query": body.get("query", ""),
        "answer": "",
        "data_ingested": False,
        "status": "",
        "messages": body.get("messages", []),
        "web_search": body.get("web_search", False),
        "rewrite": False,
        "finish": False,
    }
    print(f"[API] Starting new chat session with thread_id: {thread_id}")
    graph = build_graph(checkpointer)
    result = graph.invoke(state, config={"configurable": {"thread_id": thread_id}})
    return {"thread_id": thread_id, "state": result}

# --- Continue the session (user sends a new message) ---
@router.post("/continue")
async def continue_graph(request: Request):
    body = await request.json()
    thread_id = body["thread_id"]
    state = body["state"]
    print(f"[API] Continuing chat session with thread_id: {thread_id}")
    
    # Ensure all required state variables are present
    if "finish" not in state:
        state["finish"] = False
    if "web_search" not in state:
        state["web_search"] = False
    if "query" not in state:
        state["query"] = ""
    if "answer" not in state:
        state["answer"] = ""
    if "messages" not in state:
        state["messages"] = []
    if "status" not in state:
        state["status"] = ""
    if "data_ingested" not in state:
        state["data_ingested"] = False
    if "files_uploaded" not in state:
        state["files_uploaded"] = []
    
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
        config={"configurable": {"thread_id": thread_id}})
    return {"thread_id": thread_id, "state": result}

# --- Finish the session (user wants to end chat) ---
@router.post("/finish")
async def finish_graph(request: Request):
    body = await request.json()
    thread_id = body["thread_id"]
    # state = body["state"]
    print(f"[API] Finishing chat session with thread_id: {thread_id}")
    
    # state["finish"] = True
    graph = build_graph(checkpointer)
    result = graph.invoke(Command(resume={"finish": True}), config={"configurable": {"thread_id": thread_id}})

    return {"thread_id": thread_id, "state": result}
