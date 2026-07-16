# Closing the Admin Console backend gaps

## Context
The Show of Hands admin console (`projects/show_of_hands/frontend/src/pages/admin/`) was built
frontend-only against the real backend, and eight gaps were flagged where the design spec
called for something the backend couldn't support. This plan closes those gaps with real
schema/endpoint changes plus the matching frontend updates, so the console stops working
around missing data and starts using it directly.

Conventions below come from reading the actual codebase (alembic migration style, model/schema/
controller patterns, test fixtures) — not assumed, so migrations and endpoints match the house
style exactly (e.g. `projects/show_of_hands/backend/alembic/versions/a3f7c1d2e4b5_add_url_to_assignments.py`
is the template for every new migration; `verify_user` in
`backend/controllers/users_controller.py` is the template for every new admin PATCH endpoint).

Decisions locked in with you:
- `last_active_at` updates on every authenticated request, throttled to ~5 min, in `get_current_user` (dependencies.py) — accurate without hammering the DB.
- School Settings gets a small inline edit form (name/district/grades) backed by a new `PATCH /schools/me`.
- No "assignment" field invented for pending signups — only real fields get added (email exposure + a free-text signup note).
- Sections' dual archive mechanism (`status='archived'` vs `DELETE` `is_archived`) stays as-is — no code change, just confirming the console's existing choice to only use `status='archived'` remains correct.

## Migrations (alembic, chained off current head `a3f7c1d2e4b5`)

Three new migrations in `backend/alembic/versions/`, each following the existing template
(`revision`/`down_revision`/`upgrade`/`downgrade`, `op.add_column`/`op.drop_column`,
`nullable=False` boolean columns get a `server_default` for backfill then drop it):

1. **`users` table** — add:
   - `is_active BOOLEAN NOT NULL DEFAULT true` (server_default `'true'` for backfill, dropped after)
   - `rejection_reason TEXT NULL`
   - `last_active_at TIMESTAMP NULL`
   - `signup_note TEXT NULL`
2. **`class_requests` table** — add `subject VARCHAR NULL`, `description TEXT NULL`
3. **`schools` table** — add `district VARCHAR NULL`, `grades VARCHAR NULL`

## Backend changes

### Models
- `models/user_model.py`: `is_active = Column(Boolean, nullable=False, default=True)`,
  `rejection_reason = Column(Text, nullable=True)`, `last_active_at = Column(DateTime, nullable=True)`,
  `signup_note = Column(Text, nullable=True)` — same style as existing `is_verified`/`is_archived`.
- `models/class_request_model.py`: `subject = Column(String, nullable=True)`,
  `description = Column(Text, nullable=True)`.
- `models/school_model.py`: `district = Column(String, nullable=True)`, `grades = Column(String, nullable=True)`.

### Schemas
- `schemas/user.py`: add `is_active`, `total_points`, `email`, `last_active_at` to `UserListResponse`
  (closes the "no email/points/last-active in the directory list" gap); add `note: Optional[str] = None`
  to `RegisterRequest`.
- `schemas/class_request.py`: add `subject: Optional[str] = None`, `description: Optional[str] = None`
  to both `ClassRequestCreate` and the response schemas; add `similar_classes: list[str] = []` to
  `ClassRequestListResponse` (computed, not stored — see controller below).
- `schemas/school.py`: add `district`, `grades` (`Optional[str] = None`) to `SchoolResponse`; new
  `SchoolUpdate` request schema `{name?, district?, grades?}` for the new PATCH.

