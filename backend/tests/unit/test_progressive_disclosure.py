import uuid
from typing import Any

from langchain.agents.middleware.types import ModelRequest, ModelResponse, ToolCallRequest
from langchain.tools import ToolRuntime
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, ToolMessage
from langgraph.types import Command

from app.agent.middleware.progressive_disclosure import ProgressiveDisclosure
from app.agent.skill_loader import load_skills
from app.agent.state import AgentContext
from app.agent.tools import (
    NO_HITS,
    READ_SKILL_FILE,
    RETRIEVE_FROM_DOCUMENTS,
    make_read_skill_file,
    make_retrieve_from_documents,
)
from app.domain.models import ChunkHit

CATALOG = load_skills()
RETRIEVING = CATALOG.skills["retrieving-from-documents"]
CONTEXT = AgentContext(owner_id="alice")
BOTH = [READ_SKILL_FILE, RETRIEVE_FROM_DOCUMENTS]


async def _no_hits(owner_id: str, query: str, limit: int) -> list[ChunkHit]:
    return []


TOOLS = [make_read_skill_file(CATALOG), make_retrieve_from_documents(_no_hits)]


def _read(text: str) -> ToolMessage:
    return ToolMessage(text, tool_call_id="1", name=READ_SKILL_FILE)


async def _visible_tools(state: dict[str, Any]) -> list[str]:
    seen: list[ModelRequest[AgentContext]] = []

    async def handler(request: ModelRequest[AgentContext]) -> ModelResponse[None]:
        seen.append(request)
        return ModelResponse(result=[AIMessage("ok")])

    messages: list[AnyMessage] = state["messages"]
    request: ModelRequest[AgentContext] = ModelRequest(
        # The model is never called: the handler stands in for it.
        model=GenericFakeChatModel(messages=iter([])),
        messages=messages,
        tools=list(TOOLS),
        state=state,  # type: ignore[arg-type]
    )
    await ProgressiveDisclosure(CATALOG).awrap_model_call(request, handler)
    return [t.name for t in seen[0].tools]  # type: ignore[union-attr]


async def test_tool_is_hidden_until_a_skill_listing_it_is_read() -> None:
    assert await _visible_tools({"messages": [HumanMessage("q")]}) == [READ_SKILL_FILE]
    assert await _visible_tools({"messages": [HumanMessage("q"), _read(RETRIEVING.text)]}) == BOTH


async def test_unknown_file_text_unlocks_nothing() -> None:
    assert await _visible_tools({"messages": [_read("Unknown file 'x'.")]}) == [READ_SKILL_FILE]


async def test_locked_tool_call_is_refused_without_running() -> None:
    ran: list[str] = []

    async def handler(request: ToolCallRequest) -> ToolMessage | Command[Any]:
        ran.append(request.tool_call["name"])
        return ToolMessage("ran", tool_call_id="1")

    call = {"name": RETRIEVE_FROM_DOCUMENTS, "args": {"query": "q"}, "id": "1", "type": "tool_call"}
    result = await ProgressiveDisclosure(CATALOG).awrap_tool_call(
        ToolCallRequest(
            tool_call=call,  # type: ignore[arg-type]
            tool=TOOLS[1],
            state={"messages": [HumanMessage("q")]},
            runtime=None,  # type: ignore[arg-type]
        ),
        handler,
    )

    assert ran == []
    assert isinstance(result, ToolMessage)
    assert result.status == "error"
    assert "locked" in str(result.content)


async def test_citation_rules_live_in_the_skill_and_results_are_passages_only() -> None:
    hit = ChunkHit(
        chunk_id=uuid.uuid4(),
        filename="report.pdf",
        page=3,
        content="Budget 4.2 M.",
        context_before="",
        context_after="",
    )

    async def one_hit(owner_id: str, query: str, limit: int) -> list[ChunkHit]:
        return [hit]

    runtime: ToolRuntime[AgentContext] = ToolRuntime(
        state={"messages": []},
        context=CONTEXT,
        config={},
        stream_writer=lambda _: None,
        tool_call_id="1",
        store=None,
        tools=[],
    )
    args = {"query": "budget", "runtime": runtime}
    found = await make_retrieve_from_documents(one_hit).ainvoke(args)
    empty = await TOOLS[1].ainvoke(args)

    assert found == f"[report.pdf, page 3] (chunk {hit.chunk_id})\nBudget 4.2 M."
    assert empty == NO_HITS
    assert "Cite every fact as (filename, p. N)" in RETRIEVING.text


async def test_read_skill_file_returns_the_file_or_lists_valid_paths() -> None:
    read_skill_file = TOOLS[0]

    assert await read_skill_file.ainvoke({"path": RETRIEVING.path}) == RETRIEVING.text
    assert "Available:" in await read_skill_file.ainvoke({"path": "nope.md"})
