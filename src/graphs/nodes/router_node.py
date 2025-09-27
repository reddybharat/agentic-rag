from src.graphs.type import RAGAgentState
from langchain_core.messages import AIMessage, HumanMessage
from langchain.agents import AgentExecutor, create_react_agent
from src.helpers.prompts import router_agent_prompt
from src.tools.web_search_tool import tavily_search_tool, duckduckgo_search_tool
from src.tools.retriever_tool import retriever_tool
import os
from langchain_google_genai import ChatGoogleGenerativeAI
import json

from dotenv import load_dotenv
load_dotenv()

from langchain.prompts import PromptTemplate
from src.helpers.history_summarizer import summarize_chat_history


tools = [tavily_search_tool, duckduckgo_search_tool, retriever_tool]

router_agent_prompt_template = PromptTemplate(
    input_variables=["input"],
    template=router_agent_prompt
)

def router_agent_node(state: RAGAgentState) -> RAGAgentState:
    # Summarize chat history for context
    history_summary = summarize_chat_history(state.get("messages", []))
    # Enhance query with history context
    enhanced_query = state["query"]
    if history_summary and history_summary != "This is a new conversation with no previous history.":
        enhanced_query = f"Context from previous conversation: {history_summary}\n\nCurrent query: {state['query']}"
    # If finishing or no query, skip processing
    if state.get("finish") or "query" not in state:
        return state
    api_keys_str = os.getenv("GOOGLE_GENAI_API_KEYS", "")
    if api_keys_str.strip().startswith("["):
        try:
            gemini_api_keys = json.loads(api_keys_str)
        except Exception as e:
            raise ValueError(f"Failed to parse GOOGLE_GENAI_API_KEYS as JSON: {e}")
    else:
        gemini_api_keys = [k.strip() for k in api_keys_str.split(",") if k.strip()]
    if not gemini_api_keys:
        raise ValueError("Gemini API Key not provided. Please provide GEMINI_API_KEY as an environment variable")
    
    for i, key in enumerate(gemini_api_keys):
        try:
            llm = ChatGoogleGenerativeAI(google_api_key=key, model="gemini-2.0-flash-lite")
            agent = create_react_agent(
                tools=tools,
                llm=llm,
                prompt=router_agent_prompt_template
            )
            agent_executor = AgentExecutor(agent=agent, tools=tools, handle_parsing_errors=True, verbose=True)
            import concurrent.futures
            TIMEOUT_SECONDS = 30  # Increased timeout for debugging
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(agent_executor.invoke, {"input": enhanced_query})
                try:
                    result = future.result(timeout=TIMEOUT_SECONDS)
                    print(f"[ROUTER NODE] Agent result: {result}")
                except concurrent.futures.TimeoutError:
                    print("[ROUTER NODE] Agent timed out, falling back to direct LLM call")
                    llm_with_tools = llm.bind_tools(tools)
                    response = llm_with_tools.invoke(enhanced_query)
                    result = {'output': str(response.content)}
                    print(f"[ROUTER NODE] Direct LLM result: {result}")
        except Exception as e:
            print(f"[ROUTER NODE] Exception with key {i+1}: {e}")
            if any(keyword in str(e).lower() for keyword in ['permission_denied', 'invalid api key', 'authentication']):
                print(f"[ROUTER NODE] Auth/API error: {e}")
                continue
            else:
                print(f"[ROUTER NODE] Non-auth error: {e}")
                break
    # Prepare new messages to append
    new_messages = [
        HumanMessage(content=state["query"]),
        AIMessage(content=result.get('output') if result and isinstance(result, dict) else "Sorry, I couldn't process your request.")
    ]
    
    state["messages"] = state["messages"] + new_messages
    state["answer"] = result.get('output') if result and isinstance(result, dict) else None
    return state