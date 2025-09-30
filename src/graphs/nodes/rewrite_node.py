from src.graphs.type import RAGAgentState
from src.utils.llm_runner import LLM
from src.helpers.prompts import rewrite_prompt
from langchain_core.messages import AIMessage

def rewrite(state: RAGAgentState) -> RAGAgentState:
    """
    Node that uses an LLM to rewrite and improve the answer for clarity and completeness.
    """
    print("[REWRITE NODE] 🚀 Node hit")
    
    # Ensure state variables are properly set
    if 'finish' not in state:
        state['finish'] = False
    answer = state.get("answer", "")
    try:
        if answer:
            llm = LLM()
            prompt = rewrite_prompt.format(answer=answer)
            rewritten = llm.generate_response(prompt)
            state["answer"] = rewritten
            # Update the latest AI message with the rewritten content
            messages = state.get("messages", [])
            
            # Find the last AI message and update it
            for i in range(len(messages) - 1, -1, -1):  # Search backwards
                if isinstance(messages[i], dict) and messages[i].get('type') == 'ai':
                    # Update the latest AI message with rewritten content
                    messages[i]['content'] = rewritten
                    break
                elif hasattr(messages[i], 'type') and messages[i].type == 'ai':
                    # Handle LangChain objects if they exist
                    messages[i] = AIMessage(content=rewritten)
                    break
            else:
                # If no AI message found, add a new one
                messages.append({'type': 'ai', 'content': rewritten})
            
            state["messages"] = messages
        else:
            print("[REWRITE NODE] No answer to improve.")
    except Exception as e:
        print(f"[REWRITE NODE] Error: {str(e)}")
        state['status'] = "Rewrite Error"
    
    return state
