import os
import google.generativeai as genai
from chromadb import Documents, EmbeddingFunction, Embeddings
from dotenv import load_dotenv
load_dotenv()

class GeminiEmbeddingFunction(EmbeddingFunction):
    """
    Custom embedding function using the Gemini AI API for document retrieval.

    This class extends the EmbeddingFunction class and implements the __call__ method
    to generate embeddings for a given set of documents using the Gemini AI API.

    Parameters:
    - input (Documents): A collection of documents to be embedded.

    Returns:
    - Embeddings: Embeddings generated for the input documents.
    """
    def __call__(self, input: Documents) -> Embeddings:
        api_keys_str = os.getenv("GOOGLE_GENAI_API_KEYS", "")
        gemini_api_keys = [k.strip() for k in api_keys_str.split(",") if k.strip()]

        if not gemini_api_keys:
            error_msg = "Gemini API Key not provided. Please provide GOOGLE_GENAI_API_KEYS as an environment variable"
            raise ValueError(error_msg)
        
        for i, key in enumerate(gemini_api_keys):
            try:
                genai.configure(api_key=key)
                model = "models/embedding-001"
                title = "Custom query"
                
                embeddings = genai.embed_content(
                    model=model,
                    content=input,
                    task_type="retrieval_document",
                    title=title
                )["embedding"]
                
                return embeddings
                
            except Exception as e:
                error_msg = str(e).lower()
                if any(keyword in error_msg for keyword in ['permission_denied', 'invalid api key', 'authentication']):
                    if i == len(gemini_api_keys) - 1:  # Last key
                        error_msg = "All API keys failed authentication"
                        raise ValueError(error_msg)
                    continue
                else:
                    raise e
        
        # This should never be reached, but just in case
        error_msg = "All API keys failed"
        raise ValueError(error_msg)
