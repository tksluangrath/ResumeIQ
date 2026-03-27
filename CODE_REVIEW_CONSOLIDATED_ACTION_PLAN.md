# Phase 2 Code Review — Consolidated Action Plan

**Date:** 2026-03-25
**Phase Status:** Phase 2 (FastAPI + Streamlit MVP)
**Backend Status:** APPROVED WITH CONDITIONS (170 tests passing, v0.2.0)
**Frontend Status:** UNDER REVIEW (Streamlit UI not yet built)
**Deployment Readiness:** BLOCKED pending fixes

---

## Executive Summary

Two code reviews (FastAPI backend and Streamlit UI) have identified **8 critical issues**, **12 warnings**, and **11 minor issues** across both components. Of these, **5 are true blockers** for any production or demo deployment:

1. **Unbound variable crash on timeout** (Streamlit C1)
2. **Silent LaTeX render failures** (API C4)
3. **File buffer exhaustion** (Streamlit C4)
4. **Markdown injection vulnerability** (Streamlit C3)
5. **Dependency access outside lifespan** (API C2)

Additionally, **3 cross-cutting architectural issues** span both components and must be addressed holistically:
- Error handling fragility
- Type safety gaps
- Magic numbers and unvalidated input

---

## Section 1: Blocker Issues — Must Fix Before Demo/Prod

These 5 issues **MUST be resolved** before any public-facing deployment or demo.

| ID | Component | Issue | Impact | Fix Effort | Owner |
|----|-----------|----|--------|-----------|-------|
| **API-C2** | FastAPI | Dependency `KeyError` raised outside lifespan | Unhandled crash in tests or rare edge cases | Low (5 min) | backend-developer |
| **API-C4** | FastAPI | `except Exception: pass` swallows LaTeX render errors | Silent failures, corrupted output returned to user | Low (10 min) | backend-developer |
| **UI-C1** | Streamlit | `resp` unbound on timeout → `UnboundLocalError` | Unhandled exception, app crash on slow API | Low (10 min) | (needs assignment) |
| **UI-C4** | Streamlit | `file.read()` exhausts buffer; reruns send empty bytes | Duplicate submission silently fails or corrupts data | Low (5 min) | (needs assignment) |
| **UI-C3** | Streamlit | User-derived data rendered via `st.markdown` | Markdown injection/XSS risk | Low (10 min) | (needs assignment) |

**Subtotal Blocker Effort:** ~40 minutes

---

## Section 2: High-Priority Warnings — Must Fix Before Production

These 6 warnings directly impact security, stability, or data integrity. Fix after blockers but before any prod deployment.

| ID | Component | Issue | Impact | Fix Effort | Owner |
|----|-----------|----|--------|-----------|-------|
| **API-W2** | FastAPI | Sync CPU-bound work (spaCy, transformers) in `async def` routes | Event loop blocked; timeout + cascading failures | Medium (30–45 min) | backend-developer |
| **API-W1** | FastAPI | Content-type check spoofable — no magic bytes validation | Arbitrary file upload attack surface | Low (15 min) | backend-developer |
| **API-W4** | FastAPI | No server-level request body size limit | OOM / DoS risk | Low (5 min) | backend-developer |
| **UI-C2** | Streamlit | `resp.json()` crashes on non-JSON error responses | Unhandled exception when API returns HTML 502 | Low (10 min) | (needs assignment) |
| **UI-W1** | Streamlit | `breakdown` typed as bare `dict` instead of `ScoreBreakdown` | Type safety gap; fragile refactoring; violates CLAUDE.md | Medium (20 min) | (needs assignment) |
| **UI-W2** | Streamlit | Profile save uses raw `dict` instead of Pydantic models | Type safety gap; duplicates validator logic; violates CLAUDE.md Section 5 | Medium (30 min) | (needs assignment) |

**Subtotal High-Priority Effort:** ~2.5–3 hours

---

## Section 3: Cross-Cutting Issues — Architectural Debt

These problems appear in both API and UI and should be addressed holistically to prevent future recurrence.

### Error Handling Architecture

**Pattern:** Partial exception catching that hides true errors.

