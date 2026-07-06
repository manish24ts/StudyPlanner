"""
Agent 1 - Ingestion (plain code, no LLM).

Responsibility: turn raw pasted text into clean, reasonably-sized chunks that
the Planner agent can reason over without blowing past context/token limits.
"""
import re

MAX_WORDS_PER_CHUNK = 600


def clean_text(raw_text: str) -> str:
    text = raw_text.replace("\r\n", "\n")
    # collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # collapse repeated whitespace/tabs (but keep newlines)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def chunk_text(text: str, max_words: int = MAX_WORDS_PER_CHUNK) -> list[str]:
    """Chunk by paragraphs first, then merge/split to respect max_words."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current_words: list[str] = []

    for para in paragraphs:
        para_words = para.split()
        if len(current_words) + len(para_words) > max_words and current_words:
            chunks.append(" ".join(current_words))
            current_words = []

        if len(para_words) > max_words:
            # split an oversized paragraph on its own
            for i in range(0, len(para_words), max_words):
                chunks.append(" ".join(para_words[i:i + max_words]))
        else:
            current_words.extend(para_words)

    if current_words:
        chunks.append(" ".join(current_words))

    return chunks or [text.strip()]


def run_ingestion(raw_text: str) -> list[str]:
    cleaned = clean_text(raw_text)
    return chunk_text(cleaned)
