from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ---------- Auth ----------

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Plans ----------

class PlanCreateRequest(BaseModel):
    title: str
    content: str = Field(min_length=20, description="Raw study material pasted by the user")
    hours_per_day: float = Field(gt=0, le=16, default=2.0)
    deadline: Optional[date] = None


class QuizQuestionOut(BaseModel):
    question: str
    options: list[str]
    # correct_answer intentionally omitted from the public/calendar view


class BlogLinkOut(BaseModel):
    title: str
    url: str


class SubtopicOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    key_points: list[str] = []
    study_tip: Optional[str] = None
    is_supplementary: bool = False
    est_minutes: int
    youtube_url: Optional[str] = None
    youtube_title: Optional[str] = None
    youtube_channel: Optional[str] = None
    blog_links: list[BlogLinkOut] = []
    quiz_id: Optional[int] = None

    class Config:
        from_attributes = True


class TopicOut(BaseModel):
    id: int
    title: str
    summary: Optional[str] = None
    subtopics: list[SubtopicOut] = []

    class Config:
        from_attributes = True


class PlanOut(BaseModel):
    id: int
    title: str
    deadline: Optional[date]
    hours_per_day: float
    created_at: datetime

    class Config:
        from_attributes = True


class PlanCreateResponse(BaseModel):
    plan_id: int
    title: str
    topics: list[TopicOut]


# ---------- Calendar ----------

class CalendarEventOut(BaseModel):
    event_id: int
    scheduled_date: date
    status: str
    topic_title: str
    subtopic_id: int
    subtopic_title: str
    description: Optional[str] = None
    key_points: list[str] = []
    study_tip: Optional[str] = None
    is_supplementary: bool = False
    est_minutes: int
    youtube_url: Optional[str] = None
    youtube_title: Optional[str] = None
    youtube_channel: Optional[str] = None
    blog_links: list[BlogLinkOut] = []
    quiz_id: Optional[int] = None


class PlanStatsOut(BaseModel):
    topic_count: int
    subtopic_count: int
    total_minutes: int
    supplementary_count: int
    days_scheduled: int


class CalendarResponse(BaseModel):
    plan_id: int
    plan_title: str
    hours_per_day: float
    deadline: Optional[date]
    stats: PlanStatsOut
    topics: list[TopicOut]
    days: dict[str, list[CalendarEventOut]]


class QuizOut(BaseModel):
    quiz_id: int
    subtopic_title: str
    questions: list[QuizQuestionOut]
    pass_threshold: float


# ---------- Quiz submission ----------

class QuizSubmitRequest(BaseModel):
    answers: list[int] = Field(description="Index of the selected option per question, in order")


class QuizSubmitResponse(BaseModel):
    score_percent: float
    passed: bool
    schedule_event_status: str
