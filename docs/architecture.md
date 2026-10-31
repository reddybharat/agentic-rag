# Architecture

> **Status:** v2, built phase by phase. Detailed walkthrough of every mechanism (embeddings, chunking, model selection, agent loop): [internals.md](internals.md). P0 (skeleton), P1 (model catalog, `ModelFactory`, Ollama chat + embedder, `GET /models`) P2 (sessions CRUD, stateless SSE chat, auto-title, `turn_usage`) and P3 (capability framework, `documents`, ingestion) are built; P4 and P5 are in progress. The `web` capability (Tavily) is a later enhancement. Update this file whenever a phase changes the architecture.

## TL;DR

- **What:** chat with your PDFs. One agent, running locally on Ollama (`qwen3:4b-instruct`), retrieves from Postgres + pgvector. Web search (Tavily) is a later enhancement.
- **Core idea: progressive disclosure.** The agent only sees a short *catalog* of capabilities. It calls `load_capability(name)` to unlock a capability's instructions and tools. `documents` switches on automatically once a session has a ready PDF.
- **Layers:** `api → services → domain ← infra`, with `agent` depending only on domain ports. `container.py` is the only module that wires concrete classes.
- **Stateless turns:** each question is answered on its own. No history is sent back to the model (follow-ups are a later enhancement).
- **Sessions = document workspaces.** Uploaded PDFs are scoped to the session they were uploaded in.

---

## System overview

```mermaid
flowchart LR
    user([User])

    subgraph Host["Local machine (Windows, native processes)"]
        ui["UI<br/>React + Vite dev server"]
        api["API<br/>FastAPI · uvicorn"]
        db[("PostgreSQL 18<br/>+ pgvector")]
        ollama["Ollama<br/>qwen3:4b-instruct · qwen3-embedding:0.6b"]
    end

    tavily["Tavily<br/>web search (later)"]

    user --> ui
    ui -- "REST + SSE" --> api
    api -- "sessions, documents,<br/>chunks, usage" --> db
    api -- "localhost:11434" --> ollama
    api -. "HTTPS (later)" .-> tavily
```

Everything runs natively; there is no Docker locally. Ollama uses the GPU directly, and Postgres runs as a Windows service with pgvector built from source. CI uses a `pgvector/pgvector:pg18` container instead.

---

## Layers

```mermaid
flowchart TB
    api["<b>api/</b><br/>routes · schemas · deps<br/><i>HTTP only</i>"]
    services["<b>services/</b><br/>ChatService · SessionService · DocumentService<br/><i>use cases</i>"]
    agent["<b>agent/</b><br/>build_agent · middleware · CapabilityRegistry<br/><i>agent loop</i>"]
    domain["<b>domain/</b><br/>models · ports (Protocols)<br/><i>no I/O</i>"]
    infra["<b>infra/</b><br/>db · llm · embeddings · rag · search<br/><i>adapters, I/O only</i>"]
    container{{"<b>container.py</b><br/>composition root"}}

    api --> services
    services --> domain
    services --> agent
    agent --> domain
    infra -. implements .-> domain
    container -. wires .-> api
    container -. wires .-> services
    container -. wires .-> agent
    container -. wires .-> infra
```

| Layer | Owns | Must not |
|---|---|---|
| `api/` | Request parsing, response/SSE shaping, status codes | Contain business rules or touch the DB directly |
| `services/` | Use cases: chat turn, session CRUD, ingestion | Import concrete adapters |
| `agent/` | Agent assembly, middleware, capabilities | Import concrete adapters |
| `domain/` | Entities, value objects, ports | Do I/O |
| `infra/` | Postgres, pgvector, Ollama, Tavily, PDF parsing | Make decisions beyond translating I/O |

### Ports and their adapters

| Port (`domain/ports.py`) | Adapter (`infra/`) |
|---|---|
| `ChatModelProvider` | `llm/ollama.py` via `ModelFactory` |
| `Embedder` | `embeddings/ollama.py` |
| `VectorStore` | `rag/pgvector_store.py` |
| `SessionRepository`, `DocumentRepository`, `UsageRepository` | `db/repositories/*` |
| `UnitOfWork` | `db/unit_of_work.py` |
| `CapabilityProvider` | `agent/capabilities/builtin/*` (later: skill files, memory, MCP) |

