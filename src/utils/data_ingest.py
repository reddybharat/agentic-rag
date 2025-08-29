__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import os
import re
from typing import List
from pypdf import PdfReader
import chromadb
from src.utils.gemini_embedding import GeminiEmbeddingFunction

class IngestData:
    def __init__(self, db_path=None):
        # Use a user data directory outside the project to avoid Streamlit watcher issues
        # default_path = os.path.join(str(Path.home()), "vectorDB")
        # self.DB_PATH = db_path or default_path
        self.DB_PATH = "./src/data/vectorDB"

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
        Splits a text string into a list of non-empty substrings based on the specified pattern.
        The "\n \n" pattern will split the document para by para
        Parameters:
        - text (str): The input text to be split.

        Returns:
        - List[str]: A list containing non-empty substrings obtained by splitting the input text.

        """
        split_text = re.split('\n \n', text)
        chunks = [i for i in split_text if i != ""]
        return chunks

    def create_chroma_db(self, documents:List, name:str="devuser"):
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
            # Ensure the database directory exists
            os.makedirs(self.DB_PATH, exist_ok=True)
            
            chroma_client = chromadb.PersistentClient(path=self.DB_PATH)
            
            # Remove the collection if it already exists
            try:
                chroma_client.delete_collection(name)
            except Exception:
                pass  # Ignore if it doesn't exist
            
            db = chroma_client.create_collection(name=name, embedding_function=GeminiEmbeddingFunction())

            for i, d in enumerate(documents):
                try:
                    db.add(documents=d, ids=str(i))
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
                
                # Create ChromaDB collection with the chunks
                self.create_chroma_db(chunked_text, "devuser")
                
                total_chunks += len(chunked_text)
                any_content = True
                
            except Exception as e:
                continue
        
        if not any_content:
            error_msg = "No valid content found in any of the provided files"
            raise ValueError(error_msg)

    def load_chroma_collection(self, name: str = "devuser"):
        """
        Loads an existing ChromaDB collection.

        Parameters:
        - name (str): The name of the collection to load.

        Returns:
        - chromadb.Collection: The loaded ChromaDB collection.
        """
        try:
            chroma_client = chromadb.PersistentClient(path=self.DB_PATH)
            collection = chroma_client.get_collection(name=name)
            return collection
        except Exception as e:
            raise