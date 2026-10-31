# Internals

How the backend actually works, mechanism by mechanism, with the real numbers. [architecture.md](architecture.md) has the big picture; this file has the details. When a constant, prompt or flow changes in code, update it here too.

Paths are relative to `backend/`.

---

## 1. Startup: who builds what

`uvicorn app.main:create_app --factory` calls `create_app()`:

1. `Settings()` reads env vars / `backend/.env`.
2. `configure_logging()` sets up structlog (console or JSON). The `bind_request_id` middleware binds `request_id` to every log line of a request and echoes it in the `X-Request-ID` header.
3. The **lifespan** runs `Container.build(settings)` once ([app/container.py](../backend/app/container.py)). This is the only place concrete classes are created, in this order:

```text
engine (SQLAlchemy async, asyncpg, pool_pre_ping)
 └─ uow = SqlUnitOfWork factory           one DB transaction per `async with uow()`
ModelFactory.from_yaml(config/models.yaml, {"ollama": OllamaChatProvider})
SessionService(uow, owner, fast model, prompts/title.md)
OllamaEmbedder(qwen3-embedding:0.6b, dim 1024)
DocumentService(uow, owner, embedder, load_pdf_pages, split_words, MAX_UPLOAD_BYTES)
CapabilityRegistry([DocumentsCapabilityProvider(prompts/documents.md,
                                                documents.search, documents.has_ready)])
agent = build_agent(smart model, prompts/system.md, registry)
ChatService(uow, agent, "qwen3-4b-smart", sessions)
```

Routes get services through `app/api/deps.py` (`request.app.state.container`). Services never import infra classes; they receive them.

---

## 2. Configuration

All settings live in `app/core/config.py` (`Settings`, pydantic-settings, case-insensitive env vars):

| Setting | Default | Used for |
|---|---|---|
| `DATABASE_URL` | required | app DB (`postgresql+asyncpg://…`) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | chat + embeddings |
| `LOG_LEVEL` / `LOG_JSON` | `INFO` / `true` | logging (`.env.example` sets `LOG_JSON=false` for dev) |
| `DEFAULT_OWNER_ID` | `local` | owner of every session and document until auth exists |
| `READINESS_TIMEOUT_S` | `2.0` | per-check timeout in `/ready` |
| `MODELS_CONFIG_PATH` | `config/models.yaml` | chat model catalog |
| `LLM_TIMEOUT_S` | `120.0` | HTTP timeout for Ollama chat and embedding calls |
| `EMBEDDING_MODEL` | `qwen3-embedding:0.6b` | embedder; stored on each document |
| `EMBEDDING_DIM` | `1024` | requested vector size; **must equal** the `vector(1024)` column from migration 0003 |
| `MAX_UPLOAD_BYTES` | `20971520` (20 MiB) | upload size limit |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | browser origins allowed to call the API (JSON list) |

Tests read `TEST_DATABASE_URL` separately (`tests/conftest.py`).

---

## 3. Chat models and how one is selected

**Catalog:** `config/models.yaml` → list of `ModelSpec {id, provider, model_name, tier, supports_tools, options}`.

| id | model | tier | options | used by |
|---|---|---|---|---|
| `qwen3-4b-fast` | `qwen3:4b-instruct` | fast | `reasoning: false`, `num_predict: 256` | session auto-title |
| `qwen3-4b-smart` | `qwen3:4b-instruct` | smart | `reasoning: false`, `num_ctx: 8192` | the agent (all answers) |

**Selection is fixed at startup, not per request:** the container asks `ModelFactory.for_tier(Tier.SMART)` for the agent and `for_tier(Tier.FAST)` for titles. No router or classifier is involved, and there is no user-facing model choice yet.

**`ModelFactory`** (`app/infra/llm/model_factory.py`) validates the catalog when the app starts. Startup fails if:
- a tier has zero models or more than one,
- a spec names a provider that isn't registered.

It builds each model once and caches it.

**`OllamaChatProvider`** (`app/infra/llm/ollama.py`) turns a spec into a `ChatOllama`. It **rejects unknown option keys**, because `ChatOllama` silently ignores them and a typo like `num_ctxx` would otherwise vanish.

**Why these choices:**
- Both tiers use the same weights, so Ollama never swaps models within the laptop's 6 GB of VRAM. The chat model and the embedder together take about 3.2 GB.
- `qwen3:4b-instruct` is the non-thinking variant. Plain `qwen3:4b` is now thinking-only: it ignores `reasoning=false` and spends about 2.7k tokens on "say hi".
- `reasoning: false` is the ChatOllama field that turns thinking off. `num_ctx: 8192` leaves room for the system prompt, the capability instructions and 4 search passages.