| Issue | API Location | UI Location | Root Cause | Fix Strategy |
|-------|--------------|-------------|-----------|--------------|
| Silent exception swallow | `routers/improve.py` (C4: `except Exception: pass`) | `streamlit_app.py` (W6: only `ConnectionError` caught) | No centralized error boundary | Create `ErrorResponse` Pydantic model; always log with context; return structured error or propagate |
| Unbound variables on edge cases | `dependencies.py` (C2: KeyError → unbound) | `streamlit_app.py` (C1: Timeout → unbound `resp`) | Missing exhaustive exception handling | Use context managers and ensure all code paths set variables before use |
| Non-JSON responses not handled | N/A | `streamlit_app.py` (C2) | Assumes all error responses are JSON | Wrap `resp.json()` in try/except; parse HTML fallback or return generic message |

**Fix:** Create a unified error response contract:
- All API errors return `{"error": str, "code": str, "detail": str}` (Pydantic `ErrorResponse` model)
- Streamlit always wraps HTTP calls in try/except for each exception type (Timeout, ConnectionError, HTTPError)
- Never silently swallow exceptions; always log with full context

**Effort:** Low–Medium (1–2 hours to implement consistently)

### Type Safety Gaps

**Pattern:** Bare `dict` returns and untyped session state violating CLAUDE.md Section 5.

| Issue | Location | Impact | Fix |
|-------|----------|--------|-----|
| `breakdown: dict` instead of `ScoreBreakdown` | `streamlit_app.py` line ~50 | Fragile; field renames break UI | Import `ScoreBreakdown` from `engine.scorer`; type hint session state |
| Profile save builds raw dict | `streamlit_app.py` line ~150 | Duplicates validation logic; data integrity risk | Use `UserProfile`, `WorkDetail`, `ProjectDetail`, `SkillEntry` models from `api.models` (or create if missing) |
| Session state type annotations are no-ops | `streamlit_app.py` line ~20 | Misleading; no runtime validation | Use Pydantic models or plain typed dicts; document session state shape in `api/models.py` |

**Fix:** Audit all Streamlit session state and API response handling; ensure every `dict` is a Pydantic model.

**Effort:** Medium (1–2 hours)

### Magic Numbers & Unvalidated Input

**Pattern:** Constants hardcoded or missing validation.

| Issue | Location | Solution |
|-------|----------|----------|
| JD minimum length hardcoded (50) | `streamlit_app.py` | Pull from `config.MIN_JD_CHARS` (via API Settings) |
| Validation constants duplicated | `routers/match.py` + `routers/improve.py` | Create `api/constants.py` or pull from `config.py` (single source of truth) |
| `.tex` extension assumed but not validated | `routers/improve.py` | Check file extension AND magic bytes (LaTeX files are UTF-8 text) |
| Score normalization heuristic (`raw <= 1.0`) | `streamlit_app.py` | Document and move to a constant or helper function |

**Fix:** Create `api/constants.py` with all validation limits; export from `config.py` if sensitive (API keys, limits).

**Effort:** Low (30 minutes)

---

## Section 4: Priority Matrix — What to Fix First

Grouped by effort and impact. **Bold = blocker or blocks demo**.

### Phase 1: Blockers (Must fix immediately — ~40 min)

Priority order (by criticality × ease):

1. **API-C2** (5 min) — Add RuntimeError guard in `dependencies.py` to catch KeyError on singleton access outside lifespan
2. **API-C4** (10 min) — Replace `except Exception: pass` with proper logging and error response in `routers/improve.py`
3. **UI-C4** (5 min) — Use `file.getvalue()` instead of `file.read()` in Streamlit
4. **UI-C1** (10 min) — Move `resp = None` to top of try block to prevent UnboundLocalError
5. **UI-C3** (10 min) — Use `st.code()` or escape Markdown when rendering user data

**Effort:** ~40 minutes
**Owner Assignment:** backend-developer (API-C2, C4); Streamlit developer (UI-C1, C4, C3)

---

### Phase 2: High-Priority Warnings (Fix before prod — ~3 hours)

Priority order (by risk):

1. **API-W1** (15 min) — Add magic bytes check (`%PDF-`) in `routers/match.py`
2. **API-W4** (5 min) — Set FastAPI `max_body_size` in `create_app()`
3. **API-C3** (10 min) — Add content-type + extension validation for `.tex` files
4. **UI-C2** (10 min) — Wrap `resp.json()` in try/except; handle non-JSON 502 responses
5. **API-W2** (45 min) — Refactor sync CPU-bound work to `def` routes or use `run_in_executor()` (see details below)
6. **UI-W1** (20 min) — Import `ScoreBreakdown` from engine; replace bare dict with typed model
7. **UI-W2** (30 min) — Refactor profile save to use Pydantic models (create if missing)

**Effort:** ~2.5–3 hours
**Owner Assignment:** backend-developer (API W1–W4); Streamlit developer (UI C2, W1, W2)

