# Agentic RAG

Chat with your PDFs and the web. One agent running locally on Ollama (`qwen3:4b`) retrieves from Postgres + pgvector and searches the web, unlocking tools on demand through pluggable capabilities.

> v2 is being rebuilt phase by phase. The previous Streamlit version lives in git history.

- Architecture: [docs/architecture.md](docs/architecture.md)
- Backend setup and commands: [backend/README.md](backend/README.md)

## Stack
FastAPI · LangChain/LangGraph · Ollama (`qwen3:4b`, `qwen3-embedding:0.6b`) · PostgreSQL 18 + pgvector · Alembic · uv · React + Vite (planned)

## Layout
```
backend/    FastAPI app, migrations, tests
docs/       architecture and ADRs
frontend/   React + Vite UI (phase P4)
```
