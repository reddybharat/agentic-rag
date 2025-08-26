from src.graphs.type import RAGAgentState
from src.utils.data_ingest import IngestData
from src.utils.retriever import Retriever
from langchain_core.messages import HumanMessage
import os


def ingestor_node(state: RAGAgentState) -> RAGAgentState:
    """
    A node that can ingest user files into the vector DB (if needed) and then generate a response to the user query using the vectorDB context.
    """
    print("[INGESTION NODE] 🚀 Node hit")

    # Check if files are uploaded and not yet ingested
    files_uploaded = state.get('files_uploaded', [])
    data_ingested = state.get('data_ingested', False)
    
    if files_uploaded and not data_ingested:
        print(f"[INGESTION NODE] 📁 Processing {len(files_uploaded)} file(s)")
        
        # Validate that files exist
        valid_files = []
        for file_path in files_uploaded:
            if os.path.exists(file_path):
                valid_files.append(file_path)
            else:
                pass
        
        if not valid_files:
            error_msg = "No valid files found for ingestion"
            print(f"[INGESTION NODE] ❌ {error_msg}")
            state['data_ingested'] = False
            state['status'] = f"Ingestion failed: {error_msg}"
            return state
        
        ingestor = IngestData()
        state['status'] = "Ingestion started"
        
        try:
            print("[INGESTION NODE] 🔄 Starting ingestion pipeline...")
            ingestor.run_ingestion_pipeline(valid_files)
            state['data_ingested'] = True
            state['status'] = "Ingestion completed successfully"
            print("[INGESTION NODE] ✅ Ingestion completed successfully")
        except ValueError as e:
            # Handle specific ValueError (like no valid content)
            error_msg = f"Ingestion failed: {str(e)}"
            print(f"[INGESTION NODE] ❌ {error_msg}")
            state['data_ingested'] = False
            state['status'] = error_msg
        except Exception as e:
            # Handle other exceptions (API errors, file reading errors, etc.)
            error_msg = f"Ingestion failed: {str(e)}"
            print(f"[INGESTION NODE] ❌ {error_msg}")
            state['data_ingested'] = False
            state['status'] = error_msg
    else:
        if not files_uploaded:
            print("[INGESTION NODE] ℹ️ No files uploaded, skipping ingestion")
        elif data_ingested:
            print("[INGESTION NODE] ℹ️ Data already ingested, skipping ingestion")
        state['status'] = "No ingestion needed"

    return state