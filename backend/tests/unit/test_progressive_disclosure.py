import uuid
from typing import Any

import pytest
from langchain.agents.middleware.types import ModelRequest, ModelResponse, ToolCallRequest
from langchain.tools import ToolRuntime
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, ToolMessage
from langgraph.runtime import Runtime
from langgraph.types import Command

from app.agent.middleware.progressive_disclosure import Condition, ProgressiveDisclosure
from app.agent.skill_loader import load_skills
from app.agent.state import AgentContext
from app.agent.tools import (
    CITATION_RULES,
    NO_HITS,
    READ_SKILL_FILE,
    RETRIEVE_DOCUMENTS,
    make_read_skill_file,
    make_retrieve_documents,
)
from app.container import LIBRARY_HAS_DOCUMENTS
from app.domain.models import ChunkHit

CATALOG = load_skills()
ANSWERING = CATALOG.skills["answering-document-questions"]
RUNTIME = Runtime(context=AgentContext(owner_id="alice"))
BOTH = [READ_SKILL_FILE, RETRIEVE_DOCUMENTS]


async def _no_hits(owner_id: str, query: str, limit: int) -> list[ChunkHit]:
    return []


TOOLS = [make_read_skill_file(CATALOG), make_retrieve_documents(_no_hits)]


def _middleware(library_has_documents: bool = False) -> ProgressiveDisclosure:
    async def check(owner_id: str) -> bool:
        return library_has_documents

    conditions: dict[str, Condition] = {LIBRARY_HAS_DOCUMENTS: check}
    return ProgressiveDisclosure(CATALOG, conditions)


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
    await _middleware().awrap_model_call(request, handler)
    return [t.name for t in seen[0].tools]  # type: ignore[union-attr]


async def test_tool_is_hidden_until_a_skill_listing_it_is_read() -> None:
    assert await _visible_tools({"messages": [HumanMessage("q")]}) == [READ_SKILL_FILE]
    assert await _visible_tools({"messages": [HumanMessage("q"), _read(ANSWERING.text)]}) == BOTH


async def test_unknown_file_text_unlocks_nothing() -> None:
    assert await _visible_tools({"messages": [_read("Unknown file 'x'.")]}) == [READ_SKILL_FILE]


async def test_condition_enables_tool_without_a_skill() -> None:
    with_docs = await _middleware(library_has_documents=True).abefore_agent(
        {"messages": [HumanMessage("hello")]}, RUNTIME
    )
    empty = await _middleware().abefore_agent({"messages": [HumanMessage("hello")]}, RUNTIME)

    assert with_docs == {"enabled_tools": [RETRIEVE_DOCUMENTS]}
    assert empty is None
    assert await _visible_tools({"messages": [HumanMessage("hello")], **with_docs}) == BOTH


async def test_trigger_word_preloads_skill_as_a_read_round() -> None:
    update = await _middleware().abefore_agent(
        {"messages": [HumanMessage("What is the budget?")]}, RUNTIME
    )

    assert update is not None
    call, result = update["messages"]
    assert call.tool_calls[0]["args"] == {"path": ANSWERING.path}
    assert result.content == ANSWERING.text
    assert await _visible_tools({"messages": [HumanMessage("q"), *update["messages"]]}) == BOTH


async def test_locked_tool_call_is_refused_without_running() -> None:
    ran: list[str] = []

    async def handler(request: ToolCallRequest) -> ToolMessage | Command[Any]:
        ran.append(request.tool_call["name"])
        return ToolMessage("ran", tool_call_id="1")

    call = {"name": RETRIEVE_DOCUMENTS, "args": {"query": "q"}, "id": "1", "type": "tool_call"}
    result = await _middleware().awrap_tool_call(
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


def test_unknown_condition_is_rejected_at_build() -> None:
    with pytest.raises(ValueError, match="unknown conditions"):
        ProgressiveDisclosure(CATALOG, {})


async def test_retrieve_documents_sends_citation_rules_with_passages_only() -> None:
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
        context=RUNTIME.context,
        config={},
        stream_writer=lambda _: None,
        tool_call_id="1",
        store=None,
        tools=[],
    )
    args = {"query": "budget", "runtime": runtime}
    found = await make_retrieve_documents(one_hit).ainvoke(args)
    empty = await TOOLS[1].ainvoke(args)

    assert found.startswith("[report.pdf, page 3]")
    assert found.endswith(CITATION_RULES)
    assert empty == NO_HITS


async def test_read_skill_file_returns_the_file_or_lists_valid_paths() -> None:
    read_skill_file = TOOLS[0]

    assert await read_skill_file.ainvoke({"path": ANSWERING.path}) == ANSWERING.text
    assert "Available:" in await read_skill_file.ainvoke({"path": "nope.md"})
