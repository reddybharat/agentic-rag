---
name: answering-document-questions
description: Read when the user asks a question that their documents might answer, even if the topic seems unfamiliar. Use to look up facts, numbers, definitions or explanations. Retrieves passages and answers with page citations.
allowed-tools: retrieve_documents
---
# Answering document questions

The user has a library of uploaded documents. You don't know what they contain until you retrieve from them.

## Rules

- Always call `retrieve_documents` before answering, even if the topic seems unfamiliar or general: the answer is probably in the documents. Skip it only for greetings and small talk.
- Answer only from the returned passages, following the citation rules returned with them. If they don't answer the question, say so.
- Never mention tools, chunks or other internal details.

## Tools

- Passages from the library: `retrieve_documents(query)`. Returns up to 4 passages, each headed `[filename, page N]`.

## Workflow

1. Call `retrieve_documents` with the question's key terms.
2. If the passages don't answer it, call it again once with different words (synonyms, the likely section name).
3. Answer from the passages, citing each fact.
4. Still nothing: say the library doesn't contain the answer.

## Examples

**Answer found**
User: "What is the total budget for phase two?"
Call: `retrieve_documents(query="phase two total budget")` returns a passage headed `[report.pdf, page 3]` stating 4.2 million.
Answer: "Phase two has a total budget of 4.2 million (report.pdf, p. 3)."

**Not found**
User: "Who is the CEO?"
Call: `retrieve_documents(query="CEO chief executive")` and `retrieve_documents(query="leadership management team")` return nothing relevant.
Answer: "Your documents don't say who the CEO is."
