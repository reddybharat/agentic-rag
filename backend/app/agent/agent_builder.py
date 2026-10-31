from collections.abc import Mapping, Sequence
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain.agents.middleware.types import AgentMiddleware, InputAgentState, OutputAgentState
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.graph.state import CompiledStateGraph

from app.agent.middleware.progressive_disclosure import Condition, ProgressiveDisclosure
from app.agent.skill_loader import SkillCatalog
from app.agent.state import AgentContext
from app.agent.tools import make_read_skill_file

type Agent = CompiledStateGraph[Any, AgentContext, InputAgentState, OutputAgentState[Any]]

MAX_TOOL_CALLS_PER_TURN = 8


def build_agent(
    model: BaseChatModel,
    system_prompt: str,
    catalog: SkillCatalog,
    tools: Sequence[BaseTool],
    conditions: Mapping[str, Condition],
) -> Agent:
    named = {t for s in catalog.skills.values() for t in s.allowed_tools}
    named |= {r.name for r in catalog.tool_rules}
    missing = named - {t.name for t in tools}
    if missing:
        raise ValueError(f"skills or preactivation.yaml name unknown tools: {sorted(missing)}")
    middleware: list[AgentMiddleware[Any, AgentContext, Any]] = [
        ProgressiveDisclosure(catalog, conditions),
        # Over the limit, further tool calls get an error result and the model has to answer.
        ToolCallLimitMiddleware(run_limit=MAX_TOOL_CALLS_PER_TURN, exit_behavior="continue"),
    ]
    return create_agent(
        model,
        tools=[make_read_skill_file(catalog), *tools],
        system_prompt=catalog.system_prompt(system_prompt),
        middleware=middleware,
        context_schema=AgentContext,
    )
