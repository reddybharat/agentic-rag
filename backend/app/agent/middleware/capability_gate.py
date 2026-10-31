from collections.abc import Awaitable, Callable
from typing import Any, cast

from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse
from langchain.tools import ToolRuntime
from langchain_core.messages import SystemMessage, ToolMessage
from langchain_core.tools import BaseTool, tool
from langgraph.runtime import Runtime
from langgraph.types import Command

from app.agent.capabilities.registry import CapabilityRegistry
from app.agent.state import AgentContext, CapabilityState

LOAD_CAPABILITY = "load_capability"


class CapabilityGate(AgentMiddleware[CapabilityState, AgentContext, Any]):
    """Progressive disclosure: every tool is registered up front, but each model call sees only
    `load_capability` plus the tools of active capabilities, and its system prompt carries the
    active capabilities' instructions and a catalog of the inactive ones."""

    state_schema = CapabilityState

    def __init__(self, registry: CapabilityRegistry) -> None:
        super().__init__()
        self._registry = registry
        self.tools = [
            self._load_capability_tool(),
            *(t for c in registry.capabilities for t in c.tools),
        ]

    def _load_capability_tool(self) -> BaseTool:
        registry = self._registry

        @tool(LOAD_CAPABILITY)
        def load_capability(
            name: str, runtime: ToolRuntime[AgentContext, CapabilityState]
        ) -> Command[Any] | str:
            """Activate a capability from the catalog so its tools become available."""
            if name in runtime.state.get("active_capabilities", []):
                return f"Capability {name!r} is already active; use its tools."
            capability = registry.get(name)
            if capability is None:
                known = ", ".join(c.name for c in registry.capabilities)
                return f"Unknown capability {name!r}. Available: {known}."
            tool_names = ", ".join(t.name for t in capability.tools)
            message = f"Capability {name!r} is active. Tools now available: {tool_names}."
            return Command(
                update={
                    "active_capabilities": [name],
                    "messages": [ToolMessage(message, tool_call_id=runtime.tool_call_id)],
                }
            )

        return load_capability

    async def abefore_agent(
        self, state: CapabilityState, runtime: Runtime[AgentContext]
    ) -> dict[str, Any] | None:
        active = [
            c.name
            for c in self._registry.capabilities
            if c.auto_activate_when is not None
            and await c.auto_activate_when(runtime.context.session_id)
        ]
        return {"active_capabilities": active} if active else None

    async def awrap_model_call(
        self,
        request: ModelRequest[AgentContext],
        handler: Callable[[ModelRequest[AgentContext]], Awaitable[ModelResponse[Any]]],
    ) -> ModelResponse[Any]:
        active_names = cast(CapabilityState, request.state).get("active_capabilities", [])
        capabilities = self._registry.capabilities
        active = [c for c in capabilities if c.name in active_names]
        inactive = [c for c in capabilities if c.name not in active_names]

        visible = {t.name for c in active for t in c.tools}
        sections = [request.system_prompt or ""]
        sections += [f"## Capability: {c.name}\n{c.instructions}" for c in active]
        if inactive:
            visible.add(LOAD_CAPABILITY)
            catalog = "\n".join(f"- {c.name}: {c.description}" for c in inactive)
            sections.append(
                f"## More capabilities\nCall `{LOAD_CAPABILITY}` with a name to use one:\n{catalog}"
            )
        return await handler(
            request.override(
                system_message=SystemMessage("\n\n".join(s for s in sections if s)),
                tools=[t for t in request.tools if isinstance(t, BaseTool) and t.name in visible],
            )
        )
