from app.agents.planner import _ensure_minimum_subtopics


def test_ensure_minimum_subtopics_expands_sparse_plans():
    topics = [{
        "title": "DSA",
        "summary": "Fallback",
        "subtopics": [{
            "title": "Core concepts",
            "est_minutes": 30,
            "description": "Intro",
            "key_points": ["A"],
            "study_tip": "Review",
            "is_supplementary": False,
        }],
    }]

    expanded = _ensure_minimum_subtopics(topics, target_subtopics=6)

    assert sum(len(topic["subtopics"]) for topic in expanded) == 6
