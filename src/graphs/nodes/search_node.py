from src.graphs.type import RAGAgentState
from src.helpers.history_summarizer import summarize_chat_history
from langchain_core.messages import HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_react_agent
import os
import json

from langchain import hub

from src.tools.web_search_tool import tavily_search_tool, duckduckgo_search_tool

from dotenv import load_dotenv
load_dotenv()

tools = [tavily_search_tool, duckduckgo_search_tool]


search_agent_prompt = hub.pull("hwchase17/react")

def search_agent_node(state: RAGAgentState) -> RAGAgentState:
    """
    A node that utilizes provided tools along with the functionalities provided by the LLM to get the appropriate answer to the user query
    """
    result = None
    try:
        print("[SEARCH NODE] 🚀 Node hit")
        # Summarize chat history for context
        history_summary = summarize_chat_history(state.get("messages", []))
        
        # Enhance query with history context
        enhanced_query = state["query"]
        if history_summary and history_summary != "This is a new conversation with no previous history.":
            enhanced_query = f"Context from previous conversation: {history_summary}\n\nCurrent query: {state['query']}"

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
                    prompt=search_agent_prompt
                )
                agent_executor = AgentExecutor(agent=agent, tools=tools, handle_parsing_errors=True)

                import concurrent.futures
                TIMEOUT_SECONDS = 30  # Increased timeout for debugging
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(agent_executor.invoke, {"input": enhanced_query})
                    try:
                        result = future.result(timeout=TIMEOUT_SECONDS)
                        print(f"[SEARCH NODE] Agent result: {result}")
                    except concurrent.futures.TimeoutError:
                        print("[SEARCH NODE] Agent timed out, falling back to direct LLM call")
                        llm_with_tools = llm.bind_tools(tools)
                        response = llm_with_tools.invoke(enhanced_query)
                        result = {'output': str(response.content)}
                        print(f"[SEARCH NODE] Direct LLM result: {result}")

            except Exception as e:
                print(f"[SEARCH NODE] Exception with key {i+1}: {e}")
                if any(keyword in str(e).lower() for keyword in ['permission_denied', 'invalid api key', 'authentication']):
                    print(f"[SEARCH NODE] Auth/API error: {e}")
                    continue
                else:
                    print(f"[SEARCH NODE] Non-auth error: {e}")
                    break
    except Exception as e:
        print(f"[SEARCH NODE] Error: {str(e)}")
        state['status'] = "Error"
    
    # Prepare new messages to append
    new_messages = [
        HumanMessage(content=state["query"]),
        AIMessage(content=result.get('output') if result and isinstance(result, dict) else "Sorry, I couldn't process your request.")
    ]
    
    state["messages"] = state["messages"] + new_messages
    state["answer"] = result.get('output') if result and isinstance(result, dict) else None
    return state