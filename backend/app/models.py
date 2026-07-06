import enum
from datetime import datetime, date

from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, DateTime, Date,
    Float, Enum, JSON, Boolean, UniqueConstraint
)
from sqlalchemy.orm import relationship

from app.database import Base


class ScheduleStatus(str, enum.Enum):
    PENDING = "PENDING"
    DONE = "DONE"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    plans = relationship("Plan", back_populates="user", cascade="all, delete-orphan")


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    deadline = Column(Date, nullable=True)
    hours_per_day = Column(Float, nullable=False, default=2.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="plans")
    topics = relationship("Topic", back_populates="plan", cascade="all, delete-orphan",
                           order_by="Topic.order_index")
    schedule_events = relationship("ScheduleEvent", back_populates="plan",
                                    cascade="all, delete-orphan")


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=True)
    order_index = Column(Integer, nullable=False, default=0)

    plan = relationship("Plan", back_populates="topics")
    subtopics = relationship("Subtopic", back_populates="topic", cascade="all, delete-orphan",
                              order_by="Subtopic.order_index")


class Subtopic(Base):
    __tablename__ = "subtopics"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    key_points = Column(JSON, nullable=True)
    study_tip = Column(Text, nullable=True)
    is_supplementary = Column(Boolean, nullable=False, default=False)
    est_minutes = Column(Integer, nullable=False, default=30)
    youtube_url = Column(String, nullable=True)
    youtube_title = Column(String, nullable=True)
    youtube_channel = Column(String, nullable=True)
    blog_links = Column(JSON, nullable=True)
    order_index = Column(Integer, nullable=False, default=0)

    topic = relationship("Topic", back_populates="subtopics")
    quiz = relationship("Quiz", back_populates="subtopic", uselist=False,
                         cascade="all, delete-orphan")
    schedule_events = relationship("ScheduleEvent", back_populates="subtopic")


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    subtopic_id = Column(Integer, ForeignKey("subtopics.id", ondelete="CASCADE"),
                          nullable=False, unique=True)
    questions_json = Column(JSON, nullable=False)  # list[{question, options, correct_answer}]
    pass_threshold = Column(Float, nullable=False, default=70.0)

    subtopic = relationship("Subtopic", back_populates="quiz")


class ScheduleEvent(Base):
    __tablename__ = "schedule_events"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False)
    subtopic_id = Column(Integer, ForeignKey("subtopics.id", ondelete="CASCADE"), nullable=False)
    scheduled_date = Column(Date, nullable=False)
    status = Column(Enum(ScheduleStatus), nullable=False, default=ScheduleStatus.PENDING)

    plan = relationship("Plan", back_populates="schedule_events")
    subtopic = relationship("Subtopic", back_populates="schedule_events")

    __table_args__ = (
        UniqueConstraint("plan_id", "subtopic_id", name="uq_plan_subtopic_event"),
    )
