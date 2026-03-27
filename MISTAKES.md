# MISTAKES.md — Phase 2 Common Pitfalls

This document captures mistakes that are easy to make and hard to debug.
Read this before touching any code in `api/` or `tests/test_api.py`.

---

## 1. Forgetting `python-multipart`

FastAPI silently fails to parse `multipart/form-data` if `python-multipart` is not installed.
The route handler receives `None` for all `UploadFile` and `Form()` fields with no clear error
at import time — only at runtime.

**Fix:** Ensure `python-multipart>=0.0.9` is in `requirements.txt` and installed.

---

## 2. Instantiating engine objects per-request

`SemanticMatcher.__init__` is cheap (just reads config), but the `SentenceTransformer` model
is lazy-loaded on first `.encode()` call. If you instantiate `SemanticMatcher()` inside a
route handler, you pay zero cost at `__init__` but 3–10 seconds on the first encode of each
new instance.

**Fix:** Use the singleton from `api/dependencies.py` via `Depends(get_matcher)`. Never
call `SemanticMatcher()` inside a route handler.

---

## 3. Not calling `.encode("warmup")` in lifespan

`SemanticMatcher.__init__` sets `self._model = None`. The actual model load happens inside
`_load_model()`, which is only called from `encode()`. If lifespan only calls
`SemanticMatcher()` without a follow-up `.encode("warmup")`, the model still loads lazily
on the first real request — causing a cold-load delay for the first user.

**Fix:** In `api/dependencies.py` lifespan, call `_state["matcher"].encode("warmup")`
immediately after instantiation to force the load at startup.

---

## 4. Passing UploadFile bytes directly to pdfplumber

`engine/parser.py::extract_text_from_pdf` takes a `str | Path`. Passing `UploadFile.file`
(a `SpooledTemporaryFile`) or raw bytes will raise a `TypeError` inside pdfplumber.

**Fix:** Always write bytes to `tempfile.NamedTemporaryFile(suffix=".pdf")`, call `.flush()`,
then pass `Path(tmp.name)` to `extract_text_from_pdf`. Same pattern applies to `.tex` files
and `parse_tex_to_resume_data`.

---

## 5. NamedTemporaryFile on Windows (file locking)

`tempfile.NamedTemporaryFile(delete=True)` on Windows keeps the file open exclusively while
the context manager is active. pdfplumber tries to open the same file and fails with
`PermissionError`. This project targets macOS/Linux so it is safe as-is.

**If porting to Windows:** Use `delete=False` and manually `os.unlink(tmp.name)` in a
`finally` block.

---

## 6. Mixing `files=` and `data=` incorrectly in TestClient/httpx

When sending multipart form data, file uploads go in `files=` and string form fields go
in `data=`. Putting a string form field inside `files=` causes httpx to encode it differently
and FastAPI's `Form()` parameter will receive `None`.

**Correct:**
```python
client.post("/match",
    files={"resume": ("name.pdf", file_obj, "application/pdf")},
    data={"job_description": "..."})
```

**Wrong:**
```python
client.post("/match",
    files={"resume": (...), "job_description": "..."})
```

---

## 7. Using `@app.on_event("startup")` instead of `lifespan`

`@app.on_event("startup")` was deprecated in FastAPI 0.93 and will be removed in a future
version. It produces deprecation warnings in test output.

**Fix:** Use the `@asynccontextmanager` lifespan pattern and pass it to
`FastAPI(lifespan=lifespan)`. See `api/dependencies.py` for the correct pattern.

---

## 8. Using `WeakBullet(**wb)` instead of `WeakBullet.model_validate(wb)`

`engine/optimizer.py::optimize()` returns `OptimizationResult.weak_bullets` as
`list[dict[str, str]]`. The dicts have varying keys depending on the section:
- Experience entries: `{"section": "Experience", "company": "...", "bullet": "..."}`
- Experience entries with no metric: same but bullet prefixed with `[no metric]` and optional `"hint"` key
- Project entries: `{"section": "Projects", "project": "...", "bullet": "..."}`

`WeakBullet(**wb)` will raise `TypeError` if a key in the dict doesn't match a constructor
parameter exactly.

**Fix:** Use `WeakBullet.model_validate(wb)`. Pydantic v2's `model_validate` handles missing
optional fields (`company`, `project`, `hint`) by defaulting them to `None`.

---

## 9. Swallowing `render_latex` failure is intentional

In `api/routers/improve.py`, the `render_latex()` call is wrapped in a bare `try/except`
that sets `latex_source = None` on failure. This is **not** lazy error handling.

`ImproveResponse.latex_source: str | None` is a documented valid state in `api/models.py`.
A LaTeX rendering failure is recoverable — the score, skill analysis, recommendations, and
optimizer notes are all still valid. Crashing the whole `/improve` response because of a
template rendering error would be wrong.

**Do not "fix" this by re-raising the exception.**

---

## 10. `content_type` validation is not sufficient alone

`UploadFile.content_type` is set by the HTTP client, not by inspecting the file bytes. Any
client can upload a `.txt` file with `Content-Type: application/pdf` and bypass the check.

The check exists as a fast early-reject for obviously wrong types (e.g., a user accidentally
uploads a `.docx`). The real defense is `pdfplumber` — it will fail to parse non-PDF bytes
and `extract_text_from_pdf` will raise `ValueError`, which the route catches as a 422.

**Do not remove either check. Both are needed.**

---

## 11. `create_app()` factory vs module-level `app` import

`api/main.py` exposes both `create_app()` and a module-level `app = create_app()`.

Tests must use `create_app()` to build a fresh instance — importing the module-level `app`
directly means the lifespan has already been triggered (or not) depending on import order,
which causes flaky test behavior with module-scoped fixtures.

**In tests:**
```python
from api.main import create_app
with TestClient(create_app()) as client:
    ...
```

**Not:**
```python
from api.main import app
with TestClient(app) as client:   # risky — lifespan state may be stale
    ...
```
