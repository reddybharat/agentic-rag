from src.graphs.type import RAGAgentState
from src.utils.data_ingest import IngestData
from src.utils.retriever import Retriever
from langchain_core.messages import AIMessage, HumanMessage

# Print statement for debugging node execution
def retriever_node(state: RAGAgentState) -> RAGAgentState:
    """
    A node that creates a retriever to get data from the vectorDB
    """
    print(f"[RETRIEVER NODE] Starting with state : {state}")
    result = ""
    new_messages = ""
    try:
        print("[RETRIEVER NODE] Running retriever_node")
        db = IngestData().load_chroma_collection("devuser")
        result = Retriever().run_retriever_node(state["query"], db, 5)
        # Prepare new messages to append
        new_messages = [
            HumanMessage(content=state["query"]),
            AIMessage(content=result)
        ]

    except Exception as e:
        print(f"[RETRIEVER NODE] Error occurred during retrieval: {str(e)}")
        state['status'] = "Error"

    state["messages"] = state["messages"] + new_messages
    state["answer"] = result
    print(f"[RETRIEVER NODE] Ending with state : {state}")
    return state