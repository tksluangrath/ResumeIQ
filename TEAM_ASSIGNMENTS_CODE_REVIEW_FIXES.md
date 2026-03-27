# Code Review Fixes — Team Assignments & Roadmap

**Updated:** 2026-03-25
**Phase:** Phase 2 (FastAPI + Streamlit MVP)
**Status:** APPROVED WITH CONDITIONS

---

## Team 1: Backend (backend-developer)

### DAY 1 (TODAY) — Blockers [~25 min]

**Route:** `api/dependencies.py` → `api/routers/improve.py` → `api/routers/match.py`

1. **API-C2** (5 min) — Dependency Safety
   - File: `api/dependencies.py`
   - Function: `get_engine()` and `get_matcher()`
   - Change: Add `getattr(..., None)` guard; raise RuntimeError if None with clear message
   - Tests: Verify pytest still passes (no new tests needed unless there's a test that calls outside lifespan)
   - PR message: "Fix: Guard against KeyError when engine accessed outside lifespan"

2. **API-C4** (10 min) — LaTeX Error Handling
   - File: `api/routers/improve.py`
   - Function: Route that renders LaTeX (search for `except Exception: pass`)
   - Change: Replace with proper logging + HTTPException
   - Tests: Run pytest; no crash on bad LaTeX
   - PR message: "Fix: Log LaTeX render errors instead of silent failure"

3. **API-C3** (10 min) — .tex File Validation
   - File: `api/routers/improve.py`
   - Function: File upload handler
   - Change: Add extension check (`.endswith(".tex")`) + UTF-8 decode test
   - Tests: Try uploading .txt file as .tex; should 400
   - PR message: "Fix: Validate .tex file extension before upload"

**After Day 1:** Blockers resolved. Can schedule internal demo. Run full test suite:
```bash
pytest tests/ -v
```

---

### WEEK 1 (Days 2–5) — High-Priority Warnings [~1.5–2 hours]

**Route:** `api/routers/match.py` → `api/main.py` → refactor routes → constants

1. **API-W1** (15 min) — PDF Magic Bytes
   - File: `api/routers/match.py`
   - Function: POST /match handler
   - Change: After `file.read()`, check first 4 bytes `== b"%PDF-"` before parser
   - Tests: Try uploading `.txt` with `.pdf` extension; verify rejection
   - Reference: See CODE_REVIEW_CONSOLIDATED_ACTION_PLAN.md Section 8
   - PR message: "Fix: Validate PDF magic bytes to prevent spoofing"

2. **API-W4** (5 min) — Request Body Size Limit
   - File: `api/main.py`
   - Function: `create_app()`
   - Change: Add middleware or uvicorn flag `--max-body-size 52428800` (50 MB)
   - Tests: Try uploading 100 MB file; should return 413
   - PR message: "Fix: Add request body size limit to prevent OOM"

3. **API-W2** (45 min) — Sync CPU Work Blocking Event Loop
   - File: `api/routers/match.py`, `api/routers/improve.py`
   - Functions: All route handlers calling `engine.score()`, `engine.improve()`
   - Issue: These are sync CPU-bound (spaCy NER, sentence-transformers); block event loop in `async def`
   - Decision point:
     - **Option A (Preferred):** Convert routes to `def` (sync). FastAPI handles via thread pool.
     - **Option B:** Use `asyncio.get_event_loop().run_in_executor()` to offload to thread pool.
   - Change: Apply chosen option to all route handlers
   - Tests: Load test with `ab -n 100 -c 10 http://localhost:8000/match`; measure latency (should stay <500ms with 10 workers)
   - PR message: "Fix: Move CPU-bound work to executor or sync routes to prevent event loop blocking"

4. **API-W3 + M2 + M3 + M5** (30 min) — Code Quality Pass
   - File: All API files
   - Tasks:
     - W3: Deduplicate validation constants (MAX_PDF_BYTES, MIN_JD_CHARS, MAX_JD_CHARS) → create `api/constants.py` or consolidate in `config.py`
     - M2: Extract timing logic to `api/utils.py` helper
     - M3: Add UTF-8 encoding check for .tex bytes
     - M5: Add `from __future__ import annotations` to files missing it
   - Tests: `ruff check api/ && black api/`; manual review
   - PR message: "Refactor: Consolidate constants, add utils, improve code quality"

5. **API-W5 + W6** (20 min) — Safety & Error Messages
   - File: `api/dependencies.py`, `api/routers/`
   - Tasks:
     - W5: Add docstring/comment about thread-safety of `_state` dict on shutdown (or wrap in lock if needed)
     - W6: Sanitize Pydantic validation errors before returning to client
   - Tests: Manual test; no field name leakage in error responses
   - PR message: "Fix: Clarify thread-safety and sanitize error messages"

**After High-Priority:** All API routes are secure, performant, and well-structured. Can proceed to stakeholder demo.

---

### Checklist Before Sign-Off

- [ ] All blockers fixed and tests passing
- [ ] High-priority fixes merged and tested
- [ ] Load test passed (no event loop blocking)
- [ ] `pytest tests/ -v` — 170+ tests passing
- [ ] `ruff check api/ && black api/` — no style issues
- [ ] Code review by `code-reviewer` agent
- [ ] MISTAKES.md updated with lessons from W2 fix

---

## Team 2: Streamlit UI (TBD — Need Assignment)

**CRITICAL:** Streamlit developer has not yet been assigned. Backend team does not own UI code.

### DAY 1 (TODAY) — Blockers [~25 min]

**Route:** `ui/streamlit_app.py`

1. **UI-C4** (5 min) — File Buffer Exhaustion
   - File: `ui/streamlit_app.py`
   - Function: Wherever `st.file_uploader()` is used
   - Change: Replace `uploaded_file.read()` with `uploaded_file.getvalue()`
   - Reason: `.getvalue()` doesn't consume state; safe for reruns
   - Tests: Upload file twice; verify both times get full bytes (not empty second time)
   - PR message: "Fix: Use getvalue() instead of read() for file uploads to prevent buffer exhaustion"

2. **UI-C1** (10 min) — Unbound Variable on Timeout
   - File: `ui/streamlit_app.py`
   - Function: API call wrapper (search for `try:` and `requests.post`)
   - Issue: `resp` unbound if Timeout exception (not ConnectionError)
   - Change: Init `resp = None` before try, OR ensure all except branches exit early (use `return` or `st.stop()`)
   - Tests: Manually slow API to trigger timeout; verify error shown, no UnboundLocalError crash
   - PR message: "Fix: Prevent UnboundLocalError on API timeout"

3. **UI-C3** (10 min) — Markdown Injection
   - File: `ui/streamlit_app.py`
   - Function: Anywhere user-derived data is rendered via `st.markdown()`
   - Issue: User can inject Markdown or HTML
   - Change: Use `st.text()` for untrusted user data, or use `html.escape()` before markdown
   - Tests: Try entering `**BOLD**` in input field; verify it's shown as literal text, not bold
   - PR message: "Fix: Escape markdown injection in user-derived data"

**After Day 1:** Blockers resolved. Can show demo internally.

---

### WEEK 1 (Days 2–5) — High-Priority [~1.5–2 hours]

**Route:** Error handling → Type safety → Modernization

1. **UI-C2** (10 min) — Non-JSON Error Responses
   - File: `ui/streamlit_app.py`
   - Function: API call wrapper (same location as C1)
   - Issue: `resp.json()` crashes if server returns HTML (e.g., nginx 502)
   - Change: Wrap in try/except ValueError; show generic error message on HTML response
   - Tests: Mock 502 HTML response; verify graceful error display
   - PR message: "Fix: Handle non-JSON error responses gracefully"

2. **UI-W1** (20 min) — Type Safety: ScoreBreakdown
   - File: `ui/streamlit_app.py`
   - Function: Wherever match response is processed
   - Issue: `breakdown: dict` has no type safety; field renames break UI
   - Change: Import `ScoreBreakdown` from `engine.scorer`; use it to validate API response at boundary
   - Tests: Change `ScoreBreakdown` field in engine; verify Streamlit app catches error (or adapter handles it)
   - PR message: "Refactor: Use ScoreBreakdown Pydantic model instead of bare dict"

3. **UI-W2** (30 min) — Type Safety: User Profile Models
   - File: `ui/streamlit_app.py`
   - Function: Profile building/saving section
   - Issue: Profile save builds raw `dict` instead of Pydantic models
   - Change: Import `UserProfile`, `WorkDetail`, `ProjectDetail`, `SkillEntry` from `api.models` (create if missing); use them to build and validate profile
   - Tests: Try saving profile with invalid data (e.g., empty name); verify Pydantic validation error shown
   - PR message: "Refactor: Use Pydantic models for profile building (UserProfile, WorkDetail, etc.)"

4. **UI-M1** (20 min) — Modernization: httpx instead of requests
   - File: `ui/streamlit_app.py`
   - Rationale: `httpx` is modern-python aligned; has both sync and async; Streamlit is sync, so sync API fine
   - Change: Replace `import requests` with `import httpx`; update calls to `httpx.Client().post()`
   - Tests: Verify API calls still work
   - PR message: "Refactor: Replace requests with httpx for modern-python alignment"

5. **UI-W3 + W4 + Minor** (30 min) — Polish
   - W3: Split timeout into connect/read timeouts (separate params)
   - W4: Fix `st.rerun()` in removal loop (only first item deleted) — likely use list comprehension instead of loop
   - M2, M3, etc.: Hardcoded JD min length → config constant; type annotations cleanup
   - Tests: Manual testing of removal/rerun behavior
   - PR message: "Polish: Timeout tuning, rerun fix, config constants"

**After High-Priority:** UI is secure, typed, and modern. Can proceed to stakeholder demo.

---

### Checklist Before Sign-Off

- [ ] All blockers fixed
- [ ] High-priority fixes merged
- [ ] Manual testing: Upload, submit, save profile — all work
- [ ] API integration with backend tested (end-to-end)
- [ ] Error handling unified with backend expectations
- [ ] Code review by `code-reviewer` agent

---

## Coordinator Role: Project Manager

### DAY 1
- [ ] Confirm backend-developer assignment
- [ ] Assign Streamlit developer (TBD)
- [ ] Send quick reference card to both teams
- [ ] Monitor blocker fixes (5pm sign-off call)

### WEEK 1
- [ ] Daily standup on high-priority progress
- [ ] Flag any blockers to project momentum
- [ ] Prepare internal demo slides after blockers fixed
- [ ] Coordinate code reviews

### BEFORE Demo/Prod
- [ ] Final verification: `pytest tests/ -v` passes
- [ ] Load test: `ab -n 100 -c 10` (no timeouts)
- [ ] Code review sign-off from `code-reviewer`
- [ ] Update MISTAKES.md with lessons learned

---

## Effort Summary

| Team | Blockers | High-Priority | Total | ETA |
|------|----------|---------------|-------|-----|
| Backend | 25 min | 1.5–2 hours | 2–2.5 hours | Today + Week 1 |
| Streamlit | 25 min | 1.5–2 hours | 2–2.5 hours | Today + Week 1 |
| **Total** | **50 min** | **3–4 hours** | **4–5 hours** | **Today + Week 1** |

---

## Definition of Done

All issues resolved when:

1. All blockers (5 issues) fixed and tested
2. All high-priority (6 issues) fixed and tested
3. `pytest tests/ -v` passes (170+ tests)
4. Load test passes (no event loop blocking)
5. Code review approved by `code-reviewer`
6. MISTAKES.md updated
7. **Final Verdict:** APPROVED (move to demo/prod)

---

## Questions?

Refer to:
- CODE_REVIEW_CONSOLIDATED_ACTION_PLAN.md — Full details, fix code samples
- CODE_REVIEW_QUICK_REFERENCE.md — One-page cheat sheet
- MISTAKES.md — Project-specific pitfalls

Good luck!
