# Adaptive Study Planner

Paste study material in, get a scheduled, quizzed, day-by-day study calendar out.

4 agents (2 are plain Python, no LLM), 6 database tables, 6 API endpoints.

```
Ingestion (code) → Planner (LLM) → Resource+Quiz (LLM + YouTube API) → Scheduler (code)
```

## Project layout

```
adaptive-study-planner/
├── backend/            FastAPI + LangGraph + SQLAlchemy + Alembic
│   ├── app/
│   │   ├── agents/     the 4 pipeline agents + LangGraph wiring
│   │   ├── routers/    auth, plans, quizzes
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── auth.py
│   │   ├── database.py
│   │   └── config.py
│   ├── alembic/        migrations
│   ├── requirements.txt
│   ├── render.yaml      one-click Render deploy config
│   └── .env.example
└── frontend/            static HTML/CSS/JS, no build step
    ├── index.html
    ├── css/style.css
    └── js/{config.js, app.js}
```

## 1. Local setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows Git Bash: source venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env            # then fill in DATABASE_URL, GROQ_API_KEY, YOUTUBE_API_KEY
alembic upgrade head
uvicorn app.main:app --reload
```

API docs (Swagger UI) will be live at `http://127.0.0.1:8000/docs`.

### Frontend

No build step — it's plain HTML/CSS/JS. Just open `frontend/index.html` in a
browser, or serve it with any static server, e.g.:

```bash
cd frontend
python -m http.server 5500
```

Then visit `http://127.0.0.1:5500`. `frontend/js/config.js` already points at
`http://127.0.0.1:8000` for local dev.

## 2. Getting your (free) API keys

| Key | Where to get it |
|---|---|
| `DATABASE_URL` | [neon.tech](https://neon.tech) or [supabase.com](https://supabase.com) — free Postgres, copy the connection string |
| `GROQ_API_KEY` | [console.groq.com/keys](https://console.groq.com/keys) — free tier, used for `llama-3.3-70b-versatile` |
| `YOUTUBE_API_KEY` | [Google Cloud Console](https://console.cloud.google.com/apis/credentials) — enable "YouTube Data API v3", free daily quota |

The app runs without `YOUTUBE_API_KEY` (subtopics just won't get a video
link), but `GROQ_API_KEY` is required — the Planner and Quiz agents can't run
without it.

## 3. Free deployment

### Backend → Render

1. Push this repo to GitHub.
2. In [Render](https://render.com), "New +" → "Blueprint", point it at your repo.
   It will read `render.yaml` at the repo root (or `backend/render.yaml` if you set
   the service root directory to `backend`).
3. Fill in `DATABASE_URL`, `GROQ_API_KEY`, `YOUTUBE_API_KEY`, and `CORS_ORIGINS`
   in the Render dashboard (`CORS_ORIGINS` = your Vercel frontend URL, e.g.
   `https://your-app.vercel.app`).
4. Render uses **Python 3.12** (`backend/runtime.txt`) so dependencies install
   from pre-built wheels — do not remove `runtime.txt` or Render may default to
   Python 3.14 and fail building `pydantic-core`.
5. Render runs `pip install -r requirements.txt && alembic upgrade head` on
   every deploy, so migrations apply automatically.
6. Your API will be live at `https://<your-service-name>.onrender.com`.

Note: Render's free tier spins down after inactivity — the first request
after idling takes ~30-50s to wake up. That's expected, not a bug.

### Database → Neon or Supabase

Either works and both have generous free tiers. Neon is the simpler of the
two for a single Postgres database — create a project, copy the pooled
connection string (it includes `?sslmode=require`), paste it into
`DATABASE_URL`.

### Frontend → Vercel (recommended), Netlify, or any static host

No bundler — plain HTML/CSS/JS. For **Vercel**:

1. Import the repo in [Vercel](https://vercel.com) and set **Root Directory** to `frontend`.
2. Add environment variable `API_BASE_URL` = your Render backend URL
   (e.g. `https://adaptive-study-planner-api.onrender.com`, no trailing slash).
3. Deploy. Vercel runs `frontend/build.sh`, which writes `js/config.js` from that URL.
4. Set the same URL's frontend origin in Render as `CORS_ORIGINS`
   (e.g. `https://your-app.vercel.app`).

For other static hosts, edit `frontend/js/config.js` and set `API_BASE_URL` manually,
then publish the `frontend/` folder.

## 4. API reference

| Method | Path | Description |
|---|---|---|
| POST | `/auth/signup` | create account, returns JWT |
| POST | `/auth/login` | returns JWT |
| POST | `/plans` | runs the full 4-agent pipeline, persists everything, returns `plan_id` |
| GET | `/plans` | list the current user's plans |
| GET | `/plans/{id}/calendar` | day-by-day view: topic, video, quiz id, status |
| GET | `/quizzes/{id}` | fetch quiz questions (no answers) for the modal |
| POST | `/quizzes/{id}/submit` | scores answers; on pass, flips that day to `DONE` |

All routes except `/auth/*` require `Authorization: Bearer <token>`.

## 5. Design notes

- **Ingestion** and **Scheduler** are deliberately plain Python — deterministic,
  fast, free, and easy to debug. No LLM call in the critical path for these.
- **Planner** and **Resource+Quiz** are the only two LLM calls in the whole
  pipeline. `Planner` is where output quality matters most — a bad topic
  breakdown ruins everything downstream — so it gets a tightly-constrained
  JSON-only prompt.
- The calendar is **not** synced to any external calendar service on purpose,
  to avoid OAuth complexity. It's just rows in `schedule_events`, rendered by
  the frontend as a day-by-day ledger.
- Quiz grading is deterministic server-side code (compare selected index to
  `correct_answer`, compare against `pass_threshold`) — no LLM judgment call
  on "did they pass."
