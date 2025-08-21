# Agentic Retrieval-Augmented Generation

## About & Features

This is a graph-based RAG system for querying your PDFs or the web, with LLM-powered reasoning and a Streamlit UI.
---

## Tech Stack & Tools

Python, LangGraph, LangChain, Gemini, Tavily Search, ChromaDB, Streamlit

---

## Quick Start

### Install dependencies
```bash
pip install -r requirements.txt
```

1. **Set up environment variables**
   - Create a `.env` file in the project root with:
     ```env
     GOOGLE_GENAI_API_KEYS="your_gemini_api_key1,your_gemini_api_key2"
     TAVILY_API_KEY="your_tavily_api_key"
     ```
2. **Run the Streamlit app**
   ```bash
   streamlit run streamlit_app.py
   ```
3. **Use the UI**
   - Upload PDF files and ask questions, or enable Web Search for open-domain queries.
   - View the agent's response and the reasoning graph.

---

## Project Structure

```
agentic-rag/
├── app.py                # (Entry point for API, if used)
├── streamlit_app.py      # Main Streamlit UI
├── graph.png             # Example graph visualization
├── requirements.txt      # Python dependencies
├── src/
│   ├── graphs/           # Graph builder and node logic
│   ├── utils/            # Data ingestion, embeddings, LLM runner, logger
│   ├── tools/            # Web search/crawl tools
│   ├── helpers/          # Prompt templates
│   ├── prompts/          # Prompt files
│   ├── data/             # VectorDB storage
│   ├── models.py, schemas.py
│   └── routers/          # (API routers, if extended)
└── test_graph.py         # Test script for the graph
```

---

## Configuration

- **Environment variables** (set in `.env`):
  - `GOOGLE_GENAI_API_KEYS`: Comma-separated Gemini API keys
  - `TAVILY_API_KEY`: Tavily web search API key

---