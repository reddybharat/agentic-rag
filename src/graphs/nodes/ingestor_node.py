from src.graphs.type import RAGAgentState
from src.utils.data_ingest import IngestData
from src.utils.retriever import Retriever
from langchain_core.messages import HumanMessage


def ingestor_node(state: RAGAgentState) -> RAGAgentState:
    """
    A node that can ingest user files into the vector DB (if needed) and then generate a response to the user query using the vectorDB context.
    """
    print("[INGESTION NODE] 🚀 Node hit")

    # Ingest data if files are uploaded and not yet ingested
    if state.get('files_uploaded') and not state.get('data_ingested', False):
        ingestor = IngestData()
        state['status'] = "Ingestion started"
        try:
            ingestor.run_ingestion_pipeline(state['files_uploaded'])
            state['data_ingested'] = True
            state['status'] = "Ingestion completed"
        except Exception as e:
            state['data_ingested'] = False
            state['status'] = f"Ingestion failed: {str(e)}"
            print(f"[INGESTION NODE] Error: {str(e)}")

    return state