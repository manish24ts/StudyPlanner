"""
Learning resource discovery — blogs, articles, and reference material via web search.
"""
import re
from urllib.parse import urlparse

BLOCKED_DOMAINS = {
    "youtube.com", "youtu.be", "facebook.com", "twitter.com", "x.com",
    "instagram.com", "tiktok.com", "pinterest.com", "reddit.com",
    "amazon.com", "ebay.com", "linkedin.com", "quora.com",
    "stackoverflow.com",  # prefer docs/tutorials over Q&A threads
}

PREFERRED_DOMAINS = {
    "developer.mozilla.org", "mdn.io", "w3schools.com", "geeksforgeeks.org",
    "freecodecamp.org", "realpython.com", "dev.to", "medium.com",
    "towardsdatascience.com", "khanacademy.org", "coursera.org",
    "tutorialspoint.com", "javatpoint.com", "ibm.com", "microsoft.com",
    "google.com", "oracle.com", "postgresql.org", "python.org",
    "react.dev", "vuejs.org", "nodejs.org", "digitalocean.com",
    "baeldung.com", "spring.io", "kubernetes.io", "aws.amazon.com",
    "cloud.google.com", "learn.microsoft.com", "statisticshowto.com",
    "runestone.academy", "openstax.org", "mathisfun.com", "mathworld.wolfram.com",
    "brilliant.org", "codecademy.com", "scrimba.com", "javascript.info",
    "css-tricks.com", "smashingmagazine.com", "refactoring.guru",
    "nature.com", "sciencedirect.com", "britannica.com",
}


def _domain(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


def _is_blocked(url: str) -> bool:
    d = _domain(url)
    return any(d == b or d.endswith("." + b) for b in BLOCKED_DOMAINS)


def _domain_score(url: str) -> float:
    d = _domain(url)
    if any(d == p or d.endswith("." + p) for p in PREFERRED_DOMAINS):
        return 1.0
    if d.endswith(".edu") or d.endswith(".gov"):
        return 0.9
    if "wiki" in d:
        return 0.75
    if any(kw in d for kw in ("blog", "docs", "learn", "guide", "tutorial", "handbook")):
        return 0.65
    return 0.3


def _title_relevance(title: str, topic_title: str, subtopic_title: str) -> float:
    title_lower = title.lower()
    terms = re.findall(r"[a-z0-9]+", f"{subtopic_title} {topic_title}".lower())
    terms = [t for t in terms if len(t) > 2]
    if not terms:
        return 0.0
    hits = sum(1 for t in terms if t in title_lower)
    learn_bonus = 0.15 if any(kw in title_lower for kw in (
        "tutorial", "guide", "learn", "explained", "introduction", "beginner",
        "overview", "handbook", "documentation", "cheatsheet",
    )) else 0
    return min(1.0, (hits / len(terms)) + learn_bonus)


def search_learning_articles(
    topic_title: str,
    subtopic_title: str,
    max_results: int = 5,
) -> list[dict]:
    """
    Returns [{"title": str, "url": str}, ...] — helpful blog/article links.
    """
    try:
        from ddgs import DDGS
    except ImportError:
        return []

    queries = [
        f"{subtopic_title} {topic_title} tutorial guide blog",
        f"learn {subtopic_title} {topic_title} explained article",
        f"{subtopic_title} {topic_title} documentation beginner",
        f"{subtopic_title} {topic_title} complete guide site:edu OR site:org",
        f"best {subtopic_title} {topic_title} tutorial for beginners",
    ]

    candidates: list[dict] = []
    seen_urls: set[str] = set()

    try:
        with DDGS() as ddgs:
            for query in queries:
                if len(candidates) >= max_results * 3:
                    break
                try:
                    results = list(ddgs.text(query, max_results=8, safesearch="moderate"))
                except Exception:
                    continue
                for r in results:
                    url = (r.get("href") or "").strip()
                    title = (r.get("title") or "").strip()
                    if not url or not title or _is_blocked(url):
                        continue
                    if len(title) < 10:
                        continue
                    url_key = url.split("#")[0].rstrip("/").lower()
                    if url_key in seen_urls:
                        continue
                    seen_urls.add(url_key)
                    rel = _title_relevance(title, topic_title, subtopic_title)
                    candidates.append({
                        "title": title[:120],
                        "url": url,
                        "_score": (
                            0.45 * _domain_score(url)
                            + 0.40 * rel
                            + (0.15 if subtopic_title.lower() in title.lower() else 0)
                        ),
                    })
    except Exception:
        return []

    candidates.sort(key=lambda c: c["_score"], reverse=True)
    return [{"title": c["title"], "url": c["url"]} for c in candidates[:max_results]]
