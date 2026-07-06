"""
Agent 4 - Scheduler (plain code, no LLM).

Responsibility: deterministically map subtopics onto calendar dates based on
hours_per_day and an optional deadline. The schedule spreads work across the
available study window so that each day gets at most one planned subtopic,
while still allowing very long subtopics to spill to the next day when needed.
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

    if deadline is None:
        deadline = start_date + timedelta(days=max(6, len(subtopics_flat) - 1))

    available_days = max(1, (deadline - start_date).days + 1)
    effective_days = max(available_days, len(subtopics_flat))

    schedule: list[dict] = []
    current_day_offset = 0

    for item in subtopics_flat:
        est = int(item["est_minutes"])

        if est > daily_budget_minutes:
            schedule.append({
                "subtopic_id": item["subtopic_id"],
                "scheduled_date": start_date + timedelta(days=current_day_offset),
            })
            current_day_offset += 1
            continue

        schedule.append({
            "subtopic_id": item["subtopic_id"],
            "scheduled_date": start_date + timedelta(days=min(current_day_offset, effective_days - 1)),
        })
        current_day_offset += 1

    return schedule
