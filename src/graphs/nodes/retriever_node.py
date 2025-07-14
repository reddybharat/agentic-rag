from src.graphs.type import RAGAgentState
from src.utils.data_ingest import IngestData
from src.utils.retriever import Retriever
from langchain_core.messages import AIMessage, HumanMessage

def retriever_node(state: RAGAgentState) -> RAGAgentState:
    """
    A node that creates a retriever to get data from the vectorDB
    """
    db = IngestData().load_chroma_collection("devuser")
    result = Retriever().run_retriever_node(state["query"], db, 5)
    # Prepare new messages to append
    new_messages = [
        HumanMessage(content=state["query"]),
        AIMessage(content=result)
    ]
    return {
        **state,
        "messages": new_messages,
        "answer": result
    } 