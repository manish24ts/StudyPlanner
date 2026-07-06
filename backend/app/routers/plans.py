from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user
from app.agents.graph import run_pipeline

router = APIRouter(prefix="/plans", tags=["plans"])


def _blog_links_out(links) -> list[schemas.BlogLinkOut]:
    if not links:
        return []
    return [
        schemas.BlogLinkOut(title=link.get("title", "Article"), url=link["url"])
        for link in links
        if link.get("url")
    ]


def _subtopic_out(sub: models.Subtopic) -> schemas.SubtopicOut:
    return schemas.SubtopicOut(
        id=sub.id,
        title=sub.title,
        description=sub.description,
        key_points=sub.key_points or [],
        study_tip=sub.study_tip,
        is_supplementary=bool(sub.is_supplementary),
        est_minutes=sub.est_minutes,
        youtube_url=sub.youtube_url,
        youtube_title=sub.youtube_title,
        youtube_channel=sub.youtube_channel,
        blog_links=_blog_links_out(sub.blog_links),
        quiz_id=sub.quiz.id if sub.quiz else None,
    )


def _topic_out(topic: models.Topic) -> schemas.TopicOut:
    return schemas.TopicOut(
        id=topic.id,
        title=topic.title,
        summary=topic.summary,
        subtopics=[_subtopic_out(s) for s in topic.subtopics],
    )


@router.post("", response_model=schemas.PlanCreateResponse)
def create_plan(
    payload: schemas.PlanCreateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    try:
        result = run_pipeline(
            raw_text=payload.content,
            hours_per_day=payload.hours_per_day,
            deadline=payload.deadline,
            plan_title=payload.title,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Pipeline failed: {e}")

    plan = models.Plan(
        user_id=current_user.id,
        title=payload.title,
        deadline=payload.deadline,
        hours_per_day=payload.hours_per_day,
    )
    db.add(plan)
    db.flush()

    subtopic_lookup: dict[tuple[int, int], models.Subtopic] = {}

    for t_idx, topic_data in enumerate(result["enriched_topics"]):
        topic = models.Topic(
            plan_id=plan.id,
            title=topic_data["title"],
            summary=topic_data.get("summary"),
            order_index=t_idx,
        )
        db.add(topic)
        db.flush()

        for s_idx, sub_data in enumerate(topic_data["subtopics"]):
            subtopic = models.Subtopic(
                topic_id=topic.id,
                title=sub_data["title"],
                description=sub_data.get("description"),
                key_points=sub_data.get("key_points") or [],
                study_tip=sub_data.get("study_tip"),
                is_supplementary=bool(sub_data.get("is_supplementary", False)),
                est_minutes=sub_data["est_minutes"],
                youtube_url=sub_data.get("youtube_url"),
                youtube_title=sub_data.get("youtube_title"),
                youtube_channel=sub_data.get("youtube_channel"),
                blog_links=sub_data.get("blog_links") or [],
                order_index=s_idx,
            )
            db.add(subtopic)
            db.flush()

            quiz = models.Quiz(
                subtopic_id=subtopic.id,
                questions_json=sub_data["questions"],
                pass_threshold=70.0,
            )
            db.add(quiz)

            subtopic_lookup[(t_idx, s_idx)] = subtopic

    for entry in result["schedule"]:
        t_idx, s_idx = entry["subtopic_id"]
        subtopic = subtopic_lookup[(t_idx, s_idx)]
        event = models.ScheduleEvent(
            plan_id=plan.id,
            subtopic_id=subtopic.id,
            scheduled_date=entry["scheduled_date"],
            status=models.ScheduleStatus.PENDING,
        )
        db.add(event)

    db.commit()
    db.refresh(plan)

    plan = (
        db.query(models.Plan)
        .options(joinedload(models.Plan.topics).joinedload(models.Topic.subtopics)
                 .joinedload(models.Subtopic.quiz))
        .filter(models.Plan.id == plan.id)
        .first()
    )

    topics_out = [_topic_out(t) for t in plan.topics]

    return schemas.PlanCreateResponse(plan_id=plan.id, title=plan.title, topics=topics_out)


@router.get("", response_model=list[schemas.PlanOut])
def list_plans(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    plans = (
        db.query(models.Plan)
        .filter(models.Plan.user_id == current_user.id)
        .order_by(models.Plan.created_at.desc())
        .all()
    )
    return plans


@router.get("/{plan_id}/calendar", response_model=schemas.CalendarResponse)
def get_calendar(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    plan = (
        db.query(models.Plan)
        .options(
            joinedload(models.Plan.topics).joinedload(models.Topic.subtopics)
            .joinedload(models.Subtopic.quiz)
        )
        .filter(models.Plan.id == plan_id, models.Plan.user_id == current_user.id)
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    events = (
        db.query(models.ScheduleEvent)
        .options(
            joinedload(models.ScheduleEvent.subtopic).joinedload(models.Subtopic.topic),
            joinedload(models.ScheduleEvent.subtopic).joinedload(models.Subtopic.quiz),
        )
        .filter(models.ScheduleEvent.plan_id == plan_id)
        .order_by(models.ScheduleEvent.scheduled_date)
        .all()
    )

    days: dict[str, list[schemas.CalendarEventOut]] = defaultdict(list)
    total_minutes = 0
    supplementary_count = 0
    subtopic_count = 0

    for topic in plan.topics:
        for sub in topic.subtopics:
            subtopic_count += 1
            total_minutes += sub.est_minutes
            if sub.is_supplementary:
                supplementary_count += 1

    for event in events:
        sub = event.subtopic
        days[event.scheduled_date.isoformat()].append(
            schemas.CalendarEventOut(
                event_id=event.id,
                scheduled_date=event.scheduled_date,
                status=event.status.value,
                topic_title=sub.topic.title,
                subtopic_id=sub.id,
                subtopic_title=sub.title,
                description=sub.description,
                key_points=sub.key_points or [],
                study_tip=sub.study_tip,
                is_supplementary=bool(sub.is_supplementary),
                est_minutes=sub.est_minutes,
                youtube_url=sub.youtube_url,
                youtube_title=sub.youtube_title,
                youtube_channel=sub.youtube_channel,
                blog_links=_blog_links_out(sub.blog_links),
                quiz_id=sub.quiz.id if sub.quiz else None,
            )
        )

    stats = schemas.PlanStatsOut(
        topic_count=len(plan.topics),
        subtopic_count=subtopic_count,
        total_minutes=total_minutes,
        supplementary_count=supplementary_count,
        days_scheduled=len(days),
    )

    return schemas.CalendarResponse(
        plan_id=plan.id,
        plan_title=plan.title,
        hours_per_day=plan.hours_per_day,
        deadline=plan.deadline,
        stats=stats,
        topics=[_topic_out(t) for t in plan.topics],
        days=dict(days),
    )
