# Show of Hands ✋

## Project Description: Show of Hands ✋

Show of Hands aims to bridge the gap between learning and school communities. Its primary goal is to make learning fun while also rewarding students for engaging with others and building lasting relationships with each other. With the social aspects, students will get rewarded for not only helping other students that might be falling behind, but even students who need help will get rewarded for going to their fellow classmates for help instead of the internet or AI. With the learning aspects, teachers will be able to see exactly where most students are experiencing difficulties, and can update the curriculum or add **personalized quests** for students to practice more on topics that might be difficult to grasp.

## What is a Quest?

Non academic tasks/deliverables that encourage students to practice with each other, have fun, help others who may not understand course content, and/or have learning experiences outside of the classroom.

Examples:

* Find a study group and schedule a meeting  
* Go to library  
* Read a book for 1 hour  
* Take a picture, write a short summary about what you find most interesting

## Technology Stack

### Frontend

* **React 19 + Vite 8** — component UI and dev server/bundler. Chosen for fast HMR and a large ecosystem; alternatives considered: Next.js (unneeded for a pure SPA with no SSR/SEO requirement) or Vue.
* **react-router-dom 7** — client-side routing for the SPA. Alternative: TanStack Router.
* **TanStack Query 5** — the app's server-state/cache layer (queries, mutations, cache invalidation) rather than a general client-state store. Paired with a custom `RealtimeProvider` that listens on a notifications WebSocket and invalidates matching query keys as events arrive, with a 7-minute background refetch as a rare fallback for missed events (`queryClient.js`) — a push-driven model instead of polling. Alternatives: Redux/Zustand/MobX (would require hand-building the caching/dedup/refetch logic TanStack Query already provides) or SWR.
* **axios** — HTTP client for REST calls. Alternative: the native `fetch` API.
* **Plain CSS per component** (no CSS framework) — one `.css` file per component, no Tailwind/CSS Modules/styled-components. Keeps styling dependency-free at the cost of manual scoping discipline; alternative: Tailwind CSS for utility-first styling and smaller bespoke stylesheets.
* **@daily-co/daily-js** — embeds Daily.co's video/voice call UI into study rooms.
* **jsPDF** — generates report-card PDFs client-side, avoiding a server-side PDF rendering dependency.

### Backend

* **FastAPI + Uvicorn** — the API framework and ASGI server. Chosen for native async support (needed for the WebSocket chat/notification streams) and automatic request validation via Pydantic. Alternatives: Django (heavier, batteries-included but less natural for a WebSocket-heavy API) or Flask (would need separate async/WebSocket tooling).
* **Pydantic + pydantic-settings** — request/response schema validation and typed environment config.
* **SQLAlchemy + Alembic** — ORM and schema migrations. Alternatives: Django ORM (tied to Django) or Prisma (less mature Python support).
* **psycopg2-binary** — PostgreSQL driver underneath SQLAlchemy.
* **python-jose + passlib/bcrypt** — hand-rolled JWT auth (access + refresh tokens, hashed refresh-token storage, single-use rotation) rather than a managed auth provider. Alternatives: Auth0, Clerk, or Supabase Auth — any of which would offload token management but add an external dependency and cost for what is currently a small, self-contained auth flow.
* **APScheduler** — runs in-process background jobs (e.g. the stale-grade reminder check in `main.py`) without standing up a separate task queue.
* **httpx** — used for hand-rolled wrapper calls to the Gemini and Daily.co REST APIs (`gemini_advisor.py`, `daily_client.py`) instead of their official SDKs, each behind an `is_configured()` check so those features degrade gracefully when a key isn't set — a Gemini or Daily outage never blocks the chat/room's core functionality.
* **Pillow** — re-encodes and validates uploaded avatar images server-side so a malicious file can't be smuggled past the extension/content-type check.

### Database & Realtime

* **PostgreSQL, hosted on Supabase** — used purely as a managed Postgres instance plus a Storage bucket for avatars; Supabase Auth/RLS/Realtime are intentionally not used. The connection pooling is split across two Supavisor modes for the same reason: a permanent session-mode connection (port 5432) is reserved solely for `LISTEN/NOTIFY`, while the app's SQLAlchemy engine uses a small transaction-mode pool (port 6543, `pool_size=5, max_overflow=3`) — Supabase's free tier caps session-mode connections at 15 shared across every developer, so ordinary dev/test traffic on session mode alone was exhausting it (`db/pool.py`).
* **Homegrown realtime layer** — Postgres `LISTEN/NOTIFY` bridged into asyncio queues and fanned out over WebSockets (chat, notifications), rather than a separate broker. Alternatives: Redis pub/sub, Supabase Realtime, or a hosted service like Pusher/Ably — any of which would add infrastructure this single small Postgres instance doesn't otherwise need.

### Third-Party APIs

* **Google Gemini (`gemini-3.1-flash-lite`)** — powers an "assignment-fit" advisor that judges whether a class is ready for a draft assignment against real grade/help-request data, with explicit prompt-injection defenses around teacher-authored free text.
* **Daily.co** — provisions private, token-gated, auto-expiring video/voice rooms for study sessions.
* **Supabase Storage** — hosts uploaded avatar images.

### Hosting & Deployment

* **Render** (backend, free tier) — alternatives: Railway, Fly.io.
* **Vercel** (frontend, static SPA) — alternatives: Netlify, Cloudflare Pages.
* No Docker/containerization and no CI/CD (no GitHub Actions or equivalent) are currently configured — tests and linting run locally/manually only.

### Testing

* **pytest + pytest-asyncio** — backend test suite (30+ files covering nearly every controller). The frontend has no test framework configured yet (no Jest/Vitest/Playwright/Testing Library).

