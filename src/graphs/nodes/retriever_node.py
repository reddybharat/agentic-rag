from src.graphs.type import RAGAgentState
from src.utils.data_ingest import IngestData
from src.utils.retriever import Retriever

def retriever_node(state: RAGAgentState) -> RAGAgentState:
    """
    A node that creates a retriever to get data from the vectorDB
    """
    db = IngestData().load_chroma_collection("devuser")
    result = Retriever().run_retriever_node(state["query"], db, 5)
    state['answer'] = result
    return state 