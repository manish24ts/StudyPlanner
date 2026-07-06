"""
Agent 4 - Scheduler (plain code, no LLM).

Responsibility: deterministically map subtopics onto calendar dates based on
hours_per_day and an optional deadline. The schedule is spread across the
available study window so the work fits naturally within the requested pace.
"""
import math
from datetime import date, timedelta


def build_schedule(
    subtopics_flat: list[dict],
    hours_per_day: float,
    deadline: date | None = None,
    start_date: date | None = None,
) -> list[dict]:
    """
    subtopics_flat: [{"subtopic_id": int, "est_minutes": int}, ...] in study order
    Returns: [{"subtopic_id": int, "scheduled_date": date}, ...]
    """
    start_date = start_date or date.today()
    daily_budget_minutes = max(1, int(hours_per_day * 60))

    if deadline is None:
        deadline = start_date + timedelta(days=6)

    available_days = max(1, (deadline - start_date).days + 1)
    total_minutes = sum(int(item["est_minutes"]) for item in subtopics_flat)
    required_daily_minutes = max(1, math.ceil(total_minutes / available_days))
    effective_daily_budget = max(daily_budget_minutes, required_daily_minutes)

    schedule: list[dict] = []
    current_day_offset = 0
    minutes_used_today = 0

    for item in subtopics_flat:
        est = int(item["est_minutes"])

        if est > effective_daily_budget:
            if minutes_used_today > 0:
                current_day_offset += 1
                minutes_used_today = 0
            schedule.append({
                "subtopic_id": item["subtopic_id"],
                "scheduled_date": start_date + timedelta(days=current_day_offset),
            })
            current_day_offset += 1
            minutes_used_today = 0
            continue

        if minutes_used_today + est > effective_daily_budget:
            current_day_offset += 1
            minutes_used_today = 0

        schedule.append({
            "subtopic_id": item["subtopic_id"],
            "scheduled_date": start_date + timedelta(days=current_day_offset),
        })
        minutes_used_today += est

    return schedule
