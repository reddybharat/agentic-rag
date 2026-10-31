from langchain.agents import create_agent
from langchain.agents.middleware.types import AgentState, InputAgentState, OutputAgentState
from langchain_core.language_models import BaseChatModel
from langgraph.graph.state import CompiledStateGraph

type Agent = CompiledStateGraph[AgentState[None], None, InputAgentState, OutputAgentState[None]]


def build_agent(model: BaseChatModel, system_prompt: str) -> Agent:
    # shortcut: no tools or middleware until capabilities land (P3); grow into AgentBuilder then.
    return create_agent(model, tools=[], system_prompt=system_prompt)
