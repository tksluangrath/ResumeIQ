# Phase 2 Code Review — Quick Reference Card

**Print this. Tape it to your monitor.**

---

## Status: APPROVED WITH CONDITIONS

- FastAPI backend: v0.2.0, 170 tests passing ✅
- Streamlit UI: Not yet built (ready after blockers)
- Deployment: **BLOCKED** pending fixes

---

## Blockers to Fix TODAY (~40 min)

| Issue | File | Line | Fix | Time |
|-------|------|------|-----|------|
| API-C2 | `api/dependencies.py` | `get_engine()` | Add RuntimeError guard for None check | 5 min |
| API-C4 | `api/routers/improve.py` | `except Exception: pass` | Log + raise HTTPException | 10 min |
| UI-C1 | `ui/streamlit_app.py` | try/except block | Init `resp = None` before try OR use `return` in except | 10 min |
| UI-C3 | `ui/streamlit_app.py` | `st.markdown()` | Use `st.text()` or escape HTML for user data | 10 min |
| UI-C4 | `ui/streamlit_app.py` | `file.read()` | Change to `file.getvalue()` | 5 min |

---

## High-Priority to Fix THIS WEEK (~3 hours)

| Issue | File | Fix Summary |
|-------|------|------------|
| API-W1 | `api/routers/match.py` | Add magic bytes check: `if not pdf_bytes.startswith(b"%PDF-")` |
| API-W2 | `api/routers/match.py`, `improve.py` | Refactor sync routes to `def` (not `async def`) OR use `run_in_executor()` for spaCy/transformers |
| API-W4 | `api/main.py` | Add max body size limit (50 MB) via middleware or uvicorn flag |
| UI-C2 | `ui/streamlit_app.py` | Wrap `resp.json()` in try/except ValueError; handle HTML 502s |
| UI-W1 | `ui/streamlit_app.py` | Import `ScoreBreakdown` from `engine.scorer`; replace `breakdown: dict` |
| UI-W2 | `ui/streamlit_app.py` | Build profile using Pydantic models (`UserProfile`, etc.) not raw dicts |

---

## Cross-Cutting Issues

### Error Handling
- **API:** Never `except Exception: pass`. Log with context; return structured error.
- **UI:** Catch all 3 exception types: `ConnectionError`, `Timeout`, `HTTPError`. Use try/except around `resp.json()`.

### Type Safety
- **Rule:** Every `dict` must be a Pydantic model. No bare dicts crossing module boundaries.
- **Audit:** Session state in Streamlit should be typed dicts or Pydantic models.

### Magic Numbers
- **JD min length (50):** Pull from `config.MIN_JD_CHARS`
- **Validation limits:** Deduplicate from `api/constants.py` (single source of truth)

---

## Testing Checklist (After fixes)

- [ ] `pytest tests/ -v` — all 170+ tests pass
- [ ] Manual: Upload non-PDF file → 400 error (W1 fix)
- [ ] Manual: Trigger LaTeX error → structured error response logged (C4 fix)
- [ ] Manual: Reupload file in Streamlit → bytes correct, not empty (C4 fix)
- [ ] Load test: `ab -n 100 -c 10 http://localhost:8000/match` (no timeouts from W2)
- [ ] Manual: Slow API by 30s → Streamlit shows error, no crash (C1 fix)

---

## Owner Assignments

| Owner | Blockers | High-Priority |
|-------|----------|---------------|
| `backend-developer` | API-C2, C4 | API-W1, W2, W4 |
| `Streamlit dev (TBD)` | UI-C1, C3, C4 | UI-C2, W1, W2 |

---

## Deploy Readiness

**AFTER Blockers fixed (~today):**
- Internal demo OK
- Stakeholder demo OK after High-Priority fixes

**BEFORE production:**
- All High-Priority must be fixed
- Error handling architecture unified
- Type safety audit passed
- Load test passed (no event loop blocking)

---

## Key Principle

**NEVER silently fail.** Log everything. Return structured errors. Validate at every boundary.

---

See `CODE_REVIEW_CONSOLIDATED_ACTION_PLAN.md` for full details.
