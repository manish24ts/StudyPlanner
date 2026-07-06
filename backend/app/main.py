from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, plans, quizzes

app = FastAPI(
    title="Adaptive Study Planner API",
    description="Multi-agent RAG-lite study planner: paste content, get a scheduled, "
                "quizzed study calendar.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(plans.router)
app.include_router(quizzes.router)


@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "service": "adaptive-study-planner"}


@app.get("/health", tags=["health"])
def health():
    return {"status": "healthy"}
