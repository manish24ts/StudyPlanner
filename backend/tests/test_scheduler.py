from datetime import date

from app.agents.scheduler import build_schedule


def test_build_schedule_spreads_subtopics_across_deadline_days():
    subtopics = [
        {"subtopic_id": i, "est_minutes": 30}
        for i in range(5)
    ]

    schedule = build_schedule(
        subtopics,
        hours_per_day=2.0,
        deadline=date(2026, 7, 10),
        start_date=date(2026, 7, 6),
    )

    scheduled_dates = [entry["scheduled_date"] for entry in schedule]

    assert scheduled_dates == [
        date(2026, 7, 6),
        date(2026, 7, 7),
        date(2026, 7, 8),
        date(2026, 7, 9),
        date(2026, 7, 10),
    ]


def test_build_schedule_allows_long_subtopic_to_spill_to_next_day():
    subtopics = [
        {"subtopic_id": 1, "est_minutes": 180},
        {"subtopic_id": 2, "est_minutes": 30},
    ]

    schedule = build_schedule(
        subtopics,
        hours_per_day=2.0,
        deadline=date(2026, 7, 7),
        start_date=date(2026, 7, 6),
    )

    assert [entry["scheduled_date"] for entry in schedule] == [
        date(2026, 7, 6),
        date(2026, 7, 7),
    ]
