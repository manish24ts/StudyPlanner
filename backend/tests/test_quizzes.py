from app.routers.quizzes import _get_owned_schedule_event


class DummyPlan:
    def __init__(self, user_id):
        self.user_id = user_id


class DummyEvent:
    def __init__(self, plan):
        self.plan = plan


class DummySubtopic:
    def __init__(self, events):
        self.schedule_events = events


class DummyQuiz:
    def __init__(self, subtopic):
        self.subtopic = subtopic


class DummyUser:
    def __init__(self, user_id):
        self.id = user_id


def test_get_owned_schedule_event_uses_users_plan():
    matching_event = DummyEvent(DummyPlan(7))
    other_event = DummyEvent(DummyPlan(8))
    quiz = DummyQuiz(DummySubtopic([other_event, matching_event]))
    user = DummyUser(7)

    event = _get_owned_schedule_event(quiz, user)

    assert event is matching_event
