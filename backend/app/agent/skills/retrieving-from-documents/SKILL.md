---
name: retrieving-from-documents
description: Read before answering any question, unless it is a greeting or small talk, since the answer is probably in the user's documents. Use for facts, numbers, definitions, explanations and summaries. Unlocks retrieve_from_documents, which searches the document library and returns passages with page numbers.
allowed-tools: retrieve_from_documents
---
# Retrieving from documents

## The tool
`retrieve_from_documents(query)` searches the user's library by meaning (vector search over page-sized chunks of their PDFs). It returns up to 4 passages, best match first, each headed `[filename, page N]`, sometimes with a little context from the same page. It returns "No matching passages" when nothing matches or the library is empty. You don't know what the documents contain until you search.

## How to search
1. Always search before answering, even if the topic seems general or familiar.
2. Query with the question's key terms, not the whole sentence.
3. If the passages don't answer it, search once more with different words (synonyms, the likely section name).

## How to answer
- Answer only from the passages. Combine them when the question needs it.
- Cite every fact as (filename, p. N) using the page in its header. Never guess a page.
- Quote exactly only when the wording matters.
- If passages disagree, report both with their citations.
- Nothing relevant after two searches: say the documents don't contain the answer.
- Never mention tools, chunks or search.

## Examples
User: "What is the total budget for phase two?"
`retrieve_from_documents(query="phase two total budget")` → `[report.pdf, page 3]` states 4.2 million.
Answer: "Phase two has a total budget of 4.2 million (report.pdf, p. 3)."

User: "Who is the CEO?" → two searches find nothing relevant.
Answer: "Your documents don't say who the CEO is."
