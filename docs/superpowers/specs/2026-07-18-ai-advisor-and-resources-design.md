# Design: AI Assignment-Fit Advisor + Section Resources Card

**Date:** 2026-07-18
**Status:** Draft — awaiting approval

## Overview

Two features for Show of Hands:

1. **AI Assignment-Fit Advisor** — teachers get an AI read on whether a draft
   assignment matches where their class currently is, based on real grade data.
2. **Section Resources Card** — teachers post curated links per section;
   students (and admins) see them as clickable cards on the section page.

Decisions already made with the user:

- AI approach: **hybrid** — backend computes class stats deterministically,
  the model interprets them (no raw-data dumps, no hallucinated numbers).
- AI provider: **Google Gemini** (`gemini-2.5-flash` via the free AI Studio
  tier) — chosen for zero cost; the integration is provider-thin so it could
  be swapped later.
- Resources scope: **per-section**, visible to enrolled students + the teacher.
- Link preview: **teacher-written title/description + domain badge** (no
  server-side URL fetching in v1; schema leaves room for OpenGraph later).

---

## Feature 1: AI Assignment-Fit Advisor

### Endpoint

`POST /sections/{section_id}/assignment-fit` — teacher-only, must own the section.

Request body (the draft assignment, not yet saved):

```json
{
  "title": "Chapter 7 Quiz: Quadratic Equations",
  "description": "...",
  "category": "quizzes",
  "point_value": 20,
  "due_date": "2026-07-25T23:59:00Z"
}
```

### Class snapshot (computed in Python, not by the AI)

- Per-category class averages (homework / quizzes / tests) from graded submissions.
- Letter-grade distribution across enrolled students (reuses
  `compute_section_grade_for_student` in `grading.py`).
- The last ~10 graded assignments: title, category, class average, submission rate.
- Recent help-request topics with counts (the `topic` column on help_requests —
  a direct "class is struggling with X" signal).

### Gemini API call

- Official `google-genai` Python SDK, model `gemini-2.5-flash` — chosen because
  Google AI Studio provides a free-tier API key (daily request quotas, no cost),
  which fits this project's budget. The key is set as `GEMINI_API_KEY` in the
  backend environment and never reaches the browser.
- Structured output: the request sets `response_mime_type="application/json"`
  and a `response_schema` (Pydantic model), so the SDK returns validated JSON —
  no manual parsing of prose.
- System instruction frames the role: teaching assistant analyzing readiness;
  must ground every claim in the provided stats; resource suggestions are ideas
  the teacher should vet, not guaranteed-valid URLs.
- Free-tier rate limits are fine for this usage pattern (one request per
  button click); a 429 from quota exhaustion degrades the same way as any
  other API failure (stats-only response).

Response shape:

```json
{
  "readiness": "ready | review_first | mixed",
  "rationale": "2-4 sentence plain-language explanation",
  "topics_to_review": ["factoring", "graphing parabolas"],
  "suggested_resources": [
    {"title": "Khan Academy: Quadratics", "url": "https://...", "why": "..."}
  ]
}
```

The API response to the frontend includes both the AI verdict and the raw
computed stats, so the UI always shows real numbers.

### Frontend

- "Check fit" button inside the new-assignment form in
  `components/section-detail/AssignmentsPanel.jsx`.
- Result renders as an advisory panel: verdict badge, rationale, topics to
  review, suggested resources, and the stats used.
- Non-blocking: the teacher can create the assignment regardless of verdict.
- Each suggested resource gets a "post to section resources" shortcut that
  pre-fills the resources form (connects to Feature 2).

### Failure modes

- `GEMINI_API_KEY` not configured → 503 with a clear message; UI hides the
  button for the session.
- Gemini API error/timeout/quota (429) → respond with computed stats only and
  an "AI analysis unavailable" note; stats alone are still useful.
- Section has no graded submissions yet → skip the API call, return
  "not enough data" with whatever stats exist.
- Tests mock the Gemini client; no real API calls in CI.

---

## Feature 2: Section Resources Card

### Data model

New `resources` table (SQLAlchemy model + Alembic migration):

| column        | type      | notes                          |
|---------------|-----------|--------------------------------|
| resource_id   | int PK    |                                |
| section_id    | FK        | sections.section_id            |
| teacher_id    | FK        | users.user_id (poster)         |
| title         | string    | required, teacher-written      |
| url           | string    | required, must be http/https   |
| description   | text      | optional, teacher-written      |
| created_at    | datetime  |                                |
| updated_at    | datetime  |                                |
| deleted_at    | datetime  | soft delete, null = active     |

(An `image_url` column can be added later for OG previews — not in v1.)

### Endpoints

- `GET /sections/{id}/resources` — enrolled students, the section's teacher, admins.
- `POST /sections/{id}/resources` — section's teacher only.
- `PATCH /resources/{id}` / `DELETE /resources/{id}` — posting teacher only.
- URL validation: http/https scheme required.

### Frontend

- **Students** (`SectionDetail.jsx` student view): a "resources" card listing
  title, description, and a domain badge (e.g. `khanacademy.org`); the whole
  row is a link opening in a new tab with `rel="noopener noreferrer"`.
- **Teachers** (`TeacherSectionDetail`): a `ResourcesPanel` following the
  existing panel pattern (like `QuestsPanel`) with add/edit/delete.
- **Admins**: read-only resources card on their section view.

### Testing

- pytest: CRUD, permission matrix (student can't post, other teacher can't
  edit, admin can read), URL validation, soft delete.
- Frontend: ESLint + production build.

---

## Out of scope for v1

- Automatic OpenGraph link previews (fetch + parse).
- Per-topic tagging of assignments (AI infers topics from titles/descriptions).
- Caching/rate-limiting of AI checks beyond one-click-per-request.