## Getting Started

**Prerequisites:** Python 3.9+, Node 18+, and a Supabase Postgres project (or any Postgres instance).

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL, JWT_SECRET, SUPABASE_URL/KEY;
                        # GEMINI_API_KEY and DAILY_API_KEY are optional —
                        # those features degrade gracefully without them
alembic upgrade head    # run DB migrations
uvicorn main:app --reload
```

Setting `ENV=development` in `.env` also auto-seeds a demo school, roster, and quest set on startup (`db/seed.py`) — handy for local frontend development without creating data by hand.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_BASE_URL, defaults to http://127.0.0.1:8000/api
npm run dev
```

### Running Tests

```bash
cd backend
pytest
```

See [Hosting & Deployment](#hosting--deployment) above for how the backend/frontend are actually deployed (Render/Vercel).

## User Personas/Audience

**The Problem**  
Modern high school and higher education has drifted toward standardized testing and rigid, one-size-fits-all instruction. This creates a few compounding issues:

* Students memorize for tests rather than build genuine understanding.  
* Individual learning styles are ignored, so students who don't fit the "standard" pace fall behind or disengage.  
* Social connection between students has eroded, especially with the rise of virtual/hybrid learning. Kids increasingly turn to the internet or AI tools for help instead of each other.  
* Teachers lack real-time visibility into *where* students are struggling until it shows up on a graded assignment or test, by which point the gap has already widened.  
* Learning is often confined to the classroom, with little room for real-world application or self-directed exploration.

**Our Position**

**Show of Hands** takes the position that **learning improves when it's social, gamified, and data-informed** rather than isolated and test-driven. Specifically, the platform argues:

* Peer-to-peer help should be incentivized and rewarded, repositioning classmates (not search engines or AI) as the first line of academic support.  
* Gamification (points, quests, streaks) can make engagement with coursework and community feel rewarding rather than obligatory.  
* Teachers should have a live, structured feed of where students are struggling — via submissions, quest performance, and help-request activity — so curriculum and personalized quests can respond to real gaps instead of after-the-fact test results.  
* Autonomy matters: students should have some say in how they engage (which quests to pursue, when to seek help, who to help), rather than being pushed through a fixed track.

**The Impact**

* **For students:** a built-in incentive to ask for help and to give it — reducing the isolation of struggling silently and reducing overreliance on AI/internet shortcuts for problems a classmate could walk them through. Points and quests reward curiosity and collaboration, not just grades.  
* **For teachers:** a live dashboard of where a section is collectively struggling (via submission grades, help-request topics, quest completion patterns), enabling faster curriculum adjustments and targeted, personalized quests instead of one-size-fits-all reteaching.  
* **For school culture:** a nudge back toward relationship-building and community within the student body — even in a virtual/hybrid setting — by making peer collaboration a rewarded, visible, everyday behavior rather than an optional extra.

---

### **User Personas**

#### **1\. Maya Chen — The Disengaged-but-Capable Student**

* **Age/Grade:** 15, 10th grade  
* **Role:** Student  
* **Background:** Maya is bright but bored. She does fine on tests through last-minute cramming but doesn't feel like she *understands* half of what she's tested on. She's constantly on her phone during class, and when she gets stuck on homework, she defaults to searching the answer online rather than asking a classmate. For her, it feels faster and less embarrassing.  
* **Goals:** Wants school to feel less like a chore and more like something she's actually invested in. Wants recognition for effort, not just grades.  
* **Frustrations:** Standardized pacing that doesn't match how she learns; feels anonymous in a large class; doesn't see the point of "office hours" since no one goes.  
* **How Show of Hands helps:** The bulletin board keeps a help request's poster hidden from other students until someone actually joins it, so she can post without the social risk of asking in class out loud — and can't be cherry-picked or avoided by classmates who'd recognize her name. Quests and points make small wins visible and rewarding, giving her a reason to engage.

#### **2\. Jordan Reyes — The Quiet Struggler**

* **Age/Grade:** 18, college freshman  
* **Role:** Student  
* **Background:** Jordan is falling behind in his intro math course but is too self-conscious to raise his hand or admit confusion in a 200-person lecture hall. He doesn't reach out to classmates because he doesn't want to seem "behind," and he doesn't know anyone in the class yet. Online/hybrid sections make it worse, with no opportunity for hallway conversations. No casual "Hey, did you get \#7 on the problem set?"  
* **Goals:** Wants to catch up without feeling singled out. Wants low-stakes ways to get help.  
* **Frustrations:** Fear of judgment from peers; teachers can't always tell he's struggling until a bad grade shows up.  
* **How Show of Hands helps:** Help requests hide the requester's identity from other students until a classmate joins, which removes the social risk of asking and — just as importantly — forces students into a random classmate's study room instead of always defaulting to their existing friend group. Being rewarded (points) for reaching out reframes asking for help as a positive, active behavior rather than an admission of weakness. Teacher-side visibility into help-request topics also flags struggling areas before a graded assignment does.

#### **3\. Ms. Patel — The Overloaded, Data-Hungry Teacher**

* **Age/Role:** 34, high school science teacher, 5 sections a day  
* **Background:** Ms. Patel wants to personalize instruction but has 150+ students and no efficient way to know who's actually confused versus who's just quiet. She relies on test scores and the occasional student who speaks up, which she knows is an incomplete picture. She'd love to assign targeted extra practice but doesn't have time to build it per-student manually.  
* **Goals:** Wants a clear, real-time signal of where her sections are struggling as a whole and individually. Wants to reward students who help each other, since it lightens her own support load.  
* **Frustrations:** Grading and administrative overhead leave little time to personalize; struggles are often invisible until it's "too late" (i.e., a bad test).  
* **How Show of Hands helps:** She can see which topics generate the most help requests and submission struggles across a section, then assign personalized or section-wide quests to reinforce those areas. Notifications keep her looped in without requiring her to manually check in on every student. The gamified peer-help system also offloads some support burden onto capable peers, rewarding students like Maya for stepping in.

## User Stories

**MVP (Without these features, the application will not be useful)**

1. As a teacher, I can assign “quests” for students to complete (Quests can be academic or non academic). I can set “quest” difficulty, topic, completion conditions, duration, and points gained. I am able to check if a student met the completion requirements and approve point gains.  
2. As a student, I can send out an anonymous “party request” (anonymous to ensure the same people are not teaming up all the time — the requester's identity is hidden from other students until one of them joins) for help or study time for a particular class or topic. I can specify my desired group size and session duration; the requester can extend the duration once the session starts, and group members can decide whether to stay or leave. **[Built]** — implemented as help requests + study rooms, including live text chat and a Daily.co video/voice call in the room.  
3. As a student, I can complete quests (teacher assigned or default) individually to gain “XP points/currency”. **[Built, single-student only]** — the original vision below describes teaming up with classmates on a quest ("form a party of 4"); that group-completion mechanic isn't implemented. Quest completion today is one student, one quest, one completion record.  
   (Original vision, not yet built: Form a party of 4, go to the library, check out a book, and read for 1 hour. Take a picture with your party at the library and write a short summary of what you found most interesting.)

**Stretch Features (When time is running short, these features will get cut)**

1. As a student, I can “challenge a friend” and compete to see how quickly and accurately we can complete tests/quizzes based on learning  
2. As a User, I can join an “Accountability Party” which is a party of people who consistently holds each other accountable in submitting assignments and completing quests

---

## **Feedback:**

* Make a matchmaking limiter: If a user matches up too many times with the same person, force them to choose someone else.  
* How would you stop students from faking tasks? \- We considered using location services to ensure that students are where they say they are.  
* Scale down the application for proof of concept 

- [ ] ## Reviewed by Instructor

---

# Part II — Technical Specifications

## Schema Design

Document the tables required for your project. For each table, include the name of the table, the field names, and any relevant constraints. Below is an example of a simple todo application's schema.

**Schools** (`schools`)

| Column | Type | Constraints |
| :---- | :---- | :---- |
| school_id | INTEGER | PK |
| name | VARCHAR | UNIQUE, NOT NULL |
| school_code | VARCHAR | UNIQUE, NOT NULL |
| district | VARCHAR | NULL |
| grades | VARCHAR | NULL |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

**Users** (`users`)

| Column | Type | Constraints |
| :---- | :---- | :---- |
| user_id | INTEGER | PK |
| school_id | INTEGER | FK → schools.school_id, NOT NULL |
| username | VARCHAR | NOT NULL |
| full_name | VARCHAR | NOT NULL |
| profile_picture_url | VARCHAR | NULL |
| password_hash | VARCHAR | NOT NULL |
| email | VARCHAR | NULL |
| role | ENUM(student, teacher, admin) | NOT NULL |
| is_verified | BOOLEAN | NOT NULL, DEFAULT false |
| is_active | BOOLEAN | NOT NULL, DEFAULT true |
| rejection_reason | TEXT | NULL |
| last_active_at | TIMESTAMPTZ | NULL |
| signup_note | TEXT | NULL |
| total_points | INTEGER | NOT NULL, DEFAULT 0 |
| featured_badge_item_id | INTEGER | FK → shop_items.item_id, ON DELETE SET NULL, NULL |
| is_archived | BOOLEAN | NOT NULL, DEFAULT false |
| deleted_at | TIMESTAMPTZ | NULL |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now(), ON UPDATE now() |

**Classes** (`classes`) — a global catalog of class names, not school-scoped

| Column | Type | Constraints |
| :---- | :---- | :---- |
| class_id | INTEGER | PK |
| name | VARCHAR | UNIQUE, NOT NULL |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

**Class Requests** (`class_requests`) — a teacher's request to add a new class to the catalog

| Column | Type | Constraints |
| :---- | :---- | :---- |
| class_request_id | INTEGER | PK |
| class_name | VARCHAR | NOT NULL |
| subject | VARCHAR | NULL |
| description | TEXT | NULL |
| requested_by | INTEGER | FK → users.user_id, NOT NULL |
| school_id | INTEGER | FK → schools.school_id, NOT NULL |
| status | ENUM(pending, approved, rejected) | NOT NULL, DEFAULT pending |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

**Sections** (`sections`) — one teacher's roster for one class/period

| Column | Type | Constraints |
| :---- | :---- | :---- |
| section_id | INTEGER | PK |
| class_id | INTEGER | FK → classes.class_id, NOT NULL |
| school_id | INTEGER | FK → schools.school_id, NOT NULL |
| teacher_id | INTEGER | FK → users.user_id, ON DELETE SET NULL, NULL |
| period | VARCHAR | NOT NULL |
| capacity | INTEGER | NOT NULL |
| status | ENUM(active, archived, pending_reassignment) | NOT NULL, DEFAULT active |
| is_archived | BOOLEAN | NOT NULL, DEFAULT false |
| deleted_at | TIMESTAMPTZ | NULL |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now(), ON UPDATE now() |

**Enrollments** (`enrollments`) — a student's confirmed seat in a section

| Column | Type | Constraints |
| :---- | :---- | :---- |
| enrollment_id | INTEGER | PK |
| section_id | INTEGER | FK → sections.section_id, ON DELETE CASCADE, NOT NULL |
| student_id | INTEGER | FK → users.user_id, ON DELETE CASCADE, NOT NULL |
| is_archived | BOOLEAN | NOT NULL, DEFAULT false |
| deleted_at | TIMESTAMPTZ | NULL |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

UNIQUE (section_id, student_id)

**Enrollment Requests** (`enrollment_requests`) — a student's pending ask to join a section

| Column | Type | Constraints |
| :---- | :---- | :---- |
| enrollment_request_id | INTEGER | PK |
| section_id | INTEGER | FK → sections.section_id, ON DELETE CASCADE, NOT NULL |
| student_id | INTEGER | FK → users.user_id, ON DELETE CASCADE, NOT NULL |
| status | ENUM(pending, accepted, rejected, archived) | NOT NULL, DEFAULT pending |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now(), ON UPDATE now() |

UNIQUE (section_id, student_id)

**Unenroll Requests** (`unenroll_requests`) — a teacher's request to remove a student from their section, subject to admin approval

| Column | Type | Constraints |
| :---- | :---- | :---- |
| unenroll_request_id | INTEGER | PK |
| section_id | INTEGER | FK → sections.section_id, ON DELETE CASCADE, NOT NULL |
| student_id | INTEGER | FK → users.user_id, ON DELETE CASCADE, NOT NULL |
| requested_by | INTEGER | FK → users.user_id, NOT NULL |
| reason | TEXT | NOT NULL |
| status | ENUM(pending, approved, rejected, cancelled) | NOT NULL, DEFAULT pending |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now(), ON UPDATE now() |

**Assignments** (`assignments`)

| Column | Type | Constraints |
| :---- | :---- | :---- |
| assignment_id | INTEGER | PK |
| section_id | INTEGER | FK → sections.section_id, NOT NULL |
| title | VARCHAR | NOT NULL |
| description | TEXT | NULL |
| url | VARCHAR | NULL |
| due_date | TIMESTAMPTZ | NOT NULL |
| point_value | INTEGER | NOT NULL |
| category | ENUM(homework, quizzes, tests) | NOT NULL, DEFAULT homework |
| is_archived | BOOLEAN | NOT NULL, DEFAULT false |
| deleted_at | TIMESTAMPTZ | NULL |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now(), ON UPDATE now() |

**Submissions** (`submissions`) — a student's turned-in work for an assignment

| Column | Type | Constraints |
| :---- | :---- | :---- |
| submission_id | INTEGER | PK |
| assignment_id | INTEGER | FK → assignments.assignment_id, NOT NULL |
| student_id | INTEGER | FK → users.user_id, NOT NULL |
| content | TEXT | NULL |
| file_url | VARCHAR | NULL |
| status | ENUM(submitted, pending, graded) | NOT NULL, DEFAULT submitted |
| grade | FLOAT | NULL |
| points_awarded | INTEGER | NOT NULL, DEFAULT 0 |
| finalized_at | TIMESTAMPTZ | NULL |
| reminder_sent_at | TIMESTAMPTZ | NULL |
| is_archived | BOOLEAN | NOT NULL, DEFAULT false |
| deleted_at | TIMESTAMPTZ | NULL |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now(), ON UPDATE now() |

UNIQUE (assignment_id, student_id)

**Quests** (`quests`)

| Column | Type | Constraints |
| :---- | :---- | :---- |
| quest_id | INTEGER | PK |
| section_id | INTEGER | FK → sections.section_id, NOT NULL |
| title | VARCHAR | NOT NULL |
| description | TEXT | NOT NULL |
| category | ENUM(academic, social) | NOT NULL |
| point_value | INTEGER | NOT NULL |
| quest_type | ENUM(daily, weekly, monthly) | NOT NULL |
| source | ENUM(teacher, system) | NOT NULL |
| assigned_to | INTEGER | FK → users.user_id, NULL |
| is_archived | BOOLEAN | NOT NULL, DEFAULT false |
| deleted_at | TIMESTAMPTZ | NULL |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now(), ON UPDATE now() |

**Quest Completions** (`quest_completions`) — single-student only; there is no group/party completion mechanic (see [User Stories](#user-stories))

| Column | Type | Constraints |
| :---- | :---- | :---- |
| quest_completion_id | INTEGER | PK |
| quest_id | INTEGER | FK → quests.quest_id, NOT NULL |
| student_id | INTEGER | FK → users.user_id, NOT NULL |
| points_awarded | INTEGER | NOT NULL |
| description | TEXT | NULL |
| file_url | VARCHAR | NULL |
| completed_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

UNIQUE (quest_id, student_id)

**Point Transactions** (`point_transactions`) — ledger of every point award/spend, keyed to its originating source

| Column | Type | Constraints |
| :---- | :---- | :---- |
| transaction_id | INTEGER | PK |
| user_id | INTEGER | FK → users.user_id, NOT NULL |
| amount | INTEGER | NOT NULL |
| source | ENUM(assignment, quest, help_request, shop_purchase) | NOT NULL |
| source_id | INTEGER | NOT NULL |
| awarded_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

UNIQUE (user_id, source, source_id) — the idempotency guard that prevents double-awarding points for the same event

**Help Requests** (`help_requests`)

| Column | Type | Constraints |
| :---- | :---- | :---- |
| help_request_id | INTEGER | PK |
| section_id | INTEGER | FK → sections.section_id, NOT NULL |
| requester_id | INTEGER | FK → users.user_id, NOT NULL |
| topic | VARCHAR | NOT NULL |
| description | TEXT | NULL |
| group_size | INTEGER | NOT NULL |
| current_size | INTEGER | NOT NULL, DEFAULT 1 |
| duration_minutes | INTEGER | NOT NULL |
| status | ENUM(open, active, closed, expired) | NOT NULL, DEFAULT open |
| is_archived | BOOLEAN | NOT NULL, DEFAULT false |
| deleted_at | TIMESTAMPTZ | NULL |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now(), ON UPDATE now() |

> **Note:** `requester_id`/`requester_username` are only ever returned to teachers/admins, or to students in the room after they've joined via `room_members` — never in the student-facing bulletin-board listing. This is what makes a help request "anonymous until joined."

**Help Request Acceptances** (`help_request_acceptances`) — who joined which help request, and when

| Column | Type | Constraints |
| :---- | :---- | :---- |
| help_request_id | INTEGER | PK (composite), FK → help_requests.help_request_id |
| user_id | INTEGER | PK (composite), FK → users.user_id |
| accepted_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

**Study Rooms** (`study_rooms`)

| Column | Type | Constraints |
| :---- | :---- | :---- |
| room_id | INTEGER | PK |
| help_request_id | INTEGER | FK → help_requests.help_request_id, UNIQUE, NOT NULL |
| timer_ends_at | TIMESTAMPTZ | NOT NULL |
| status | ENUM(active, closed) | NOT NULL, DEFAULT active |
| daily_room_name | VARCHAR | NULL |
| daily_room_url | VARCHAR | NULL |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

**Room Members** (`room_members`) — who is currently in a study room; this is where a joined student first sees the requester's identity

| Column | Type | Constraints |
| :---- | :---- | :---- |
| room_id | INTEGER | PK (composite), FK → study_rooms.room_id |
| user_id | INTEGER | PK (composite), FK → users.user_id |
| joined_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

**Notifications** (`notifications`)

| Column | Type | Constraints |
| :---- | :---- | :---- |
| notification_id | INTEGER | PK |
| user_id | INTEGER | FK → users.user_id, NOT NULL |
| type | ENUM(enrollment_approved, enrollment_rejected, new_assignment, new_quest, new_help_request, help_request_accepted, section_status, new_class_request, class_request_approved, class_request_rejected, grade_finalization_reminder, assignment_overdue, password_reset_requested, new_unenroll_request, unenroll_request_approved, unenroll_request_rejected, removed_from_section) | NOT NULL |
| message | TEXT | NOT NULL |
| is_read | BOOLEAN | NOT NULL, DEFAULT false |
| assignment_id | INTEGER | FK → assignments.assignment_id, NULL |
| entity_type | VARCHAR | NULL |
| entity_id | INTEGER | NULL |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

**Resources** (`resources`) — teacher-posted links for a section

| Column | Type | Constraints |
| :---- | :---- | :---- |
| resource_id | INTEGER | PK |
| section_id | INTEGER | FK → sections.section_id, NOT NULL |
| teacher_id | INTEGER | FK → users.user_id, NOT NULL |
| title | VARCHAR | NOT NULL |
| url | VARCHAR | NOT NULL |
| description | TEXT | NULL |
| is_archived | BOOLEAN | NOT NULL, DEFAULT false |
| deleted_at | TIMESTAMPTZ | NULL |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now(), ON UPDATE now() |

**Shop Items** (`shop_items`) — cosmetics/badges purchasable (or earned) with points

| Column | Type | Constraints |
| :---- | :---- | :---- |
| item_id | INTEGER | PK |
| name | VARCHAR | NOT NULL |
| description | TEXT | NULL |
| item_type | ENUM(avatar_base, avatar_accessory, badge, theme) | NOT NULL |
| cost | INTEGER | NOT NULL |
| image_url | VARCHAR | NOT NULL |
| theme_key | VARCHAR | NULL |
| is_archived | BOOLEAN | NOT NULL, DEFAULT false |
| deleted_at | TIMESTAMPTZ | NULL |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

> **Note:** `owned`, `equipped`, and badge `progress` are not columns — the shop endpoints compute and attach them to each item at request time, per requesting user.

**Student Inventory** (`student_inventory`) — items a student has purchased or been granted

| Column | Type | Constraints |
| :---- | :---- | :---- |
| inventory_id | INTEGER | PK |
| student_id | INTEGER | FK → users.user_id, NOT NULL |
| item_id | INTEGER | FK → shop_items.item_id, NOT NULL |
| is_equipped | BOOLEAN | NOT NULL, DEFAULT false |
| purchased_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

UNIQUE (student_id, item_id)

**Badge Rules** (`badge_rules`) — defines the criteria that auto-unlock a badge-type shop item

| Column | Type | Constraints |
| :---- | :---- | :---- |
| badge_rule_id | INTEGER | PK |
| item_id | INTEGER | FK → shop_items.item_id, UNIQUE, NOT NULL |
| criteria_type | ENUM(first_quest, quest_streak, event_count, lifetime_points, quest_total_count, section_grade_threshold) | NOT NULL |
| threshold | INTEGER | NOT NULL |
| params | JSON | NULL |
| is_archived | BOOLEAN | NOT NULL, DEFAULT false |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

**Refresh Tokens** (`refresh_tokens`) — see the [Authentication](#authentication) section; the only hard-deleted table in the schema

| Column | Type | Constraints |
| :---- | :---- | :---- |
| id | INTEGER | PK |
| user_id | INTEGER | FK → users.user_id, NOT NULL |
| jti | VARCHAR | UNIQUE |
| token_hash | VARCHAR | UNIQUE (SHA-256 of the token) |
| expires_at | TIMESTAMPTZ | NOT NULL |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

## API Contract

All endpoints are prefixed with `/api` (except the unauthenticated `GET /` health check used by Render). All requests/responses use `application/json` unless noted otherwise (multipart form uploads are called out explicitly). Timestamps are ISO 8601. JWT access tokens go in the `Authorization: Bearer <token>` header; WebSocket connections instead pass the token via the `Sec-WebSocket-Protocol` handshake header, since query-string tokens end up in proxy/CDN access logs and browser history. Soft deletes (`is_archived` + `deleted_at`) are used across academic records — the only hard-deleted table is `refresh_tokens`, cleared on logout/rotation. Roles: `student` | `teacher` | `admin`.

This section is intentionally condensed to method/path/role/description rather than full request-and-response JSON for every one of the ~90 endpoints below — see the model tables above for the exact fields each resource returns, and the controller source under `backend/controllers/` for exact validation rules.

### Authentication (`/api/auth`)

| Method | Path | Roles | Description |
| :---- | :---- | :---- | :---- |
| POST | `/auth/register` | Public | Creates a user under a school by `school_code`. Students auto-verify; teacher/admin signups stay pending until an admin approves them via `PATCH /users/{id}/verify`. |
| POST | `/auth/login` | Public | Returns an access + refresh token pair. Usernames are looked up across all schools, not scoped by `school_code`. |
| POST | `/auth/refresh` | Public (token in body) | Rotates a refresh token (old one is deleted, a new pair issued). Reuse of an already-rotated token revokes every refresh token for that user. |
| POST | `/auth/logout` | any authenticated user | Deletes the presented refresh token. |
| POST | `/auth/reset-password` | admin, teacher | Resets a student's password (target must be a student in the caller's school). |
| POST | `/auth/change-password` | teacher, admin | Changes the caller's own password; requires the old password. |

### Schools (`/api/schools`)

| Method | Path | Roles | Description |
| :---- | :---- | :---- | :---- |
| POST | `/schools` | Public | Creates a new school plus its first admin account; returns tokens for that admin. |
| GET | `/schools/code` | admin | Returns the caller's school join code. |
| GET | `/schools/me` | student, teacher, admin | Returns the caller's school. |
| PATCH | `/schools/me` | admin | Updates the school's name/district/grades. |
| GET | `/schools/points` | admin | Sums `total_points` across every non-archived user in the school. |

### Classes (`/api/classes`) & Class Requests (`/api/class-requests`)

| Method | Path | Roles | Description |
| :---- | :---- | :---- | :---- |
| GET | `/classes` | teacher, admin | Lists the global class catalog, alphabetized. There is no direct `POST /classes` — new classes are created via the seed job or class-request approval below. |
| POST | `/class-requests` | teacher | Requests a new class be added to the catalog; notifies school admins. |
| GET | `/class-requests` | admin | Lists class requests for the school, annotated with fuzzy-matched existing class names. |
| PATCH | `/class-requests/{class_request_id}` | admin | Approves (creates the `Class_` row if needed) or rejects a pending request; notifies the requester. |

### Sections (`/api/sections`)

| Method | Path | Roles | Description |
| :---- | :---- | :---- | :---- |
| GET | `/sections` | student, teacher, admin | Lists sections in the caller's school. `?scope=mine` (default) filters to the student's enrolled sections; `?scope=all` returns every section, optionally filtered by `?class_id=`. |
| POST | `/sections` | teacher | Creates a section owned by the calling teacher. |
| GET | `/sections/{id}` | any (enrolled student / owning teacher / admin) | Full section detail: roster, assignments, quests. |
| GET | `/sections/{id}/analytics` | teacher, admin | Paginated grade/points/attention analytics for the section, plus per-quest completion analytics (`quest_count`, `quests[]` with `completed_count`/`completion_rate`) and paginated study-room activity (`study_rooms[]`, via `?rooms_page=`/`?rooms_page_size=`). `average_grade` is the mean of each enrolled student's official weighted grade, not a flat mean of raw submission grades. |
| GET | `/sections/{id}/grades/me` | student | The calling student's own computed grade for the section. |
| GET | `/sections/{id}/grades/{student_id}` | teacher, admin | A specific enrolled student's computed grade. |
| GET | `/sections/{id}/grades/{student_id}/detail` | teacher, admin | Full student detail for the section: computed grade, every assignment's status/grade, quest completions (with total quest points), and the student's study room history. |
| PATCH | `/sections/{id}` | teacher (own section, period/capacity only), admin (+status, +teacher reassignment) | Updates section fields; a teacher's `status`/`teacher_id` fields, if sent, are silently ignored. |
| DELETE | `/sections/{id}` | admin | Soft-deletes (archives) the section. |

### Enrollments (`/api/sections/{id}/enrollment-requests`, `/api/enrollment-requests`, `/api/unenroll-requests`)

| Method | Path | Roles | Description |
| :---- | :---- | :---- | :---- |
| POST | `/sections/{id}/enrollment-requests` | student | Requests to join a section (blocked if already enrolled or already pending). |
| GET | `/sections/{id}/enrollment-requests` | teacher (owner), admin | Lists a section's pending requests. |
| PATCH | `/enrollment-requests/{id}` | teacher | Accepts (creates the `Enrollment`, capacity-checked) or rejects a request; notifies the student. |
| DELETE | `/sections/{id}/students/{student_id}` | admin | Directly drops (archives) a student's enrollment. |
| POST | `/sections/{id}/unenroll-requests` | teacher | Requests removal of one of their own students; notifies admins. |
| GET | `/sections/{id}/unenroll-requests` | teacher, admin | Lists a section's pending unenroll requests. |
| GET | `/unenroll-requests` | admin | Lists every pending/processed unenroll request in the school. |
| PATCH | `/unenroll-requests/{id}` | admin | Approves (archives the enrollment) or rejects a pending request. |
| POST | `/unenroll-requests/{id}/cancel` | teacher | The original requesting teacher cancels their own pending request. |

### Assignments (`/api/assignments`, `/api/sections/{id}/assignments`) & Submissions

| Method | Path | Roles | Description |
| :---- | :---- | :---- | :---- |
| GET | `/assignments` | student | Assignments across every section the student is enrolled in. |
| GET | `/sections/{id}/assignments` | enrolled student, owning teacher, admin | Assignments for one section. |
| POST | `/sections/{id}/assignments` | teacher | Creates an assignment for the teacher's own section; notifies enrolled students. |
| GET | `/assignments/{id}` | same access as list | Fetches one assignment. |
| PATCH | `/assignments/{id}` | teacher (owner) | Updates an assignment's fields. |
| DELETE | `/assignments/{id}` | teacher (owner), admin | Soft-deletes an assignment. |
| POST | `/assignments/{id}/submissions` | student | Creates a submission (awards an initial 25% of `point_value` immediately). |
| GET | `/assignments/{id}/submissions` | teacher (owner), admin | Lists all submissions for an assignment. |
| GET | `/assignments/{id}/my-submission` | student | The caller's own submission for an assignment. |
| PATCH | `/submissions/{id}/grade` | teacher | Sets a numeric grade (not yet finalized); status → `pending`. |
| POST | `/submissions/{id}/finalize` | teacher | Finalizes a graded submission: bonus points by grade threshold (≥85 → 75% of `point_value`, ≥70 → 50%, else 0%), replaces the point transaction, status → `graded`, evaluates badges. |

### Quests (`/api/quests`, `/api/sections/{id}/quests`)

| Method | Path | Roles | Description |
| :---- | :---- | :---- | :---- |
| GET | `/quests` | any | Lists quests across one or more `?section_ids=` the caller can access; students get a `completed` flag. |
| GET | `/sections/{id}/quests` | enrolled student, owning teacher, admin | Lists quests for one section, optional `?category=academic\|social`. |
| POST | `/sections/{id}/quests` | teacher | Creates a quest for the teacher's own section, optionally targeted at one enrolled student; `social`-category quests get `point_value` × 1.5 (rounded down); notifies the target(s). |
| DELETE | `/quests/{id}` | teacher (owner) | Soft-deletes a teacher-created quest (system-generated quests can't be deleted this way). |
| POST | `/quests/{id}/complete` | student | Marks the quest complete — multipart form, optional description + file upload (JPEG/PDF); awards points; evaluates badges; one completion per student per quest. |
| GET | `/quests/{id}/completions` | teacher (owner), admin | Lists all completions for a quest. |
| POST | `/quests/completions/{quest_completion_id}/reverse` | teacher (owner), admin | Reverses a quest completion: deletes it and its point transaction, decrementing the student's `total_points`. |

### Help Requests / Bulletin Board (`/api/help-requests`, `/api/sections/{id}/help-requests`)

| Method | Path | Roles | Description |
| :---- | :---- | :---- | :---- |
| GET | `/help-requests` | student | Help requests across every section the student is enrolled in. |
| GET | `/sections/{id}/help-requests` | enrolled student, owning teacher, admin | Lists a section's help requests. Response shape differs by role: students never receive `requester_id`/`requester_username`; teachers/admins do, plus the list of who's accepted. |
| POST | `/sections/{id}/help-requests` | student | Creates a help request in an enrolled section; notifies classmates. |
| PATCH | `/help-requests/{id}` | student (requester) | Edits topic/description/group_size/duration — only while still `open` and nobody else has joined. |
| POST | `/help-requests/{id}/accept` | student (not the requester) | Joins the request. First acceptance creates the `StudyRoom` (+ a Daily.co room, best-effort) and adds both students as `room_members` — this is the moment the requester's identity becomes visible to the joiner. Status flips to `active` once `current_size` reaches `group_size`. |
| POST | `/help-requests/{id}/drop` | student (requester) | Closes/archives the requester's own help request. |
| POST | `/help-requests/{id}/confirm` | student (requester) | Confirms whether the session actually happened; if so, awards 25 points to the requester and every accepted participant (idempotent — enforced by a unique constraint on `point_transactions`). |

### Study Rooms (`/api/rooms/{id}`)

| Method | Path | Roles | Description |
| :---- | :---- | :---- | :---- |
| GET | `/rooms/{id}` | room member (student), same-school staff | Room state: members, timer, status, video URL. |
| POST | `/rooms/{id}/video-token` | room member | Issues a Daily.co meeting token for an active room. |
| POST | `/rooms/{id}/kick` | requester | Removes a member; room auto-closes if ≤1 member remains. |
| POST | `/rooms/{id}/leave` | any member | Caller leaves; room closes if empty, and the underlying help request re-opens or closes as appropriate. |
| POST | `/rooms/{id}/extend` | requester | Extends the countdown timer by 10 minutes. |
| POST | `/rooms/{id}/close` | requester | Closes the room and the underlying help request; sends a `session_confirmation_required` message over the requester's socket first. |
| DELETE | `/rooms/{id}` | requester | Deletes the room outright: members removed, Daily room torn down, help request archived. |
| WS | `/rooms/{id}/chat` | room member (JWT via `Sec-WebSocket-Protocol`) | Real-time text chat. In-memory only (`room_registry`), never persisted. Disconnect codes: `1000` normal, `4001` bad/expired token or not a member, `4003` room missing/inactive. |

### Notifications (`/api/notifications`)

| Method | Path | Roles | Description |
| :---- | :---- | :---- | :---- |
| GET | `/notifications` | any | Lists the caller's notifications, optional `?is_read=`. |
| PATCH | `/notifications/read-all` | any | Marks all of the caller's unread notifications read. |
| PATCH | `/notifications/{id}/read` | any | Marks one notification read. |
| POST | `/sections/{id}/notify` | admin | Broadcasts a custom message to every student enrolled in a section. |
| WS | `/notifications/stream` | JWT via `Sec-WebSocket-Protocol` | Push channel for new notifications and generic "data events" (used by the frontend's `RealtimeProvider` to invalidate cached queries). |

### Resources (`/api/sections/{id}/resources`, `/api/resources`)

| Method | Path | Roles | Description |
| :---- | :---- | :---- | :---- |
| GET | `/sections/{id}/resources` | enrolled student, owning teacher | Lists a section's resource links. |
| POST | `/sections/{id}/resources` | teacher | Creates a resource link for the teacher's own section. |
| PATCH | `/resources/{id}` | teacher (owner) | Updates a resource's title/url/description. |
| DELETE | `/resources/{id}` | teacher (owner) | Soft-deletes a resource. |

### Assignment Fit / AI Advisor (`/api/sections/{id}/assignment-fit`)

| Method | Path | Roles | Description |
| :---- | :---- | :---- | :---- |
| POST | `/sections/{id}/assignment-fit` | teacher (owner); rate-limited to 10 calls/60s | Sends a draft assignment plus the section's grading snapshot to Gemini and returns a readiness verdict (`ready` / `review_first` / `mixed`). Returns "unavailable" if there isn't enough grading data yet, or if `GEMINI_API_KEY` isn't configured, or on any Gemini failure — this endpoint is designed to degrade rather than error. |

### Shop & Inventory (`/api/shop`, `/api/inventory`, `/api/users/{id}/inventory`)

| Method | Path | Roles | Description |
| :---- | :---- | :---- | :---- |
| GET | `/shop/items` | any | Lists shop items, optional `?item_type=`; annotates `owned`/`equipped` for the caller and badge `progress` for students. |
| POST | `/shop/items` | admin | Creates a shop item; auto-grants it to every existing staff account. |
| PATCH | `/shop/items/{id}` | admin | Updates a shop item's fields. |
| DELETE | `/shop/items/{id}` | admin | Archives a shop item. |
| POST | `/shop/items/{id}/purchase` | student | Buys a non-badge item with points; records an `InventoryItem` and a negative `PointTransaction`. |
| GET | `/users/{id}/inventory` | self, or teacher/admin same school | Lists a user's owned inventory items. |
| PATCH | `/inventory/{id}/equip` | student, teacher, admin | Equips/unequips an owned item; single-equip categories (avatar_base, avatar_accessory, theme) un-equip any sibling item of the same type first. |

### Users (`/api/users`, `/api/users/{id}/points`)

| Method | Path | Roles | Description |
| :---- | :---- | :---- | :---- |
| GET | `/users` | admin | Lists users in the admin's school, optional `?role=`. |
| GET | `/users/{id}` | self (student), teacher, admin | Fetches one user's profile (same-school only). |
| GET | `/users/{id}/points` | self (student), teacher, admin | Paginated point-transaction history plus running `total_points`. |
| GET | `/users/{id}/grades` | admin | A student's computed grade per enrolled section. |
| GET | `/users/{id}/report_card` | admin | Full report card (grades + assignment/quest items) across all of a student's sections. |
| PATCH | `/users/me` | any | Updates the caller's own username (unique within school). |
| POST | `/users/me/profile-picture` | any | Uploads (multipart) and sets the caller's avatar, re-encoding server-side and deleting the old image. |
| DELETE | `/users/me/profile-picture` | any | Removes the caller's avatar. |
| PATCH | `/users/me/featured-badge` | student | Sets/clears the student's featured badge (must own it). |
| POST | `/users/me/request-password-reset` | student | Notifies all school admins that the student needs a reset. |
| DELETE | `/users/me` | any | Self-service soft delete; blocked if the caller is a school's last remaining admin. |
| PATCH | `/users/{id}/verify` | admin | Approves a pending signup (approving a self-registered admin requires an extra `confirm_role="admin"` echo). No error if already verified. |
| PATCH | `/users/{id}/reject` | admin | Rejects a pending signup, with an optional reason. |
| PATCH | `/users/{id}/deactivate` | admin | Deactivates a user (not self). |
| PATCH | `/users/{id}/reactivate` | admin | Reactivates a previously deactivated user. |
| DELETE | `/users/{id}` | admin | Soft-deletes another user (not self); cascades teacher-section fallout. |

> **Route-ordering note:** in `users_controller.py` and `notifications_controller.py`, literal sub-paths (`/me`, `/me/...`, `/read-all`) are registered *before* the corresponding `/{id}` route, so FastAPI doesn't try to parse `"me"` or `"read-all"` as an integer path parameter.

## Wireframe 

## Future Ideas

**School milestone unlocks.** Beyond the per-student badge-rule engine (`backend/services/badge_rules.py`) and the teacher/admin cosmetics auto-unlock, a school-wide milestone system could unlock additional collectibles for a school's teachers/admins once the school crosses cumulative activity thresholds — e.g. total points ever earned school-wide, total quests completed, or total assignments graded. This would be a new concept (no school-scoped achievement tracking exists today) and is undesigned; scoping it — what counts as a milestone, how it's tracked, and what unlocks — is a future planning exercise.


