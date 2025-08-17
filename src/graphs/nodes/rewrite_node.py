from src.graphs.type import RAGAgentState
from src.utils.llm_runner import LLM
from src.helpers.prompts import rewrite_prompt
from langchain_core.messages import AIMessage

def rewrite(state: RAGAgentState) -> RAGAgentState:
    """
    Node that uses an LLM to rewrite and improve the answer for clarity and completeness.
    """
    print(f"[REWRITE NODE] Starting with state : {state}")
    answer = state.get("answer", "")
    try:
        if answer:
            llm = LLM()
            prompt = rewrite_prompt.format(answer=answer)
            rewritten = llm.generate_response(prompt)
            state["answer"] = rewritten
            state["messages"] = state.get("messages", []) + [AIMessage(content=rewritten)]
            print(f"[REWRITE NODE] Improved answer: {rewritten[:100]}...")
        else:
            print("[REWRITE NODE] No answer to improve.")
    except Exception as e:
        print(f"[REWRITE NODE] Error: {str(e)}")
        state['status'] = "Rewrite Error"
    print(f"[REWRITE NODE] Ending with state : {state}")
    return state
