from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain.agents.middleware.types import AgentMiddleware, InputAgentState, OutputAgentState
from langchain_core.language_models import BaseChatModel
from langgraph.graph.state import CompiledStateGraph

from app.agent.capabilities.registry import CapabilityRegistry
from app.agent.middleware.capability_gate import CapabilityGate
from app.agent.state import AgentContext

type Agent = CompiledStateGraph[Any, AgentContext, InputAgentState, OutputAgentState[Any]]

MAX_TOOL_CALLS_PER_TURN = 8


def build_agent(model: BaseChatModel, system_prompt: str, registry: CapabilityRegistry) -> Agent:
    middleware: list[AgentMiddleware[Any, AgentContext, Any]] = [
        CapabilityGate(registry),
        # Over the limit, further tool calls get an error result and the model has to answer.
        ToolCallLimitMiddleware(run_limit=MAX_TOOL_CALLS_PER_TURN, exit_behavior="continue"),
    ]
    return create_agent(
        model, system_prompt=system_prompt, middleware=middleware, context_schema=AgentContext
    )
