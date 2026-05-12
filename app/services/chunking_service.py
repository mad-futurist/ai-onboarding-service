import re


def estimate_tokens(text: str) -> int:
    """
    Rough estimate.
    Good enough for MVP.
    1 token ~= 4 characters in English/French documentation.
    """
    return max(1, len(text) // 4)


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def split_text_into_chunks(
    text: str,
    chunk_size: int = 1200,
    overlap: int = 200,
) -> list[str]:
    """
    Character-based chunking for MVP.
    Later we can replace it with token-based chunking.
    """

    text = normalize_text(text)

    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = end - overlap

        if start < 0:
            start = 0

    return chunks