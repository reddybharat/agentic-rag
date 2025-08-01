from src.graphs.type import RAGAgentState
from src.tools.web_search_tool import tavily_search_tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent, create_react_agent
import os
import json

from langchain import hub
# from langchain.agents import load_tools
from langchain_community.agent_toolkits.load_tools import load_tools

tools = load_tools(["ddg-search"])
prompt = hub.pull("hwchase17/react")

# tools = [get_weather, search_web]

def search_agent_node(state: RAGAgentState) -> RAGAgentState:
    """
    A node that utilizes provided tools along with the functionalities provided by the LLM to get the appropriate answer to the user query
    """
    # Ensure messages is initialized at the start
    messages = state.get("messages") or []
    try:
        print(f"[SearchNode] Starting with state : {state}")
        # No longer initializing or checking state['messages']

        print("[SearchNode] Initializing LLM")
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
                print("[SearchNode] LLM created with provided API key")


                # Create the agent using create_react_agent
                print("[SearchNode] React agent created")
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
                output = []

                # #test react agent
                # print("[SearchNode] Invoking react agent")
                # result = agent_executor.invoke({"input": state["query"]})
                # print("[SearchNode] React agent result : ", result)
                # output.append(AIMessage(content=result.get('output')))

                # # #test
                # # llm_with_tools = llm.bind_tools(tools)
                # # print("[SearchNode] LLM bound with tools")
                # # response = llm_with_tools.invoke(messages)
                # # output.append(AIMessage(content=str(response.content)))

                #test react agent with timeout fallback
                import concurrent.futures
                TIMEOUT_SECONDS = 10
                print("[SearchNode] Invoking react agent with timeout fallback")
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(agent_executor.invoke, {"input": state["query"]})
                    try:
                        result = future.result(timeout=TIMEOUT_SECONDS)
                        print("[SearchNode] React agent result : ", result)
                        output.append(AIMessage(content=result.get('output')))
                    except concurrent.futures.TimeoutError:
                        print(f"[SearchNode] React agent timed out after {TIMEOUT_SECONDS} seconds, running fallback.")
                        llm_with_tools = llm.bind_tools(tools)
                        print("[SearchNode] LLM bound with tools")
                        response = llm_with_tools.invoke(state["query"])
                        output.append(AIMessage(content=str(response.content)))

            except Exception as e:
                if any(keyword in str(e).lower() for keyword in ['permission_denied', 'invalid api key', 'authentication']):
                    print(f"[SearchNode] Auth/API error: {e}")
                    continue
                else:
                    raise e
                
    except Exception as e:
        print(f"[SearchNode] Error occurred during retrieval: {str(e)}")
        state['status'] = "Error"

    state["messages"] = messages + output
    state["answer"] = output.content
    print(f"[SearchNode] Ending with state : {state}")
    return state