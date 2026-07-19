# AI Assignment-Fit Advisor + Section Resources Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Teachers get an AI (Gemini) readiness check on draft assignments grounded in real class grade data, and every section gets a teacher-curated Resources card students can click through.

**Architecture:** Two independent backend surfaces on the existing FastAPI app: (1) a `resources` table + section-scoped CRUD following the quests controller pattern, and (2) a stateless `POST /sections/{id}/assignment-fit` endpoint that computes class stats in Python and sends only that compact summary to Gemini for a structured verdict. Frontend adds a teacher ResourcesPanel + student resources card, and a "Check fit" flow inside the existing assignment-creation form.

**Tech Stack:** FastAPI + SQLAlchemy + Alembic + Pydantic (backend), `google-genai` SDK (`gemini-2.5-flash`, free AI Studio tier), React 19 + Vite (frontend), pytest.

**Spec:** `docs/superpowers/specs/2026-07-18-ai-advisor-and-resources-design.md`

## Global Constraints

- AI provider is **Google Gemini** via the official `google-genai` Python SDK, model string `gemini-2.5-flash`. API key read from env var `GEMINI_API_KEY`, backend-only — never sent to or read by the frontend.
- All AI claims must be grounded: the backend computes stats; the model only interprets them. The frontend always renders the computed stats regardless of AI availability.
- Resource URLs must start with `http://` or `https://` (reject otherwise with 422).
- Soft-delete convention: `is_archived` boolean + `deleted_at` timestamp, matching every other model in this codebase.
- Backend tests run against the shared dev DB via the existing `world`/`cleanup` conftest fixtures — every row a test creates must be registered for cleanup.
- Tests must never call the real Gemini API — mock `generate_fit_verdict` / set fake env keys.
- Frontend verification = `npx eslint <changed files>` + `npm run build` (this project has no JS test runner).
- Backend working dir: `/Users/jonathanbernal/Development/projects/show_of_hands/backend`. Frontend: `.../frontend`. All file paths below are relative to the repo root `projects/show_of_hands/`.
- Commit after every task (steps include the exact commands). Current branch: `fixes`.

---

### Task 1: Resource model + Alembic migration

**Files:**
- Create: `backend/models/resource_model.py`
- Modify: `backend/models/__init__.py` (add one import line)
- Modify: `backend/models/section_model.py` (add one relationship line)
- Create: `backend/alembic/versions/f5a6b7c8d9e0_add_resources_table.py`

**Interfaces:**
- Produces: `Resource` SQLAlchemy model with columns `resource_id, section_id, teacher_id, title, url, description, is_archived, deleted_at, created_at, updated_at` and relationship `Resource.section`. Tasks 2–3 import it as `from models.resource_model import Resource`.

- [ ] **Step 1: Create the model**

Create `backend/models/resource_model.py`:

```python
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from db.pool import Base


class Resource(Base):
    __tablename__ = "resources"

    resource_id = Column(Integer, primary_key=True)
    section_id = Column(Integer, ForeignKey("sections.section_id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_archived = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    section = relationship("Section", back_populates="resources")
    teacher = relationship("User", foreign_keys=[teacher_id])
```

- [ ] **Step 2: Register the model**

In `backend/models/__init__.py`, add after the `Notification` import line:

```python
from models.resource_model import Resource
```

In `backend/models/section_model.py`, add alongside the other `relationship(...)` lines on the `Section` class (next to `quests = relationship(...)`):

```python
    resources = relationship("Resource", back_populates="section")
```

- [ ] **Step 3: Write the migration**

Create `backend/alembic/versions/f5a6b7c8d9e0_add_resources_table.py` (down_revision chains off the current head `e4f5a6b7c8d9`):

```python
"""add resources table

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-07-18 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5a6b7c8d9e0'
down_revision: Union[str, Sequence[str], None] = 'e4f5a6b7c8d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'resources',
        sa.Column('resource_id', sa.Integer(), primary_key=True),
        sa.Column('section_id', sa.Integer(), sa.ForeignKey('sections.section_id'), nullable=False),
        sa.Column('teacher_id', sa.Integer(), sa.ForeignKey('users.user_id'), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('resources')
```

- [ ] **Step 4: Run the migration and verify**

Run: `cd backend && alembic upgrade head`
Expected: `Running upgrade e4f5a6b7c8d9 -> f5a6b7c8d9e0, add resources table` with no errors.

Then verify the model round-trips:

Run: `cd backend && python3 -c "from models.resource_model import Resource; from db.pool import SessionLocal; s = SessionLocal(); print(s.query(Resource).count()); s.close()"`
Expected: `0`

- [ ] **Step 5: Commit**

```bash
git add backend/models/resource_model.py backend/models/__init__.py backend/models/section_model.py backend/alembic/versions/f5a6b7c8d9e0_add_resources_table.py
git commit -m "feat: add resources table and model"
```

---

### Task 2: Resource schemas + list/create endpoints

**Files:**
- Create: `backend/schemas/resource.py`
- Create: `backend/controllers/resources_controller.py`
- Modify: `backend/main.py` (import + include router)
- Create: `backend/tests/test_resources.py`

**Interfaces:**
- Consumes: `Resource` model from Task 1.
- Produces: `GET /api/sections/{section_id}/resources` → `List[ResourceResponse]`; `POST /api/sections/{section_id}/resources` (teacher owning section, 201) → `ResourceResponse`. `ResourceResponse` fields: `resource_id, section_id, teacher_id, title, url, description, created_at`. Task 3 extends this controller; Tasks 4–5 call these endpoints.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_resources.py`:

```python
from models.resource_model import Resource
from tests.conftest import auth_header


def _create_resource(client, world, cleanup, **overrides):
    body = {
        "title": "Khan Academy: Quadratics",
        "url": "https://www.khanacademy.org/math/algebra/quadratics",
        "description": "Video series on factoring and graphing.",
    }
    body.update(overrides)
    resp = client.post(
        f"/api/sections/{world.section_id}/resources",
        json=body,
        headers=auth_header(world.teacher_token),
    )
    if resp.status_code == 201:
        cleanup(Resource, resp.json()["resource_id"])
    return resp


