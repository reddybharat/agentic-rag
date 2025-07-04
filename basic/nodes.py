from typing import Dict, TypedDict, List
from langgraph.graph import StateGraph
from basic.type import AgentState
from basic.llm_runner import LLM

def response_node(state: AgentState) -> AgentState:
    """
    A node that returns a response to the user query provided.
    """
    llm = LLM()
    state['answer'] = llm.generate_response(state['query'])

    return state
    
def validator_node(state: AgentState) -> AgentState:
    """
    A node that validates the result of the previous nodes.
    """
    llm = LLM()
    state['answer'] = llm.generate_response(state['query'])

    return state
    

# # Summarizer node expects file bytes, decodes and generates a summary
# def summarizer_node(state: SummaryState):
#     # Include thread id and session id from the db. Also store the the flow in MongoDb
#     file_bytes = state.get("file_bytes", b"")
#     session_id = state.get("session_id")
#     upload_file_to_azure(file_bytes, session_id, "notice.pdf")
#     summary = ""
#     if file_bytes:
#         try:
#             # text = file_bytes.decode("utf-8")
#             summary = an_notice.summarize_notice(file_bytes)
#         except Exception as e:
#             summary = f"Error decoding file bytes: {e}"
#     state.update(summary=summary, session_id=session_id)
#     # print(state)
#     return state

# # Categorizer node receives the summary and categorizes it
# def categorizer_node(state: SummaryState):
#     summary = state.get("summary", "")
#     # print(summary)
#     print("Categorizing notice")
#     category = an_notice.categorize_notice(summary)
#     state.update(category=category)
#     return state