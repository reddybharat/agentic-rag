# Agentic RAG

Chat with your PDFs. One agent running locally on Ollama (`qwen3:4b-instruct`) answers from documents stored in Postgres + pgvector and cites pages. Tools are unlocked on demand through pluggable capabilities.

> v2 is being rebuilt phase by phase: the backend (P0–P4: models, sessions, streaming chat, capabilities, shared PDF library), the frontend (P5) and structured logging (P6) are built; skill files (P7) are next. Web search is a later enhancement. The previous Streamlit version lives in git history.

## Docs
- [docs/architecture.md](docs/architecture.md): the big picture (layers, request flow, data model)
- [docs/internals.md](docs/internals.md): every mechanism in detail (model selection, embeddings, chunking, retrieval, agent loop, SSE events)
- [frontend/README.md](frontend/README.md): run the UI
- [backend/README.md](backend/README.md): setup, commands, inspecting the database and ingestion

## Stack
FastAPI · LangChain/LangGraph · Ollama (`qwen3:4b-instruct`, `qwen3-embedding:0.6b`) · PostgreSQL 18 + pgvector · Alembic · uv · React + Vite + Tailwind + shadcn/ui

## Layout
```
backend/    FastAPI app, migrations, tests
docs/       architecture, internals, ADRs
frontend/   React + Vite UI
```