---

## 4. Embeddings

`app/infra/embeddings/ollama.py` wraps `langchain_ollama.OllamaEmbeddings`.

| Aspect | Value |
|---|---|
| Model | `qwen3-embedding:0.6b` (via Ollama) |
| Dimension | 1024, passed as `dimensions=` (the model's native size; Qwen3-Embedding can also truncate to smaller sizes) |
| Chunk side | text embedded **as-is**, no prefix |
| Query side | `Instruct: Given a question, retrieve document passages that answer it\nQuery: <question>` |
| Batching | `DocumentService` sends chunks in batches of `EMBED_BATCH_SIZE = 32` |
| Distance | cosine (`vector_cosine_ops` HNSW index, `cosine_distance` in queries) |

Qwen3-Embedding is trained asymmetrically: queries carry an instruction and documents don't. Using the instruction on both sides, or on neither, lowers retrieval quality.

**Guarding against mixed vectors:** every document row stores `embedding_model`. Vectors from different models live in different spaces and can't be compared, so `/ready` returns 503 (`checks.embeddings = false`) if any `ready` document used a model other than `EMBEDDING_MODEL`.

**Changing the embedding model:**
1. Set `EMBEDDING_MODEL`.
2. If the dimension changes, set `EMBEDDING_DIM` and write a new migration that recreates `chunks.embedding` as `vector(<new dim>)` together with its HNSW index.
3. Re-ingest the documents (delete and re-upload). `/ready` stays red until no old-model documents remain.

---

## 5. Ingestion: from upload to searchable chunks

```text
POST /documents (multipart "file", one file per request)
  route: file.read()
  DocumentService.upload
    1. len(data) > MAX_UPLOAD_BYTES       → 413 payload_too_large
    2. not data.startswith(b"%PDF-")      → 422 invalid_document
    3. sha256 already in the library      → 409 conflict  (also a DB unique constraint on (owner_id, sha256))
    4. insert documents row, status = pending, embedding_model = current
  response 202 {id, filename, status: "pending", ...}
  background task: DocumentService.ingest(document_id, data)
    a. pypdf: text of each page          (runs in a thread: CPU-bound)
    b. chunk each page separately        (split_words)
    c. no chunks at all                  → failed: "No extractable text: the PDF may be scanned images."
    d. embed chunks, 32 per call
    e. one transaction: insert chunks + status = ready + page_count
    any exception                        → logged with traceback, status = failed,
                                           error = "Could not read this PDF." (or the message from c)
```

Poll `GET /documents` to see `pending → ready | failed`. `DELETE /documents/{id}` removes a document and, through `ON DELETE CASCADE`, its chunks (404 for an unknown id or another owner's). Deleting a document while it is still ingesting makes the background task fail on `mark_ready` and log `ingestion_failed`; nothing is left behind.

The frontend uploads several files as several parallel requests, so each file gets its own status and error.

### Page loading (`app/infra/rag/pdf_loader.py`)
`pypdf.PdfReader(...).pages[i].extract_text()`. Layout, tables and images are flattened or lost. Image-only (scanned) pages return empty text; there is no OCR.

### Chunking strategy (`app/infra/rag/chunkers.py`, `split_words`)
- **Per page.** Chunks never cross page boundaries, so every chunk has exactly one page number. That is what makes citations precise.
- **Word packing.** Whitespace-split words are packed into a chunk until adding the next word would exceed `CHUNK_CHARS = 1000` characters. A single word longer than that becomes its own chunk.
- **Overlap.** The next chunk starts `OVERLAP_WORDS = 30` words before the previous one ended, so a sentence cut at a boundary appears whole in at least one chunk.
- **Whitespace is normalised.** Newlines and runs of spaces become single spaces.
- **Ordinal.** `chunks.ordinal` numbers chunks across the whole document (0, 1, 2…, continuing across pages). It's used to fetch neighbours.

A dense page of about 3,000 characters becomes roughly 4 chunks. The 4 sample pages are about 300 characters each, so 1 chunk per page.

### Storage (migrations `0003`, `0004`)
- `documents`: one row per library PDF, with a unique constraint on `(owner_id, sha256)`.
- `chunks`: `page, ordinal, content, embedding vector(1024)`, plus `owner_id` copied from the document so search filters without a join. Indexes cover `document_id`, `owner_id` and an HNSW cosine index on `embedding`.
- Deleting a document cascades to its chunks. Documents are independent of sessions.

---

## 6. Retrieval: what `search_docs` does

`search_docs(query)` (`app/agent/capabilities/builtin/documents.py`):

1. `owner_id` comes from the run's `AgentContext`, **not from the model**, so the model can't search another owner's library.
2. `embed_query(query)` (with the instruction prefix, see §4).
3. `SqlDocumentRepository.search`:
   - `SET LOCAL hnsw.iterative_scan = strict_order`. HNSW finds nearest neighbours first and filters afterwards. Without iterative scan, an owner filter applied to the default 40 candidates could return fewer than `limit` rows when many owners exist.
   - Top `SEARCH_LIMIT = 4` chunks of this owner's library by cosine distance.
   - For each hit, fetch chunks `ordinal ± 1` **on the same page** as context. Context from another page used to be shown under the hit's page header, and the model then cited the wrong page.
4. Format, with each context side cut to `CONTEXT_CHARS = 300`:

```text
[sample.pdf, page 3] (chunk 1b6e…)
The total budget for phase two is 4.2 million euros, …
Context before: …<last 300 chars of the previous chunk on this page>
Context after: <first 300 chars of the next chunk on this page>…
```

No hits → `No matching passages in the document library.` Only chunks of `ready` documents exist, because chunks are written in the same transaction that marks the document ready.

---

## 7. The agent

Built once by `build_agent` (`app/agent/agent_builder.py`) with LangChain's `create_agent`. The result is a LangGraph loop: model → (tools → model)* → end.

```text
create_agent(smart model, system_prompt=system.md,
             middleware=[CapabilityGate(registry), ToolCallLimitMiddleware(run_limit=8)],
             context_schema=AgentContext)
```

- **State** (`app/agent/state.py`): `messages` plus `active_capabilities: list[str]`, whose reducer merges names without duplicates. The state lives for **one run only**: there is no checkpointer, so every turn starts empty.
- **Context:** `AgentContext(owner_id)` is passed per run by `ChatService` and is readable by middleware and tools.

### Capabilities (progressive disclosure)
A `Capability` (`app/domain/models.py`) is `{name, description, instructions, tools, auto_activate_when}`. Providers return them from `discover()`. `CapabilityRegistry` collects all of them at startup and rejects duplicate names.

`CapabilityGate` (`app/agent/middleware/capability_gate.py`) does four things:

1. **Registers every tool at build time** (`self.tools`): `load_capability` plus all capability tools. `create_agent` can't add tools mid-run, so visibility is filtered instead.
2. **`abefore_agent`, once per turn:** runs each capability's `auto_activate_when(owner_id)`. For `documents` that is "does this owner have a `ready` document?" (one `EXISTS` query). It costs no model call.
3. **`awrap_model_call`, before every model call:**
   - tools the model sees = tools of the active capabilities, plus `load_capability` if any capability is still inactive;
   - system prompt = `system.md` + `## Capability: <name>\n<instructions>` for each active one + a `## More capabilities` catalog (name: description) for the inactive ones.
4. **`load_capability(name)` tool:** unknown name → error text listing the valid names; already active → "already active; use its tools" (loop guard); otherwise it returns a `Command` that adds the name to `active_capabilities`, so the **next** model call sees the tools.

`ToolCallLimitMiddleware(run_limit=8, exit_behavior="continue")`: after 8 tool calls in a turn, further calls get an error result instead of running, so the model has to answer.

### Prompts (`app/agent/prompts/`)
| File | Role |
|---|---|
| `system.md` | base system prompt for every turn |
| `documents.md` | `documents` instructions: always search first, answer only from the passages, cite `(filename, p. N)` |
| `title.md` | auto-title instruction for the fast model |

`documents.md` tells the model to search **even when the topic seems unfamiliar**. Without that line, `qwen3:4b-instruct` answered "I don't have information about Project Halcyon" without searching.

---

## 8. One chat turn, end to end

`POST /sessions/{id}/messages {"text": "..."}` (1–8000 characters after trimming, otherwise 422).

1. The `get_session` dependency loads the session with the owner filter. An unknown session gives 404 **before** the stream starts.
2. `ChatService.stream` calls `agent.astream({"messages": [HumanMessage(text)]}, stream_mode=["messages", "updates"], context=AgentContext(session.owner_id))`.
   - `messages` mode → `AIMessageChunk`s → a `token` event for each non-empty `.text` (thinking content never appears in `.text`). `usage_metadata` is summed across all model calls in the turn.
   - `updates` mode → per-node results: an `AIMessage` with `tool_calls` gives `tool_start` per call, and a `ToolMessage` gives `tool_end` (`ok = status != "error"`).
3. Any exception during the stream → logged with traceback → one `error` event (`chat_failed`). No usage is saved.
4. On success: insert a `turn_usage` row → `SessionService.auto_title` (only while the title is still `New chat`; uses the fast model; a failure is logged as a warning and never fails the turn) → `done`.

### SSE events
| event | data |
|---|---|
| `tool_start` | `{id, name, args}` |
| `tool_end` | `{id, name, ok}` |
| `token` | `{text}` |
| `done` | `{input_tokens, output_tokens, latency_ms}` |
| `error` | `{code, message}` |

Order: (`tool_start`/`tool_end` and `token` interleaved)* then exactly one `done` or `error`.

The frontend (`frontend/src/lib/api.ts`) reads this with `fetch` + `TextDecoderStream`, splitting frames on a blank line and turning `event:`/`data:` into `{type, ...data}`. Its API types are hand-written mirrors of the backend schemas.

---

## 9. Persistence rules

- **Unit of work** (`app/infra/db/unit_of_work.py`): each `async with uow()` is one session and transaction. Nothing persists unless `commit()` is called; leaving the block without a commit rolls back.
- **Owner scoping:** every `SessionRepository` method filters by `owner_id`, so another owner's session behaves as missing (404). Document and chunk queries filter by `owner_id` as well (`DocumentService` uses the configured owner; the agent gets it from `AgentContext`).
- **Migrations:** one per phase in `migrations/versions/` (`0001` sessions + `vector` extension, `0002` turn_usage, `0003` documents + chunks, `0004` documents/chunks scoped to the owner). `env.py` is async and reads `DATABASE_URL` unless `sqlalchemy.url` is set (tests set it to the test DB).

---

## 10. Errors

`AppError` subclasses (`app/core/errors.py`) become `{"error": {"code", "message"}}`:

| class | status | code |
|---|---|---|
| `AppError` | 400 | `bad_request` |
| `NotFoundError` | 404 | `not_found` |
| `ConflictError` | 409 | `conflict` |
| `PayloadTooLargeError` | 413 | `payload_too_large` |
| `InvalidDocumentError` | 422 | `invalid_document` |
| anything else | 500 | `internal_error` (logged with traceback) |

FastAPI's own validation errors stay 422 with FastAPI's default body.

---

## 11. Tests and the sample PDF

`uv run pytest -rs`. Tests hit **real** Postgres (`TEST_DATABASE_URL`, truncated before each test) and **real** Ollama. They skip with a reason when either is unavailable.

`tests/fixtures/sample.pdf` is a synthetic 4-page report about a fictional "Project Halcyon", generated with a small stdlib script (not committed) so the facts can't come from the model's training data:

| Page | Facts |
|---|---|
| 1 | Ostrava Water Cooperative, founded 2011, eleven coastal villages |
| 2 | Kessel Bay plant: 1,840 m³/day (1,120 during February storms), 3.1 kWh/m³ |
| 3 | Phase two budget 4.2 M€ (approved 14 March 2025), 2.6 M€ membrane train, 0.9 M€ solar array |
| 4 | Lead engineer Mirela Vantongeren, Quillfeather Membranes (Tallinn), Brannock Laboratory |

The chat-with-document test asserts that `search_docs` is called, the answer contains `4.2` and cites page 3. It depends on the model's output, so it can fail intermittently.

---

## 12. Known shortcuts

| Shortcut | Limit | Upgrade when |
|---|---|---|
| FastAPI `BackgroundTasks` for ingestion | in-flight jobs lost on restart; a `pending` row stays pending | ingestion must survive restarts → job queue |
| Size check after the body is received | multipart spools the whole upload first | exposed publicly → body limit at the proxy |
| pypdf text only | no OCR, tables flattened | scanned PDFs matter → OCR loader |
| Fixed tiers | no per-question routing | multiple models → routing middleware |
| Hand-written frontend API types | drift if schemas change (`openapi-typescript` needs TypeScript 5) | API grows → codegen |
| Stateless turns | no follow-up questions | history enhancement (checkpointer) |
