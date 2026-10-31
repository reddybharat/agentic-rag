CHUNK_CHARS = 1000
OVERLAP_WORDS = 30


def split_words(
    text: str, chunk_chars: int = CHUNK_CHARS, overlap_words: int = OVERLAP_WORDS
) -> list[str]:
    """Pack whole words into chunks of at most `chunk_chars` (a longer word stands alone),
    repeating the last `overlap_words` of each chunk at the start of the next."""
    words = text.split()
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end, length = start + 1, len(words[start])
        while end < len(words) and length + 1 + len(words[end]) <= chunk_chars:
            length += 1 + len(words[end])
            end += 1
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = max(end - overlap_words, start + 1)
    return chunks
