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
    if 'web_search' not in state:
        state['web_search'] = False
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
    
    # Debug print statements for state[messages] at the end
    messages = state.get("messages", [])
    print(f"[REWRITE NODE DEBUG] Final messages count: {len(messages)}")
    print(f"[REWRITE NODE DEBUG] Final state[messages]: {messages}")
    
    # Print each message with its index for better debugging
    for i, msg in enumerate(messages):
        if hasattr(msg, 'content'):
            # LangChain message object
            role = getattr(msg, 'type', None) or msg.__class__.__name__
            content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
        elif isinstance(msg, dict):
            # Dictionary format
            role = msg.get('type', msg.get('role', 'unknown'))
            content = msg.get('content', str(msg))
            content = content[:100] + "..." if len(content) > 100 else content
        else:
            # Fallback
            role = 'unknown'
            content = str(msg)[:100] + "..." if len(str(msg)) > 100 else str(msg)
        
        print(f"[REWRITE NODE DEBUG] Message {i}: {role} - {content}")
    
    return state
