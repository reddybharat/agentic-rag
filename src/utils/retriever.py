from src.prompts.rag_prompt import rag_prompt
import google.generativeai as genai
from google.genai import types
import os
from src.utils.logger import logger

class Retriever:
    def __init__(self) -> None:
        api_keys_str = os.getenv("GOOGLE_GENAI_API_KEYS", "")
        self.api_keys = [k.strip() for k in api_keys_str.split(",") if k.strip()]
        self.model = "gemini-2.0-flash-lite"
        logger.log(f"[Retriever] Initialized with {len(self.api_keys)} API key(s) and model '{self.model}'")

    def get_relevant_passage(self, query, db, n_results):
        logger.log(f"[Retriever] Retrieving top {n_results} passages for query: {query}")
        passage = db.query(query_texts=[query], n_results=n_results)['documents'][0]
        # Ensure passage is a string
        if isinstance(passage, list):
            passage = '\n'.join(str(p) for p in passage)
        logger.log(f"[Retriever] Retrieved passage: {passage[:100]}..." if passage else "[Retriever] No passage found.")
        return passage

    def generate_answer(self, context):
        if not self.api_keys:
            logger.log("[Retriever] ERROR: Gemini API Key not provided.")
            raise ValueError("Gemini API Key not provided. Please provide GEMINI_API_KEY as an environment variable")

        for key in self.api_keys:
            try:
                logger.log("[Retriever] Configuring Gemini API with provided key.")
                genai.configure(api_key=key)
                model = genai.GenerativeModel(self.model)
                logger.log(f"[Retriever] Generating answer with context: {context[:100]}...")
                response = model.generate_content(context)
                logger.log(f"[Retriever] Received response: {response.text.strip()[:100]}...")
                return response.text.strip()
            except Exception as e:
                logger.log(f"[Retriever] Exception: {str(e)}")
                if any(keyword in str(e).lower() for keyword in ['permission_denied', 'invalid api key', 'authentication']):
                    continue
                else:
                    raise e
        logger.log("[Retriever] All API keys failed.")
        return "[Retriever] ERROR: All API keys failed."

    def run_retriever_node(self, query, db, n_results=5):
        logger.log(f"[Retriever] Running retriever node for query: {query}")
        context = self.get_relevant_passage(query, db, n_results)
        response = self.generate_answer(context)
        logger.log(f"[Retriever] Final answer: {response[:100]}...")
        return response
