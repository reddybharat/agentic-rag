# __import__('pysqlite3')
# import sys
# sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import os
import re
from typing import List
from datetime import datetime
from pypdf import PdfReader
import chromadb
from src.utils.gemini_embedding import GeminiEmbeddingFunction



class IngestData:
    def __init__(self, db_path=None):
        # Use a user data directory outside the project to avoid Streamlit watcher issues
        # default_path = os.path.join(str(Path.home()), "vectorDB")
        # self.DB_PATH = db_path or default_path
        self.DB_PATH = "./src/data/vectorDB"

        # ChromaDB Cloud configuration
        self.chroma_api_key = os.getenv("CHROMA_API_KEY")
        self.chroma_tenant = os.getenv("CHROMA_TENANT")
        self.chroma_database = os.getenv("CHROMA_DATABASE")
        
        if not self.chroma_api_key:
            raise ValueError("CHROMA_API_KEY environment variable is required for Chroma Cloud")
        if not self.chroma_tenant:
            raise ValueError("CHROMA_TENANT environment variable is required for Chroma Cloud")
        if not self.chroma_database:
            raise ValueError("CHROMA_DATABASE environment variable is required for Chroma Cloud")

        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.google_api_key = os.getenv("GOOGLE_GENAI_API_KEYS")

    def _get_chroma_client(self):
        """
        Returns a ChromaDB Cloud client
        """
        return chromadb.CloudClient(
            api_key=self.chroma_api_key,
            tenant=self.chroma_tenant,
            database=self.chroma_database
        )

    def load_pdf(self, file_path):
        """
        Reads the text content from a PDF file and returns it as a single string.

        Parameters:
        - file_path (str): The file path to the PDF file.

        Returns:
        - str: The concatenated text content of all pages in the PDF.
        """
        try:
            # Logic to read pdf
            reader = PdfReader(file_path)

            # Loop over each page and store it in a variable
            text = ""
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                text += page_text

            return text
        except Exception as e:
            raise

    def split_text(self, text: str):
        """
        Splits a text string into chunks with proper size limits and overlap.
        
        Parameters:
        - text (str): The input text to be split.

        Returns:
        - List[str]: A list containing text chunks with minimum size.
        """
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Split by sentences first (more natural boundaries)
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        chunks = []
        current_chunk = ""
        min_chunk_size = 100  # Minimum characters per chunk
        max_chunk_size = 1000  # Maximum characters per chunk
        
        for idx, sentence in enumerate(sentences):
            # If adding this sentence would exceed max size, save current chunk
            if current_chunk and len(current_chunk + " " + sentence) > max_chunk_size:
                if len(current_chunk) >= min_chunk_size:
                    chunks.append(current_chunk)
                current_chunk = sentence
            else:
                # Add sentence to current chunk
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
        
        # Add the last chunk if it meets minimum size
        if current_chunk and len(current_chunk) >= min_chunk_size:
            chunks.append(current_chunk)
        
        # If no chunks meet minimum size, create one chunk anyway
        if not chunks and text:
            chunks = [text]
        
        return chunks

    def create_chroma_db(self, documents:List, name:str="agentic-rag"):
        """
        Creates a Chroma database using the provided documents, path, and collection name.

        Parameters:
        - documents: An iterable of documents to be added to the Chroma database.
        - path (str): The path where the Chroma database will be stored.
        - name (str): The name of the collection within the Chroma database.

        Returns:
        - Tuple[chromadb.Collection, str]: A tuple containing the created Chroma Collection and its name.
        """
        try:
            chroma_client = self._get_chroma_client()
            
            # Remove the collection if it already exists
            try:
                chroma_client.delete_collection(name)
            except Exception as e:
                pass  # Ignore if it doesn't exist
            
            db = chroma_client.create_collection(name=name, embedding_function=GeminiEmbeddingFunction())

            for idx, dict_data in enumerate(documents):
                try:
                    # Add metadata for better organization
                    metadata = {
                        'filename': dict_data['filename'],
                        "chunk_index": idx,
                        "chunk_size": len(dict_data['text']),
                        "timestamp": str(datetime.now())
                    }
                    db.add(documents=dict_data['text'], ids=str(idx), metadatas=metadata)
                except Exception as e:
                    # Continue with other documents even if one fails
                    continue

            return db, name
            
        except Exception as e:
            raise
    
    def run_ingestion_pipeline(self, file_paths: List[str]):
        """
        Runs the data ingestion pipeline

        Args:
            file_paths (List[str]): A list of file paths to the PDF files.
        """
        any_content = False
        total_chunks = 0
        all_chunks = []
        
        for i, file in enumerate(file_paths):
            try:
                # Load PDF content
                text = self.load_pdf(file)
                
                if not text or not text.strip():
                    continue
                
                # Split text into chunks
                chunked_text = self.split_text(text)
                
                if not chunked_text:
                    continue
                
                # Add file information to chunks
                file_name = os.path.basename(file)
                for j, chunk in enumerate(chunked_text):
                    all_chunks.append({
                        'text': chunk,
                        'file_name': file_name,
                        'file_index': i,
                        'chunk_index': j
                    })
                
                total_chunks += len(chunked_text)
                any_content = True
                
            except Exception as e:
                continue
        
        if not any_content:
            error_msg = "No valid content found in any of the provided files"
            raise ValueError(error_msg)
        
        # Create ChromaDB collection with all chunks
        if all_chunks:
            self.create_chroma_db([{'text': chunk['text'], 'filename': chunk['file_name']} for chunk in all_chunks], "agentic-rag")
        
        return total_chunks

    def load_chroma_collection(self, name: str = "agentic-rag"):
        """
        Loads an existing ChromaDB collection.

        Parameters:
        - name (str): The name of the collection to load.

        Returns:
        - chromadb.Collection: The loaded ChromaDB collection.
        """
        try:
            chroma_client = self._get_chroma_client()
            collection = chroma_client.get_collection(name=name, embedding_function=GeminiEmbeddingFunction())
            return collection
        except Exception as e:
            raise    