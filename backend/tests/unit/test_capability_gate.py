import uuid

import pytest
from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langgraph.runtime import Runtime

from app.agent.capabilities.registry import CapabilityRegistry
from app.agent.middleware.capability_gate import LOAD_CAPABILITY, CapabilityGate
from app.agent.state import AgentContext, CapabilityState
from app.domain.models import Capability


@tool
def lookup(query: str) -> str:
    """Look something up."""
    return query


class _Provider:
    def __init__(self, *capabilities: Capability) -> None:
        self._capabilities = list(capabilities)

    def discover(self) -> list[Capability]:
        return self._capabilities


DOCS = Capability("docs", "Search PDFs.", "Cite pages.", [lookup])


async def _visible(gate: CapabilityGate, active: list[str]) -> ModelRequest[AgentContext]:
    """Run the gate and return the request the model would have received."""
    seen: list[ModelRequest[AgentContext]] = []

    async def handler(request: ModelRequest[AgentContext]) -> ModelResponse[None]:
        seen.append(request)
        return ModelResponse(result=[AIMessage("ok")])

    request: ModelRequest[AgentContext] = ModelRequest(
        # The model is never called: the handler stands in for it.
        model=GenericFakeChatModel(messages=iter([])),
        messages=[],
        system_prompt="Base.",
        tools=list(gate.tools),
        state=CapabilityState(messages=[], active_capabilities=active),
    )
    await gate.awrap_model_call(request, handler)
    return seen[0]


async def test_inactive_capability_shows_only_catalog_and_loader() -> None:
    request = await _visible(CapabilityGate(CapabilityRegistry([_Provider(DOCS)])), active=[])

    assert [t.name for t in request.tools] == [LOAD_CAPABILITY]  # type: ignore[union-attr]
    assert "- docs: Search PDFs." in (request.system_prompt or "")
    assert "Cite pages." not in (request.system_prompt or "")


async def test_active_capability_shows_its_tools_and_instructions() -> None:
    request = await _visible(CapabilityGate(CapabilityRegistry([_Provider(DOCS)])), ["docs"])

    assert [t.name for t in request.tools] == ["lookup"]  # type: ignore[union-attr]
    assert "Cite pages." in (request.system_prompt or "")
    assert LOAD_CAPABILITY not in (request.system_prompt or "")


def test_registry_rejects_duplicate_names() -> None:
    with pytest.raises(ValueError, match="Duplicate capability 'docs'"):
        CapabilityRegistry([_Provider(DOCS), _Provider(DOCS)])


async def test_auto_activation_runs_rules_with_session_id() -> None:
    seen: list[uuid.UUID] = []

    async def has_docs(session_id: uuid.UUID) -> bool:
        seen.append(session_id)
        return True

    auto = Capability("docs", "d", "i", [lookup], auto_activate_when=has_docs)
    gate = CapabilityGate(CapabilityRegistry([_Provider(auto)]))
    session_id = uuid.uuid4()

    update = await gate.abefore_agent(
        {"messages": []}, Runtime(context=AgentContext(session_id=session_id))
    )

    assert update == {"active_capabilities": ["docs"]}
    assert seen == [session_id]
