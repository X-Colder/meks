import tiktoken

from meks.config import settings

_encoder = None


def _get_encoder():
    global _encoder
    if _encoder is None:
        _encoder = tiktoken.get_encoding("cl100k_base")
    return _encoder


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> list[dict]:
    chunk_size = chunk_size or settings.chunk_size_tokens
    overlap = overlap or settings.chunk_overlap_tokens
    encoder = _get_encoder()

    sentences = _split_sentences(text)
    chunks = []
    current_tokens = []
    current_text_parts = []
    chunk_index = 0

    for sentence in sentences:
        sentence_tokens = encoder.encode(sentence)

        if len(current_tokens) + len(sentence_tokens) > chunk_size and current_tokens:
            chunk_content = " ".join(current_text_parts)
            chunks.append({
                "index": chunk_index,
                "content": chunk_content,
                "token_count": len(current_tokens),
            })
            chunk_index += 1

            overlap_tokens = current_tokens[-overlap:] if overlap else []
            overlap_text = encoder.decode(overlap_tokens) if overlap_tokens else ""
            current_tokens = list(overlap_tokens)
            current_text_parts = [overlap_text] if overlap_text else []

        current_tokens.extend(sentence_tokens)
        current_text_parts.append(sentence)

    if current_text_parts:
        chunks.append({
            "index": chunk_index,
            "content": " ".join(current_text_parts),
            "token_count": len(current_tokens),
        })

    return chunks


def _split_sentences(text: str) -> list[str]:
    import re
    sentences = re.split(r'(?<=[。！？.!?])\s*', text)
    return [s.strip() for s in sentences if s.strip()]
