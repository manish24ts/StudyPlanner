"""
Agent 3 - Resource + Quiz (LLM + YouTube Data API v3 + web articles).

For each subtopic: pick the most relevant popular YouTube video, find helpful
blog/article links, and generate mastery quizzes.
"""
import json
import math
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain_groq import ChatGroq

from app.config import settings
from app.agents.learning_resources import search_learning_articles

QUIZ_BATCH_PROMPT = """You are a quiz generator for a study app. Given a list of \
subtopics (with their parent topic), produce exactly 3 multiple-choice questions \
per subtopic that test understanding.

Return STRICT JSON only, no markdown fences, no commentary, matching this exact shape:

{
  "quizzes": [
    {
      "subtopic_title": "string (must match input exactly)",
      "questions": [
        {
          "question": "string",
          "options": ["string", "string", "string", "string"],
          "correct_answer": 0
        }
      ]
    }
  ]
}

`correct_answer` is the zero-based index into `options`. Include one entry per subtopic."""

_TUTORIAL_KEYWORDS = {
    "tutorial", "explained", "course", "lecture", "guide", "introduction",
    "learn", "crash", "full", "complete", "beginner", "basics", "overview",
}
_CLICKBAIT_KEYWORDS = {"you won't believe", "gone wrong", "reacts", "prank", "shorts"}

# Well-known educational channels — bonus when matched (case-insensitive substring)
_TRUSTED_CHANNELS = {
    "3blue1brown", "khan academy", "freecodecamp", "crash course", "mit opencourseware",
    "stanford", "harvard", "coursera", "edx", "nptel", "sentdex", "corey schafer",
    "traversy media", "fireship", "the net ninja", "programming with mosh",
    "cs dojo", "mycodeschool", "thenewboston", "derek banas", "statquest",
    "patrickjmt", "professor leonard", "organic chemistry tutor", "physics wallah",
    "unacademy", "veritasium", "minutephysics", "numberphile", "computerphile",
    "tech with tim", "code with harry", "geeksforgeeks", "simplilearn",
    "ibm technology", "google cloud tech", "microsoft developer",
}


def _get_llm(*, fast: bool = False) -> ChatGroq:
    if not settings.GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to your .env file before running the pipeline."
        )
    model = settings.GROQ_FAST_MODEL if fast else settings.GROQ_MODEL
    return ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model=model,
        temperature=0.3,
    )


def _extract_json(text: str) -> dict:
    if not text:
        raise ValueError("Quiz LLM returned empty output.")

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"Quiz LLM did not return JSON. Raw output: {text[:500]}")

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Quiz LLM returned invalid JSON: {exc}") from exc


def _query_terms(topic_title: str, subtopic_title: str) -> list[str]:
    combined = f"{subtopic_title} {topic_title}".lower()
    words = re.findall(r"[a-z0-9]+", combined)
    return [w for w in words if len(w) > 2]


def _title_relevance(title: str, terms: list[str]) -> float:
    title_lower = title.lower()
    if not terms:
        return 0.5
    hits = sum(1 for t in terms if t in title_lower)
    bonus = 0.2 if any(kw in title_lower for kw in _TUTORIAL_KEYWORDS) else 0
    penalty = 0.3 if any(kw in title_lower for kw in _CLICKBAIT_KEYWORDS) else 0
    return max(0.0, min(1.0, (hits / len(terms)) + bonus - penalty))


def _channel_trust(channel: str) -> float:
    channel_lower = channel.lower()
    return 1.0 if any(trusted in channel_lower for trusted in _TRUSTED_CHANNELS) else 0.0


def _parse_duration_seconds(iso_duration: str) -> int:
    """Parse ISO 8601 duration (PT#H#M#S) to total seconds."""
    if not iso_duration:
        return 0
    match = re.match(
        r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",
        iso_duration,
    )
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def _search_queries(topic_title: str, subtopic_title: str) -> list[str]:
    return [
        f"{subtopic_title} {topic_title} tutorial explained",
        f"{subtopic_title} {topic_title} full course lecture",
        f"learn {subtopic_title} {topic_title} beginner guide",
    ]