---

### Phase 3: Cross-Cutting Architecture (Fix for robustness — ~2–3 hours)

1. **Error handling unification** (1–2 hours)
   - Create `api/errors.py` with `ErrorResponse` Pydantic model
   - Audit all route exception handling
   - Update Streamlit to consistently catch Timeout, ConnectionError, HTTPError

2. **Magic numbers & constants** (30 min)
   - Create `api/constants.py` or add to `config.py`
   - Pull all validation constants to single source
   - Update Streamlit to import from config

3. **Type safety audit** (1 hour)
   - Review all session state and dict returns in Streamlit
   - Ensure Pydantic models used everywhere
   - Add missing models to `api/models.py` if needed

**Effort:** ~2–3 hours
**Owner Assignment:** code-reviewer + backend-developer (leading) + Streamlit developer

---

### Phase 4: Minor Issues (Optional improvements — ~1 hour)

These can be deferred until after demo but should be on the backlog:

- **API-M1:** Add router tags for OpenAPI docs (5 min)
- **API-M5:** Add `from __future__ import annotations` (5 min, should be done preemptively)
- **API-W3:** Extract timing logic to helper (15 min)
- **API-M3:** Add UTF-8 encoding check for `.tex` bytes (10 min)
- **API-W5:** Add thread-safety guard for `_state` dict on shutdown (20 min)
- **API-W6:** Sanitize Pydantic error messages (10 min)
- **UI-M1:** Use `httpx` instead of `requests` (modern-python alignment) (20 min)
- **UI-W3:** Split timeout into connect/read timeouts (10 min)
- **UI-W4:** Fix `st.rerun()` in removal loop (only first item removed) (15 min)
- **UI-W5:** Session state type annotations (10 min)
- **UI-M2–M6:** Various UI polish items (30 min total)

**Effort:** ~1–1.5 hours
**Owner Assignment:** Backlog for future sprints

---

## Section 5: Deployment Readiness Checklist

| Requirement | Status | Blocker? | Note |
|-------------|--------|----------|------|
| **Security** | CONDITIONAL | YES | C3 (Markdown injection), W1 (magic bytes), W4 (body size limit) must be fixed |
| **Error Handling** | CONDITIONAL | YES | C2, C4 (API), C1, C2 (Streamlit) must be fixed; then unified architecture |
| **Type Safety** | PARTIAL | NO | UI-W1, W2 violations of CLAUDE.md Section 5; should fix before prod |
| **Performance** | CONDITIONAL | YES | W2 (sync CPU work blocking async loop) must be fixed or app will timeout under load |
| **File Handling** | CONDITIONAL | YES | C4 (buffer exhaustion) must be fixed |
| **API Spec** | OK | NO | OpenAPI docs complete; minor tags can be added later |
| **Tests** | OK (170 passing) | NO | Backend tests comprehensive; Streamlit needs test framework (Phase 3) |
| **Documentation** | PARTIAL | NO | MISTAKES.md exists; need deployment/Streamlit docs |

---

## Section 6: Assignment & Timeline

### Immediate (Today — ~1 hour)

**Blockers only:**

- **backend-developer:** Fix API-C2, API-C4, API-C3 (~25 min)
- **Streamlit dev (TBD):** Fix UI-C1, UI-C4, UI-C3 (~25 min)
- **Project Manager:** Track and sign off (~5 min)

### Tomorrow/This Week (~3 hours)

**High-Priority Warnings + Cross-Cutting:**

- **backend-developer:** API-W1, W2, W4 + start error architecture
- **Streamlit dev:** UI-C2, W1, W2 + start error architecture
- **code-reviewer:** Audit type safety gaps, validate fixes

### Next Week (~1 hour)

**Minor issues + Polish:**

- Backlog for continuous improvement
- Update documentation (SETUP.md, API docs)

---

## Section 7: Final Sign-Off Verdict

### APPROVED WITH CONDITIONS

**Current State:**
- FastAPI backend: **170 tests passing**, v0.2.0 stable
- Streamlit UI: **Not yet built** (next sprint)
- Deployment: **BLOCKED pending blocker fixes**

**Conditions for Approval:**

1. **Must fix (Blockers)** — API-C2, C4; UI-C1, C3, C4
   - ETA: Today (1 hour)
   - Sign-off: When all blockers pass test suite

2. **Must fix (High-Priority)** — API-W1, W2, W4; UI-C2, W1, W2
   - ETA: By end of week
   - Sign-off: When performance test shows no event loop blocking; type checking passes

