// ============================================================
// Adaptive Study Planner — frontend logic (vanilla JS, no build step)
// ============================================================

const state = {
  token: localStorage.getItem("asp_token") || null,
  userEmail: localStorage.getItem("asp_email") || null,
  authMode: "login",
  currentPlanId: null,
  currentQuiz: null,
  selectedAnswers: [],
  loadingTimer: null,
  syllabusExpanded: true,
};

const LOADING_STEPS = ["prep", "planner", "resources", "schedule"];
const LOADING_INTERVAL_MS = 8000;

// ---------- API helper ----------

async function api(path, { method = "GET", body, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth && state.token) headers["Authorization"] = `Bearer ${state.token}`;

  const res = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  let data = null;
  try { data = await res.json(); } catch (_) { /* no body */ }

  if (!res.ok) {
    const detail = (data && data.detail) ? data.detail : `Request failed (${res.status})`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

// ---------- Screen navigation ----------

function showScreen(name) {
  document.getElementById("screen-auth").classList.toggle("hidden", name !== "auth");
  document.getElementById("screen-dashboard").classList.toggle("hidden", name !== "dashboard");
  document.getElementById("screen-calendar").classList.toggle("hidden", name !== "calendar");

  document.getElementById("user-email-label").classList.toggle("hidden", name === "auth");
  document.getElementById("btn-logout").classList.toggle("hidden", name === "auth");
}

function setLoading(buttonEl, labelEl, isLoading, loadingText, normalText) {
  buttonEl.disabled = isLoading;
  labelEl.innerHTML = isLoading
    ? `<span class="spinner"></span> ${loadingText}`
    : normalText;
}

// ---------- Loading overlay ----------

function showLoadingOverlay() {
  const overlay = document.getElementById("loading-overlay");
  overlay.classList.remove("hidden");
  setLoadingStep(0);

  let stepIndex = 0;
  clearInterval(state.loadingTimer);
  state.loadingTimer = setInterval(() => {
    stepIndex = Math.min(stepIndex + 1, LOADING_STEPS.length - 1);
    setLoadingStep(stepIndex);
  }, LOADING_INTERVAL_MS);
}

function hideLoadingOverlay() {
  clearInterval(state.loadingTimer);
  state.loadingTimer = null;
  document.getElementById("loading-overlay").classList.add("hidden");
}

function setLoadingStep(index) {
  const items = document.querySelectorAll("#loading-steps li");
  items.forEach((el, i) => {
    el.classList.toggle("active", i === index);
    el.classList.toggle("done", i < index);
  });
}

// ---------- Auth ----------

document.getElementById("tab-login").addEventListener("click", () => setAuthMode("login"));
document.getElementById("tab-signup").addEventListener("click", () => setAuthMode("signup"));

function setAuthMode(mode) {
  state.authMode = mode;
  document.getElementById("tab-login").classList.toggle("active", mode === "login");
  document.getElementById("tab-signup").classList.toggle("active", mode === "signup");
  document.getElementById("auth-submit-label").textContent = mode === "login" ? "Log in" : "Create account";
}

document.getElementById("form-auth").addEventListener("submit", async (e) => {
  e.preventDefault();
  const email = document.getElementById("auth-email").value.trim();
  const password = document.getElementById("auth-password").value;
  const errorEl = document.getElementById("auth-error");
  const btn = document.getElementById("btn-auth-submit");
  const label = document.getElementById("auth-submit-label");
  errorEl.classList.add("hidden");

  const path = state.authMode === "login" ? "/auth/login" : "/auth/signup";
  const normalText = state.authMode === "login" ? "Log in" : "Create account";

  setLoading(btn, label, true, "Please wait…", normalText);
  try {
    const data = await api(path, { method: "POST", body: { email, password }, auth: false });
    state.token = data.access_token;
    state.userEmail = email;
    localStorage.setItem("asp_token", state.token);
    localStorage.setItem("asp_email", email);
    enterApp();
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.remove("hidden");
  } finally {
    setLoading(btn, label, false, "", normalText);
  }
});

document.getElementById("btn-logout").addEventListener("click", () => {
  state.token = null;
  state.userEmail = null;
  localStorage.removeItem("asp_token");
  localStorage.removeItem("asp_email");
  showScreen("auth");
});

function enterApp() {
  document.getElementById("user-email-label").textContent = state.userEmail;
  showScreen("dashboard");
  loadPlans();
}

// ---------- Plan creation ----------

const planContentEl = document.getElementById("plan-content");
const charCountEl = document.getElementById("content-char-count");

planContentEl.addEventListener("input", () => {
  const len = planContentEl.value.length;
  charCountEl.textContent = `${len.toLocaleString()} character${len === 1 ? "" : "s"}`;
});

document.getElementById("form-plan").addEventListener("submit", async (e) => {
  e.preventDefault();
  const title = document.getElementById("plan-title").value.trim();
  const content = planContentEl.value.trim();
  const hours_per_day = parseFloat(document.getElementById("plan-hours").value);
  const deadlineRaw = document.getElementById("plan-deadline").value;
  const errorEl = document.getElementById("plan-error");
  const btn = document.getElementById("btn-plan-submit");
  const label = document.getElementById("plan-submit-label");
  errorEl.classList.add("hidden");

  setLoading(btn, label, true, "Generating…", "Generate study calendar");
  showLoadingOverlay();

  try {
    const body = { title, content, hours_per_day };
    if (deadlineRaw) body.deadline = deadlineRaw;

    const result = await api("/plans", { method: "POST", body });
    document.getElementById("form-plan").reset();
    document.getElementById("plan-hours").value = "2";
    charCountEl.textContent = "0 characters";
    await loadPlans();
    openCalendar(result.plan_id);
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.remove("hidden");
  } finally {
    hideLoadingOverlay();
    setLoading(btn, label, false, "", "Generate study calendar");
  }
});

async function loadPlans() {
  const listEl = document.getElementById("plan-list");
  try {
    const plans = await api("/plans");
    if (!plans.length) {
      listEl.innerHTML = `<div class="empty-state">No plans yet — paste your notes above to generate your first personalized study calendar.</div>`;
      return;
    }
    listEl.innerHTML = plans.map((p) => `
      <div class="plan-list-item" data-plan-id="${p.id}">
        <div>
          <div class="plan-title">${escapeHtml(p.title)}</div>
          <div class="plan-meta">${p.hours_per_day}h/day${p.deadline ? " · due " + formatDate(p.deadline) : ""}</div>
        </div>
        <div class="plan-meta">${formatDate(p.created_at)}</div>
      </div>
    `).join("");

    listEl.querySelectorAll(".plan-list-item").forEach((el) => {
      el.addEventListener("click", () => openCalendar(parseInt(el.dataset.planId, 10)));
    });
  } catch (err) {
    listEl.innerHTML = `<div class="error-msg">${escapeHtml(err.message)}</div>`;
  }
}

// ---------- Calendar ----------

document.getElementById("btn-back-dashboard").addEventListener("click", () => {
  showScreen("dashboard");
  loadPlans();
});

document.getElementById("btn-toggle-syllabus").addEventListener("click", () => {
  state.syllabusExpanded = !state.syllabusExpanded;
  const overview = document.getElementById("syllabus-overview");
  overview.classList.toggle("hidden", !state.syllabusExpanded);
  document.getElementById("btn-toggle-syllabus").textContent = state.syllabusExpanded ? "Collapse" : "Expand";
});

async function openCalendar(planId) {
  state.currentPlanId = planId;
  showScreen("calendar");
  const ledgerEl = document.getElementById("ledger");
  ledgerEl.innerHTML = `<div class="empty-state">Loading your study plan…</div>`;

  try {
    const data = await api(`/plans/${planId}/calendar`);
    document.getElementById("calendar-plan-title").textContent = data.plan_title;

    const metaParts = [`${data.hours_per_day}h/day`];
    if (data.deadline) metaParts.push(`deadline ${formatDate(data.deadline)}`);
    if (data.stats) {
      metaParts.push(`${formatDuration(data.stats.total_minutes)} total study time`);
    }
    document.getElementById("calendar-meta").textContent = metaParts.join(" · ");

    renderStats(data.stats);
    renderSyllabus(data.topics || []);
    renderLedger(data.days);
  } catch (err) {
    ledgerEl.innerHTML = `<div class="error-msg">${escapeHtml(err.message)}</div>`;
  }
}

function renderStats(stats) {
  const el = document.getElementById("calendar-stats");
  if (!stats) {
    el.innerHTML = "";
    return;
  }
  el.innerHTML = `
    <div class="stat-card">
      <div class="stat-value">${stats.topic_count}</div>
      <div class="stat-label">Topics</div>
    </div>
    <div class="stat-card teal">
      <div class="stat-value">${stats.subtopic_count}</div>
      <div class="stat-label">Lessons</div>
    </div>
    <div class="stat-card purple">
      <div class="stat-value">${formatDuration(stats.total_minutes)}</div>
      <div class="stat-label">Study time</div>
    </div>
    <div class="stat-card green">
      <div class="stat-value">${stats.supplementary_count || 0}</div>
      <div class="stat-label">Web extras</div>
    </div>
  `;
}

function renderResourcesBlock(sub) {
  const parts = [];

  if (sub.youtube_url) {
    const ytLabel = sub.youtube_title
      ? escapeHtml(sub.youtube_title)
      : "Watch on YouTube";
    const channel = sub.youtube_channel
      ? `<span class="resource-meta">${escapeHtml(sub.youtube_channel)}</span>`
      : "";
    parts.push(`
      <div class="resource-item">
        <span class="resource-label">Video</span>
        <a class="link-video" href="${escapeAttr(sub.youtube_url)}" target="_blank" rel="noopener">▶ ${ytLabel}</a>
        ${channel}
      </div>
    `);
  }

  if (sub.blog_links && sub.blog_links.length) {
    const linksHtml = sub.blog_links.map((link) => `
      <a class="link-article" href="${escapeAttr(link.url)}" target="_blank" rel="noopener" title="${escapeAttr(link.title)}">
        ${escapeHtml(link.title.length > 60 ? link.title.slice(0, 57) + "…" : link.title)}
      </a>
    `).join("");
    parts.push(`
      <div class="resource-item">
        <span class="resource-label">Articles</span>
        <div class="resource-links">${linksHtml}</div>
      </div>
    `);
  }

  if (!parts.length) return "";
  return `<div class="learning-resources">${parts.join("")}</div>`;
}

function renderSyllabus(topics) {
  const el = document.getElementById("syllabus-overview");
  if (!topics.length) {
    el.innerHTML = `<div class="empty-state">No topics in this plan.</div>`;
    return;
  }

  el.innerHTML = topics.map((topic, tIdx) => {
    const totalMins = topic.subtopics.reduce((sum, s) => sum + s.est_minutes, 0);
    const subtopicsHtml = topic.subtopics.map((sub) => `
      <div class="syllabus-subtopic">
        <div class="syllabus-subtopic-title">
          ${escapeHtml(sub.title)}
          <span class="badge badge-time">${sub.est_minutes}m</span>
          ${sub.is_supplementary ? `<span class="badge badge-supplementary">Web research</span>` : ""}
        </div>
        ${sub.description ? `<p class="syllabus-subtopic-desc">${escapeHtml(sub.description)}</p>` : ""}
        ${sub.key_points && sub.key_points.length ? `
          <ul class="key-points">${sub.key_points.map((kp) => `<li>${escapeHtml(kp)}</li>`).join("")}</ul>
        ` : ""}
        ${sub.study_tip ? `<p class="study-tip">Tip: ${escapeHtml(sub.study_tip)}</p>` : ""}
        ${renderResourcesBlock(sub)}
      </div>
    `).join("");

    return `
      <div class="syllabus-topic open" data-topic-idx="${tIdx}">
        <div class="syllabus-topic-header" data-toggle-topic>
          <div>
            <h3>${escapeHtml(topic.title)}</h3>
            ${topic.summary ? `<p class="syllabus-topic-summary">${escapeHtml(topic.summary)}</p>` : ""}
          </div>
          <span class="syllabus-topic-meta">${topic.subtopics.length} lessons · ${formatDuration(totalMins)}</span>
        </div>
        <div class="syllabus-subtopics">${subtopicsHtml}</div>
      </div>
    `;
  }).join("");

  el.querySelectorAll("[data-toggle-topic]").forEach((header) => {
    header.addEventListener("click", () => {
      header.closest(".syllabus-topic").classList.toggle("open");
    });
  });

  el.classList.toggle("hidden", !state.syllabusExpanded);
}

function renderLedger(days) {
  const ledgerEl = document.getElementById("ledger");
  const dateKeys = Object.keys(days).sort();

  let totalEvents = 0;
  let doneEvents = 0;

  if (!dateKeys.length) {
    ledgerEl.innerHTML = `<div class="empty-state">No scheduled sessions found.</div>`;
    updateProgress(0, 0);
    return;
  }

  ledgerEl.innerHTML = dateKeys.map((dateKey) => {
    const events = days[dateKey];
    const dayTotal = events.reduce((sum, ev) => sum + ev.est_minutes, 0);
    const dateObj = new Date(dateKey + "T00:00:00");
    const dow = dateObj.toLocaleDateString(undefined, { weekday: "short" });
    const niceDate = dateObj.toLocaleDateString(undefined, { month: "short", day: "numeric" });

    const eventsHtml = events.map((ev) => {
      totalEvents++;
      if (ev.status === "DONE") doneEvents++;
      const isDone = ev.status === "DONE";
      return `
        <div class="ledger-event ${isDone ? "done" : ""} ${ev.is_supplementary ? "supplementary" : ""}">
          <div class="checkbox">${isDone ? "✓" : ""}</div>
          <div class="ledger-event-body">
            <div class="ledger-event-topic">${escapeHtml(ev.topic_title)}</div>
            <div class="ledger-event-title">
              ${escapeHtml(ev.subtopic_title)}
              ${ev.is_supplementary ? `<span class="badge badge-supplementary">Web extra</span>` : ""}
            </div>
            ${ev.description ? `<p class="ledger-event-desc">${escapeHtml(ev.description)}</p>` : ""}
            ${ev.key_points && ev.key_points.length ? `
              <ul class="key-points">${ev.key_points.slice(0, 4).map((kp) => `<li>${escapeHtml(kp)}</li>`).join("")}</ul>
            ` : ""}
            ${ev.study_tip ? `<p class="study-tip">Tip: ${escapeHtml(ev.study_tip)}</p>` : ""}
            ${renderResourcesBlock(ev)}
          </div>
          <div class="ledger-event-actions">
            <span class="est-pill">${ev.est_minutes}m</span>
            ${!isDone && ev.quiz_id ? `<button class="btn btn-sm" data-quiz-id="${ev.quiz_id}">Quiz</button>` : ""}
            ${isDone ? `<span class="mono text-dim" style="font-size:11px;">Complete</span>` : ""}
          </div>
        </div>
      `;
    }).join("");

    return `
      <div class="ledger-day">
        <div class="ledger-date">
          <span class="dow">${dow}</span>${niceDate}
          <div class="ledger-day-total">${formatDuration(dayTotal)}</div>
        </div>
        <div class="ledger-events">${eventsHtml}</div>
      </div>
    `;
  }).join("");

  updateProgress(doneEvents, totalEvents);

  ledgerEl.querySelectorAll("button[data-quiz-id]").forEach((btn) => {
    btn.addEventListener("click", () => openQuiz(parseInt(btn.dataset.quizId, 10)));
  });
}

function updateProgress(done, total) {
  const pct = total ? Math.round((done / total) * 100) : 0;
  document.getElementById("calendar-progress-label").textContent = `${done}/${total} complete (${pct}%)`;
  document.getElementById("calendar-progress-fill").style.width = `${pct}%`;
}

// ---------- Quiz modal ----------

const quizBackdrop = document.getElementById("quiz-modal-backdrop");
document.getElementById("btn-quiz-close").addEventListener("click", closeQuiz);
quizBackdrop.addEventListener("click", (e) => { if (e.target === quizBackdrop) closeQuiz(); });

function closeQuiz() {
  quizBackdrop.classList.add("hidden");
  state.currentQuiz = null;
  state.selectedAnswers = [];
}

async function openQuiz(quizId) {
  document.getElementById("quiz-title").textContent = "Loading…";
  document.getElementById("quiz-body").innerHTML = "";
  quizBackdrop.classList.remove("hidden");

  try {
    const quiz = await api(`/quizzes/${quizId}`);
    state.currentQuiz = quiz;
    state.selectedAnswers = new Array(quiz.questions.length).fill(null);
    document.getElementById("quiz-title").textContent = quiz.subtopic_title;
    renderQuizQuestions();
  } catch (err) {
    document.getElementById("quiz-title").textContent = "Error";
    document.getElementById("quiz-body").innerHTML = `<div class="error-msg">${escapeHtml(err.message)}</div>`;
  }
}

function renderQuizQuestions() {
  const quiz = state.currentQuiz;
  const bodyEl = document.getElementById("quiz-body");

  const questionsHtml = quiz.questions.map((q, qIdx) => `
    <div class="quiz-question">
      <div class="quiz-question-text">${qIdx + 1}. ${escapeHtml(q.question)}</div>
      ${q.options.map((opt, oIdx) => `
        <div class="quiz-option" data-q="${qIdx}" data-o="${oIdx}">${escapeHtml(opt)}</div>
      `).join("")}
    </div>
  `).join("");

  bodyEl.innerHTML = `
    ${questionsHtml}
    <button class="btn btn-lg" id="btn-quiz-submit" disabled>Submit answers</button>
    <div class="error-msg hidden" id="quiz-error"></div>
  `;

  bodyEl.querySelectorAll(".quiz-option").forEach((el) => {
    el.addEventListener("click", () => {
      const qIdx = parseInt(el.dataset.q, 10);
      const oIdx = parseInt(el.dataset.o, 10);
      state.selectedAnswers[qIdx] = oIdx;

      bodyEl.querySelectorAll(`.quiz-option[data-q="${qIdx}"]`).forEach((sib) => sib.classList.remove("selected"));
      el.classList.add("selected");

      const allAnswered = state.selectedAnswers.every((a) => a !== null);
      document.getElementById("btn-quiz-submit").disabled = !allAnswered;
    });
  });

  document.getElementById("btn-quiz-submit").addEventListener("click", submitQuiz);
}

async function submitQuiz() {
  const btn = document.getElementById("btn-quiz-submit");
  const errorEl = document.getElementById("quiz-error");
  btn.disabled = true;
  btn.textContent = "Scoring…";

  try {
    const result = await api(`/quizzes/${state.currentQuiz.quiz_id}/submit`, {
      method: "POST",
      body: { answers: state.selectedAnswers },
    });
    renderQuizResult(result);
    if (result.passed) {
      openCalendar(state.currentPlanId);
    }
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.remove("hidden");
    btn.disabled = false;
    btn.textContent = "Submit answers";
  }
}

function renderQuizResult(result) {
  const bodyEl = document.getElementById("quiz-body");
  bodyEl.innerHTML = `
    <div class="quiz-result ${result.passed ? "pass" : "fail"}">
      <div class="score">${result.score_percent}%</div>
      <div class="text-dim">${result.passed ? "Passed — session marked complete!" : "Not quite — review the material and try again."}</div>
      <button class="btn ${result.passed ? "" : "btn-ghost"}" style="margin-top:20px;" id="btn-quiz-done">Close</button>
    </div>
  `;
  document.getElementById("btn-quiz-done").addEventListener("click", closeQuiz);
}

// ---------- Utils ----------

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

function escapeAttr(str) {
  return (str ?? "").replace(/"/g, "&quot;");
}

function formatDate(value) {
  if (!value) return "";
  const d = new Date(typeof value === "string" && !value.includes("T") ? value + "T00:00:00" : value);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function formatDuration(minutes) {
  if (minutes < 60) return `${minutes}m`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m ? `${h}h ${m}m` : `${h}h`;
}

// ---------- Boot ----------

setAuthMode("login");
if (state.token) {
  enterApp();
} else {
  showScreen("auth");
}