Ports use `langchain_core` types (`BaseChatModel`, `BaseTool`, `Document`) directly instead of rewrapping them.

---

## A chat turn

```mermaid
sequenceDiagram
    autonumber
    participant UI
    participant API as api/chat
    participant Chat as ChatService
    participant Agent as Agent + middleware
    participant LLM as Ollama qwen3:4b-instruct
    participant Tools as search_docs

    UI->>API: POST /sessions/{id}/messages
    API->>Chat: send(session_id, text)
    Chat->>Chat: load session (owner filter)
    Chat->>Agent: astream([user], context=session_id)
    Agent->>Agent: capability_gate → auto-activate documents,<br/>add catalog, filter tools
    loop until final answer or tool-call limit
        Agent->>LLM: messages + visible tools
        LLM-->>Agent: tool call / tokens
        Agent->>Tools: run tool
        Tools-->>Agent: result
        Agent-->>API: tool_start / tool_end
    end
    Agent-->>API: token … token
    API-->>UI: SSE stream
    Chat->>Chat: persist turn_usage
    API-->>UI: done
```

### Example SSE stream

```text
event: tool_start
data: {"id": "call_1", "name": "search_docs", "args": {"query": "phase two budget"}}

event: tool_end
data: {"id": "call_1", "name": "search_docs", "ok": true}

event: token
data: {"text": "The phase two budget is 4.2 million euros "}

event: token
data: {"text": "(sample.pdf, p. 3)."}

event: done
data: {"input_tokens": 1830, "output_tokens": 41, "latency_ms": 2910}
```

Qwen's thinking tokens are filtered out before `token` events go out.

---

## Capabilities and progressive disclosure

A **capability** is a bundle of `{name, description, instructions, tools, auto_activate_when}` (`requires_approval` arrives with HITL). All tools are registered once when the agent is built; `capability_gate` decides what the model actually sees on each call.

```mermaid
stateDiagram-v2
    [*] --> Catalog: registered
    Catalog --> Active: load_capability(name)
    Catalog --> Active: auto_activate_when holds<br/>(e.g. session has a ready PDF)
    Active --> Active: load_capability(name)<br/>returns "already active"
    Active --> [*]: turn ends (stateless)
```

| State | Model sees |
|---|---|
| Catalog | One line: name + description |
| Active | Full instructions + the capability's tools |

### Built-in capabilities

| Capability | Tools | Activation |
|---|---|---|
| `documents` | `search_docs` → snippets + page + chunk id + surrounding context from the same page | Automatic once the session has a `ready` document |
| `web` (later enhancement) | `tavily_search`, `fetch_page` | On demand via `load_capability("web")` |

### Example: what the model sees

Session **without** a ready PDF: the system prompt ends with a catalog, and the only tool is `load_capability`.

```text
<system.md>

## More capabilities
Call `load_capability` with a name to use one:
- documents: Search the PDFs uploaded to this session and answer with page citations.
```

Session **with** a ready PDF: `documents` is auto-activated, so the prompt carries its instructions (`prompts/documents.md`) instead, the only tool is `search_docs`, and `load_capability` disappears because nothing is left to load.

```text
<system.md>

## Capability: documents
<documents.md>
```

### Adding a capability

Write a new `CapabilityProvider`, register it in `container.py`, and that's it; no existing code changes. Later sources (skill files, memory, MCP servers) plug in the same way.

---

## Document ingestion

```mermaid
flowchart LR
    up["POST /sessions/{id}/documents"] --> val{"validate<br/>PDF · size · sha256"}
    val -- "duplicate in session" --> dup["409"]
    val -- "not a PDF" --> bad["422"]
    val -- "too large" --> big["413"]
    val -- ok --> pend["documents row<br/>status = pending"]
    pend --> bg["background task"]
    bg --> load["pypdf loader"] --> chunk["chunker"] --> emb["qwen3-embedding<br/>1024-d"] --> store[("chunks<br/>pgvector + HNSW")]
    store --> ready["status = ready"]
    bg -. error .-> failed["status = failed + error"]
```

