"""
Agent 2 - Planner (LLM).

Produces a comprehensive Topic → Subtopic breakdown with descriptions,
key points, and study tips. Infers full curriculum even from sparse input.
"""
import json
import re

from langchain_groq import ChatGroq

from app.config import settings
from app.agents.web_enrichment import format_hints_for_planner

SYSTEM_PROMPT = """You are an expert curriculum designer and subject-matter tutor. \
Given study material (which may be very brief — even just a subject name), produce \
a COMPREHENSIVE, exam-ready learning plan that covers the FULL standard curriculum.

Coverage rules (critical — follow strictly):
- If the pasted material is sparse (few sentences, only a title, or vague notes), \
INFER the complete standard curriculum for that subject. Do NOT limit yourself to \
what was explicitly written — include everything a student needs for mastery.
- For a full subject (e.g. "Machine Learning", "Organic Chemistry", "Data Structures"): \
produce 6-10 major Topics minimum.
- For a narrow sub-unit (e.g. "Binary Search Trees only"): produce 3-5 Topics.
- Each Topic MUST have 5-8 Subtopics — cover the topic thoroughly; never skip obvious \
subtopics a student would need.
- Structure the curriculum in this order:
  1. Prerequisites & foundations (definitions, notation, setup)
  2. Core concepts (the main ideas)
  3. Techniques & methods (how to apply the concepts)
  4. Applications & examples (real-world use, worked problems)
  5. Advanced / edge cases (where relevant)
  6. Review & exam prep (common mistakes, practice areas)
- Order topics logically: foundations first, then intermediate, then advanced/applied.
- Weave in web-research hints as supplementary subtopics where they add value.

Content rules:
- Each Topic needs a one-sentence `summary`.
- Each Subtopic needs a 2-4 sentence `description` (what, why, how it connects).
- Include 3-5 `key_points` — specific concepts, terms, formulas, or skills.
- Add a practical `study_tip` (flashcards, practice problems, diagrams, etc.).
- Mark `is_supplementary: true` only for subtopics from web research, not inferred core curriculum.
- Estimate `est_minutes` realistically (15-90 minutes per subtopic).
- Keep titles short and specific (max ~8 words).

Return STRICT JSON only, no markdown fences, no commentary:

{
  "topics": [
    {
      "title": "string",
      "summary": "string",
      "subtopics": [
        {
          "title": "string",
          "est_minutes": 30,
          "description": "string",
          "key_points": ["string"],
          "study_tip": "string",
          "is_supplementary": false
        }
      ]
    }
  ]
}
"""


def _get_llm() -> ChatGroq:
    if not settings.GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to your .env file before running the pipeline."
        )
    return ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model=settings.GROQ_MODEL,
        temperature=0.25,
    )


def _extract_json(text: str) -> dict:
    if not text:
        return {"topics": []}

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {"topics": []}

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {"topics": []}


def _is_sparse(text: str) -> bool:
    words = text.split()
    return len(words) < 80


def run_planner(
    chunks: list[str],
    *,
    web_hints: list[dict] | None = None,
    plan_title: str = "",
) -> list[dict]:
    llm = _get_llm()
    combined_text = "\n\n---\n\n".join(chunks)

    human_parts = [f"Plan title: {plan_title}\n\nStudy material:\n\n{combined_text}"]

    if _is_sparse(combined_text):
        human_parts.append(
            "NOTE: The pasted material above is brief. Use the plan title and any "
            "keywords to infer a FULL, COMPREHENSIVE standard curriculum for this subject. "
            "Include ALL major topics and subtopics a student would need for mastery — "
            "prerequisites, core concepts, techniques, applications, advanced topics, and "
            "exam-relevant areas. Do NOT limit yourself to only what was explicitly written. "
            "Aim for 6-10 topics with 5-8 subtopics each for a full subject."
        )

    hints_block = format_hints_for_planner(web_hints or [])
    if hints_block:
        human_parts.append(hints_block)

    messages = [
        ("system", SYSTEM_PROMPT),
        ("human", "\n\n".join(human_parts)),
    ]

    response = llm.invoke(messages)
    parsed = _extract_json(response.content)

    topics = parsed.get("topics", [])
    if not topics:
        raise ValueError("Planner returned no topics.")

    for topic in topics:
        topic.setdefault("summary", "")
        for sub in topic.get("subtopics", []):
            sub["est_minutes"] = max(5, min(180, int(sub.get("est_minutes", 30))))
            sub.setdefault("description", "")
            sub.setdefault("key_points", [])
            sub.setdefault("study_tip", "")
            sub.setdefault("is_supplementary", False)
            if not isinstance(sub["key_points"], list):
                sub["key_points"] = []

    return topics
