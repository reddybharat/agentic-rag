# Backend

FastAPI + Postgres/pgvector + Ollama. Architecture: [../docs/architecture.md](../docs/architecture.md).

## One-time setup (Windows)

### 1. uv
```powershell
winget install --id=astral-sh.uv -e
# or: powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
Open a new terminal, then check: `uv --version`.

### 2. PostgreSQL 18
1. Download the Windows installer from https://www.postgresql.org/download/windows/ (EDB).
2. Install with defaults: port `5432`, set a password for the `postgres` superuser. Skip Stack Builder.
3. Add `C:\Program Files\PostgreSQL\18\bin` to your user `PATH`, open a new terminal, and check: `psql --version`.

### 3. pgvector (built from source; there is no Windows installer)
1. Install **Visual Studio Build Tools** (2022 or 2026) with the **"Desktop development with C++"** workload: https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. Open **"x64 Native Tools Command Prompt for VS <version>"** *as Administrator* (it's a `cmd` prompt) and run the commands below. It must be the **x64** prompt: the default "Developer Command Prompt" builds 32-bit and fails with `error C2196: case value '4' already used` in `tupmacs.h`. After a failed 32-bit attempt, delete `src\*.obj` before rebuilding.
   ```bat
   set "PGROOT=C:\Program Files\PostgreSQL\18"
   cd %TEMP%
   git clone --branch v0.8.1 https://github.com/pgvector/pgvector.git
   cd pgvector
   nmake /F Makefile.win
   nmake /F Makefile.win install
   ```
   PostgreSQL 18 needs pgvector 0.8.1 or newer; use the latest tag from https://github.com/pgvector/pgvector/tags.

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
The extension is created by the superuser once; migrations only run `CREATE EXTENSION IF NOT EXISTS`.

### 5. Ollama
Update to the latest version from https://ollama.com/download, then:
```powershell
ollama pull qwen3:4b-instruct
ollama pull qwen3-embedding:0.6b
```

### 6. Project
```powershell
cd backend
copy .env.example .env      # adjust passwords if you changed them
uv sync
uv run alembic upgrade head
uv run pre-commit install
```

## Everyday commands (run in `backend/`)

| Task | Command |
|---|---|
| Run API (reload) | `uv run uvicorn app.main:create_app --factory --reload` |
| Lint | `uv run ruff check` |
| Format | `uv run ruff format` |
| Typecheck | `uv run mypy` |
| Tests | `uv run pytest -rs` |
| Migrate | `uv run alembic upgrade head` |
| New migration | `uv run alembic revision -m "<message>"` |

Check it runs: http://localhost:8000/health and http://localhost:8000/ready.

Tests that need Postgres skip unless `TEST_DATABASE_URL` is set; the Ollama-backed readiness test skips if Ollama isn't running. **`TEST_DATABASE_URL` must point to a disposable database**: migration tests downgrade it to an empty schema.

## Migrations (Alembic)

| Task | Command |
|---|---|
| Current revision | `uv run alembic current` |
| All revisions | `uv run alembic history` |
| Apply all | `uv run alembic upgrade head` |
| Undo the last one | `uv run alembic downgrade -1` |
| Undo all (drops app tables) | `uv run alembic downgrade base` |

## Inspecting the database

```powershell
psql -U app -d agentic_rag
```
```sql
\dt                                    -- sessions, turn_usage, documents, chunks, alembic_version
SELECT * FROM alembic_version;
SELECT id, filename, status, page_count, error FROM documents;
SELECT page, ordinal, left(content, 80) FROM chunks ORDER BY document_id, ordinal;
SELECT model_id, input_tokens, output_tokens, latency_ms FROM turn_usage ORDER BY created_at DESC;
```

## Trying ingestion and chat by hand

With the API running (`uv run uvicorn app.main:create_app --factory --reload`), in a second PowerShell:

```powershell
curl.exe -F "file=@tests/fixtures/sample.pdf;type=application/pdf" http://localhost:8000/documents
curl.exe http://localhost:8000/documents      # library; status: pending -> ready
$s = (Invoke-RestMethod -Method Post http://localhost:8000/sessions -ContentType application/json -Body '{}').id
curl.exe -N -X POST http://localhost:8000/sessions/$s/messages -H "Content-Type: application/json" -d '{\"text\":\"What is the phase two budget?\"}'
```

Expect `tool_start` (search_docs) → `tool_end` → `token`… → `done`, with a citation like `(sample.pdf, p. 3)`. Uploading the same file again returns 409; `curl.exe -X DELETE http://localhost:8000/documents/<id>` removes it from the library. Any session can answer from any library document. Interactive API docs: http://localhost:8000/docs. The facts in `sample.pdf` are listed in [docs/internals.md](../docs/internals.md#11-tests-and-the-sample-pdf).