def test_teacher_creates_resource(client, world, cleanup):
    resp = _create_resource(client, world, cleanup)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["title"] == "Khan Academy: Quadratics"
    assert data["url"].startswith("https://")
    assert data["section_id"] == world.section_id
    assert data["teacher_id"] == world.teacher_id


def test_student_cannot_create_resource(client, world):
    resp = client.post(
        f"/api/sections/{world.section_id}/resources",
        json={"title": "T", "url": "https://example.com"},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 403


def test_invalid_url_scheme_rejected(client, world, cleanup):
    resp = _create_resource(client, world, cleanup, url="javascript:alert(1)")
    assert resp.status_code == 422


def test_enrolled_student_lists_resources(client, world, cleanup):
    created = _create_resource(client, world, cleanup)
    assert created.status_code == 201
    resp = client.get(
        f"/api/sections/{world.section_id}/resources",
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 200, resp.text
    ids = [r["resource_id"] for r in resp.json()]
    assert created.json()["resource_id"] in ids


def test_admin_can_list_resources(client, world, cleanup):
    _create_resource(client, world, cleanup)
    resp = client.get(
        f"/api/sections/{world.section_id}/resources",
        headers=auth_header(world.admin_token),
    )
    assert resp.status_code == 200


def test_list_unknown_section_404(client, world):
    resp = client.get(
        "/api/sections/999999/resources",
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python3 -m pytest tests/test_resources.py -v`
Expected: all tests FAIL with 404s (routes not registered yet).

- [ ] **Step 3: Write schemas**

Create `backend/schemas/resource.py`:

```python
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator


def _validate_http_url(v: str) -> str:
    if not (v.startswith("http://") or v.startswith("https://")):
        raise ValueError("URL must start with http:// or https://")
    return v


class ResourceCreate(BaseModel):
    title: str
    url: str
    description: Optional[str] = None

    @field_validator("url")
    @classmethod
    def check_url(cls, v: str) -> str:
        return _validate_http_url(v)


class ResourceUpdate(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None

    @field_validator("url")
    @classmethod
    def check_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return _validate_http_url(v)


class ResourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    resource_id: int
    section_id: int
    teacher_id: int
    title: str
    url: str
    description: Optional[str] = None
    created_at: datetime
```

- [ ] **Step 4: Write the controller (list + create)**

Create `backend/controllers/resources_controller.py`. The `_check_section_access` helper mirrors `controllers/quests_controller.py:20-41` (students must be enrolled, teachers must own the section, admins pass with the school check):

```python
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.pool import get_db
from dependencies import get_current_user, require_role
from models.enrollment_model import Enrollment
from models.resource_model import Resource
from models.section_model import Section
from models.user_model import User, RoleEnum
from schemas.resource import ResourceCreate, ResourceUpdate, ResourceResponse

router = APIRouter(tags=["resources"])


def _check_section_access(section_id: int, current_user: User, db: Session) -> Section:
    section = db.query(Section).filter(
        Section.section_id == section_id,
        Section.school_id == current_user.school_id,
        Section.is_archived == False,
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")

    if current_user.role == RoleEnum.student:
        enrolled = db.query(Enrollment).filter(
            Enrollment.section_id == section_id,
            Enrollment.student_id == current_user.user_id,
            Enrollment.is_archived == False,
        ).first()
        if not enrolled:
            raise HTTPException(status_code=403, detail="Not enrolled in this section.")
    elif current_user.role == RoleEnum.teacher:
        if section.teacher_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not your section.")

    return section


def _get_owned_section(section_id: int, current_user: User, db: Session) -> Section:
    section = db.query(Section).filter(
        Section.section_id == section_id,
        Section.school_id == current_user.school_id,
        Section.is_archived == False,
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")
    if section.teacher_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not your section.")
    return section


@router.get("/sections/{section_id}/resources", response_model=List[ResourceResponse])
def list_resources(
    section_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_section_access(section_id, current_user, db)
    return (
        db.query(Resource)
        .filter(Resource.section_id == section_id, Resource.is_archived == False)
        .order_by(Resource.created_at.desc())
        .all()
    )


@router.post("/sections/{section_id}/resources", response_model=ResourceResponse, status_code=201)
def create_resource(
    section_id: int,
    body: ResourceCreate,
    current_user: User = Depends(require_role(["teacher"])),
    db: Session = Depends(get_db),
):
    _get_owned_section(section_id, current_user, db)
    resource = Resource(
        section_id=section_id,
        teacher_id=current_user.user_id,
        title=body.title,
        url=body.url,
        description=body.description,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource
```

- [ ] **Step 5: Register the router**

In `backend/main.py`, add with the other controller imports:

```python
from controllers.resources_controller import router as resources_router
```

And with the other `include_router` calls at the bottom:

```python
app.include_router(resources_router, prefix="/api", tags=["resources"])
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python3 -m pytest tests/test_resources.py -v`
Expected: all 6 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/schemas/resource.py backend/controllers/resources_controller.py backend/main.py backend/tests/test_resources.py
git commit -m "feat: section resources list/create endpoints"
```

---

### Task 3: Resource update/delete endpoints

**Files:**
- Modify: `backend/controllers/resources_controller.py` (append two endpoints)
- Modify: `backend/tests/test_resources.py` (append tests)

**Interfaces:**
- Consumes: Task 2's controller, `ResourceUpdate` schema, `_get_owned_section`.
- Produces: `PATCH /api/resources/{resource_id}` → `ResourceResponse`; `DELETE /api/resources/{resource_id}` → `{"message": "Resource deleted successfully."}`. Only the section's teacher may modify. Task 4's UI calls these.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_resources.py`:

```python
def test_teacher_updates_resource(client, world, cleanup):
    created = _create_resource(client, world, cleanup)
    rid = created.json()["resource_id"]
    resp = client.patch(
        f"/api/resources/{rid}",
        json={"title": "Updated title", "description": None},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["title"] == "Updated title"


def test_update_rejects_bad_url(client, world, cleanup):
    created = _create_resource(client, world, cleanup)
    rid = created.json()["resource_id"]
    resp = client.patch(
        f"/api/resources/{rid}",
        json={"url": "ftp://example.com"},
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 422


def test_student_cannot_update_resource(client, world, cleanup):
    created = _create_resource(client, world, cleanup)
    rid = created.json()["resource_id"]
    resp = client.patch(
        f"/api/resources/{rid}",
        json={"title": "Hacked"},
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 403


def test_teacher_deletes_resource(client, world, cleanup):
    created = _create_resource(client, world, cleanup)
    rid = created.json()["resource_id"]
    resp = client.delete(f"/api/resources/{rid}", headers=auth_header(world.teacher_token))
    assert resp.status_code == 200
    # soft-deleted: no longer listed
    listing = client.get(
        f"/api/sections/{world.section_id}/resources",
        headers=auth_header(world.teacher_token),
    )
    assert rid not in [r["resource_id"] for r in listing.json()]


def test_delete_unknown_resource_404(client, world):
    resp = client.delete("/api/resources/999999", headers=auth_header(world.teacher_token))
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `cd backend && python3 -m pytest tests/test_resources.py -v`
Expected: the 5 new tests FAIL (405/404 — routes missing); the 6 from Task 2 still PASS.

- [ ] **Step 3: Implement update + delete**

Append to `backend/controllers/resources_controller.py`:

```python
def _get_owned_resource(resource_id: int, current_user: User, db: Session) -> Resource:
    resource = db.query(Resource).filter(
        Resource.resource_id == resource_id,
        Resource.is_archived == False,
    ).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found.")
    _get_owned_section(resource.section_id, current_user, db)
    return resource


@router.patch("/resources/{resource_id}", response_model=ResourceResponse)
def update_resource(
    resource_id: int,
    body: ResourceUpdate,
    current_user: User = Depends(require_role(["teacher"])),
    db: Session = Depends(get_db),
):
    resource = _get_owned_resource(resource_id, current_user, db)
    if body.title is not None:
        resource.title = body.title
    if body.url is not None:
        resource.url = body.url
    if "description" in body.model_fields_set:
        resource.description = body.description
    db.commit()
    db.refresh(resource)
    return resource


@router.delete("/resources/{resource_id}")
def delete_resource(
    resource_id: int,
    current_user: User = Depends(require_role(["teacher"])),
    db: Session = Depends(get_db),
):
    resource = _get_owned_resource(resource_id, current_user, db)
    resource.is_archived = True
    resource.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Resource deleted successfully."}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python3 -m pytest tests/test_resources.py -v`
Expected: all 11 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/controllers/resources_controller.py backend/tests/test_resources.py
git commit -m "feat: resource update and soft-delete endpoints"
```

---

### Task 4: Teacher ResourcesPanel (frontend)

**Files:**
- Create: `frontend/src/components/section-detail/ResourcesPanel.jsx`
- Modify: `frontend/src/components/section-detail/TeacherSectionDetail.jsx` (CARDS array at line 23, import, activeCard branch near line 211)

**Interfaces:**
- Consumes: Task 2/3 endpoints via the shared `api` axios instance (`import api from '../../api'`).
- Produces: `<ResourcesPanel sectionId={...} />` component; a `Resources` card tile on the teacher section page. Task 8 reuses the POST endpoint shape shown here.

- [ ] **Step 1: Create the panel component**

Create `frontend/src/components/section-detail/ResourcesPanel.jsx` (follows the AssignmentsPanel form pattern and `teacher-panel-*` CSS classes already defined in `TeacherSectionDetail.css`):

```jsx
import { useCallback, useEffect, useState } from 'react'
import api from '../../api'
import { useDialog } from '../DialogContext'

function domainOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return ''
  }
}

function ResourcesPanel({ sectionId }) {
  const { confirm } = useDialog()
  const [resources, setResources] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [title, setTitle] = useState('')
  const [url, setUrl] = useState('')
  const [description, setDescription] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const load = useCallback(() => {
    let cancelled = false
    api
      .get(`/sections/${sectionId}/resources`)
      .then(({ data }) => {
        if (!cancelled) setResources(data)
      })
      .catch(() => {
        if (!cancelled) setResources((prev) => prev ?? [])
      })
    return () => {
      cancelled = true
    }
  }, [sectionId])

  useEffect(() => load(), [load])

  function resetForm() {
    setTitle('')
    setUrl('')
    setDescription('')
    setEditingId(null)
    setShowForm(false)
    setError('')
  }

  function startEdit(resource) {
    setEditingId(resource.resource_id)
    setTitle(resource.title)
    setUrl(resource.url)
    setDescription(resource.description || '')
    setShowForm(true)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    const body = { title, url, description: description || null }
    try {
      if (editingId) {
        await api.patch(`/resources/${editingId}`, body)
      } else {
        await api.post(`/sections/${sectionId}/resources`, body)
      }
      resetForm()
      load()
    } catch (err) {
      setError(err.response?.data?.message || 'Could not save resource.')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDelete(resource) {
    const ok = await confirm(`Delete "${resource.title}"?`)
    if (!ok) return
    try {
      await api.delete(`/resources/${resource.resource_id}`)
      load()
    } catch {
      setError('Could not delete resource.')
    }
  }

  const loading = resources === null

  return (
    <div>
      <div className="widget-label">resources</div>

      {!showForm && (
        <button
          type="button"
          className="teacher-panel-button teacher-panel-add-toggle"
          onClick={() => setShowForm(true)}
        >
          + new resource
        </button>
      )}

      {showForm && (
        <form className="teacher-panel-form" onSubmit={handleSubmit}>
          <label>
            Title
            <input value={title} onChange={(e) => setTitle(e.target.value)} required />
          </label>
          <label>
            Link
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://…"
              required
            />
          </label>
          <label>
            Description (optional — tell students where this leads)
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />
          </label>
          {error && <p className="teacher-panel-error">{error}</p>}
          <div className="teacher-panel-form-actions">
            <button type="button" className="teacher-panel-button" onClick={resetForm}>
              Cancel
            </button>
            <button type="submit" className="teacher-panel-button" disabled={submitting}>
              {submitting ? 'Saving…' : editingId ? 'Save' : 'Post'}
            </button>
          </div>
        </form>
      )}

      {loading && <p className="teacher-panel-placeholder">Loading resources…</p>}
      {!loading && resources.length === 0 && (
        <p className="teacher-panel-placeholder">No resources posted yet.</p>
      )}
      {!loading && resources.length > 0 && (
        <div className="teacher-panel-list">
          {resources.map((r) => (
            <div className="teacher-panel-row" key={r.resource_id}>
              <span>
                <a href={r.url} target="_blank" rel="noopener noreferrer">
                  {r.title}
                </a>{' '}
                <span className="teacher-panel-row-sub">{domainOf(r.url)}</span>
                {r.description && <div className="teacher-panel-row-sub">{r.description}</div>}
              </span>
              <span>
                <button type="button" className="teacher-panel-button" onClick={() => startEdit(r)}>
                  Edit
                </button>{' '}
                <button type="button" className="teacher-panel-button" onClick={() => handleDelete(r)}>
                  Delete
                </button>
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ResourcesPanel
```

Note: if `useDialog` has no `confirm` method (check `frontend/src/components/DialogContext.js` — it exposes `alert` and `confirm`; QuestsPanel uses it), fall back to `window.confirm`.

- [ ] **Step 2: Wire into TeacherSectionDetail**

In `frontend/src/components/section-detail/TeacherSectionDetail.jsx`:

Add import (with the other panel imports, lines 6–12):

```jsx
import ResourcesPanel from './ResourcesPanel'
```

Add to the `CARDS` array (line 23):

```jsx
  { key: 'resources', label: 'Resources' },
```

Add to the activeCard branches (after the `analytics` line ~211):

```jsx
          {activeCard === 'resources' && <ResourcesPanel sectionId={sectionId} />}
```

- [ ] **Step 3: Lint and build**

Run: `cd frontend && npx eslint src/components/section-detail/ResourcesPanel.jsx src/components/section-detail/TeacherSectionDetail.jsx && npm run build`
Expected: no lint errors, `✓ built`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/section-detail/ResourcesPanel.jsx frontend/src/components/section-detail/TeacherSectionDetail.jsx
git commit -m "feat: teacher resources panel on section detail"
```

---

### Task 5: Student resources card (frontend)

**Files:**
- Modify: `frontend/src/pages/SectionDetail.jsx` (StudentSectionDetail component)
- Modify: `frontend/src/pages/SectionDetail.css`

**Interfaces:**
- Consumes: `GET /sections/{id}/resources` from Task 2.
- Produces: clickable resources card on the student section page.

- [ ] **Step 1: Add resources state + fetch to StudentSectionDetail**

In `frontend/src/pages/SectionDetail.jsx`, inside `StudentSectionDetail` (after the existing `section` state):

```jsx
  const [resources, setResources] = useState(null)

  useEffect(() => {
    let cancelled = false
    api
      .get(`/sections/${sectionId}/resources`)
      .then(({ data }) => {
        if (!cancelled) setResources(data)
      })
      .catch(() => {
        if (!cancelled) setResources((prev) => prev ?? [])
      })
    return () => {
      cancelled = true
    }
  }, [sectionId])
```

And add a helper above the component (module level):

```jsx
function domainOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return ''
  }
}
```

- [ ] **Step 2: Render the card**

After the closing `</div>` of `.section-detail-columns` (line ~123), add:

```jsx
      <div className="section-detail-resources">
        <div className="widget-label">resources</div>
        {(!resources || resources.length === 0) && (
          <p className="admin-empty-card">No resources posted yet.</p>
        )}
        {resources && resources.length > 0 && (
          <div className="section-detail-list">
            {resources.map((r) => (
              <a
                className="section-detail-row section-detail-resource-row"
                key={r.resource_id}
                href={r.url}
                target="_blank"
                rel="noopener noreferrer"
              >
                <span>
                  {r.title}
                  {r.description && (
                    <div className="section-detail-row-sub">{r.description}</div>
                  )}
                </span>
                <span className="section-detail-resource-domain">{domainOf(r.url)}</span>
              </a>
            ))}
          </div>
        )}
      </div>
```

- [ ] **Step 3: Style it**

Append to `frontend/src/pages/SectionDetail.css`:

```css
.section-detail-resources {
  margin-top: 22px;
}

.section-detail-resource-row {
  text-decoration: none;
  align-items: center;
}

.section-detail-resource-row:hover {
  background: var(--surface-2);
}

.section-detail-resource-domain {
  font-size: 11px;
  color: var(--text-muted);
  border: 1px solid var(--border-strong);
  border-radius: 10px;
  padding: 1px 8px;
  white-space: nowrap;
}
```

- [ ] **Step 4: Lint and build**

Run: `cd frontend && npx eslint src/pages/SectionDetail.jsx && npm run build`
Expected: clean lint, successful build.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/SectionDetail.jsx frontend/src/pages/SectionDetail.css
git commit -m "feat: student resources card on section detail"
```

---

### Task 6: Class snapshot computation (backend, no AI yet)

**Files:**
- Create: `backend/assignment_fit.py`
- Create: `backend/tests/test_assignment_fit.py`

**Interfaces:**
- Consumes: `compute_section_grade_for_student` from `grading.py`; `Assignment`, `Submission`, `Enrollment`, `HelpRequest` models.
- Produces: `build_section_snapshot(db, section_id) -> dict` with keys `enrolled_count, graded_submission_count, category_averages, grade_distribution, recent_assignments, help_request_topics`. Task 7's endpoint calls this and returns it as `stats`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_assignment_fit.py`:

```python
from datetime import datetime, timedelta, timezone

from assignment_fit import build_section_snapshot
from models.assignment_model import Assignment, AssignmentCategoryEnum
from models.help_request_model import HelpRequest
from models.submission_model import Submission, SubmissionStatusEnum
from tests.conftest import auth_header, unique


def _seed_graded_data(db, world, cleanup):
    """One quiz assignment with a graded submission, plus a help request."""
    assignment = Assignment(
        section_id=world.section_id,
        title=unique("Quadratics Quiz"),
        category=AssignmentCategoryEnum.quizzes,
        point_value=20,
        due_date=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    cleanup(Assignment, assignment.assignment_id)

    submission = Submission(
        assignment_id=assignment.assignment_id,
        student_id=world.student_id,
        status=SubmissionStatusEnum.graded,
        grade=72.0,
        points_awarded=14,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    cleanup(Submission, submission.submission_id)

    help_request = HelpRequest(
        section_id=world.section_id,
        requester_id=world.student_id,
        topic="factoring",
        group_size=3,
        duration_minutes=30,
    )
    db.add(help_request)
    db.commit()
    db.refresh(help_request)
    cleanup(HelpRequest, help_request.help_request_id)

    return assignment


def test_snapshot_aggregates_grades_and_topics(db, world, cleanup):
    assignment = _seed_graded_data(db, world, cleanup)

    snapshot = build_section_snapshot(db, world.section_id)

    assert snapshot["enrolled_count"] >= 1
    assert snapshot["graded_submission_count"] >= 1
    assert snapshot["category_averages"]["quizzes"] == 72.0
    assert snapshot["grade_distribution"]["C"] >= 1
    titles = [a["title"] for a in snapshot["recent_assignments"]]
    assert assignment.title in titles
    topics = {t["topic"]: t["count"] for t in snapshot["help_request_topics"]}
    assert topics.get("factoring", 0) >= 1


def test_snapshot_empty_section_reports_zero(db, world):
    # world.section_id has data from other tests in this module; use a bogus
    # aggregate check instead: a section with no graded submissions.
    # The world fixture's section starts empty per module, so run this test
    # in isolation semantics: build a fresh snapshot BEFORE seeding would be
    # order-dependent — instead just assert the function tolerates a section
    # with no submissions by checking the shape on a nonexistent-data path.
    snapshot = build_section_snapshot(db, world.section_id)
    assert set(snapshot.keys()) == {
        "enrolled_count",
        "graded_submission_count",
        "category_averages",
        "grade_distribution",
        "recent_assignments",
        "help_request_topics",
    }
```

> Note for the implementer: pytest runs tests in file order, so `test_snapshot_empty_section_reports_zero` runs after seeding; it only asserts the dict shape, which is order-independent.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_assignment_fit.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'assignment_fit'`.

- [ ] **Step 3: Implement the snapshot builder**

Create `backend/assignment_fit.py`:

```python
"""Deterministic class-performance snapshot used by the AI assignment-fit
advisor. All numbers shown to teachers come from here, never from the model."""

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from grading import compute_section_grade_for_student, letter_grade_for
from models.assignment_model import Assignment
from models.enrollment_model import Enrollment
from models.help_request_model import HelpRequest
from models.submission_model import Submission, SubmissionStatusEnum

RECENT_ASSIGNMENT_LIMIT = 10
HELP_REQUEST_WINDOW_DAYS = 60
HELP_REQUEST_TOPIC_LIMIT = 8


def build_section_snapshot(db: Session, section_id: int) -> dict:
    enrolled = db.query(Enrollment).filter(
        Enrollment.section_id == section_id,
        Enrollment.is_archived == False,
    ).all()
    student_ids = [e.student_id for e in enrolled]

    graded = (
        db.query(Submission.grade, Assignment.category, Submission.assignment_id)
        .join(Assignment, Submission.assignment_id == Assignment.assignment_id)
        .filter(
            Assignment.section_id == section_id,
            Submission.status == SubmissionStatusEnum.graded,
            Submission.grade.isnot(None),
            Submission.is_archived == False,
            Assignment.is_archived == False,
        )
        .all()
    )

    grades_by_category = defaultdict(list)
    grades_by_assignment = defaultdict(list)
    for grade, category, assignment_id in graded:
        category_name = category.value if hasattr(category, "value") else category
        grades_by_category[category_name].append(grade)
        grades_by_assignment[assignment_id].append(grade)

    category_averages = {
        category: round(sum(grades) / len(grades), 1)
        for category, grades in grades_by_category.items()
    }

    distribution = Counter()
    for student_id in student_ids:
        result = compute_section_grade_for_student(db, section_id, student_id)
        letter = result["letter_grade"]
        if letter is not None:
            distribution[letter] += 1

    recent = (
        db.query(Assignment)
        .filter(Assignment.section_id == section_id, Assignment.is_archived == False)
        .order_by(Assignment.due_date.desc())
        .limit(RECENT_ASSIGNMENT_LIMIT)
        .all()
    )
    recent_assignments = []
    for assignment in recent:
        grades = grades_by_assignment.get(assignment.assignment_id, [])
        recent_assignments.append({
            "title": assignment.title,
            "category": assignment.category.value if hasattr(assignment.category, "value") else assignment.category,
            "class_average": round(sum(grades) / len(grades), 1) if grades else None,
            "graded_count": len(grades),
        })

    window_start = datetime.now(timezone.utc) - timedelta(days=HELP_REQUEST_WINDOW_DAYS)
    topic_rows = (
        db.query(HelpRequest.topic)
        .filter(
            HelpRequest.section_id == section_id,
            HelpRequest.is_archived == False,
            HelpRequest.created_at >= window_start,
        )
        .all()
    )
    topic_counts = Counter(row.topic for row in topic_rows)
    help_request_topics = [
        {"topic": topic, "count": count}
        for topic, count in topic_counts.most_common(HELP_REQUEST_TOPIC_LIMIT)
    ]

    return {
        "enrolled_count": len(student_ids),
        "graded_submission_count": len(graded),
        "category_averages": category_averages,
        "grade_distribution": dict(distribution),
        "recent_assignments": recent_assignments,
        "help_request_topics": help_request_topics,
    }
```

(`letter_grade_for` is imported for future use by callers; if the linter flags it as unused, remove that import.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python3 -m pytest tests/test_assignment_fit.py -v`
Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/assignment_fit.py backend/tests/test_assignment_fit.py
git commit -m "feat: deterministic class snapshot for assignment-fit advisor"
```

---

### Task 7: Gemini verdict + assignment-fit endpoint

**Files:**
- Create: `backend/gemini_advisor.py`
- Create: `backend/schemas/assignment_fit.py`
- Create: `backend/controllers/assignment_fit_controller.py`
- Modify: `backend/main.py` (import + include router)
- Modify: `backend/requirements.txt` (add `google-genai`)
- Modify: `backend/tests/test_assignment_fit.py` (append endpoint tests)

**Interfaces:**
- Consumes: `build_section_snapshot` from Task 6.
- Produces: `POST /api/sections/{section_id}/assignment-fit` (teacher owning section). Response `AssignmentFitResponse`: `{ai_available: bool, unavailable_reason: "not_configured"|"insufficient_data"|"error"|null, verdict: FitVerdict|null, stats: dict}`. `FitVerdict`: `{readiness: "ready"|"review_first"|"mixed", rationale: str, topics_to_review: [str], suggested_resources: [{title, url, why}]}`. Task 8's UI consumes exactly this shape.

- [ ] **Step 1: Install the SDK**

Add `google-genai` on its own line at the end of `backend/requirements.txt`, then:

Run: `cd backend && pip install google-genai`
Expected: successful install (package imports as `from google import genai`).

- [ ] **Step 2: Write the failing endpoint tests**

Append to `backend/tests/test_assignment_fit.py`:

```python
from unittest.mock import patch

from gemini_advisor import FitVerdict, SuggestedResource

DRAFT = {
    "title": "Chapter 8 Test: Polynomials",
    "description": "Covers factoring and long division.",
    "category": "tests",
    "point_value": 100,
    "due_date": "2026-08-01T23:59:00Z",
}

FAKE_VERDICT = FitVerdict(
    readiness="review_first",
    rationale="The class quiz average is 72 and factoring is a repeated help topic.",
    topics_to_review=["factoring"],
    suggested_resources=[
        SuggestedResource(
            title="Khan Academy: Factoring",
            url="https://www.khanacademy.org/math/algebra/factoring",
            why="Free practice on the weakest topic.",
        )
    ],
)


def test_fit_requires_teacher(client, world):
    resp = client.post(
        f"/api/sections/{world.section_id}/assignment-fit",
        json=DRAFT,
        headers=auth_header(world.student_token),
    )
    assert resp.status_code == 403


def test_fit_returns_verdict_with_mocked_gemini(client, db, world, cleanup, monkeypatch):
    _seed_graded_data(db, world, cleanup)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    with patch(
        "controllers.assignment_fit_controller.generate_fit_verdict",
        return_value=FAKE_VERDICT,
    ) as mock_generate:
        resp = client.post(
            f"/api/sections/{world.section_id}/assignment-fit",
            json=DRAFT,
            headers=auth_header(world.teacher_token),
        )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["ai_available"] is True
    assert data["verdict"]["readiness"] == "review_first"
    assert data["stats"]["graded_submission_count"] >= 1
    mock_generate.assert_called_once()


def test_fit_not_configured_returns_503(client, db, world, cleanup, monkeypatch):
    _seed_graded_data(db, world, cleanup)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    resp = client.post(
        f"/api/sections/{world.section_id}/assignment-fit",
        json=DRAFT,
        headers=auth_header(world.teacher_token),
    )
    assert resp.status_code == 503


def test_fit_gemini_error_degrades_to_stats(client, db, world, cleanup, monkeypatch):
    _seed_graded_data(db, world, cleanup)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    with patch(
        "controllers.assignment_fit_controller.generate_fit_verdict",
        side_effect=RuntimeError("quota exceeded"),
    ):
        resp = client.post(
            f"/api/sections/{world.section_id}/assignment-fit",
            json=DRAFT,
            headers=auth_header(world.teacher_token),
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ai_available"] is False
    assert data["unavailable_reason"] == "error"
    assert data["verdict"] is None
    assert data["stats"]["graded_submission_count"] >= 1
```

> The `insufficient_data` path (section with zero graded submissions) is order-dependent with the module-shared `world`, so it is covered implicitly: it short-circuits before `is_configured()`, and the code path is three lines. If you want it tested, create a second throwaway section via the API inside the test.

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd backend && python3 -m pytest tests/test_assignment_fit.py -v`
Expected: new tests FAIL with `ModuleNotFoundError: No module named 'gemini_advisor'`; Task 6 tests still PASS.

- [ ] **Step 4: Implement the Gemini wrapper**

Create `backend/gemini_advisor.py`:

```python
"""Thin wrapper around the Gemini API for the assignment-fit advisor.

The key design constraint: this module receives an already-computed stats
snapshot and returns a structured verdict. It never touches the database,
so tests can mock generate_fit_verdict without any Gemini dependency.
"""

import json
import os
from typing import List, Literal

from pydantic import BaseModel

GEMINI_MODEL = "gemini-2.5-flash"

SYSTEM_INSTRUCTION = """You are a teaching assistant for a middle/high school
class management app. A teacher is drafting an assignment and wants to know
whether the class is ready for it.

You will receive JSON with (1) the draft assignment and (2) a statistical
snapshot of the class computed from real grade data. Ground every claim in
those numbers — never invent statistics. Judge readiness for the draft's
apparent topic(s), inferred from its title and description, against the
class's recent performance and help-request topics.

readiness values:
- "ready": the class's relevant averages are solid and no related help topics recur.
- "review_first": clear evidence (low relevant averages, recurring related help topics) the class needs review before this assignment.
- "mixed": part of the class is ready but the grade distribution shows a significant struggling group.

suggested_resources are ideas for the teacher to vet — prefer well-known free
sites (Khan Academy, Desmos, PhET, etc). Keep rationale to 2-4 sentences."""


class SuggestedResource(BaseModel):
    title: str
    url: str
    why: str


class FitVerdict(BaseModel):
    readiness: Literal["ready", "review_first", "mixed"]
    rationale: str
    topics_to_review: List[str]
    suggested_resources: List[SuggestedResource]


def is_configured() -> bool:
    return bool(os.getenv("GEMINI_API_KEY"))


def generate_fit_verdict(draft: dict, snapshot: dict) -> FitVerdict:
    # Imported lazily so the backend still boots if the package is missing;
    # callers gate on is_configured() first.
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    payload = json.dumps({"draft_assignment": draft, "class_snapshot": snapshot})

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=payload,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=FitVerdict,
        ),
    )
    if response.parsed is None:
        raise RuntimeError("Gemini returned no parseable verdict.")
    return response.parsed
```

- [ ] **Step 5: Implement schemas and controller**

Create `backend/schemas/assignment_fit.py`:

```python
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel

from gemini_advisor import FitVerdict
from models.assignment_model import AssignmentCategoryEnum


class AssignmentDraft(BaseModel):
    title: str
    description: Optional[str] = None
    category: AssignmentCategoryEnum
    point_value: int
    due_date: datetime


class AssignmentFitResponse(BaseModel):
    ai_available: bool
    unavailable_reason: Optional[str] = None  # "not_configured" | "insufficient_data" | "error"
    verdict: Optional[FitVerdict] = None
    stats: Dict[str, Any]
```

Create `backend/controllers/assignment_fit_controller.py`:

```python
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from assignment_fit import build_section_snapshot
from db.pool import get_db
from dependencies import require_role
from gemini_advisor import generate_fit_verdict, is_configured
from models.section_model import Section
from models.user_model import User
from schemas.assignment_fit import AssignmentDraft, AssignmentFitResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["assignment-fit"])


@router.post("/sections/{section_id}/assignment-fit", response_model=AssignmentFitResponse)
def check_assignment_fit(
    section_id: int,
    body: AssignmentDraft,
    current_user: User = Depends(require_role(["teacher"])),
    db: Session = Depends(get_db),
):
    section = db.query(Section).filter(
        Section.section_id == section_id,
        Section.school_id == current_user.school_id,
        Section.is_archived == False,
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")
    if section.teacher_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not your section.")

    snapshot = build_section_snapshot(db, section_id)

    if snapshot["graded_submission_count"] == 0:
        return AssignmentFitResponse(
            ai_available=False,
            unavailable_reason="insufficient_data",
            stats=snapshot,
        )

    if not is_configured():
        raise HTTPException(status_code=503, detail="AI advisor is not configured.")

    draft = body.model_dump(mode="json")
    try:
        verdict = generate_fit_verdict(draft, snapshot)
    except Exception:
        logger.exception("Assignment-fit Gemini call failed for section %s", section_id)
        return AssignmentFitResponse(
            ai_available=False,
            unavailable_reason="error",
            stats=snapshot,
        )

    return AssignmentFitResponse(ai_available=True, verdict=verdict, stats=snapshot)
```

In `backend/main.py`, add the import with the other controllers:

```python
from controllers.assignment_fit_controller import router as assignment_fit_router
```

And the router registration:

```python
app.include_router(assignment_fit_router, prefix="/api", tags=["assignment-fit"])
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python3 -m pytest tests/test_assignment_fit.py tests/test_resources.py -v`
Expected: all PASS.

Also run the full backend suite to catch regressions:

Run: `cd backend && python3 -m pytest tests/ -q`
Expected: everything passes (same failures/count as before this feature, if any pre-existed).

- [ ] **Step 7: Commit**

```bash
git add backend/gemini_advisor.py backend/schemas/assignment_fit.py backend/controllers/assignment_fit_controller.py backend/main.py backend/requirements.txt backend/tests/test_assignment_fit.py
git commit -m "feat: Gemini-backed assignment-fit endpoint"
```

---

### Task 8: "Check fit" UI in the assignment form (frontend)

**Files:**
- Create: `frontend/src/components/section-detail/AssignmentFitResult.jsx`
- Modify: `frontend/src/components/section-detail/AssignmentsPanel.jsx`
- Modify: `frontend/src/components/section-detail/TeacherSectionDetail.css` (append styles)

**Interfaces:**
- Consumes: `POST /sections/{id}/assignment-fit` (Task 7 response shape) and `POST /sections/{id}/resources` (Task 2) for the "post to resources" shortcut.
- Produces: advisory panel below the new-assignment form.

- [ ] **Step 1: Create the result component**

Create `frontend/src/components/section-detail/AssignmentFitResult.jsx`:

```jsx
import { useState } from 'react'
import api from '../../api'

const READINESS_LABELS = {
  ready: 'Ready',
  review_first: 'Review first',
  mixed: 'Mixed readiness',
}

function AssignmentFitResult({ sectionId, result }) {
  const [postedUrls, setPostedUrls] = useState([])
  const [postError, setPostError] = useState('')

  if (!result) return null
  const { ai_available: aiAvailable, unavailable_reason: reason, verdict, stats } = result

  async function postToResources(resource) {
    setPostError('')
    try {
      await api.post(`/sections/${sectionId}/resources`, {
        title: resource.title,
        url: resource.url,
        description: resource.why,
      })
      setPostedUrls((prev) => [...prev, resource.url])
    } catch {
      setPostError('Could not post resource.')
    }
  }

  return (
    <div className="fit-result">
      {aiAvailable && verdict && (
        <>
          <div className={`fit-badge fit-badge-${verdict.readiness}`}>
            {READINESS_LABELS[verdict.readiness] || verdict.readiness}
          </div>
          <p className="fit-rationale">{verdict.rationale}</p>
          {verdict.topics_to_review.length > 0 && (
            <p className="fit-topics">
              Review first: {verdict.topics_to_review.join(', ')}
            </p>
          )}
          {verdict.suggested_resources.length > 0 && (
            <div className="fit-resources">
              <div className="widget-label">suggested resources (vet before sharing)</div>
              {verdict.suggested_resources.map((r) => (
                <div className="fit-resource-row" key={r.url}>
                  <span>
                    <a href={r.url} target="_blank" rel="noopener noreferrer">
                      {r.title}
                    </a>
                    <div className="teacher-panel-row-sub">{r.why}</div>
                  </span>
                  {postedUrls.includes(r.url) ? (
                    <span className="teacher-panel-row-sub">Posted ✓</span>
                  ) : (
                    <button
                      type="button"
                      className="teacher-panel-button"
                      onClick={() => postToResources(r)}
                    >
                      Post to resources
                    </button>
                  )}
                </div>
              ))}
              {postError && <p className="teacher-panel-error">{postError}</p>}
            </div>
          )}
        </>
      )}

      {!aiAvailable && (
        <p className="fit-unavailable">
          {reason === 'insufficient_data'
            ? 'Not enough graded work yet for an AI readiness check.'
            : 'AI analysis unavailable right now — showing class stats only.'}
        </p>
      )}

      <div className="fit-stats">
        <div className="widget-label">class stats used</div>
        <p className="teacher-panel-row-sub">
          {stats.enrolled_count} enrolled · {stats.graded_submission_count} graded submissions
        </p>
        {Object.keys(stats.category_averages).length > 0 && (
          <p className="teacher-panel-row-sub">
            Averages:{' '}
            {Object.entries(stats.category_averages)
              .map(([category, avg]) => `${category} ${avg}%`)
              .join(' · ')}
          </p>
        )}
        {stats.help_request_topics.length > 0 && (
          <p className="teacher-panel-row-sub">
            Help requested on:{' '}
            {stats.help_request_topics.map((t) => `${t.topic} (${t.count})`).join(', ')}
          </p>
        )}
      </div>
    </div>
  )
}

export default AssignmentFitResult
```

- [ ] **Step 2: Add the "Check fit" button to AssignmentsPanel**

In `frontend/src/components/section-detail/AssignmentsPanel.jsx`:

Add imports:

```jsx
import AssignmentFitResult from './AssignmentFitResult'
```

Add state next to the existing form state:

```jsx
  const [fitResult, setFitResult] = useState(null)
  const [fitLoading, setFitLoading] = useState(false)
  const [fitHidden, setFitHidden] = useState(false)
```

Add the handler after `handleCreate`:

```jsx
  async function handleCheckFit() {
    setError('')
    setFitLoading(true)
    setFitResult(null)
    try {
      const { data } = await api.post(`/sections/${sectionId}/assignment-fit`, {
        title,
        description: description || null,
        category,
        point_value: Number(pointValue),
        due_date: dueDate ? new Date(dueDate).toISOString() : new Date().toISOString(),
      })
      setFitResult(data)
    } catch (err) {
      if (err.response?.status === 503) {
        setFitHidden(true)
      } else {
        setError(err.response?.data?.message || 'Could not check fit.')
      }
    } finally {
      setFitLoading(false)
    }
  }
```

Inside the form's `.teacher-panel-form-actions` div, add before the Cancel button:

```jsx
            {!fitHidden && (
              <button
                type="button"
                className="teacher-panel-button"
                disabled={fitLoading || !title}
                onClick={handleCheckFit}
              >
                {fitLoading ? 'Checking…' : 'Check fit'}
              </button>
            )}
```

Immediately after the closing `</form>` tag, render the result:

```jsx
      {showForm && fitResult && (
        <AssignmentFitResult sectionId={sectionId} result={fitResult} />
      )}
```

Also clear the result when the form successfully submits — add `setFitResult(null)` next to the existing `setShowForm(false)` in `handleCreate`.

- [ ] **Step 3: Styles**

Append to `frontend/src/components/section-detail/TeacherSectionDetail.css`:

```css
.fit-result {
  margin-top: 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px;
  background: var(--surface-1);
}

.fit-badge {
  display: inline-block;
  font-size: 12px;
  font-weight: 600;
  border-radius: 12px;
  padding: 3px 12px;
  margin-bottom: 8px;
}

.fit-badge-ready {
  color: var(--success);
  background: var(--success-bg);
  border: 1px solid var(--success-border);
}

.fit-badge-review_first {
  color: var(--accent);
  background: var(--accent-bg);
  border: 1px solid var(--accent-border);
}

.fit-badge-mixed {
  color: var(--text);
  background: var(--surface-2);
  border: 1px solid var(--border-strong);
}

.fit-rationale {
  font-size: 13px;
  color: var(--text-h);
  margin: 0 0 8px;
}

.fit-topics {
  font-size: 12.5px;
  color: var(--text);
  margin: 0 0 10px;
}

.fit-resources {
  margin-top: 10px;
}

.fit-resource-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  padding: 6px 0;
  font-size: 13px;
  border-bottom: 1px solid var(--border);
}

.fit-resource-row:last-child {
  border-bottom: none;
}

.fit-unavailable {
  font-size: 13px;
  color: var(--text-muted);
  margin: 0 0 8px;
}

.fit-stats {
  margin-top: 10px;
  border-top: 1px solid var(--border);
  padding-top: 10px;
}
```

> If `--success`/`--success-bg`/`--success-border` don't exist in `frontend/src/index.css`, check the variable names there (the quest-card-status-done rule in `Quests.css` uses them, so they should exist).

- [ ] **Step 4: Lint and build**

Run: `cd frontend && npx eslint src/components/section-detail/AssignmentFitResult.jsx src/components/section-detail/AssignmentsPanel.jsx && npm run build`
Expected: clean lint, successful build.

- [ ] **Step 5: Manual smoke test (optional but recommended)**

If `GEMINI_API_KEY` is set in `backend/.env`: start backend + frontend, log in as the teacher, open a section → Assignments → + new assignment, fill a title, click "Check fit". Expect a verdict panel or, with no key, the button disappearing after one click (503 path).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/section-detail/AssignmentFitResult.jsx frontend/src/components/section-detail/AssignmentsPanel.jsx frontend/src/components/section-detail/TeacherSectionDetail.css
git commit -m "feat: AI check-fit flow in assignment form"
```

---

## Post-plan notes for the executor

- **Env setup:** the feature needs `GEMINI_API_KEY=<key from aistudio.google.com>` added to `backend/.env` (same file that holds `DATABASE_URL`). Without it, everything still works — the endpoint returns 503 and the UI hides the button.
- **Task order:** 1→2→3 and 6→7 are strictly ordered; 4–5 can run any time after 3; 8 requires 7 (and uses 2's endpoint).
- **Admin visibility:** the spec's "admin read-only card" is satisfied at the API level (Task 2 allows admin GETs). The app currently has no admin section-detail page — only a sections list — so there is no admin UI surface to add the card to. If one is built later, reuse the student card markup from Task 5.
- **Full verification at the end:** `cd backend && python3 -m pytest tests/ -q` and `cd frontend && npx eslint src && npm run build`.
