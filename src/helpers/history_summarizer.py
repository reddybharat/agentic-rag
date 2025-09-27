from src.helpers.prompts import history_summarizer_prompt
from src.utils.llm_runner import LLM
from src.helpers.summarizer import serialize_messages
import json
import re

def is_substantive_message(content):
    """
    Returns True if the message content is substantive (not a greeting, salutation, or guardrail response).
    Uses regex for robust matching.
    """
    if not content or not content.strip():
        return False

    # Remove [NO_REWRITE]...[/NO_REWRITE] wrappers for guardrail detection
    content_clean = re.sub(r'\[NO_REWRITE\](.*?)\[/NO_REWRITE\]', r'\1', content, flags=re.IGNORECASE | re.DOTALL).strip().lower()

    # Patterns for greetings, pleasantries, and guardrails
    greeting_patterns = [
        r'^(hi|hello|hey|greetings|good (morning|afternoon|evening))\\b',
        r'how (are|r) (you|u)\\b',
        r'what\'s up\\b',
        r'^yo\\b',
        r'^sup\\b'
    ]
    pleasantry_patterns = [
        r'thank(s| you)\\b',
        r'you\'re welcome\\b',
        r'no problem\\b',
        r'my pleasure\\b',
        r'(have|wish) (a )?(nice|good|great) day\\b',
        r'take care\\b',
        r'see you\\b',
        r'bye\\b'
    ]
    guardrail_patterns = [
        r'as an ai',
        r'i am an ai',
        r'i\'m an ai',
        r'i am a language model',
        r'i\'m a language model',
        r'i cannot',
        r'i\'m unable',
        r'i do not have',
        r'i don\'t have',
        r'i am not able'
    ]

    # Check for greetings, pleasantries, or guardrail phrases
    for pattern in greeting_patterns + pleasantry_patterns + guardrail_patterns:
        if re.search(pattern, content_clean):
            return False

    # If the message is very short (<= 2 words), likely not substantive
    if len(content_clean.split()) <= 2:
        return False

    return True


def summarize_chat_history(messages):
    """
    Summarizes the chat history using the LLM to provide context for query processing.
    
    Args:
        messages: List of LangChain message objects or dicts
        
    Returns:
        str: A concise summary of the chat history
    """
    if not messages or len(messages) == 0:
        return "This is a new conversation with no previous history."
    
    try:
        # Serialize messages to a readable format
        serialized_messages = serialize_messages(messages)
        
        # Filter out non-substantive messages
        filtered_messages = [msg for msg in serialized_messages if is_substantive_message(msg.get("content", ""))]
        
        # Convert to a readable string format
        history_text = ""
        for i, msg in enumerate(filtered_messages):
            role = msg.get("type", "unknown")
            content = msg.get("content", "")
            if role == "human":
                history_text += f"User: {content}\n"
            elif role == "ai":
                history_text += f"Assistant: {content}\n"
            else:
                history_text += f"{role.title()}: {content}\n"
        
        # If history is too long, truncate it to keep it manageable
        if len(history_text) > 2000:
            # Keep the most recent messages
            lines = history_text.split('\n')
            recent_lines = lines[-20:]  # Keep last 20 lines
            history_text = '\n'.join(recent_lines)
            history_text = f"[Previous conversation truncated...]\n{history_text}"
        
        # Use the LLM to summarize
        llm = LLM()
        prompt = history_summarizer_prompt.format(chat_history=history_text)
        
        summary = llm.generate_response(prompt)
        
        return summary.strip()
        
    except Exception as e:
        print(f"[HISTORY SUMMARIZER] Error summarizing history: {str(e)}")
        # Fallback: return a simple summary
        fallback_summary = f"Conversation has {len(messages)} messages. Recent context may be limited due to summarization error."
        return fallback_summary
