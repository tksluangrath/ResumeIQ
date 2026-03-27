"""
Tests for reporter.py — generate_report dict structure and JSON file I/O.
"""

import json
from pathlib import Path

import pytest

from engine.reporter import generate_report
from engine.scorer import MatchReport, MatchScorer, ScoreBreakdown, SkillMatchResult


def _make_report(
    score: float = 55.0,
    matched: list[str] | None = None,
    missing: list[str] | None = None,
) -> MatchReport:
    return MatchReport(
        overall_score=score,
        breakdown=ScoreBreakdown(
            semantic_similarity=0.60,
            skill_match=SkillMatchResult(
                matched=matched or ["Python", "SQL"],
                missing=missing or ["Docker", "AWS"],
                match_rate=0.50,
            ),
            title_relevance=0.40,
            experience_match="senior_required_junior_detected",
        ),
        recommendations=["Add Docker", "Add AWS"],
    )


class TestGenerateReportDict:
    def test_returns_dict(self):
        report = _make_report()
        result = generate_report(report)
        assert isinstance(result, dict)

    def test_overall_score_present(self):
        report = _make_report(score=72.5)
        result = generate_report(report)
        assert result["overall_score"] == 72.5

    def test_breakdown_key_present(self):
        report = _make_report()
        result = generate_report(report)
        assert "breakdown" in result

    def test_skill_match_nested_present(self):
        report = _make_report()
        result = generate_report(report)
        assert "skill_match" in result["breakdown"]

    def test_matched_skills_in_output(self):
        report = _make_report(matched=["Python", "Git"])
        result = generate_report(report)
        assert "Python" in result["breakdown"]["skill_match"]["matched"]

    def test_missing_skills_in_output(self):
        report = _make_report(missing=["Kubernetes", "Terraform"])
        result = generate_report(report)
        assert "Kubernetes" in result["breakdown"]["skill_match"]["missing"]

    def test_recommendations_present(self):
        report = _make_report()
        result = generate_report(report)
        assert "recommendations" in result
        assert len(result["recommendations"]) > 0

    def test_no_output_path_does_not_write_file(self, tmp_path):
        report = _make_report()
        generate_report(report)
        assert not any(tmp_path.iterdir())


class TestGenerateReportFileIO:
    def test_writes_json_file(self, tmp_path):
        report = _make_report()
        path = tmp_path / "report.json"
        generate_report(report, output_path=path)
        assert path.exists()

    def test_written_file_is_valid_json(self, tmp_path):
        report = _make_report()
        path = tmp_path / "out.json"
        generate_report(report, output_path=path)
        data = json.loads(path.read_text())
        assert isinstance(data, dict)

    def test_creates_parent_directories(self, tmp_path):
        report = _make_report()
        path = tmp_path / "nested" / "deep" / "report.json"
        generate_report(report, output_path=path)
        assert path.exists()

    def test_file_score_matches_report(self, tmp_path):
        report = _make_report(score=88.0)
        path = tmp_path / "report.json"
        generate_report(report, output_path=path)
        data = json.loads(path.read_text())
        assert data["overall_score"] == 88.0
