from langchain_core.tools import tool
from src.utils.retriever import Retriever
from src.utils.data_ingest import IngestData
import os
from dotenv import load_dotenv
load_dotenv()

@tool
def retriever_tool(query: str) -> str:
    """
    Powerful document retriever: Use this tool to search a vector database of all uploaded documents and internal knowledge. It finds the most relevant, context-rich passages to answer the user's query, even for complex or detailed questions. Ideal for:
    - Questions about specific documents, files, or internal data
    - When you need facts, context, or details not available via web search
    - Summarizing, quoting, or referencing uploaded content
    Always consider using this tool if the user's question could be answered with information from documents or internal knowledge, or if you are unsure whether such information exists.
    Args:
        query (str): The user's question to search for in the vector database.
    Returns:
        str: The generated answer based on the most relevant passage from the database.
    """
    try:
        # Load the Chroma collection (vector DB)
        db = IngestData().load_chroma_collection("agentic-rag")
        # Use the Retriever class to get the answer
        answer = Retriever().run_retriever_node(query, db, n_results=5)
        return answer
    except Exception as e:
        return f"[Retriever Tool] Error: {str(e)}"
