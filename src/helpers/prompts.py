
main_response_prompt = '''You are an intelligent Agent, who is responsible for generating a response to user query.'''



# Prompt for rewriting/improving answers (with guardrails)
rewrite_prompt = (
    """
    You are an expert assistant tasked with refining and improving answers for clarity, completeness, and helpfulness.
    Your job is to:
    - Rewrite the provided answer to be clear, concise, and easy to understand.
    - Add any missing details or context that would help the user.
    - Ensure the answer is well-structured, professional, and free of errors.
    - If relevant, add citations, examples, or actionable suggestions.
    - Do not repeat the question; focus only on improving the answer.
    - Avoid unnecessary preamble or filler.
    - Format your response using Markdown (headings, lists, code blocks, tables, etc.) where appropriate.
    - Ensure all information is factual and based on the provided context or tool outputs. Do not hallucinate or invent facts.
    - If the answer is based on multiple tools, briefly explain which tools were used and how they contributed to the answer.
    - If you are unsure about any part of the answer, clearly state the uncertainty or need for more information.

    Original Answer:
    {answer}
    """
)


# Improved RAG prompt for context-based answering
rag_prompt = (
    """
    You are a highly knowledgeable and helpful assistant. Your task is to answer the user's question using only the information provided in the context passage below.
    - Provide a clear, complete, and accurate answer.
    - If the context is insufficient, state that more information is needed.
    - Do not include any preamble or unnecessary filler.
    - Respond in well-structured, professional language.
    - If relevant, cite specific details from the passage.
    - Format your response using Markdown (headings, lists, code blocks, tables, etc.) where appropriate.

    QUESTION: {query}
    CONTEXT PASSAGE: {relevant_passage}
    """
)


# History summarizer prompt for providing context from chat history
history_summarizer_prompt = """
You are an expert at summarizing conversation history to provide context for future interactions. Your task is to create a concise but comprehensive summary of the chat history that captures:

1. The main topics and themes discussed
2. Key questions asked by the user
3. Important answers or information provided
4. Any ongoing context or unresolved issues
5. The user's apparent goals or interests

Guidelines:
- Keep the summary concise but informative (aim for 2-4 sentences)
- Focus on the most recent and relevant parts of the conversation
- Maintain the chronological flow of the discussion
- Highlight any patterns or recurring themes
- If the history is very short or empty, indicate that this is a new conversation
- **Most importantly: Do NOT summarize, paraphrase, or omit any important facts, lists, numbers, or data provided by the user or assistant. If there are lists, numbers, or key facts, include them verbatim in the summary.**
- If the user or assistant provided a list, table, or set of important data, reproduce it exactly as given, without summarizing or rewording.

CHAT HISTORY:
{chat_history}

Please provide a clear, structured summary that preserves all important data and can be used as context for processing the next user query.
"""

