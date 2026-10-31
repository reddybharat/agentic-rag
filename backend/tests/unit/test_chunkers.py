from app.infra.rag.chunkers import split_words


def test_chunks_respect_size_and_overlap() -> None:
    text = " ".join(f"w{i:03d}" for i in range(100))  # 100 words of 4 chars

    chunks = split_words(text, chunk_chars=50, overlap_words=2)

    assert all(len(chunk) <= 50 for chunk in chunks)
    assert chunks[0].split()[-2:] == chunks[1].split()[:2]
    assert chunks[-1].split()[-1] == "w099"


def test_long_word_stands_alone_and_blank_text_has_no_chunks() -> None:
    assert split_words("a " + "x" * 20 + " b", chunk_chars=5, overlap_words=0) == [
        "a",
        "x" * 20,
        "b",
    ]
    assert split_words(" \n ") == []
