import uuid
from collections.abc import Awaitable, Callable

from langchain.tools import ToolRuntime
from langchain_core.tools import tool

from app.agent.state import AgentContext, CapabilityState
from app.domain.models import Capability, ChunkHit

NAME = "documents"
DESCRIPTION = "Search the PDFs uploaded to this session and answer with page citations."
SEARCH_LIMIT = 4
CONTEXT_CHARS = 300
NO_HITS = "No matching passages in this session's documents."


def _format(hit: ChunkHit) -> str:
    lines = [f"[{hit.filename}, page {hit.page}] (chunk {hit.chunk_id})", hit.content]
    if hit.context_before:
        lines.append(f"Context before: …{hit.context_before[-CONTEXT_CHARS:]}")
    if hit.context_after:
        lines.append(f"Context after: {hit.context_after[:CONTEXT_CHARS]}…")
    return "\n".join(lines)


class DocumentsCapabilityProvider:
    def __init__(
        self,
        instructions: str,
        search: Callable[[uuid.UUID, str, int], Awaitable[list[ChunkHit]]],
        has_ready: Callable[[uuid.UUID], Awaitable[bool]],
    ) -> None:
        self._instructions = instructions
        self._search = search
        self._has_ready = has_ready

    def discover(self) -> list[Capability]:
        search = self._search

        @tool
        async def search_docs(
            query: str, runtime: ToolRuntime[AgentContext, CapabilityState]
        ) -> str:
            """Search this session's documents. Returns passages with filename and page."""
            hits = await search(runtime.context.session_id, query, SEARCH_LIMIT)
            return "\n\n".join(_format(hit) for hit in hits) or NO_HITS

        return [
            Capability(
                name=NAME,
                description=DESCRIPTION,
                instructions=self._instructions,
                tools=[search_docs],
                auto_activate_when=self._has_ready,
            )
        ]
