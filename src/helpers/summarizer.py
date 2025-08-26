def serialize_messages(messages):
    """
    Converts LangChain message objects or dicts to a list of dicts with 'type' and 'content'.
    """
    serialized = []
    for msg in messages:
        if hasattr(msg, "content"):
            role = getattr(msg, "type", None) or msg.__class__.__name__
            if role in ["HumanMessage", "user"]:
                role = "human"
            elif role in ["AIMessage", "bot"]:
                role = "ai"
            else:
                role = str(role)
            serialized.append({"type": role, "content": msg.content})
        elif isinstance(msg, dict):
            # Already a dict
            role = msg.get("type") or msg.get("role") or "human"
            serialized.append({"type": role, "content": msg.get("content", str(msg))})
        else:
            # Fallback: treat as string
            serialized.append({"type": "unknown", "content": str(msg)})
    return serialized
