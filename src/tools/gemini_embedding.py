import os
import google.generativeai as genai
from chromadb import Documents, EmbeddingFunction, Embeddings

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
            raise ValueError("Gemini API Key not provided. Please provide GEMINI_API_KEY as an environment variable")
        
        for key in gemini_api_keys:
            try:
                genai.configure(api_key=key)
                model = "models/embedding-001"
                title = "Custom query"
                return genai.embed_content(model=model,
                                        content=input,
                                        task_type="retrieval_document",
                                        title=title)["embedding"]
            except Exception as e:
                if any(keyword in str(e).lower() for keyword in ['permission_denied', 'invalid api key', 'authentication']):
                    print(e)
                    continue
                else:
                    raise e
