from __future__ import annotations

import pytest
from engine.llm.base import BaseLLM
from engine.scorer import GapClassification, MatchReport, ScoreBreakdown, SkillMatchResult
from engine.suggester import SuggestionResult, _parse_json_list, suggest


class StubLLM(BaseLLM):
    """Returns pre-canned responses in order. Raises IndexError if exhausted."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self._index = 0

    def complete(self, prompt: str) -> str:
        if self._index >= len(self._responses):
            raise IndexError("StubLLM ran out of responses")
        response = self._responses[self._index]
        self._index += 1
        return response

    @property
    def provider_name(self) -> str:
        return "stub/test"


def _make_report() -> MatchReport:
    missing = ["PostgreSQL", "Docker"]
    return MatchReport(
        overall_score=0.72,
        breakdown=ScoreBreakdown(
            semantic_similarity=0.75,
            skill_match=SkillMatchResult(
                matched=["Python", "FastAPI"],
                missing=missing,
                match_rate=0.5,
            ),
            title_relevance=0.8,
            experience_match="mid-level",
        ),
        gap_classification=GapClassification(hard_blockers=[], nice_to_haves=missing),
        apply_recommendation="borderline",
        ats_keywords=missing,
        role_archetype="general",
        recommendations=["Add Docker to your resume"],
    )


class TestSuggestWithStubLLM:
    """Full suggest() call with StubLLM — no HTTP involved."""

    def test_returns_suggestion_result(self) -> None:
        # Provide enough responses: up to 5 bullet rewrites + skill gaps + keywords + summary
        # With no weak_bullets provided, the engine detects them; provide 10 responses to be safe
        stub = StubLLM(
            [
                "Led development of scalable REST API reducing latency by 35%.",  # bullet rewrite 1 (if any detected)
                "Built automated CI/CD pipeline cutting deploy time by 50%.",      # bullet rewrite 2
                "Implemented data validation layer improving data quality by 90%.",# bullet rewrite 3
                "Designed microservices architecture supporting 10k concurrent users.",  # bullet rewrite 4
                "Optimized database queries reducing response time by 60%.",       # bullet rewrite 5
                '["PostgreSQL experience is missing — the role requires advanced SQL.", "Docker containerization not shown."]',  # skill gaps
                '["PostgreSQL", "Docker", "Kubernetes", "CI/CD", "REST API"]',    # keywords
                "Experienced software engineer with 5 years building scalable APIs and ML pipelines.",  # summary
            ]
        )
        # Pass explicit weak_bullets to control what's tested
        weak_bullets = [
            {"section": "Experience", "context": "Acme Corp", "bullet": "worked on backend services"},
        ]
        result = suggest(
            resume_text="Developed Python backend services. Helped with deployment.",
            job_description="We need a Python developer with PostgreSQL and Docker experience " * 5,
            report=_make_report(),
            llm=stub,
            weak_bullets=weak_bullets,
        )
        assert isinstance(result, SuggestionResult)
        assert isinstance(result.bullet_rewrites, list)
        assert isinstance(result.skill_gaps, list)
        assert isinstance(result.injected_keywords, list)
        assert isinstance(result.career_summary, str)
        assert result.provider == "stub/test"

    def test_bullet_rewrites_have_correct_structure(self) -> None:
        stub = StubLLM(
            [
                "Led development of scalable API reducing latency by 35%.",
                '["Missing PostgreSQL skills"]',
                '["PostgreSQL", "Docker"]',
                "Skilled engineer with Python and API expertise.",
            ]
        )
        weak_bullets = [
            {"section": "Experience", "context": "TechCorp", "bullet": "helped with the API"},
        ]
        result = suggest(
            resume_text="Some resume text for testing purposes here.",
            job_description="Python developer role requiring PostgreSQL and Docker skills " * 5,
            report=_make_report(),
            llm=stub,
            weak_bullets=weak_bullets,
        )
        assert len(result.bullet_rewrites) == 1
        br = result.bullet_rewrites[0]
        assert br.original == "helped with the API"
        assert br.rewritten == "Led development of scalable API reducing latency by 35%."
        assert br.section == "Experience"
        assert br.context == "TechCorp"

    def test_no_weak_bullets_returns_empty_list(self) -> None:
        stub = StubLLM(
            [
                '["Missing PostgreSQL"]',
                '["PostgreSQL"]',
                "Skilled engineer.",
            ]
        )
        result = suggest(
            resume_text="Some resume text for testing purposes here.",
            job_description="Python developer role requiring PostgreSQL and Docker skills " * 5,
            report=_make_report(),
            llm=stub,
            weak_bullets=[],  # explicitly empty
        )
        assert result.bullet_rewrites == []


class TestParseJsonList:
    """Unit tests for the _parse_json_list helper."""

    def test_valid_json_array(self) -> None:
        result = _parse_json_list('["Python", "FastAPI", "Docker"]')
        assert result == ["Python", "FastAPI", "Docker"]

    def test_plain_lines(self) -> None:
        result = _parse_json_list("Python\nFastAPI\nDocker")
        assert "Python" in result
        assert "FastAPI" in result

    def test_numbered_list(self) -> None:
        result = _parse_json_list("1. Python\n2. FastAPI\n3. Docker")
        assert "Python" in result
        assert "FastAPI" in result
        assert "Docker" in result

    def test_bulleted_list(self) -> None:
        result = _parse_json_list("- Python\n- FastAPI\n* Docker")
        assert "Python" in result

    def test_markdown_fenced_json(self) -> None:
        text = '```json\n["Python", "FastAPI"]\n```'
        result = _parse_json_list(text)
        # Fence markers must be stripped — only real items returned
        assert "Python" in result
        assert "FastAPI" in result
        assert not any("```" in item for item in result)

    def test_markdown_fenced_json_no_lang_tag(self) -> None:
        text = '```\n["Go", "Rust"]\n```'
        result = _parse_json_list(text)
        assert "Go" in result
        assert "Rust" in result
        assert not any("```" in item for item in result)

    def test_empty_string(self) -> None:
        result = _parse_json_list("")
        assert result == []
