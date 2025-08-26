from src.graphs.type import RAGAgentState
from src.tools.web_search_tool import tavily_search_tool
from src.helpers.history_summarizer import summarize_chat_history
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent, create_react_agent
import os
import json

from langchain import hub
# from langchain.agents import load_tools
# from langchain_community.agent_toolkits.load_tools import load_tools

from langchain_tavily import TavilySearch

from dotenv import load_dotenv
load_dotenv()

tavily_search_tool = TavilySearch(
    tavily_api_key=os.getenv("TAVILY_API_KEY"),
    max_results=5,
    topic="general",
)

# tools = load_tools(["ddg-search"])
tools = [tavily_search_tool]

prompt = hub.pull("hwchase17/react")

# tools = [get_weather, search_web]

def search_agent_node(state: RAGAgentState) -> RAGAgentState:
    """
    A node that utilizes provided tools along with the functionalities provided by the LLM to get the appropriate answer to the user query
    """
    messages = state.get("messages") or []
    result = None
    output = []
    try:
        print("[SEARCH NODE] 🚀 Node hit")
        print(f"[SEARCH NODE DEBUG] Original query: {state['query']}")
        print(f"[SEARCH NODE DEBUG] Current messages count: {len(messages)}")

        # Summarize chat history for context
        print("[SEARCH NODE DEBUG] Starting history summarization...")
        history_summary = summarize_chat_history(messages)
        print(f"[SEARCH NODE] History summary: {history_summary}")
        
        # Enhance query with history context
        enhanced_query = state["query"]
        if history_summary and history_summary != "This is a new conversation with no previous history.":
            enhanced_query = f"Context from previous conversation: {history_summary}\n\nCurrent query: {state['query']}"
            print(f"[SEARCH NODE DEBUG] Enhanced query created with history context")
            print(f"[SEARCH NODE DEBUG] Enhanced query length: {len(enhanced_query)} characters")
        else:
            print("[SEARCH NODE DEBUG] No history context added (new conversation or no summary)")
        
        print(f"[SEARCH NODE DEBUG] Final query to use: {enhanced_query}")

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
        
        print(f"[SEARCH NODE DEBUG] Found {len(gemini_api_keys)} API keys to try")
        
        for i, key in enumerate(gemini_api_keys):
            try:
                print(f"[SEARCH NODE DEBUG] Trying API key {i+1}/{len(gemini_api_keys)}")
                llm = ChatGoogleGenerativeAI(google_api_key=key, model="gemini-2.0-flash-lite")

                agent = create_react_agent(
                    tools=tools,
                    llm=llm,
                    prompt=prompt
                )
                agent_executor = AgentExecutor(agent=agent, tools=tools, handle_parsing_errors=True)

                if not messages:
                    messages = [
                        HumanMessage(content=state["query"])
                    ]
                    print("[SEARCH NODE DEBUG] No messages found, created initial message")

                import concurrent.futures
                TIMEOUT_SECONDS = 10
                print(f"[SEARCH NODE DEBUG] Running agent with timeout of {TIMEOUT_SECONDS} seconds...")
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(agent_executor.invoke, {"input": enhanced_query})
                    try:
                        result = future.result(timeout=TIMEOUT_SECONDS)
                        output.append(AIMessage(content=result.get('output')))
                        print(f"[SEARCH NODE DEBUG] Agent execution successful, result length: {len(result.get('output', ''))}")
                    except concurrent.futures.TimeoutError:
                        print("[SEARCH NODE DEBUG] Agent execution timed out, using fallback LLM")
                        llm_with_tools = llm.bind_tools(tools)
                        response = llm_with_tools.invoke(enhanced_query)
                        result = {'output': str(response.content)}
                        output.append(AIMessage(content=result['output']))
                        print(f"[SEARCH NODE DEBUG] Fallback LLM result length: {len(result['output'])}")

            except Exception as e:
                if any(keyword in str(e).lower() for keyword in ['permission_denied', 'invalid api key', 'authentication']):
                    print(f"[SEARCH NODE] Auth/API error: {e}")
                    print(f"[SEARCH NODE DEBUG] Authentication error with key {i+1}, trying next key...")
                    continue
                else:
                    print(f"[SEARCH NODE] Exception: {e}")
                    print(f"[SEARCH NODE DEBUG] Non-auth error with key {i+1}: {type(e).__name__}: {str(e)}")
                    break
    except Exception as e:
        print(f"[SEARCH NODE] Error: {str(e)}")
        print(f"[SEARCH NODE DEBUG] Top-level exception: {type(e).__name__}: {str(e)}")
        state['status'] = "Error"
    
    print(f"[SEARCH NODE DEBUG] Final output messages count: {len(output)}")
    
    # Add the user query as a HumanMessage if it's not already in messages
    if state["query"] and state["query"].strip():
        # Check if this query is already in the messages
        query_exists = any(
            (isinstance(msg, HumanMessage) and msg.content == state["query"]) or
            (isinstance(msg, dict) and msg.get('content') == state["query"])
            for msg in messages
        )
        
        if not query_exists:
            messages.append(HumanMessage(content=state["query"]))
            print(f"[SEARCH NODE DEBUG] Added user query as HumanMessage")
    
    state["messages"] = messages + output
    state["answer"] = result.get('output') if result and isinstance(result, dict) else None
    print(f"[SEARCH NODE DEBUG] Final messages count: {len(state['messages'])}")
    return state