def _log_score(value: int, ceiling: float) -> float:
    if value <= 0:
        return 0.0
    return min(math.log10(value) / ceiling, 1.0)


def find_best_youtube_video(topic_title: str, subtopic_title: str) -> dict | None:
    """
    Search YouTube with multiple queries, rank by relevance + popularity + channel authority.
    Returns {url, title, channel, views} or None.
    """
    if not settings.YOUTUBE_API_KEY:
        return None

    terms = _query_terms(topic_title, subtopic_title)

    try:
        youtube = build("youtube", "v3", developerKey=settings.YOUTUBE_API_KEY)

        seen_ids: set[str] = set()
        video_ids: list[str] = []

        for query in _search_queries(topic_title, subtopic_title):
            search_resp = youtube.search().list(
                q=query,
                part="id,snippet",
                maxResults=20,
                type="video",
                relevanceLanguage="en",
                safeSearch="strict",
                videoDefinition="any",
                order="relevance",
            ).execute()

            for item in search_resp.get("items", []):
                vid = item.get("id", {}).get("videoId")
                if vid and vid not in seen_ids:
                    seen_ids.add(vid)
                    video_ids.append(vid)

            if len(video_ids) >= 30:
                break

        if not video_ids:
            return None

        videos: list[dict] = []
        for i in range(0, len(video_ids[:30]), 25):
            batch = video_ids[i:i + 25]
            videos_resp = youtube.videos().list(
                part="statistics,snippet,contentDetails",
                id=",".join(batch),
            ).execute()
            videos.extend(videos_resp.get("items", []))

        channel_ids = list({
            v["snippet"]["channelId"]
            for v in videos
            if v.get("snippet", {}).get("channelId")
        })

        channel_subs: dict[str, int] = {}
        if channel_ids:
            ch_resp = youtube.channels().list(
                part="statistics",
                id=",".join(channel_ids[:50]),
            ).execute()
            for ch in ch_resp.get("items", []):
                channel_subs[ch["id"]] = int(ch["statistics"].get("subscriberCount", 0))

        best = None
        best_score = -1.0

        for video in videos:
            stats = video.get("statistics", {})
            snippet = video.get("snippet", {})
            content = video.get("contentDetails", {})
            views = int(stats.get("viewCount", 0))
            channel_id = snippet.get("channelId", "")
            subs = channel_subs.get(channel_id, 0)
            title = snippet.get("title", "")
            channel = snippet.get("channelTitle", "")
            duration_s = _parse_duration_seconds(content.get("duration", ""))

            # Skip YouTube Shorts and very brief clips
            if 0 < duration_s < 120:
                continue

            rel = _title_relevance(title, terms)
            view_s = _log_score(views, 7.0)    # 10M views ≈ max
            sub_s = _log_score(subs, 8.0)       # 100M subs ≈ max
            trust = _channel_trust(channel)

            score = 0.35 * rel + 0.30 * view_s + 0.25 * sub_s + 0.10 * trust

            # Strongly prefer established educational content
            if views >= 100_000:
                score += 0.05
            if subs >= 500_000:
                score += 0.05
            if views < 10_000:
                score *= 0.6
            elif views < 50_000:
                score *= 0.85

            if score > best_score:
                best_score = score
                best = {
                    "url": f"https://www.youtube.com/watch?v={video['id']}",
                    "title": title,
                    "channel": channel,
                    "views": views,
                }

        return best
    except HttpError:
        return None
    except Exception:
        return None


def find_youtube_video(query: str) -> str | None:
    """Legacy helper — returns URL only."""
    parts = query.rsplit(" ", 2)
    if len(parts) >= 2:
        result = find_best_youtube_video(parts[-1] if len(parts) > 2 else "", query)
    else:
        result = find_best_youtube_video("", query)
    return result["url"] if result else None


