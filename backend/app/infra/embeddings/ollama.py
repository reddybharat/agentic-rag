from langchain_ollama import OllamaEmbeddings

# Qwen3-Embedding expects an instruction on the query side only; chunks are embedded as-is.
QUERY_INSTRUCTION = "Given a question, retrieve document passages that answer it"


class OllamaEmbedder:
    def __init__(self, base_url: str, model_name: str, dim: int, timeout_s: float) -> None:
        self._model_name = model_name
        self._dim = dim
        self._client = OllamaEmbeddings(
            model=model_name,
            base_url=base_url,
            dimensions=dim,
            client_kwargs={"timeout": timeout_s},
        )

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dim(self) -> int:
        return self._dim

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._client.aembed_documents(texts)

    async def embed_query(self, text: str) -> list[float]:
        return await self._client.aembed_query(f"Instruct: {QUERY_INSTRUCTION}\nQuery: {text}")
