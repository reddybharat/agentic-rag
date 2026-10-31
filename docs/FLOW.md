# Flow

Single source of truth for what is implemented **now**: how a question and an upload move through the backend, which files run, the constants in use, and how to run and test each part.

- The design and its reasons are in [ARCHITECTURE.md](ARCHITECTURE.md). Setup is in [README.md](../README.md).
- Update this file in the same change as the code (see [CLAUDE.md](../CLAUDE.md), "Definition of done"). Cite code as file plus symbol, never by line number.

Paths are relative to `backend/` unless they start with `frontend/`.

---

## 1. Run it

### 1.1 Environment

`app/core/config.py: Settings` (pydantic-settings) reads env vars or `backend/.env` (copy `backend/.env.example`).

| Setting | Default | Used for |
|---|---|---|
| `DATABASE_URL` | required | app DB (`postgresql+asyncpg://…`) |
| `TEST_DATABASE_URL` | unset → DB tests skip | disposable test DB, read by `tests/conftest.py` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | chat + embeddings |
| `LOG_LEVEL` / `LOG_JSON` | `INFO` / `true` | logging (`.env.example` sets `LOG_JSON=false`) |
| `DEFAULT_OWNER_ID` | `local` | owner of every session and document until auth exists |
| `READINESS_TIMEOUT_S` | `2.0` | per-check timeout in `/ready` |
| `MODELS_CONFIG_PATH` | `config/models.yaml` | chat model catalog |
| `LLM_TIMEOUT_S` | `120.0` | HTTP timeout for Ollama chat and embedding calls |
| `EMBEDDING_MODEL` | `qwen3-embedding:0.6b` | embedder; stored on each document |
| `EMBEDDING_DIM` | `1024` | vector size; **must equal** the `vector(1024)` column from migration `0003` |
| `MAX_UPLOAD_BYTES` | `20971520` (20 MiB) | upload size limit |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | browser origins allowed to call the API (JSON list) |

The frontend reads `VITE_API_URL` (default `http://localhost:8000`) from `frontend/.env`.

### 1.2 Tests

| Command (in `backend/`) | Needs | Covers |
|---|---|---|
| `uv run pytest tests/unit -q` | nothing | skill loader, progressive disclosure, chunker, model factory |
| `uv run pytest -rs` | Postgres (`TEST_DATABASE_URL`) + Ollama; skips with a reason otherwise | everything: health/ready, models, sessions, documents + chat, logging, migrations |

### 1.3 Check by hand

With the API running (`uv run uvicorn app.main:create_app --factory --reload`), in a second PowerShell in `backend/`:

```powershell
curl.exe -F "file=@tests/fixtures/sample.pdf;type=application/pdf" http://localhost:8000/documents
curl.exe http://localhost:8000/documents      # status: pending -> ready
$s = (Invoke-RestMethod -Method Post http://localhost:8000/sessions -ContentType application/json -Body '{}').id
curl.exe -N -X POST http://localhost:8000/sessions/$s/messages -H "Content-Type: application/json" -d '{\"text\":\"What is the phase two budget?\"}'
```

Expect `tool_start`/`tool_end` for `read_skill_file` (pre-read), then for `retrieve_documents`, then `token`… and `done`, with a citation like `(sample.pdf, p. 3)`. Uploading the same file again returns 409; `curl.exe -X DELETE http://localhost:8000/documents/<id>` removes it. Interactive API docs: http://localhost:8000/docs.

Inspect the database with `psql -U app -d agentic_rag`:

```sql
SELECT id, filename, status, page_count, error FROM documents;
SELECT page, ordinal, left(content, 80) FROM chunks ORDER BY document_id, ordinal;
SELECT model_id, input_tokens, output_tokens, latency_ms FROM turn_usage ORDER BY created_at DESC;
```

---

## 2. Startup: who builds what

`uvicorn app.main:create_app --factory` calls `main.py: create_app`:

1. `Settings()` reads the environment.
2. `core/logging.py: configure_logging` sets up structlog. The request middleware binds `request_id` to every log line of a request and echoes it in `X-Request-ID`.
3. The lifespan runs `container.py: Container.build` once. It is the only place concrete classes are created:

```text
engine (SQLAlchemy async, asyncpg, pool_pre_ping)
 └─ uow = SqlUnitOfWork factory              one DB transaction per `async with uow()`
ModelFactory.from_yaml(config/models.yaml, {"ollama": OllamaChatProvider})
SessionService(uow, owner, fast model, prompts/title.md)
OllamaEmbedder(qwen3-embedding:0.6b, dim 1024)
DocumentService(uow, owner, embedder, load_pdf_pages, split_words, MAX_UPLOAD_BYTES)
build_agent(smart model,
            prompts/system.md,                  base system prompt
            load_skills(),                      agent/skills/
            [make_retrieve_documents(documents.search)],
            {"library_has_documents": documents.has_ready})
ChatService(uow, agent, "qwen3-4b-smart", sessions)
```

