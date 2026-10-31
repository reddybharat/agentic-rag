"""Local tools. MCP tools will join these later; skills unlock either kind by name."""

from collections.abc import Awaitable, Callable

import structlog
from langchain.tools import ToolRuntime
from langchain_core.tools import BaseTool, tool

from app.agent.skill_loader import SkillCatalog
from app.agent.state import AgentContext
from app.domain.models import ChunkHit

READ_SKILL_FILE = "read_skill_file"
RETRIEVE_FROM_DOCUMENTS = "retrieve_from_documents"
RETRIEVE_LIMIT = 4
CONTEXT_CHARS = 300
NO_HITS = "No matching passages in the document library."

log = structlog.get_logger()


def make_read_skill_file(catalog: SkillCatalog) -> BaseTool:
    """The middleware unlocks a skill's tools once its exact file text is in the turn."""
    files = {s.path: s.text for s in catalog.skills.values()}

    @tool(READ_SKILL_FILE)
    def read_skill_file(path: str) -> str:
        """Read a skill listed under '## Skills', e.g. `retrieving-from-documents/SKILL.md`.
        Read it before using the tools it describes."""
        text = files.get(path.strip())
        if text is None:
            log.info("skill_read", path=path, status="unknown_path")
            return f"Unknown file {path!r}. Available: {sorted(files)}"
        log.info("skill_read", path=path, status="ok", source=READ_SKILL_FILE)
        return text

    return read_skill_file


def _format(hit: ChunkHit) -> str:
    lines = [f"[{hit.filename}, page {hit.page}] (chunk {hit.chunk_id})", hit.content]
    if hit.context_before:
        lines.append(f"Context before: …{hit.context_before[-CONTEXT_CHARS:]}")
    if hit.context_after:
        lines.append(f"Context after: {hit.context_after[:CONTEXT_CHARS]}…")
    return "\n".join(lines)


def make_retrieve_from_documents(
    search: Callable[[str, str, int], Awaitable[list[ChunkHit]]],
) -> BaseTool:
    @tool(RETRIEVE_FROM_DOCUMENTS)
    async def retrieve_from_documents(query: str, runtime: ToolRuntime[AgentContext]) -> str:
        """Similarity search over the user's document library: finds the stored passages closest
        in meaning to the query. Pass the question's key terms. Returns passages with filename
        and page."""
        hits = await search(runtime.context.owner_id, query, RETRIEVE_LIMIT)
        if not hits:
            return NO_HITS
        return "\n\n".join(_format(hit) for hit in hits)

    return retrieve_from_documents
