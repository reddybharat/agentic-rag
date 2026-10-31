"""ProgressiveDisclosure: a tool is usable once a skill that lists it is read this turn."""

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

import structlog
from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
    ToolCallRequest,
)
from langchain_core.messages import ToolMessage
from langgraph.types import Command

from app.agent.skill_loader import SkillCatalog
from app.agent.state import AgentContext
from app.agent.tools import READ_SKILL_FILE

LOCKED_TEXT = "Tool '{name}' is locked. Read the skill that lists it first."

log = structlog.get_logger()


class ProgressiveDisclosure(AgentMiddleware[AgentState[Any], AgentContext, Any]):
    def __init__(self, catalog: SkillCatalog) -> None:
        super().__init__()
        self._catalog = catalog

    def _unlocked(self, state: Mapping[str, Any]) -> set[str]:
        """Tools of every skill whose file text was returned by `read_skill_file` this turn."""
        read = {
            m.content
            for m in state["messages"]
            if isinstance(m, ToolMessage)
            and m.name == READ_SKILL_FILE
            and isinstance(m.content, str)
        }
        return {t for s in self._catalog.skills.values() if s.text in read for t in s.allowed_tools}

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
