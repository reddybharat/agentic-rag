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
ollama pull qwen3:4b
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