3. **Should fix (Architecture)** — Error handling unification, type safety audit
   - ETA: Before any production deploy
   - Sign-off: Code review confirms no more silent failures or bare dicts

4. **Can defer (Minor)** — OpenAPI tags, timing extraction, etc.
   - ETA: Post-demo, nice-to-have
   - Sign-off: Not required for initial release

### Demo Readiness

**Can proceed to demo** once Blockers (Phase 1) are fixed and High-Priority warnings are mitigated:
- Internal demo: After blockers fixed (~today)
- Stakeholder demo: After full Phase 2 warning fixes (~by Friday)
- Public/production deploy: Only after Section 7 conditions fully met

### Risk Flags

- **Critical:** Event loop blocking (API-W2) will cause timeouts under moderate load. Must fix before any stress test.
- **Critical:** Silent LaTeX failures (API-C4) could return corrupted output to users. Must add logging + error response.
- **High:** Type safety gaps (UI-W1, W2) will make Phase 3 (LLM integration) harder. Fix proactively.
- **Medium:** Markdown injection (UI-C3) is low-probability but high-severity. Simple fix worth doing immediately.

---

## Section 8: Detailed Fix Guidance

### API-C2: Dependency KeyError Outside Lifespan

**File:** `api/dependencies.py`

**Current Issue:**
```python
def get_engine() -> MatchEngine:
    engine = app.state.engine
    # Raises KeyError if called outside lifespan
```

**Fix:** Add guard with clear error message
```python
def get_engine() -> MatchEngine:
    engine = getattr(app.state, "engine", None)
    if engine is None:
        raise RuntimeError(
            "Engine not initialized. This usually means the app lifespan did not complete. "
            "Check app.state._initialized flag or restart the server."
        )
    return engine
```

---

### API-C4: Silent LaTeX Render Failures

**File:** `api/routers/improve.py`

**Current Issue:**
```python
try:
    tex_bytes = subprocess.run(...)
except Exception:
    pass  # Silent failure!
```

**Fix:** Log error and return error response
```python
import logging

logger = logging.getLogger(__name__)

try:
    tex_bytes = subprocess.run(...)
except Exception as e:
    logger.error(f"LaTeX render failed: {e}", exc_info=True)
    raise HTTPException(
        status_code=400,
        detail=f"LaTeX rendering failed: {str(e)}"
    )
```

---

### API-W2: Sync CPU Work Blocking Event Loop

**File:** `api/routers/match.py` and `api/routers/improve.py`

**Current Issue:**
```python
@router.post("/match")
async def match_route(file: UploadFile):
    text = await engine.parse_pdf(file)  # Assuming async, but spaCy NER is sync!
    scores = engine.score(text)  # Blocking call in async context
```

**Fix Pattern 1 (Preferred for heavy ops):** Use `run_in_executor()`
```python
import asyncio

@router.post("/match")
async def match_route(file: UploadFile):
    loop = asyncio.get_event_loop()
    text = await parse_pdf_async(file)  # Already async
    scores = await loop.run_in_executor(None, engine.score, text)
    return MatchResponse(...)
```

**Fix Pattern 2 (If routes can be sync):** Use sync routes
```python
@router.post("/match")
def match_route(file: UploadFile):  # No async
    text = engine.parse_pdf(file)
    scores = engine.score(text)
    return MatchResponse(...)
```

**Recommendation:** Convert routes to sync since the matching engine has no I/O. Async FastAPI can still handle concurrency via multiple worker processes (uvicorn workers).

---

### UI-C1: Unbound `resp` Variable on Timeout

**File:** `ui/streamlit_app.py`

**Current Issue:**
```python
try:
    resp = requests.post(url, ...)
except ConnectionError as e:
    st.error(f"Connection failed: {e}")
# If Timeout was raised, resp is unbound → UnboundLocalError on next line
result = resp.json()  # Crash!
```

**Fix:** Initialize `resp` before try or move logic into except
```python
resp = None
try:
    resp = requests.post(url, ...)
except (ConnectionError, Timeout) as e:
    st.error(f"Connection failed: {e}")
    st.stop()  # Exit early

# If we get here, resp is guaranteed to be set
result = resp.json()
```

Or better:
```python
try:
    resp = requests.post(url, ...)
except (ConnectionError, Timeout) as e:
    st.error(f"Connection failed: {e}")
    return  # Exit early
except Exception as e:
    st.error(f"Unexpected error: {e}")
    return

result = resp.json()
```

