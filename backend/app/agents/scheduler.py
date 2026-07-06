"""
Agent 4 - Scheduler (plain code, no LLM).

Responsibility: deterministically map subtopics onto calendar dates based on
hours_per_day and an optional deadline. Greedy bin-packing by day: fill each
day up to the hours_per_day budget, spill remainder into the next day.
"""
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

    schedule: list[dict] = []
    current_day_offset = 0
    minutes_used_today = 0

    for item in subtopics_flat:
        est = item["est_minutes"]

        # If this subtopic alone exceeds the daily budget, give it its own day.
        if est > daily_budget_minutes:
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

        if minutes_used_today + est > daily_budget_minutes:
            current_day_offset += 1
            minutes_used_today = 0

        schedule.append({
            "subtopic_id": item["subtopic_id"],
            "scheduled_date": start_date + timedelta(days=current_day_offset),
        })
        minutes_used_today += est

    # If a deadline was given and we overshot it, compress by increasing the
    # effective daily budget proportionally (simple, transparent strategy —
    # no LLM "judgment" involved, just re-run with a larger budget).
    if deadline:
        last_date = schedule[-1]["scheduled_date"] if schedule else start_date
        available_days = (deadline - start_date).days + 1
        used_days = (last_date - start_date).days + 1
        if used_days > available_days > 0:
            scale = used_days / available_days
            new_hours_per_day = hours_per_day * scale
            return build_schedule(subtopics_flat, new_hours_per_day, deadline=None,
                                   start_date=start_date)

    return schedule
