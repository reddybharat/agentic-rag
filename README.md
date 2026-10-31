# Agentic RAG

Chat with your PDFs, locally. One agent on a Gemini free-tier or Groq model (picked in the chat input) answers from a document library in Postgres + pgvector and cites pages. The agent starts with a small base prompt and an index of skills, and reads a skill before it can use that skill's tools.

**Stack:** FastAPI · LangChain/LangGraph · Gemini (`gemini-3.5-flash-lite` default) · Groq (`qwen/qwen3.8-27b`) · Ollama (`qwen3-embedding:0.6b`) · PostgreSQL 18 + pgvector · Alembic · uv · React + Vite + Tailwind + shadcn/ui

## Documentation

| Doc | Use |
| --- | --- |
| [CLAUDE.md](CLAUDE.md) | Rules for coding agents: invariants, doc rules, coding and testing standards |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Layers, flow diagrams, data model, key decisions, extension points |
| [docs/FLOW.md](docs/FLOW.md) | What is implemented now, file by file; constants; how to test and check by hand |
| [docs/skill-template/SKILL.md](docs/skill-template/SKILL.md) | Template and rules for a new skill |

## Setup (Windows, one time)

Everything runs natively; there is no Docker locally.

### 1. uv
```powershell
winget install --id=astral-sh.uv -e
```
Open a new terminal and check `uv --version`.

### 2. PostgreSQL 18
1. Install from https://www.postgresql.org/download/windows/ (EDB) with defaults: port `5432`, a password for `postgres`. Skip Stack Builder.
2. Add `C:\Program Files\PostgreSQL\18\bin` to your user `PATH` and check `psql --version`.

### 3. pgvector (built from source; there is no Windows installer)
1. Install **Visual Studio Build Tools** with the **"Desktop development with C++"** workload: https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. Open **"x64 Native Tools Command Prompt for VS"** *as Administrator*. It must be the **x64** prompt: the default developer prompt builds 32-bit and fails with `error C2196: case value '4' already used` in `tupmacs.h` (delete `src\*.obj` after a failed attempt).
   ```bat
   set "PGROOT=C:\Program Files\PostgreSQL\18"
   cd %TEMP%
   git clone --branch v0.8.1 https://github.com/pgvector/pgvector.git
   cd pgvector
   nmake /F Makefile.win
   nmake /F Makefile.win install
   ```
   PostgreSQL 18 needs pgvector 0.8.1 or newer.

### 4. Databases and role
```powershell
psql -U postgres
```
```sql
CREATE ROLE app LOGIN PASSWORD 'app';
CREATE DATABASE agentic_rag OWNER app;
CREATE DATABASE agentic_rag_test OWNER app;
\c agentic_rag
CREATE EXTENSION vector;
\c agentic_rag_test
CREATE EXTENSION vector;
\q
```
The superuser creates the extension once; migrations only run `CREATE EXTENSION IF NOT EXISTS`.

### 5. Ollama
Install the latest version from https://ollama.com/download, then:
```powershell
ollama pull qwen3-embedding:0.6b
```

For the Gemini chat models, create a free key at https://aistudio.google.com/apikey and set `GOOGLE_API_KEY` in `backend/.env`. With it, the question and the retrieved passages are sent to Google. Free-tier quotas are small and per model per day (see `docs/FLOW.md` §4).

For the Groq chat models, create a key at https://console.groq.com/keys and set `GROQ_API_KEY` in `backend/.env`. The question and the retrieved passages are sent to Groq. Set at least one of `GOOGLE_API_KEY` / `GROQ_API_KEY`; the app does not start without a chat model.

### 6. Project
```powershell
cd backend
copy .env.example .env      # adjust passwords if you changed them
uv sync
uv run alembic upgrade head
uv run pre-commit install

cd ..\frontend
copy .env.example .env      # optional; VITE_API_URL defaults to http://localhost:8000
npm install
```

## Run

| Task | Where | Command |
|---|---|---|
| API (reload) | `backend/` | `uv run uvicorn app.main:create_app --factory --reload` |
| UI | `frontend/` | `npm run dev` → http://localhost:5173 |
| Health / readiness | | http://localhost:8000/health, http://localhost:8000/ready |
| API docs | | http://localhost:8000/docs |

Upload PDFs in the **Library** view, then ask questions in a chat. To check by hand with curl, see [docs/FLOW.md](docs/FLOW.md#13-check-by-hand).

## Develop

| Task | Where | Command |
|---|---|---|
| Lint / format / typecheck | `backend/` | `uv run ruff check` · `uv run ruff format` · `uv run mypy` |
| Tests | `backend/` | `uv run pytest -rs` |
| New migration | `backend/` | `uv run alembic revision -m "<message>"` |
| Undo last migration | `backend/` | `uv run alembic downgrade -1` |
| Lint / build UI | `frontend/` | `npm run lint` · `npm run build` |
| Add a shadcn component | `frontend/` | `npx shadcn@latest add <name>` |

Tests that need Postgres skip unless `TEST_DATABASE_URL` is set; Ollama tests skip if Ollama isn't running, and live Gemini/Groq tests skip without their key. **`TEST_DATABASE_URL` must point to a disposable database**: migration tests downgrade it to an empty schema. CI (`.github/workflows/`) runs lint, format check, mypy and the tests against a `pgvector/pgvector:pg18` container.

## Repository layout

```
backend/    FastAPI app (app/), Alembic migrations, tests, config/models.yaml
frontend/   React + Vite UI
docs/       ARCHITECTURE.md, FLOW.md, skill-template/
```

The previous Streamlit version lives in git history.