---

### UI-C3: Markdown Injection via User Data

**File:** `ui/streamlit_app.py`

**Current Issue:**
```python
st.markdown(f"**Matched Score:** {api_data['score']}")  # User data!
```

If API returns `score: "**PWNED**"`, it renders as bold.

**Fix:** Use `st.code()`, `st.text()`, or escape Markdown
```python
# Option 1: Use text() for untrusted input
st.text(f"Matched Score: {api_data['score']}")

# Option 2: Use code() for structured data
st.code(json.dumps(api_data, indent=2))

# Option 3: Escape Markdown
import html
st.markdown(f"**Matched Score:** {html.escape(api_data['score'])}")
```

---

### UI-C4: File Buffer Exhaustion

**File:** `ui/streamlit_app.py`

**Current Issue:**
```python
uploaded_file = st.file_uploader(...)
pdf_bytes = uploaded_file.read()  # Consumes buffer
# Later...
pdf_bytes = uploaded_file.read()  # Returns empty bytes!
```

**Fix:** Use `getvalue()` instead
```python
uploaded_file = st.file_uploader(...)
pdf_bytes = uploaded_file.getvalue()  # Always returns full bytes, no state
# Later...
pdf_bytes = uploaded_file.getvalue()  # Same full bytes
```

---

### UI-W1 & W2: Type Safety — Use Pydantic Models

**File:** `ui/streamlit_app.py`

**Current Issue:**
```python
breakdown: dict = api_response.get("breakdown")  # No type safety!
profile = {
    "name": st.text_input("Name"),
    "skills": [...]  # Raw dict
}
```

**Fix:** Import and use models from `api.models`
```python
from api.models import ScoreBreakdown, UserProfile, SkillEntry

# In Streamlit logic:
response_data = api_response  # Assume api_response is dict
breakdown = ScoreBreakdown(**response_data["breakdown"])  # Validate at boundary

# For profile:
profile = UserProfile(
    name=st.text_input("Name"),
    skills=[
        SkillEntry(name=s, proficiency="expert")
        for s in st.multiselect("Skills", [...])
    ]
)
```

---

### API-W1: Magic Bytes Check for PDFs

**File:** `api/routers/match.py`

**Current Issue:**
```python
if not file.filename.endswith(".pdf"):
    raise HTTPException(status_code=400, detail="Must be PDF")
# But filename can be spoofed!
```

**Fix:** Check magic bytes
```python
PDF_MAGIC = b"%PDF-"

pdf_bytes = await file.read()
if not pdf_bytes.startswith(PDF_MAGIC):
    raise HTTPException(status_code=400, detail="Invalid PDF: not a valid PDF file")
```

---

### API-W4: Request Body Size Limit

**File:** `api/main.py`

**Current Issue:**
```python
app = FastAPI()
# No limit on request body size
```

**Fix:** Set limit in create_app
```python
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

def create_app() -> FastAPI:
    app = FastAPI()

    # Set max body size (e.g., 50 MB)
    app.add_middleware(
        BaseHTTPMiddleware,
        dispatch=limit_body_size_middleware(max_bytes=50 * 1024 * 1024)
    )

    return app

async def limit_body_size_middleware(request: Request, call_next, max_bytes: int):
    if request.headers.get("content-length", 0) > max_bytes:
        return JSONResponse(
            status_code=413,
            content={"error": "Payload too large"}
        )
    return await call_next(request)
```

Or simpler — use uvicorn config:
```bash
uvicorn api.main:app --limit-max-requests 0 --limit-concurrency 10 --max-body-size 52428800
```

---

### UI-C2: Handle Non-JSON Error Responses

**File:** `ui/streamlit_app.py`

**Current Issue:**
```python
if resp.status_code != 200:
    data = resp.json()  # Crashes if resp is HTML 502 from nginx
```

**Fix:** Safe JSON parsing with fallback
```python
if resp.status_code != 200:
    try:
        data = resp.json()
    except ValueError:
        # Not JSON; probably HTML error page
        st.error(f"Server error (HTTP {resp.status_code}). Try again later.")
        return
    st.error(f"API error: {data.get('error', 'Unknown error')}")
    return
```

---

## Section 9: Testing & Validation Strategy

After fixes are applied:

1. **Run existing test suite:**
   ```bash
   pytest tests/ -v --tb=short
   ```

