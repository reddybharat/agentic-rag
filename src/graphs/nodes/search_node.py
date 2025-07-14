from src.graphs.type import RAGAgentState
from src.tools.web_search_tool import tavily_search_tool
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from src.helpers.prompts import retriever_agent_system_prompt
from src.utils.retriever import Retriever
from langchain.agents import AgentExecutor, create_tool_calling_agent
import os
import json
from src.utils.logger import logger


def search_node(state: RAGAgentState) -> RAGAgentState:
    """
    A node that utilizes tools to get the appropriate answer to the user query
    """
    try:
        logger.log("[SearchNode] Running search_node")

        # No longer initializing or checking state['messages']

        tools = [tavily_search_tool]
        
        logger.log("[SearchNode] Initializing LLM")
        api_keys_str = os.getenv("GOOGLE_GENAI_API_KEYS", "")
        # Handle both JSON list and comma-separated string
        if api_keys_str.strip().startswith("["):
            try:
                gemini_api_keys = json.loads(api_keys_str)
            except Exception as e:
                raise ValueError(f"Failed to parse GOOGLE_GENAI_API_KEYS as JSON: {e}")
        else:
            gemini_api_keys = [k.strip() for k in api_keys_str.split(",") if k.strip()]
        if not gemini_api_keys:
            raise ValueError("Gemini API Key not provided. Please provide GEMINI_API_KEY as an environment variable")
        for key in gemini_api_keys:
            try:
                llm = ChatGoogleGenerativeAI(google_api_key=key, model="gemini-2.0-flash-lite")
                logger.log("[SearchNode] LLM created with provided API key")
                llm_with_tools = llm.bind_tools(tools)
                logger.log("[SearchNode] LLM bound with tools")

                # Restore use of state['messages'] if present, otherwise construct messages
                # if "messages" in state and state["messages"]:
                #     messages = state["messages"]

                state["messages"] = [
                    HumanMessage(content=f"Try to improve the answer to given query\n[Query]:{state['query']}\n[Answer]:{state['answer']}")
                ]
                response = llm_with_tools.invoke(state["messages"])
                logger.log(f"[SearchNode] LLM response: {response}")
                state['answer'] = response.content
                logger.log("[SearchNode] LLM with tools invoked successfully")
                state['status'] = "Result generated"

            except Exception as e:
                if any(keyword in str(e).lower() for keyword in ['permission_denied', 'invalid api key', 'authentication']):
                    logger.log(f"[SearchNode] Auth/API error: {e}")
                    continue
                else:
                    raise e
                
    except Exception as e:
        state['status'] = f"Error occurred during retrieval: {str(e)}"

    return state 