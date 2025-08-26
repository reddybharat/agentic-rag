from src.helpers.prompts import history_summarizer_prompt
from src.utils.llm_runner import LLM
from src.helpers.summarizer import serialize_messages
import json

def summarize_chat_history(messages):
    """
    Summarizes the chat history using the LLM to provide context for query processing.
    
    Args:
        messages: List of LangChain message objects or dicts
        
    Returns:
        str: A concise summary of the chat history
    """
    print(f"[HISTORY SUMMARIZER DEBUG] Starting summarization with {len(messages) if messages else 0} messages")
    
    if not messages or len(messages) == 0:
        print("[HISTORY SUMMARIZER DEBUG] No messages found, returning default response")
        return "This is a new conversation with no previous history."
    
    try:
        print("[HISTORY SUMMARIZER DEBUG] Serializing messages...")
        # Serialize messages to a readable format
        serialized_messages = serialize_messages(messages)
        print(f"[HISTORY SUMMARIZER DEBUG] Serialized {len(serialized_messages)} messages")
        
        # Convert to a readable string format
        history_text = ""
        for i, msg in enumerate(serialized_messages):
            role = msg.get("type", "unknown")
            content = msg.get("content", "")
            if role == "human":
                history_text += f"User: {content}\n"
            elif role == "ai":
                history_text += f"Assistant: {content}\n"
            else:
                history_text += f"{role.title()}: {content}\n"
            print(f"[HISTORY SUMMARIZER DEBUG] Message {i+1}: {role} - {content[:50]}{'...' if len(content) > 50 else ''}")
        
        print(f"[HISTORY SUMMARIZER DEBUG] History text length: {len(history_text)} characters")
        
        # If history is too long, truncate it to keep it manageable
        if len(history_text) > 2000:
            print("[HISTORY SUMMARIZER DEBUG] History too long, truncating to last 20 lines")
            # Keep the most recent messages
            lines = history_text.split('\n')
            recent_lines = lines[-20:]  # Keep last 20 lines
            history_text = '\n'.join(recent_lines)
            history_text = f"[Previous conversation truncated...]\n{history_text}"
            print(f"[HISTORY SUMMARIZER DEBUG] Truncated history length: {len(history_text)} characters")
        
        print("[HISTORY SUMMARIZER DEBUG] Calling LLM for summarization...")
        # Use the LLM to summarize
        llm = LLM()
        prompt = history_summarizer_prompt.format(chat_history=history_text)
        print(f"[HISTORY SUMMARIZER DEBUG] Prompt length: {len(prompt)} characters")
        
        summary = llm.generate_response(prompt)
        print(f"[HISTORY SUMMARIZER DEBUG] Generated summary: {summary}")
        
        return summary.strip()
        
    except Exception as e:
        print(f"[HISTORY SUMMARIZER DEBUG] Error occurred: {str(e)}")
        print(f"[HISTORY SUMMARIZER] Error summarizing history: {str(e)}")
        # Fallback: return a simple summary
        fallback_summary = f"Conversation has {len(messages)} messages. Recent context may be limited due to summarization error."
        print(f"[HISTORY SUMMARIZER DEBUG] Returning fallback summary: {fallback_summary}")
        return fallback_summary
