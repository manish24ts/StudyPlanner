"""
LangGraph wiring for the pipeline:

Prep (Ingestion + Web search in parallel) -> Planner -> Resource+Quiz -> Scheduler
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END

from app.agents.ingestion import run_ingestion
from app.agents.planner import run_planner
from app.agents.resource_quiz import enrich_topics
from app.agents.scheduler import build_schedule
from app.agents.web_enrichment import search_related_topics


class PipelineState(TypedDict, total=False):
    raw_text: str
    plan_title: str
    hours_per_day: float
    deadline: Optional[date]

    chunks: list[str]
    web_hints: list[dict]
    topics: list[dict]
    enriched_topics: list[dict]
    schedule: list[dict]


def prep_node(state: PipelineState) -> PipelineState:
    """Run ingestion and web research in parallel for faster startup."""
    raw_text = state["raw_text"]
    plan_title = state.get("plan_title", "")

    with ThreadPoolExecutor(max_workers=2) as pool:
        chunks_future = pool.submit(run_ingestion, raw_text)
        hints_future = pool.submit(search_related_topics, raw_text, plan_title)
        chunks = chunks_future.result()
        web_hints = hints_future.result()

    return {"chunks": chunks, "web_hints": web_hints}


def planner_node(state: PipelineState) -> PipelineState:
    topics = run_planner(
        state["chunks"],
        web_hints=state.get("web_hints"),
        plan_title=state.get("plan_title", ""),
    )
    return {"topics": topics}


def resource_quiz_node(state: PipelineState) -> PipelineState:
    enriched_topics = enrich_topics(state["topics"])
    return {"enriched_topics": enriched_topics}


def scheduler_node(state: PipelineState) -> PipelineState:
    flat = []
    for t_idx, topic in enumerate(state["enriched_topics"]):
        for s_idx, sub in enumerate(topic["subtopics"]):
            flat.append({
                "subtopic_id": (t_idx, s_idx),
                "est_minutes": sub["est_minutes"],
            })

    schedule = build_schedule(
        flat,
        hours_per_day=state["hours_per_day"],
        deadline=state.get("deadline"),
    )
    return {"schedule": schedule}


def build_graph():
    graph = StateGraph(PipelineState)
    graph.add_node("prep", prep_node)
    graph.add_node("planner", planner_node)
    graph.add_node("resource_quiz", resource_quiz_node)
    graph.add_node("scheduler", scheduler_node)

    graph.set_entry_point("prep")
    graph.add_edge("prep", "planner")
    graph.add_edge("planner", "resource_quiz")
    graph.add_edge("resource_quiz", "scheduler")
    graph.add_edge("scheduler", END)

    return graph.compile()


pipeline_app = build_graph()


def run_pipeline(
    raw_text: str,
    hours_per_day: float,
    deadline: Optional[date],
    plan_title: str = "",
) -> PipelineState:
    initial_state: PipelineState = {
        "raw_text": raw_text,
        "plan_title": plan_title,
        "hours_per_day": hours_per_day,
        "deadline": deadline,
    }
    return pipeline_app.invoke(initial_state)
