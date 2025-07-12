from src.graphs.type import RAGAgentState
from src.utils.data_ingest import IngestData
from src.utils.retriever import Retriever


def ingestor_node(state: RAGAgentState) -> RAGAgentState:
    """
    A node that can ingest user files into the vector DB (if needed) and then generate a response to the user query using the vectorDB context.
    """
    # Ingest data if files are uploaded and not yet ingested
    if state.get('files_uploaded') and not state.get('data_ingested', False):
        ingestor = IngestData()
        try:
            ingestor.run_ingestion_pipeline(state['files_uploaded'])
            state['data_ingested'] = True
        except Exception as e:
            state['data_ingested'] = False
            state['answer'] = f"Ingestion failed: {str(e)}"
            return state

    # Use retriever logic for answering
    db = IngestData().load_chroma_collection("devuser")
    result = Retriever().run_retriever_node(state["query"], db, 5)
    state['answer'] = result
    return state