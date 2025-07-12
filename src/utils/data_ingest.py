import os
import shutil
import time
import logging
from pypdf import PdfReader, PdfWriter
import re
from src.utils.gemini_embedding import GeminiEmbeddingFunction
import chromadb
from typing import List
from pathlib import Path


class IngestData:
    def __init__(self, db_path=None):
        # Use a user data directory outside the project to avoid Streamlit watcher issues
        default_path = os.path.join(str(Path.home()), "agentic_rag_vectorDB")
        self.DB_PATH = db_path or default_path

    def load_pdf(self, file_path):
        """
        Reads the text content from a PDF file and returns it as a single string.

        Parameters:
        - file_path (str): The file path to the PDF file.

        Returns:
        - str: The concatenated text content of all pages in the PDF.
        """
        # Logic to read pdf
        reader = PdfReader(file_path)

        # Loop over each page and store it in a variable
        text = ""
        for page in reader.pages:
            text += page.extract_text()

        return text

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
        return [i for i in split_text if i != ""]

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
        chroma_client = chromadb.PersistentClient(path=self.DB_PATH)
        # Remove the collection if it already exists
        try:
            chroma_client.delete_collection(name)
        except Exception:
            pass  # Ignore if it doesn't exist
        db = chroma_client.create_collection(name=name, embedding_function=GeminiEmbeddingFunction())

        for i, d in enumerate(documents):
            db.add(documents=d, ids=str(i))

        return db, name
    
    def run_ingestion_pipeline(self, file_paths: List[str]):
        """
        Runs the data ingestion pipeline

        Args:
            file_paths (List[str]): A list of file paths to the PDF files.
        """
        any_content = False
        for file in file_paths:
            file_content = self.load_pdf(file)
            if not file_content.strip():
                print(f"Warning: No text extracted from {file}. Skipping.")
                continue
            any_content = True
            chunked_text = self.split_text(file_content)
            self.create_chroma_db(chunked_text)
        if not any_content:
            raise ValueError("No valid content found in any uploaded PDF file.")
    
    def load_chroma_collection(self, name: str):
        """
        Loads an existing Chroma collection from the specified path with the given name.

        Parameters:
        - path (str): The path where the Chroma database is stored.
        - name (str): The name of the collection within the Chroma database.

        Returns:
        - chromadb.Collection: The loaded Chroma Collection.
        """
        chroma_client = chromadb.PersistentClient(path=self.DB_PATH)
        db = chroma_client.get_collection(name=name, embedding_function=GeminiEmbeddingFunction())

        return db