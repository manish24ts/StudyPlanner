"""
Web enrichment — searches for related study topics to supplement the plan.

Uses DuckDuckGo (via ddgs) to find syllabus-style results that the Planner
agent can weave into the curriculum as supplementary subtopics.
"""
import re


def _subject_hint(raw_text: str, plan_title: str = "") -> str:
    """Build a concise search query from title + opening content."""
    preview = re.sub(r"\s+", " ", raw_text[:400]).strip()
    if plan_title:
        return f"{plan_title} {preview[:150]}"
    return preview[:200]


def search_related_topics(
    raw_text: str,
    plan_title: str = "",
    max_results: int = 12,
) -> list[dict]:
    """
    Returns [{"title": str, "snippet": str, "url": str}, ...]
    Gracefully returns [] if search is unavailable or rate-limited.
    """
    try:
        from ddgs import DDGS
    except ImportError:
        return []

    hint = _subject_hint(raw_text, plan_title)
    queries = [
        f"{hint} syllabus topics concepts to learn",
        f"{hint} common exam questions study guide",
        f"{plan_title or hint[:80]} prerequisites fundamentals",
        f"{plan_title or hint[:80]} complete curriculum topics list",
        f"what to study for {plan_title or hint[:60]} beginner to advanced",
    ]

    topics: list[dict] = []
    seen: set[str] = set()

    try:
        with DDGS() as ddgs:
            for query in queries:
                if len(topics) >= max_results:
                    break
                try:
                    results = list(ddgs.text(query, max_results=4, safesearch="moderate"))
                except Exception:
                    continue
                for r in results:
                    title = (r.get("title") or "").strip()
                    title_key = re.sub(r"\s+", " ", title.lower())
                    if not title or title_key in seen:
                        continue
                    if len(title) < 8 or len(title) > 120:
                        continue
                    seen.add(title_key)
                    topics.append({
                        "title": title,
                        "snippet": (r.get("body") or "")[:320],
                        "url": r.get("href") or "",
                    })
                    if len(topics) >= max_results:
                        break
    except Exception:
        return topics

    return topics


def format_hints_for_planner(hints: list[dict]) -> str:
    if not hints:
        return ""
    lines = [
        "Supplementary topics found via web research.",
        "Add the most relevant ones as subtopics with is_supplementary: true.",
        "Skip duplicates or topics already covered in the pasted material.",
        "",
    ]
    for i, h in enumerate(hints, 1):
        lines.append(f"{i}. {h['title']}")
        if h.get("snippet"):
            lines.append(f"   Context: {h['snippet']}")
    return "\n".join(lines)
