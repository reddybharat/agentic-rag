"""ProgressiveDisclosure: a tool is usable once a skill that lists it is read, or once a
pre-activation condition enabled it for this turn."""

from collections.abc import Awaitable, Callable, Mapping
from typing import Any, NotRequired

import structlog
from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
    ToolCallRequest,
)
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.runtime import Runtime
from langgraph.types import Command

from app.agent.skill_loader import SkillCatalog
from app.agent.state import AgentContext
from app.agent.tools import READ_SKILL_FILE

LOCKED_TEXT = "Tool '{name}' is locked. Read the skill that lists it first."
PREACTIVATE_CALL_ID = "preactivate_{i}"

type Condition = Callable[[str], Awaitable[bool]]  # owner_id -> holds?

log = structlog.get_logger()


class DisclosureState(AgentState[Any]):
    # Per run only: turns are stateless, so every turn starts with none enabled.
    enabled_tools: NotRequired[list[str]]


class ProgressiveDisclosure(AgentMiddleware[DisclosureState, AgentContext, Any]):
    state_schema = DisclosureState

    def __init__(self, catalog: SkillCatalog, conditions: Mapping[str, Condition]) -> None:
        super().__init__()
        unknown = {r.when for r in catalog.tool_rules} - conditions.keys()
        if unknown:
            raise ValueError(f"preactivation.yaml: unknown conditions {sorted(unknown)}")
        self._catalog = catalog
        self._conditions = conditions

    def _unlocked(self, state: Mapping[str, Any]) -> set[str]:
        """Tools enabled by a condition, plus those of every skill read this turn."""
        read = {
            m.content
            for m in state["messages"]
            if isinstance(m, ToolMessage)
            and m.name == READ_SKILL_FILE
            and isinstance(m.content, str)
        }
        from_skills = {
            t for s in self._catalog.skills.values() if s.text in read for t in s.allowed_tools
        }
        return from_skills | set(state.get("enabled_tools", []))

    async def abefore_agent(
        self, state: DisclosureState, runtime: Runtime[AgentContext]
    ) -> dict[str, Any] | None:
        update: dict[str, Any] = {}
        enabled = [
            r.name
            for r in self._catalog.tool_rules
            if await self._conditions[r.when](runtime.context.owner_id)
        ]
        for tool in enabled:
            log.info("tool_enabled", tool=tool)
        if enabled:
            update["enabled_tools"] = enabled

        query = next(
            (m.text for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), ""
        )
        skills = self._catalog.preactivate(query)
        if skills:
            # A ready-made `read_skill_file` round: LangChain sees a finished tool call, so the
            # model starts with these skills read, which saves one model call.
            ids = [PREACTIVATE_CALL_ID.format(i=i) for i in range(len(skills))]
            calls = [
                {"name": READ_SKILL_FILE, "args": {"path": s.path}, "id": i, "type": "tool_call"}
                for s, i in zip(skills, ids, strict=True)
            ]
            results = [
                ToolMessage(s.text, tool_call_id=i, name=READ_SKILL_FILE)
                for s, i in zip(skills, ids, strict=True)
            ]
            for s in skills:
                log.info("skill_read", path=s.path, status="ok", source="preactivate")
            update["messages"] = [AIMessage(content="", tool_calls=calls), *results]
        return update or None

    async def awrap_model_call(
        self,
        request: ModelRequest[AgentContext],
        handler: Callable[[ModelRequest[AgentContext]], Awaitable[ModelResponse[Any]]],
    ) -> ModelResponse[Any]:
        # Hide locked tools from the schema so the model is not tempted to call them.
        allowed = self._unlocked(request.state) | {READ_SKILL_FILE}
        tools = [t for t in request.tools if getattr(t, "name", None) in allowed]
        return await handler(request.override(tools=tools))

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        name = request.tool_call["name"]
        # The model can still name a hidden tool; refuse it here.
        if name != READ_SKILL_FILE and name not in self._unlocked(request.state):
            log.warning("tool_locked", tool=name)
            return ToolMessage(
                LOCKED_TEXT.format(name=name),
                tool_call_id=request.tool_call["id"],
                name=name,
                status="error",
            )
        return await handler(request)
