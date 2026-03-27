from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient

from api.main import create_app


SAMPLES = Path(__file__).parent.parent / "samples"
RESUME_PDF = SAMPLES / "resume_template.pdf"

SAMPLE_JD = (
    "We are looking for a Python developer with experience in FastAPI, PostgreSQL, "
    "and Docker. The ideal candidate has 3+ years of backend development experience "
    "and is comfortable working in an agile environment with CI/CD pipelines."
)

# Canned LLM response — returned for every httpx.post call
_CANNED_RESPONSE = "Led development of scalable API reducing latency by 35%."


@pytest.fixture(scope="module")
def client() -> TestClient:
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": _CANNED_RESPONSE}
    mock_resp.raise_for_status.return_value = None
    with patch("httpx.post", return_value=mock_resp):
        with TestClient(create_app()) as c:
            yield c


class TestSuggestHappyPath:
    def test_returns_200(self, client: TestClient) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": _CANNED_RESPONSE}
        mock_resp.raise_for_status.return_value = None
        with patch("httpx.post", return_value=mock_resp):
            with RESUME_PDF.open("rb") as f:
                resp = client.post(
                    "/suggest",
                    files={"resume_pdf": ("resume.pdf", f, "application/pdf")},
                    data={"job_description": SAMPLE_JD},
                )
        assert resp.status_code == 200

    def test_response_has_required_fields(self, client: TestClient) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": _CANNED_RESPONSE}
        mock_resp.raise_for_status.return_value = None
        with patch("httpx.post", return_value=mock_resp):
            with RESUME_PDF.open("rb") as f:
                resp = client.post(
                    "/suggest",
                    files={"resume_pdf": ("resume.pdf", f, "application/pdf")},
                    data={"job_description": SAMPLE_JD},
                )
        body = resp.json()
        assert "overall_score" in body
        assert "breakdown" in body
        assert "bullet_rewrites" in body
        assert "skill_gaps" in body
        assert "injected_keywords" in body
        assert "career_summary" in body
        assert "provider" in body
        assert "processing_time_ms" in body

    def test_provider_is_ollama(self, client: TestClient) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": _CANNED_RESPONSE}
        mock_resp.raise_for_status.return_value = None
        with patch("httpx.post", return_value=mock_resp):
            with RESUME_PDF.open("rb") as f:
                resp = client.post(
                    "/suggest",
                    files={"resume_pdf": ("resume.pdf", f, "application/pdf")},
                    data={"job_description": SAMPLE_JD},
                )
        assert resp.json()["provider"].startswith("ollama/")

    def test_field_types(self, client: TestClient) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": _CANNED_RESPONSE}
        mock_resp.raise_for_status.return_value = None
        with patch("httpx.post", return_value=mock_resp):
            with RESUME_PDF.open("rb") as f:
                resp = client.post(
                    "/suggest",
                    files={"resume_pdf": ("resume.pdf", f, "application/pdf")},
                    data={"job_description": SAMPLE_JD},
                )
        body = resp.json()
        assert isinstance(body["overall_score"], float)
        assert isinstance(body["bullet_rewrites"], list)
        assert isinstance(body["skill_gaps"], list)
        assert isinstance(body["injected_keywords"], list)
        assert isinstance(body["career_summary"], str)
        assert isinstance(body["processing_time_ms"], int)


class TestSuggestValidation:
    def test_wrong_content_type(self, client: TestClient) -> None:
        resp = client.post(
            "/suggest",
            files={"resume_pdf": ("resume.txt", b"not a pdf", "text/plain")},
            data={"job_description": SAMPLE_JD},
        )
        assert resp.status_code == 422

    def test_invalid_pdf_magic_bytes(self, client: TestClient) -> None:
        resp = client.post(
            "/suggest",
            files={"resume_pdf": ("resume.pdf", b"not a real pdf content here", "application/pdf")},
            data={"job_description": SAMPLE_JD},
        )
        assert resp.status_code == 422

    def test_jd_too_short(self, client: TestClient) -> None:
        with RESUME_PDF.open("rb") as f:
            resp = client.post(
                "/suggest",
                files={"resume_pdf": ("resume.pdf", f, "application/pdf")},
                data={"job_description": "short"},
            )
        assert resp.status_code == 422

    def test_oversized_pdf(self, client: TestClient) -> None:
        big_pdf = b"%PDF-" + b"x" * (6 * 1024 * 1024)
        resp = client.post(
            "/suggest",
            files={"resume_pdf": ("resume.pdf", big_pdf, "application/pdf")},
            data={"job_description": SAMPLE_JD},
        )
        assert resp.status_code == 413

    def test_invalid_profile_json(self, client: TestClient) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": _CANNED_RESPONSE}
        mock_resp.raise_for_status.return_value = None
        with patch("httpx.post", return_value=mock_resp):
            with RESUME_PDF.open("rb") as f:
                resp = client.post(
                    "/suggest",
                    files={"resume_pdf": ("resume.pdf", f, "application/pdf")},
                    data={"job_description": SAMPLE_JD, "profile_json": "not valid json"},
                )
        assert resp.status_code == 422


class TestSuggestLLMErrors:
    def test_connection_error_returns_503(self, client: TestClient) -> None:
        import httpx
        with patch("httpx.post", side_effect=httpx.ConnectError("Connection refused")):
            with RESUME_PDF.open("rb") as f:
                resp = client.post(
                    "/suggest",
                    files={"resume_pdf": ("resume.pdf", f, "application/pdf")},
                    data={"job_description": SAMPLE_JD},
                )
        assert resp.status_code == 503

    def test_timeout_returns_503(self, client: TestClient) -> None:
        import httpx
        with patch("httpx.post", side_effect=httpx.TimeoutException("timed out")):
            with RESUME_PDF.open("rb") as f:
                resp = client.post(
                    "/suggest",
                    files={"resume_pdf": ("resume.pdf", f, "application/pdf")},
                    data={"job_description": SAMPLE_JD},
                )
        assert resp.status_code == 503

    def test_empty_llm_response_returns_502(self, client: TestClient) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": ""}
        mock_resp.raise_for_status.return_value = None
        with patch("httpx.post", return_value=mock_resp):
            with RESUME_PDF.open("rb") as f:
                resp = client.post(
                    "/suggest",
                    files={"resume_pdf": ("resume.pdf", f, "application/pdf")},
                    data={"job_description": SAMPLE_JD},
                )
        assert resp.status_code == 502
