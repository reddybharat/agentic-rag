from src.helpers.prompts import rag_prompt
import google.generativeai as genai
from google.genai import types
import os
from src.utils.logger import logger

class Retriever:
    def __init__(self) -> None:
        api_keys_str = os.getenv("GOOGLE_GENAI_API_KEYS", "")
        self.api_keys = [k.strip() for k in api_keys_str.split(",") if k.strip()]
        self.model = "gemini-2.0-flash-lite"

    def get_relevant_passage(self, query, db, n_results):
        # Retrieve relevant passages from the DB
        result = db.query(query_texts=[query], n_results=n_results)
        documents = result.get('documents', [])
        if not documents or not documents[0]:
            return ""
        passage = documents[0]
        # Ensure passage is a string
        if isinstance(passage, list):
            passage = '\n'.join(str(p) for p in passage)
        return passage

    def generate_answer(self, context):
        if not self.api_keys:
            raise ValueError("Gemini API Key not provided. Please provide GEMINI_API_KEY as an environment variable")

        for key in self.api_keys:
            try:
                genai.configure(api_key=key)
                model = genai.GenerativeModel(self.model)
                response = model.generate_content(context)
                return response.text.strip()
            except Exception as e:
                if any(keyword in str(e).lower() for keyword in ['permission_denied', 'invalid api key', 'authentication']):
                    continue
                else:
                    raise e
        return "[Retriever] ERROR: All API keys failed."

    def run_retriever_node(self, query, db, n_results=5):
        context = self.get_relevant_passage(query, db, n_results)
        response = self.generate_answer(context)
        return response
