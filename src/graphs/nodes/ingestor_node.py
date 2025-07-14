from src.graphs.type import RAGAgentState
from src.utils.data_ingest import IngestData
from src.utils.retriever import Retriever
from langchain_core.messages import HumanMessage


def ingestor_node(state: RAGAgentState) -> RAGAgentState:
    """
    A node that can ingest user files into the vector DB (if needed) and then generate a response to the user query using the vectorDB context.
    """
    print("[INGESTION NODE] Running ingestor_node")

    # Ingest data if files are uploaded and not yet ingested
    if state.get('files_uploaded') and not state.get('data_ingested', False):
        print("[INGESTION NODE] Files uploaded and data not yet ingested. Starting ingestion...")
        ingestor = IngestData()
        state['status'] = "Ingestion started"
        try:
            ingestor.run_ingestion_pipeline(state['files_uploaded'])
            state['data_ingested'] = True
            state['status'] = "Ingestion completed"
            print("[INGESTION NODE] Ingestion completed successfully.")
        except Exception as e:
            state['data_ingested'] = False
            state['status'] = f"Ingestion failed: {str(e)}"
            print(f"[INGESTION NODE] Ingestion failed: {str(e)}")
    else:
        if not state.get('files_uploaded'):
            print("[INGESTION NODE] No files uploaded, skipping ingestion.")
        elif state.get('data_ingested', False):
            print("[INGESTION NODE] Data already ingested, skipping ingestion.")

    return state