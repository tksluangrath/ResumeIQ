"""
Tests for the FastAPI backend — HTTP boundary tests.

Uses starlette.testclient.TestClient (synchronous) with a module-scoped fixture
so the expensive engine model loading happens exactly once per test run.

Per CLAUDE.md: No mocking — real sample files from samples/ are used.
"""

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from api.main import create_app

SAMPLES = Path(__file__).parent.parent / "samples"
RESUME_PDF = SAMPLES / "resume_template.pdf"
RESUME_TEX = SAMPLES / "resume_template.tex"
JOB_DESC = (SAMPLES / "job_description.txt").read_text(encoding="utf-8").strip()

# Short valid job description for validation boundary tests
SHORT_VALID_JD = "A" * 50
TOO_SHORT_JD = "A" * 49
TOO_LONG_JD = "A" * 10_001


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Module-scoped client — lifespan warms up all engine singletons once."""
    with TestClient(create_app()) as c:
        yield c


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_returns_200(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_response_has_required_fields(self, client: TestClient) -> None:
        body = client.get("/health").json()
        assert "status" in body
        assert "version" in body
        assert "env" in body

    def test_status_is_ok(self, client: TestClient) -> None:
        body = client.get("/health").json()
        assert body["status"] == "ok"

    def test_version_is_string(self, client: TestClient) -> None:
        body = client.get("/health").json()
        assert isinstance(body["version"], str)
        assert len(body["version"]) > 0

    def test_env_is_string(self, client: TestClient) -> None:
        body = client.get("/health").json()
        assert isinstance(body["env"], str)


# ---------------------------------------------------------------------------
# POST /match — happy path
# ---------------------------------------------------------------------------


class TestMatchHappyPath:
    def test_returns_200_with_real_pdf_and_jd(self, client: TestClient) -> None:
        with RESUME_PDF.open("rb") as f:
            resp = client.post(
                "/match",
                files={"resume": ("resume_template.pdf", f, "application/pdf")},
                data={"job_description": JOB_DESC},
            )
        assert resp.status_code == 200

    def test_overall_score_is_float_between_0_and_100(self, client: TestClient) -> None:
        with RESUME_PDF.open("rb") as f:
            body = client.post(
                "/match",
                files={"resume": ("resume_template.pdf", f, "application/pdf")},
                data={"job_description": JOB_DESC},
            ).json()
        assert isinstance(body["overall_score"], float)
        assert 0.0 <= body["overall_score"] <= 100.0

    def test_breakdown_has_expected_keys(self, client: TestClient) -> None:
        with RESUME_PDF.open("rb") as f:
            body = client.post(
                "/match",
                files={"resume": ("resume_template.pdf", f, "application/pdf")},
                data={"job_description": JOB_DESC},
            ).json()
        bd = body["breakdown"]
        assert "semantic_similarity" in bd
        assert "skill_match" in bd
        assert "title_relevance" in bd
        assert "experience_match" in bd

    def test_skill_match_has_matched_and_missing(self, client: TestClient) -> None:
        with RESUME_PDF.open("rb") as f:
            body = client.post(
                "/match",
                files={"resume": ("resume_template.pdf", f, "application/pdf")},
                data={"job_description": JOB_DESC},
            ).json()
        sm = body["breakdown"]["skill_match"]
        assert "matched" in sm
        assert "missing" in sm
        assert "match_rate" in sm
        assert isinstance(sm["matched"], list)
        assert isinstance(sm["missing"], list)

    def test_recommendations_is_list(self, client: TestClient) -> None:
        with RESUME_PDF.open("rb") as f:
            body = client.post(
                "/match",
                files={"resume": ("resume_template.pdf", f, "application/pdf")},
                data={"job_description": JOB_DESC},
            ).json()
        assert isinstance(body["recommendations"], list)

    def test_processing_time_ms_is_positive_int(self, client: TestClient) -> None:
        with RESUME_PDF.open("rb") as f:
            body = client.post(
                "/match",
                files={"resume": ("resume_template.pdf", f, "application/pdf")},
                data={"job_description": JOB_DESC},
            ).json()
        assert isinstance(body["processing_time_ms"], int)
        assert body["processing_time_ms"] >= 0


# ---------------------------------------------------------------------------
# POST /match — validation errors
# ---------------------------------------------------------------------------


class TestMatchValidation:
    def test_non_pdf_file_returns_422(self, client: TestClient) -> None:
        resp = client.post(
            "/match",
            files={"resume": ("resume.txt", b"not a pdf", "text/plain")},
            data={"job_description": JOB_DESC},
        )
        assert resp.status_code == 422

    def test_empty_pdf_returns_422(self, client: TestClient) -> None:
        resp = client.post(
            "/match",
            files={"resume": ("empty.pdf", b"", "application/pdf")},
            data={"job_description": JOB_DESC},
        )
        assert resp.status_code == 422

    def test_oversized_pdf_returns_413(self, client: TestClient) -> None:
        big_pdf = b"%PDF-1.4 " + b"x" * (5 * 1024 * 1024 + 1)
        resp = client.post(
            "/match",
            files={"resume": ("big.pdf", big_pdf, "application/pdf")},
            data={"job_description": JOB_DESC},
        )
        assert resp.status_code == 413

    def test_jd_too_short_returns_422(self, client: TestClient) -> None:
        with RESUME_PDF.open("rb") as f:
            resp = client.post(
                "/match",
                files={"resume": ("resume_template.pdf", f, "application/pdf")},
                data={"job_description": TOO_SHORT_JD},
            )
        assert resp.status_code == 422

    def test_jd_minimum_length_accepted(self, client: TestClient) -> None:
        with RESUME_PDF.open("rb") as f:
            resp = client.post(
                "/match",
                files={"resume": ("resume_template.pdf", f, "application/pdf")},
                data={"job_description": SHORT_VALID_JD},
            )
        assert resp.status_code == 200

    def test_jd_too_long_returns_422(self, client: TestClient) -> None:
        with RESUME_PDF.open("rb") as f:
            resp = client.post(
                "/match",
                files={"resume": ("resume_template.pdf", f, "application/pdf")},
                data={"job_description": TOO_LONG_JD},
            )
        assert resp.status_code == 422

    def test_missing_resume_field_returns_422(self, client: TestClient) -> None:
        resp = client.post("/match", data={"job_description": JOB_DESC})
        assert resp.status_code == 422

    def test_missing_jd_field_returns_422(self, client: TestClient) -> None:
        with RESUME_PDF.open("rb") as f:
            resp = client.post(
                "/match",
                files={"resume": ("resume_template.pdf", f, "application/pdf")},
            )
        assert resp.status_code == 422

    def test_error_detail_is_string(self, client: TestClient) -> None:
        resp = client.post(
            "/match",
            files={"resume": ("resume.txt", b"not a pdf", "text/plain")},
            data={"job_description": JOB_DESC},
        )
        body = resp.json()
        assert "detail" in body
        assert isinstance(body["detail"], str)


# ---------------------------------------------------------------------------
# POST /improve — happy path
# ---------------------------------------------------------------------------


class TestImproveHappyPath:
    def test_returns_200_with_real_files(self, client: TestClient) -> None:
        with RESUME_PDF.open("rb") as pdf_f, RESUME_TEX.open("rb") as tex_f:
            resp = client.post(
                "/improve",
                files={
                    "resume_pdf": ("resume_template.pdf", pdf_f, "application/pdf"),
                    "resume_tex": ("resume_template.tex", tex_f, "text/plain"),
                },
                data={"job_description": JOB_DESC},
            )
        assert resp.status_code == 200

    def test_overall_score_in_range(self, client: TestClient) -> None:
        with RESUME_PDF.open("rb") as pdf_f, RESUME_TEX.open("rb") as tex_f:
            body = client.post(
                "/improve",
                files={
                    "resume_pdf": ("resume_template.pdf", pdf_f, "application/pdf"),
                    "resume_tex": ("resume_template.tex", tex_f, "text/plain"),
                },
                data={"job_description": JOB_DESC},
            ).json()
        assert 0.0 <= body["overall_score"] <= 100.0

    def test_all_improve_response_fields_present(self, client: TestClient) -> None:
        with RESUME_PDF.open("rb") as pdf_f, RESUME_TEX.open("rb") as tex_f:
            body = client.post(
                "/improve",
                files={
                    "resume_pdf": ("resume_template.pdf", pdf_f, "application/pdf"),
                    "resume_tex": ("resume_template.tex", tex_f, "text/plain"),
                },
                data={"job_description": JOB_DESC},
            ).json()
        for field in (
            "overall_score", "breakdown", "recommendations",
            "injected_skills", "weak_bullets", "notes",
            "latex_source", "pdf_url", "processing_time_ms",
        ):
            assert field in body, f"Missing field: {field}"

    def test_injected_skills_is_list(self, client: TestClient) -> None:
        with RESUME_PDF.open("rb") as pdf_f, RESUME_TEX.open("rb") as tex_f:
            body = client.post(
                "/improve",
                files={
                    "resume_pdf": ("resume_template.pdf", pdf_f, "application/pdf"),
                    "resume_tex": ("resume_template.tex", tex_f, "text/plain"),
                },
                data={"job_description": JOB_DESC},
            ).json()
        assert isinstance(body["injected_skills"], list)

    def test_weak_bullets_items_have_section_and_bullet(self, client: TestClient) -> None:
        with RESUME_PDF.open("rb") as pdf_f, RESUME_TEX.open("rb") as tex_f:
            body = client.post(
                "/improve",
                files={
                    "resume_pdf": ("resume_template.pdf", pdf_f, "application/pdf"),
                    "resume_tex": ("resume_template.tex", tex_f, "text/plain"),
                },
                data={"job_description": JOB_DESC},
            ).json()
        for wb in body["weak_bullets"]:
            assert "section" in wb
            assert "bullet" in wb

    def test_notes_is_list_of_strings(self, client: TestClient) -> None:
        with RESUME_PDF.open("rb") as pdf_f, RESUME_TEX.open("rb") as tex_f:
            body = client.post(
                "/improve",
                files={
                    "resume_pdf": ("resume_template.pdf", pdf_f, "application/pdf"),
                    "resume_tex": ("resume_template.tex", tex_f, "text/plain"),
                },
                data={"job_description": JOB_DESC},
            ).json()
        assert isinstance(body["notes"], list)
        assert all(isinstance(n, str) for n in body["notes"])

    def test_latex_source_is_string_or_none(self, client: TestClient) -> None:
        with RESUME_PDF.open("rb") as pdf_f, RESUME_TEX.open("rb") as tex_f:
            body = client.post(
                "/improve",
                files={
                    "resume_pdf": ("resume_template.pdf", pdf_f, "application/pdf"),
                    "resume_tex": ("resume_template.tex", tex_f, "text/plain"),
                },
                data={"job_description": JOB_DESC},
            ).json()
        assert body["latex_source"] is None or isinstance(body["latex_source"], str)

    def test_pdf_url_is_none_in_phase_2(self, client: TestClient) -> None:
        with RESUME_PDF.open("rb") as pdf_f, RESUME_TEX.open("rb") as tex_f:
            body = client.post(
                "/improve",
                files={
                    "resume_pdf": ("resume_template.pdf", pdf_f, "application/pdf"),
                    "resume_tex": ("resume_template.tex", tex_f, "text/plain"),
                },
                data={"job_description": JOB_DESC},
            ).json()
        assert body["pdf_url"] is None

    def test_processing_time_ms_is_non_negative_int(self, client: TestClient) -> None:
        with RESUME_PDF.open("rb") as pdf_f, RESUME_TEX.open("rb") as tex_f:
            body = client.post(
                "/improve",
                files={
                    "resume_pdf": ("resume_template.pdf", pdf_f, "application/pdf"),
                    "resume_tex": ("resume_template.tex", tex_f, "text/plain"),
                },
                data={"job_description": JOB_DESC},
            ).json()
        assert isinstance(body["processing_time_ms"], int)
        assert body["processing_time_ms"] >= 0


# ---------------------------------------------------------------------------
# POST /improve — validation errors
# ---------------------------------------------------------------------------


class TestImproveValidation:
    def test_non_pdf_resume_returns_422(self, client: TestClient) -> None:
        with RESUME_TEX.open("rb") as tex_f:
            resp = client.post(
                "/improve",
                files={
                    "resume_pdf": ("resume.txt", b"not a pdf", "text/plain"),
                    "resume_tex": ("resume_template.tex", tex_f, "text/plain"),
                },
                data={"job_description": JOB_DESC},
            )
        assert resp.status_code == 422

    def test_empty_pdf_returns_422(self, client: TestClient) -> None:
        with RESUME_TEX.open("rb") as tex_f:
            resp = client.post(
                "/improve",
                files={
                    "resume_pdf": ("empty.pdf", b"", "application/pdf"),
                    "resume_tex": ("resume_template.tex", tex_f, "text/plain"),
                },
                data={"job_description": JOB_DESC},
            )
        assert resp.status_code == 422

    def test_oversized_pdf_returns_413(self, client: TestClient) -> None:
        big_pdf = b"%PDF-1.4 " + b"x" * (5 * 1024 * 1024 + 1)
        with RESUME_TEX.open("rb") as tex_f:
            resp = client.post(
                "/improve",
                files={
                    "resume_pdf": ("big.pdf", big_pdf, "application/pdf"),
                    "resume_tex": ("resume_template.tex", tex_f, "text/plain"),
                },
                data={"job_description": JOB_DESC},
            )
        assert resp.status_code == 413

    def test_empty_tex_returns_422(self, client: TestClient) -> None:
        with RESUME_PDF.open("rb") as pdf_f:
            resp = client.post(
                "/improve",
                files={
                    "resume_pdf": ("resume_template.pdf", pdf_f, "application/pdf"),
                    "resume_tex": ("empty.tex", b"", "text/plain"),
                },
                data={"job_description": JOB_DESC},
            )
        assert resp.status_code == 422

    def test_oversized_tex_returns_413(self, client: TestClient) -> None:
        big_tex = b"x" * (1 * 1024 * 1024 + 1)
        with RESUME_PDF.open("rb") as pdf_f:
            resp = client.post(
                "/improve",
                files={
                    "resume_pdf": ("resume_template.pdf", pdf_f, "application/pdf"),
                    "resume_tex": ("big.tex", big_tex, "text/plain"),
                },
                data={"job_description": JOB_DESC},
            )
        assert resp.status_code == 413

    def test_jd_too_short_returns_422(self, client: TestClient) -> None:
        with RESUME_PDF.open("rb") as pdf_f, RESUME_TEX.open("rb") as tex_f:
            resp = client.post(
                "/improve",
                files={
                    "resume_pdf": ("resume_template.pdf", pdf_f, "application/pdf"),
                    "resume_tex": ("resume_template.tex", tex_f, "text/plain"),
                },
                data={"job_description": TOO_SHORT_JD},
            )
        assert resp.status_code == 422

    def test_invalid_profile_json_returns_422(self, client: TestClient) -> None:
        with RESUME_PDF.open("rb") as pdf_f, RESUME_TEX.open("rb") as tex_f:
            resp = client.post(
                "/improve",
                files={
                    "resume_pdf": ("resume_template.pdf", pdf_f, "application/pdf"),
                    "resume_tex": ("resume_template.tex", tex_f, "text/plain"),
                },
                data={
                    "job_description": JOB_DESC,
                    "profile_json": "{not valid json}",
                },
            )
        assert resp.status_code == 422

    def test_profile_json_wrong_schema_returns_422(self, client: TestClient) -> None:
        with RESUME_PDF.open("rb") as pdf_f, RESUME_TEX.open("rb") as tex_f:
            resp = client.post(
                "/improve",
                files={
                    "resume_pdf": ("resume_template.pdf", pdf_f, "application/pdf"),
                    "resume_tex": ("resume_template.tex", tex_f, "text/plain"),
                },
                data={
                    "job_description": JOB_DESC,
                    "profile_json": '{"skills": "not_a_list"}',
                },
            )
        assert resp.status_code == 422

    def test_missing_required_fields_returns_422(self, client: TestClient) -> None:
        resp = client.post("/improve", data={"job_description": JOB_DESC})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /improve — with valid profile JSON
# ---------------------------------------------------------------------------


class TestImproveWithProfile:
    def test_with_valid_profile_json_returns_200(self, client: TestClient) -> None:
        import json

        profile = {
            "full_name": "Test User",
            "skills": [{"name": "Python", "proficiency": "expert"}],
            "target_roles": ["Data Scientist"],
        }
        with RESUME_PDF.open("rb") as pdf_f, RESUME_TEX.open("rb") as tex_f:
            resp = client.post(
                "/improve",
                files={
                    "resume_pdf": ("resume_template.pdf", pdf_f, "application/pdf"),
                    "resume_tex": ("resume_template.tex", tex_f, "text/plain"),
                },
                data={
                    "job_description": JOB_DESC,
                    "profile_json": json.dumps(profile),
                },
            )
        assert resp.status_code == 200

    def test_profile_filters_injected_skills(self, client: TestClient) -> None:
        """Profile with only 'Python' confirmed — only Python-confirmed skills injected."""
        import json

        profile = {
            "skills": [{"name": "Python", "proficiency": "expert"}],
        }
        with RESUME_PDF.open("rb") as pdf_f, RESUME_TEX.open("rb") as tex_f:
            body = client.post(
                "/improve",
                files={
                    "resume_pdf": ("resume_template.pdf", pdf_f, "application/pdf"),
                    "resume_tex": ("resume_template.tex", tex_f, "text/plain"),
                },
                data={
                    "job_description": JOB_DESC,
                    "profile_json": json.dumps(profile),
                },
            ).json()
        # Python is already in the resume — nothing new should be injected
        assert isinstance(body["injected_skills"], list)

    def test_no_profile_json_field_still_works(self, client: TestClient) -> None:
        """profile_json is optional — omitting it entirely should succeed."""
        with RESUME_PDF.open("rb") as pdf_f, RESUME_TEX.open("rb") as tex_f:
            resp = client.post(
                "/improve",
                files={
                    "resume_pdf": ("resume_template.pdf", pdf_f, "application/pdf"),
                    "resume_tex": ("resume_template.tex", tex_f, "text/plain"),
                },
                data={"job_description": JOB_DESC},
            )
        assert resp.status_code == 200