def _fallback_questions(subtopic_title: str) -> list[dict]:
    return [{
        "question": f"What is the main focus of \"{subtopic_title}\"?",
        "options": [
            "Core concepts and definitions",
            "Unrelated historical trivia",
            "Entertainment only",
            "None of the above",
        ],
        "correct_answer": 0,
    }] * 3


def generate_quizzes_batch(subtopics: list[tuple[str, str]]) -> dict[str, list[dict]]:
    if not subtopics:
        return {}

    lines = []
    for topic_title, sub_title in subtopics:
        lines.append(f"- Topic: {topic_title} | Subtopic: {sub_title}")
    human = "Generate quizzes for these subtopics:\n\n" + "\n".join(lines)

    llm = _get_llm(fast=True)
    response = llm.invoke([
        ("system", QUIZ_BATCH_PROMPT),
        ("human", human),
    ])
    parsed = _extract_json(response.content)

    result: dict[str, list[dict]] = {}
    for entry in parsed.get("quizzes", []):
        title = entry.get("subtopic_title", "").strip()
        questions = entry.get("questions", [])
        if title and questions:
            result[title] = questions

    for _, sub_title in subtopics:
        if sub_title not in result:
            result[sub_title] = _fallback_questions(sub_title)

    return result


def _resources_for_subtopic(
    topic_title: str,
    subtopic_title: str,
) -> tuple[str, dict | None, list[dict]]:
    """Returns (subtopic_title, youtube_meta, blog_links)."""
    youtube = find_best_youtube_video(topic_title, subtopic_title)
    blogs = search_learning_articles(topic_title, subtopic_title, max_results=5)
    return subtopic_title, youtube, blogs


def enrich_topics(topics: list[dict]) -> list[dict]:
    all_pairs: list[tuple[str, str]] = []
    for topic in topics:
        for sub in topic.get("subtopics", []):
            all_pairs.append((topic["title"], sub["title"]))

    all_quizzes: dict[str, list[dict]] = {}
    chunk_size = 10
    for i in range(0, len(all_pairs), chunk_size):
        batch = generate_quizzes_batch(all_pairs[i:i + chunk_size])
        all_quizzes.update(batch)

    youtube_map: dict[str, dict | None] = {}
    blogs_map: dict[str, list[dict]] = {}

    max_workers = min(6, max(1, len(all_pairs)))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [
            pool.submit(_resources_for_subtopic, topic_title, sub_title)
            for topic_title, sub_title in all_pairs
        ]
        for fut in as_completed(futures):
            sub_title, youtube, blogs = fut.result()
            youtube_map[sub_title] = youtube
            blogs_map[sub_title] = blogs

    enriched_topics = []
    for topic in topics:
        enriched_subtopics = []
        for sub in topic.get("subtopics", []):
            yt = youtube_map.get(sub["title"])
            enriched_subtopics.append({
                **sub,
                "youtube_url": yt["url"] if yt else None,
                "youtube_title": yt["title"] if yt else None,
                "youtube_channel": yt["channel"] if yt else None,
                "blog_links": blogs_map.get(sub["title"], []),
                "questions": all_quizzes.get(sub["title"], _fallback_questions(sub["title"])),
            })
        enriched_topics.append({
            "title": topic["title"],
            "summary": topic.get("summary", ""),
            "subtopics": enriched_subtopics,
        })

    return enriched_topics


def run_resource_quiz(topic_title: str, subtopic_title: str) -> tuple[str | None, list[dict]]:
    yt = find_best_youtube_video(topic_title, subtopic_title)
    quizzes = generate_quizzes_batch([(topic_title, subtopic_title)])
    return yt["url"] if yt else None, quizzes.get(subtopic_title, _fallback_questions(subtopic_title))