2. **Add new tests for fixes:**
   - Test that `get_engine()` raises RuntimeError when engine is None (API-C2)
   - Test LaTeX error logging (API-C4)
   - Test `file.getvalue()` doesn't corrupt on rerun (UI-C4)
   - Test `UnboundLocalError` doesn't occur on Timeout (UI-C1)
   - Test Markdown escaping (UI-C3)
   - Test magic bytes validation (API-W1)

3. **Manual testing:**
   - Upload non-PDF file; verify 400 error (W1)
   - Trigger LaTeX error (e.g., bad template); verify structured error response (C4)
   - Test file reupload in Streamlit; verify bytes are correct (C4)
   - Slow API by 30s; verify Streamlit timeout + error message (C1)

4. **Load test after W2 fix:**
   ```bash
   # Simulate 10 concurrent requests
   ab -n 100 -c 10 http://localhost:8000/match
   ```

---

## Section 10: Appendix — Issue Summary Table

All 23 issues across both components in priority order.

| Rank | ID | Component | Severity | Type | Title | Est. Fix (min) | Owner |
|------|----|-----------|----|------|-------|-----------|-------|
| 1 | API-C2 | FastAPI | Critical | Safety | Dependency KeyError outside lifespan | 5 | backend-dev |
| 2 | API-C4 | FastAPI | Critical | Logging | Silent LaTeX render failures | 10 | backend-dev |
| 3 | UI-C1 | Streamlit | Critical | Safety | Unbound `resp` on Timeout | 10 | UI-dev |
| 4 | UI-C4 | Streamlit | Critical | Data | File buffer exhaustion | 5 | UI-dev |
| 5 | UI-C3 | Streamlit | Critical | Security | Markdown injection | 10 | UI-dev |
| 6 | API-W1 | FastAPI | High | Security | Content-type spoofing | 15 | backend-dev |
| 7 | API-W4 | FastAPI | High | Safety | No request body size limit | 5 | backend-dev |
| 8 | API-C3 | FastAPI | High | Security | No .tex extension validation | 10 | backend-dev |
| 9 | UI-C2 | Streamlit | High | Safety | Non-JSON error response crash | 10 | UI-dev |
| 10 | API-W2 | FastAPI | High | Performance | Sync CPU work blocks event loop | 45 | backend-dev |
| 11 | UI-W1 | Streamlit | High | Type Safety | `breakdown: dict` not typed | 20 | UI-dev |
| 12 | UI-W2 | Streamlit | High | Type Safety | Profile save uses raw dict | 30 | UI-dev |
| 13 | API-W3 | FastAPI | Medium | Code Quality | Duplicate validation constants | 15 | backend-dev |
| 14 | API-M1 | FastAPI | Minor | Docs | Router tags missing | 5 | backend-dev |
| 15 | API-M2 | FastAPI | Minor | Code Quality | Timing logic duplicated | 15 | backend-dev |
| 16 | API-M3 | FastAPI | Minor | Validation | No UTF-8 encoding check for .tex | 10 | backend-dev |
| 17 | API-M4 | FastAPI | Minor | Design | `settings` could be route dependency | 10 | backend-dev |
| 18 | API-M5 | FastAPI | Minor | Code Quality | Missing `from __future__ import annotations` | 5 | backend-dev |
| 19 | API-W5 | FastAPI | Medium | Safety | No thread-safety guard on `_state` | 20 | backend-dev |
| 20 | API-W6 | FastAPI | Medium | Security | Error messages leak Pydantic field names | 10 | backend-dev |
| 21 | UI-M1 | Streamlit | Minor | Modernization | Use `httpx` over `requests` | 20 | UI-dev |
| 22 | UI-W3 | Streamlit | Medium | Config | Timeout not split into connect/read | 10 | UI-dev |
| 23 | UI-W4 | Streamlit | Medium | Bug | `st.rerun()` in removal loop | 15 | UI-dev |

**Total Effort:**
- Blockers (1–5): 40 min
- High-Priority (6–12): 2.5–3 hours
- Medium (13, 19, 20, 23): 1 hour
- Minor (14–18, 21): 1 hour
- **Grand Total:** ~5–6 hours of development time

---

## Sign-Off

**Project Manager:** Ready to proceed with Phase 2 completion upon blocker fixes.

**Status:** APPROVED WITH CONDITIONS

**Next Steps:**
1. Assign Streamlit developer for UI fixes
2. Complete blocker fixes today
3. High-priority fixes by end of week
4. Internal demo after blockers, stakeholder demo after high-priority fixes
5. Update MISTAKES.md with lessons from these reviews

**Questions?** Refer to Section 8 (Detailed Fix Guidance) for implementation details.