Chunks are embedded without a prefix; queries are embedded with an instruction prefix (`Instruct: …\nQuery: …`). The embedding model name is stored on every document, and `/ready` fails if it doesn't match the configured `EMBEDDING_MODEL`.

> `shortcut:` ingestion uses FastAPI `BackgroundTasks`, so in-flight jobs are lost on restart. Upgrade to a job queue if ingestion must survive restarts.

---

## Data model

```mermaid
erDiagram
    sessions ||--o{ documents : contains
    sessions ||--o{ chunks : scopes
    sessions ||--o{ turn_usage : records
    documents ||--o{ chunks : "split into"

    sessions {
        uuid id PK
        text owner_id
        text title
        timestamptz created_at
        timestamptz updated_at
    }
    documents {
        uuid id PK
        uuid session_id FK
        text filename
        text sha256
        int page_count
        text embedding_model
        text status "pending|ready|failed"
        text error
        timestamptz created_at
    }
    chunks {
        uuid id PK
        uuid document_id FK
        uuid session_id FK
        int page
        int ordinal
        text content
        vector embedding "1024, HNSW"
    }
    turn_usage {
        uuid id PK
        uuid session_id FK
        text model_id
        int input_tokens
        int output_tokens
        int latency_ms
        timestamptz created_at
    }
```

`chunks.session_id` is denormalised so every vector search filters by session without a join. Every repository query filters by `owner_id` (currently `DEFAULT_OWNER_ID`).

---

## Configuration

Everything comes from `Settings` (env vars, see `.env.example`) plus `config/models.yaml`.

```yaml
# config/models.yaml
models:
  - id: qwen3-4b-fast
    provider: ollama
    model_name: qwen3:4b-instruct
    tier: fast            # titles, classification
    supports_tools: true
    options: { reasoning: false, num_predict: 256 }
  - id: qwen3-4b-smart
    provider: ollama
    model_name: qwen3:4b-instruct
    tier: smart           # answers
    supports_tools: true
    options: { reasoning: false, num_ctx: 8192 }
```

```dotenv
DATABASE_URL=postgresql+asyncpg://app:app@localhost:5432/agentic_rag
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_MODEL=qwen3-embedding:0.6b
EMBEDDING_DIM=1024
LLM_TIMEOUT_S=120.0
MAX_UPLOAD_BYTES=20971520
DEFAULT_OWNER_ID=local
```

Both tiers use the same model so Ollama never swaps models within 6 GB of VRAM. Pointing `fast` at a smaller model later is a one-line YAML change.

---

## Design patterns in use

| Pattern | Where |
|---|---|
| Factory + Registry | `ModelFactory` |
| Strategy | Page loader and chunker injected into `DocumentService` as functions |
| Adapter | Ollama / pgvector behind domain ports |
| Composite | `CapabilityRegistry` over many `CapabilityProvider`s |
| Repository + Unit of Work | `infra/db` |
| Chain of Responsibility | Middleware: `CapabilityGate → ToolCallLimitMiddleware` |
| Dependency Injection | `container.py` |

---

## Not yet in the architecture

These are planned enhancements. Each plugs into an existing extension point:

| Enhancement | Extension point |
|---|---|
| Follow-ups + history | Postgres checkpointer + summarization middleware in `build_agent` |
| MCP servers + approvals | New `CapabilityProvider` + human-in-the-loop middleware (needs the checkpointer) |
| Long-term memory | New `CapabilityProvider` + `memories` table |
| Skill files (`SKILL.md`) | New `CapabilityProvider` (phase P5) |
| Agent profiles, auto routing | Profile config + routing middleware choosing a tier per call (today the tier is fixed: smart answers, fast titles) |
| Other chat providers (Gemini, …) | New provider registered in `ModelFactory` |
| Web search (Tavily) | New builtin `web` capability provider |
| Tracing + evals | Langfuse callback handler; evals datasets |
| Real auth | Replace `DEFAULT_OWNER_ID` with a resolved user in `api/deps.py` |
