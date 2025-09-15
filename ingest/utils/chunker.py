# simple text chunker


def chunk_text(text, max_tokens=500, overlap=50):
    # naive chunk by characters as proxy for tokens
    chunks = []
    start = 0
    step = max_tokens - overlap
    while start < len(text):
        end = start + max_tokens
        chunks.append(text[start:end])
        start += step
    return [c.strip() for c in chunks if c.strip()]