Startup fails fast on a malformed skill file, an unknown tool in `allowed-tools` or `preactivation.yaml`, or an unknown pre-activation condition. Routes get services through `api/deps.py` (`request.app.state.container`).

---

## 3. One chat turn, end to end

`POST /sessions/{id}/messages {"text": "..."}` (1–8000 characters after trimming, otherwise 422).

1. The `get_session` dependency loads the session with the owner filter. An unknown session gives 404 **before** the stream starts.
2. `services/chat.py: ChatService.stream` calls `agent.astream({"messages": [HumanMessage(text)]}, stream_mode=["messages", "updates"], context=AgentContext(owner_id))`.
3. `ProgressiveDisclosure.abefore_agent` (§7.3) enables condition tools and pre-reads triggered skills.
4. The agent loops: model call → tool calls → model call … until an answer or 8 tool calls.
5. Stream mapping:
   - `messages` mode → `AIMessageChunk`s → one `token` event per non-empty `.text` (thinking never appears in `.text`). `usage_metadata` is summed over all model calls.
   - `updates` mode → an `AIMessage` with `tool_calls` gives a `tool_start` per call (the pre-read round included); a `ToolMessage` gives `tool_end` (`ok = status != "error"`).
6. An exception during the stream → logged with traceback → one `error` event (`chat_failed`); no usage is saved.
7. On success: insert `turn_usage` → `SessionService.auto_title` (only while the title is `New chat`; fast model; a failure is logged as a warning and never fails the turn) → `done`.

### SSE events

| event | data |
|---|---|
| `tool_start` | `{id, name, args}` |
| `tool_end` | `{id, name, ok}` |
| `token` | `{text}` |
| `done` | `{input_tokens, output_tokens, latency_ms}` |
| `error` | `{code, message}` |

Order: `tool_start`/`tool_end` and `token` interleaved, then exactly one `done` or `error`. `frontend/src/lib/api.ts: streamMessage` POSTs and parses the stream with `fetch` + `TextDecoderStream` (`EventSource` cannot POST); its API types are hand-written mirrors of the backend schemas.

---

## 4. Chat models

`config/models.yaml` → `ModelSpec {id, provider, model_name, tier, supports_tools, options}`:

| id | model | tier | options | used by |
|---|---|---|---|---|
| `qwen3-4b-fast` | `qwen3:4b-instruct` | fast | `reasoning: false`, `num_predict: 256` | session auto-title |
| `qwen3-4b-smart` | `qwen3:4b-instruct` | smart | `reasoning: false`, `num_ctx: 8192` | the agent |

- Selection is fixed at startup: `ModelFactory.for_tier(Tier.SMART)` for the agent, `for_tier(Tier.FAST)` for titles. `GET /models` lists the catalog.
- `infra/llm/model_factory.py: ModelFactory` fails startup if a tier has zero or several models, or a spec names an unregistered provider. It builds each model once.
- `infra/llm/ollama.py: OllamaChatProvider` **rejects unknown option keys**, because `ChatOllama` silently ignores them.
- `qwen3:4b-instruct` is the non-thinking variant; `reasoning: false` is the ChatOllama field that turns thinking off. `num_ctx: 8192` leaves room for the system prompt, read skills and 4 passages.

---

## 5. Embeddings

`infra/embeddings/ollama.py: OllamaEmbedder` wraps `OllamaEmbeddings`.

| Aspect | Value |
|---|---|
| Model / dimension | `qwen3-embedding:0.6b`, 1024 (`dimensions=`) |
| Chunk side | text as-is, no prefix |
| Query side | `Instruct: Given a question, retrieve document passages that answer it\nQuery: <question>` |
| Batching | `DocumentService` embeds `EMBED_BATCH_SIZE = 32` chunks per call |
| Distance | cosine (`vector_cosine_ops` HNSW index) |

Every document row stores `embedding_model`; `/ready` returns 503 (`checks.embeddings = false`) if any `ready` document used another model. To change the model: set `EMBEDDING_MODEL` (and `EMBEDDING_DIM` plus a migration recreating `chunks.embedding` and its index if the size changes), then re-ingest.

---

## 6. Ingestion