### Controllers
- `controllers/users_controller.py` — new admin endpoints, same shape as `verify_user`:
  - `PATCH /users/{user_id}/deactivate` → `is_active = False`. This becomes what the console's
    "Deactivate" button calls (replacing `DELETE`, which stays available for real account deletion elsewhere).
  - `PATCH /users/{user_id}/reactivate` → `is_active = True`. No existing precedent for this filter;
    unlike `verify_user`, don't filter on `is_archived == False` since the point is reviving a
    deactivated account.
  - `PATCH /users/{user_id}/reject` → body `{reason: Optional[str]}`; 409 if `is_verified` is already
    `True` (mirrors `update_class_request_status`'s pending-only guard); sets `rejection_reason`
    (defaulting to `"Rejected by admin"` if no reason given).
  - `GET /users` pending-signup semantics used by the inbox move from "not verified" to
    "not verified and not rejected" (`is_verified == False AND rejection_reason IS NULL`).
- `dependencies.py` `get_current_user` — add an `is_active` check (403 "Account deactivated",
  same style as the existing `is_verified` 403) alongside the existing `is_archived`/`is_verified`
  checks; also touch `last_active_at` here (write only if the stored value is `None` or more than
  5 minutes old, to avoid a DB write on every single request).
- `controllers/auth_controller.py` `register` — accept `note`, store as `signup_note`.
- `controllers/class_requests_controller.py`:
  - `ClassRequestCreate` handling accepts `subject`/`description`.
  - `GET /class-requests` computes `similar_classes` per request: `ilike` match against `Class_.name`
    for existing catalog entries, returned as a plain list of names (empty list = no catalog collision).
- `controllers/schools_controller.py`:
  - `PATCH /schools/me` (admin) — partial update of `name`/`district`/`grades`, same
    school-scoping + `require_role(["admin"])` pattern as everywhere else.
  - `GET /schools/points` (admin) — `SUM(User.total_points)` for the school (`is_archived == False`),
    closing the "no aggregate points endpoint" gap for the top-bar pill.

### Tests
New tests in `tests/test_users.py` (deactivate/reactivate/reject flows), `tests/test_class_requests.py`
(subject/description round-trip, similar_classes), `tests/test_schools.py` (PATCH /schools/me,
GET /schools/points), following the existing `world`/`cleanup`/`unique`/`auth_header` fixture
conventions in `tests/conftest.py` — create throwaway rows, register them with `cleanup(...)`
immediately, never mutate the shared `world` fixture rows.

## Frontend changes (`projects/show_of_hands/frontend/src/pages/admin/` + `components/admin/`)

- **`AdminUsers.jsx`**: drop the session-only `deactivatedIds` workaround entirely — `is_active`
  now comes straight from `GET /users` and survives a refresh. Deactivate calls
  `PATCH /users/{id}/deactivate`; a real "Reactivate" button now calls
  `PATCH /users/{id}/reactivate`. Row gains real email, points, and last-active columns.
- **`AdminInbox.jsx`**: "Reject" calls `PATCH /users/{id}/reject` instead of `DELETE`. Signup
  cards show email; class request cards show subject, description, and a "Catalog check" line
  driven by `similar_classes` (e.g. "Matches existing: Algebra II" or "No similar classes found").
- **`AdminSettings.jsx`**: display `district`/`grades`; add a small inline edit affordance
  (name/district/grades fields + Save) calling `PATCH /schools/me`, following the same
  `useToast()`/`api.patch` pattern used elsewhere in the console.
- **`components/admin/AdminTopBar.jsx`**: add back the school-points pill, fetched from
  `GET /schools/points`.
- **`pages/Auth.jsx`**: register form gains an optional "Note" field, sent as `note` in the
  registration body.

## Verification
- Run `alembic upgrade head` against a local/dev DB and confirm no errors; `alembic downgrade -3`
  then `upgrade head` again to confirm the migrations are reversible.
- Backend: `cd backend && source .venv/bin/activate && pytest tests/test_users.py tests/test_class_requests.py tests/test_schools.py -v`.
- Manually re-run the same admin_demo walkthrough as before (login → reject a fresh throwaway
  signup and confirm it disappears from the inbox and can't log in with a "rejected" 403 →
  deactivate then reactivate a user and confirm the row survives a page refresh → submit a class
  request with a subject/description as a teacher and confirm the admin inbox shows them plus a
  catalog-check line → edit school district/grades in Settings and confirm they persist after
  reload → confirm the top-bar points pill shows a real aggregate number).