```text
POST /documents (multipart "file", one file per request)
  services/documents.py: DocumentService.upload
    1. len(data) > MAX_UPLOAD_BYTES       → 413 payload_too_large
    2. not data.startswith(b"%PDF-")      → 422 invalid_document
    3. sha256 already in the library      → 409 conflict  (also unique on (owner_id, sha256))
    4. insert documents row, status = pending
  response 202 {id, filename, status: "pending", ...}
  background task: DocumentService.ingest(document_id, data)
    a. infra/rag/pdf_loader.py: load_pdf_pages   pypdf text per page (in a thread)
    b. infra/rag/chunkers.py: split_words         per page
    c. no chunks at all                  → failed: "No extractable text: the PDF may be scanned images."
    d. embed in batches of 32
    e. one transaction: insert chunks + status = ready + page_count
    any exception                        → logged, status = failed, error = "Could not read this PDF."
```

- `GET /documents` lists the library (poll for `pending → ready | failed`). `DELETE /documents/{id}` cascades to chunks (404 for unknown or another owner's).
- **Chunking (`split_words`):** chunks never cross a page. Whitespace-split words are packed until the next word would exceed `CHUNK_CHARS = 1000`; the next chunk starts `OVERLAP_WORDS = 30` words back; whitespace is normalised; `ordinal` numbers chunks across the document.
- pypdf flattens layout and tables; scanned pages give no text (no OCR).

---

## 7. The agent

`agent/agent_builder.py: build_agent`:

```text
create_agent(smart model,
             tools=[read_skill_file, retrieve_documents],
             system_prompt=catalog.system_prompt(system.md),     base prompt + skill index
             middleware=[ProgressiveDisclosure(catalog, conditions),
                         ToolCallLimitMiddleware(run_limit=8, exit_behavior="continue")],
             context_schema=AgentContext)
```

- **Context:** `agent/state.py: AgentContext(owner_id)`, passed per run, readable by middleware and tools.
- **State:** `messages` plus `enabled_tools` (`DisclosureState`). It lives for one run: no checkpointer.
- After 8 tool calls, further calls get an error result and the model has to answer.

### 7.1 System prompt

`SkillCatalog.system_prompt(base)` = `prompts/system.md` + `## Skills` + one index line per skill:

```text
<prompts/system.md>

## Skills
Read a skill with `read_skill_file` before using its tools. Skills:
- answering-document-questions (`answering-document-questions/SKILL.md`): Read when the user asks a question ...
```

Skill bodies are never in the system prompt; they arrive as `read_skill_file` results.

### 7.2 Skills (`agent/skill_loader.py: load_skills`)

Reads `agent/skills/` once at startup and fails fast with the bad path:
- `<name>/SKILL.md`: frontmatter `name` (= folder name), `description`, `allowed-tools` (non-empty, space-separated). The whole file text is kept, because the middleware matches on it.
- `preactivation.yaml`: `max_skills >= 1`; `skills:` rules name a known skill and single-word triggers; `tools:` rules have a string `tool` and `when`.

| Skill | allowed-tools | Does |
|---|---|---|
| `answering-document-questions` | `retrieve_documents` | retrieve, retry once with other words, answer from the passages |

The format is documented in [skill-template/SKILL.md](skill-template/SKILL.md).

### 7.3 Pre-activation and progressive disclosure (`agent/middleware/progressive_disclosure.py: ProgressiveDisclosure`)

`agent/skills/preactivation.yaml`:

| Rule | Effect |
|---|---|
| `skills:` `answering-document-questions` ← what, who, when, where, why, how, which, explain, define, describe, tell, about, list, give, show, document, documents, pdf, page | pre-read |
| `tools:` `retrieve_documents` when `library_has_documents` | enabled without a skill |
| `max_skills: 2` | cap on pre-read skills |

1. **`abefore_agent`, once per turn:**
   - For each `tools:` rule, runs the named condition with the owner id. `library_has_documents` is `DocumentService.has_ready` (one `EXISTS` query for a `ready` document). Hits go to `enabled_tools`.
   - `SkillCatalog.preactivate(question)` lowercases the question, splits it into words, and returns skills whose triggers match, in rule order, capped at `max_skills`. For the hits it appends a synthetic `AIMessage(tool_calls=[read_skill_file(path)])` and matching `ToolMessage(file text)`. LangChain treats this as a finished tool round, so it saves a model call; the UI shows it as a `read_skill_file` step.
2. **`awrap_model_call`:** the model sees `read_skill_file` plus unlocked tools. Unlocked = `enabled_tools` ∪ `allowed-tools` of every skill whose exact text is a `read_skill_file` result this turn.
3. **`awrap_tool_call`:** a locked tool returns `Tool '<name>' is locked. Read the skill that lists it first.` (status error) without running.

### 7.4 Tools (`agent/tools.py`)

| Tool | Available | Returns |
|---|---|---|
| `read_skill_file(path)` | always | the skill file text, or `Unknown file '<path>'. Available: [...]` |
| `retrieve_documents(query)` | library has a `ready` document, or a skill listing it was read | up to `RETRIEVE_LIMIT = 4` passages |

`retrieve_documents`:
1. `owner_id` comes from `AgentContext`, not from the model.
2. `DocumentService.search` embeds the query (with the instruction prefix) and calls `SqlDocumentRepository.search`: `SET LOCAL hnsw.iterative_scan = strict_order` (so the owner filter can't starve the HNSW candidates), top 4 chunks of the owner by cosine distance, plus chunks `ordinal ± 1` **on the same page** as context (context from another page made the model cite the wrong page).
3. Format, each context side cut to `CONTEXT_CHARS = 300`, followed by `CITATION_RULES` (cite every fact as `(filename, p. N)` from the passage header, never guess a page, quote only when wording matters, report disagreeing passages with both citations). No hits → `No matching passages in the document library.` and no rules.

Citation rules live in the tool result, not in `system.md` or a skill: they reach the model exactly when there are passages to cite, whichever path enabled the tool, and cost nothing on turns without retrieval.

```text
[sample.pdf, page 3] (chunk 1b6e…)
The total budget for phase two is 4.2 million euros, …
Context before: …<last 300 chars of the previous chunk on this page>
Context after: <first 300 chars of the next chunk on this page>…

Citation rules: cite every fact from these passages as (filename, p. N), …
```

### 7.5 Prompts

| File | Role |
|---|---|
| `agent/prompts/system.md` | base system prompt, every turn; its last line tells the model to always call `retrieve_documents` before answering (skip only greetings and small talk) |
| `agent/prompts/title.md` | auto-title instruction for the fast model |
| `agent/skills/*/SKILL.md` | skills, read on demand |

The always-search rule must be in the **system prompt**. Measured on 7 queries against the 5-document library (2026-10-31): with the rule only in the pre-read skill (a tool result), `qwen3:4b-instruct` searched for 1 of 5 questions and answered the rest from its own knowledge; with the rule in `system.md` plus trigger pre-reads, 6 of 7 were right (`hi` correctly skips tools). Pre-reading the answering skill on every turn when the library has documents made it worse, so pre-reads stay trigger-only. The skill repeats the rule as its first bullet.

---

## 8. Persistence and errors

- **Unit of work** (`infra/db/unit_of_work.py`): each `async with uow()` is one transaction; nothing persists without `commit()`.
- **Owner scoping:** every repository method filters by `owner_id`; another owner's session or document behaves as missing (404).
- **Migrations** (`migrations/versions/`): `0001` sessions + `vector` extension, `0002` turn_usage, `0003` documents + chunks, `0004` documents/chunks scoped to the owner. `env.py` is async and reads `DATABASE_URL` unless `sqlalchemy.url` is set (tests set it).
- **Errors:** `core/errors.py: AppError` subclasses become `{"error": {"code", "message"}}`: `AppError` 400 `bad_request`, `NotFoundError` 404, `ConflictError` 409, `PayloadTooLargeError` 413, `InvalidDocumentError` 422 `invalid_document`, anything else 500 `internal_error` (logged with traceback). FastAPI validation errors stay 422 with FastAPI's body.

---

## 9. Logging

structlog, console or JSON per `LOG_JSON`; `request_id` on every line of a request. Ids, sizes, counts and durations only, never message text, document content or file bytes. Failures log at ERROR with a traceback, rejections and tool errors at WARNING, everything else at INFO.

| Event | Where | Fields |
|---|---|---|
| `http_request` | `main.py` middleware | method, path, status, duration_ms (SSE: time to first byte) |
| `upload_received` / `upload_rejected` | `DocumentService.upload` | document_id, filename, bytes / reason = size, type, duplicate |
| `ingestion_started` / `ingestion_done` / `ingestion_failed` | `DocumentService.ingest` | pages, chunks, embed_batches, `load_ms` `chunk_ms` `embed_ms` `store_ms`, total_ms |
| `document_deleted` | `DocumentService.delete` | document_id |
| `search_done` | `DocumentService.search` | hits, query_chars, duration_ms |
| `turn_started` / `turn_done` / `turn_failed` | `ChatService.stream` | session_id, model_id, tokens, latency_ms |
| `tool_start` / `tool_end` / `tool_limit_reached` | `ChatService` | tool, tool_call_id, ok, duration_ms |
| `skills_loaded` | `load_skills` (startup) | skills, tool_rules |
| `tool_enabled` | `ProgressiveDisclosure.abefore_agent` | tool |
| `preactivate` | `SkillCatalog.preactivate` | selected, triggers |
| `skill_read` | `read_skill_file` / `ProgressiveDisclosure` | path, status = ok / unknown_path, source = read_skill_file / preactivate |
| `tool_locked` | `ProgressiveDisclosure.awrap_tool_call` | tool |

Tests use `structlog.testing.capture_logs` (`tests/integration/test_logging.py`); build the app first, then enter `capture_logs`, because `create_app` configures logging.

---

## 10. Frontend

`frontend/` is a React + Vite SPA (Tailwind, shadcn/ui) calling the backend directly (CORS). `src/lib/api.ts` holds the typed REST calls and `streamMessage`. Views:
- sessions sidebar (new, rename, delete);
- chat: markdown with raw HTML skipped; under each answer one collapsed line such as `1 skill · 2 tools`, which expands to `skill: <name>` per skill read this turn (from `read_skill_file` `tool_start` args, pre-reads included) and `tool: <name> …/✓/✗` per other tool call; a one-line hint when the library is empty;
- Library: drop zone or picker, multi-file, per-file status, polls every 2 s while any document is `pending`, delete.

Chat turns live in tab state only: a refresh clears them, matching the stateless backend.

---

## 11. Tests and the sample PDF

Tests hit **real** Postgres (`TEST_DATABASE_URL`, truncated before each test) and **real** Ollama, and skip with a reason when either is unavailable. `TEST_DATABASE_URL` must be disposable: migration tests downgrade it to an empty schema.

`tests/fixtures/sample.pdf` is a synthetic 4-page report about a fictional "Project Halcyon", so the facts can't come from the model's training data:

| Page | Facts |
|---|---|
| 1 | Ostrava Water Cooperative, founded 2011, eleven coastal villages |
| 2 | Kessel Bay plant: 1,840 m³/day (1,120 during February storms), 3.1 kWh/m³ |
| 3 | Phase two budget 4.2 M€ (approved 14 March 2025), 2.6 M€ membrane train, 0.9 M€ solar array |
| 4 | Lead engineer Mirela Vantongeren, Quillfeather Membranes (Tallinn), Brannock Laboratory |

| Test file | Checks |
|---|---|
| `tests/unit/test_skill_loader.py` | shipped skills load and are indexed; trigger matching; malformed files rejected |
| `tests/unit/test_progressive_disclosure.py` | tools hidden until unlocked; condition enables a tool; pre-read round; locked call refused; unknown condition rejected |
| `tests/unit/test_chunkers.py`, `test_model_factory.py` | chunk packing/overlap; catalog validation |
| `tests/integration/test_documents.py` | upload validation, ingestion, delete cascade, owner isolation, chat answer cites p. 3 via `retrieve_documents` |
| `tests/integration/test_chat.py`, `test_sessions.py`, `test_models.py`, `test_health.py` | SSE turn + usage + auto-title, error event, session CRUD, `/models`, `/health` + `/ready` |
| `tests/integration/test_logging.py` | key log events for ingestion and a chat turn |
| `tests/integration/test_migrations.py` | upgrade → downgrade → upgrade, `0004` backfill and dedupe |

The chat-with-document tests depend on model output and can fail intermittently.

---

## 12. Known gaps and shortcuts

| Shortcut | Limit | Upgrade when |
|---|---|---|
| FastAPI `BackgroundTasks` for ingestion | in-flight jobs lost on restart; the row stays `pending` | ingestion must survive restarts → job queue |
| Size check after the body is received | multipart spools the whole upload first | exposed publicly → body limit at the proxy |
| pypdf text only | no OCR, tables flattened | scanned PDFs matter → OCR loader |
| Fixed tiers | no per-question routing | several models → routing middleware |
| Word-match pre-activation | "what"/"how" pre-read the answering skill even for small talk; phrasings without a trigger cost one extra model call | measured misses → tune triggers |
| Hand-written frontend API types | drift if schemas change | API grows → codegen |
| Stateless turns | no follow-up questions | history (checkpointer) |
| Read skill text stays in the turn | resent on every model call of the turn | long tool loops → evict old skill text |
| Model may skip retrieval on familiar topics | "Tell me about chain of thought prompting" reads the skill but answers "no information" without searching, although `cot prompting.pdf` is ready | still failing → force a first `retrieve_documents` call (`tool_choice`) when the library has documents |
