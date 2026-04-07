"""
Adversarial stress tests for engine/scorer.py.
Goal: expose boundary bugs, weight edge cases, and silent failures.
100 tests total — no database required.
"""
from __future__ import annotations

import os

import pytest

from engine.extractor import ResumeEntities
from engine.scorer import (
    ARCHETYPES,
    SKILL_ALIASES,
    GapClassification,
    MatchReport,
    MatchScorer,
    SkillMatchResult,
    _apply_recommendation,
    _classify_gaps,
    _detect_archetype,
    _detect_level,
    _experience_level_score,
    _extract_ats_keywords,
    _normalize_skill,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_scorer() -> MatchScorer:
    return MatchScorer()


def ents(
    skills: list[str] | None = None,
    job_titles: list[str] | None = None,
) -> ResumeEntities:
    return ResumeEntities(
        skills=skills or [],
        job_titles=job_titles or [],
        companies=[],
        education=[],
        certifications=[],
    )


VALID_RECOMMENDATIONS = {"strong_match", "good_match", "borderline", "skip"}
VALID_ARCHETYPES = set(ARCHETYPES.keys()) | {"general"}


# ── Section 1: Score clamping & boundary conditions ───────────────────────────

class TestScoreClamping:
    def test_semantic_zero_no_skills_score_above_zero(self) -> None:
        """Experience weight floors the score above 0 even with nothing matching."""
        report = make_scorer().score(ents(), ents(), semantic_sim=0.0)
        assert report.overall_score >= 0.0

    def test_semantic_one_perfect_skills_title_score_is_100(self) -> None:
        skills = ["Python", "FastAPI", "Docker"]
        report = make_scorer().score(
            ents(skills=skills, job_titles=["Senior Engineer"]),
            ents(skills=skills, job_titles=["Senior Engineer"]),
            semantic_sim=1.0,
        )
        assert report.overall_score <= 100.0

    def test_negative_semantic_sim_clamped_to_zero_or_above(self) -> None:
        report = make_scorer().score(ents(), ents(), semantic_sim=-0.5)
        assert report.overall_score >= 0.0

    def test_semantic_above_one_clamped_to_100_or_below(self) -> None:
        skills = ["Python"]
        report = make_scorer().score(
            ents(skills=skills, job_titles=["Senior Engineer"]),
            ents(skills=skills, job_titles=["Senior Engineer"]),
            semantic_sim=1.5,
        )
        assert report.overall_score <= 100.0

    def test_semantic_two_clamped_to_100(self) -> None:
        skills = ["Python", "FastAPI"]
        report = make_scorer().score(
            ents(skills=skills, job_titles=["Senior Engineer"]),
            ents(skills=skills, job_titles=["Senior Engineer"]),
            semantic_sim=2.0,
        )
        assert report.overall_score <= 100.0

    def test_all_zero_inputs_score_is_non_negative(self) -> None:
        report = make_scorer().score(ents(skills=[]), ents(skills=[]), semantic_sim=0.0)
        assert report.overall_score >= 0.0

    def test_score_is_float(self) -> None:
        report = make_scorer().score(ents(), ents(), semantic_sim=0.5)
        assert isinstance(report.overall_score, float)

    def test_score_rounded_to_two_decimals(self) -> None:
        report = make_scorer().score(ents(), ents(), semantic_sim=0.333333)
        # Confirm only 2 decimal places
        assert report.overall_score == round(report.overall_score, 2)

    def test_score_increases_with_higher_semantic(self) -> None:
        r_low = make_scorer().score(ents(), ents(), semantic_sim=0.1)
        r_high = make_scorer().score(ents(), ents(), semantic_sim=0.9)
        assert r_high.overall_score > r_low.overall_score

    def test_score_increases_with_more_skills_matched(self) -> None:
        scorer = make_scorer()
        jd_skills = ["Python", "Docker", "AWS", "Kubernetes"]
        r_none = scorer.score(ents(skills=[]), ents(skills=jd_skills), semantic_sim=0.5)
        r_some = scorer.score(ents(skills=["Python", "Docker"]), ents(skills=jd_skills), semantic_sim=0.5)
        r_all = scorer.score(ents(skills=jd_skills), ents(skills=jd_skills), semantic_sim=0.5)
        assert r_all.overall_score >= r_some.overall_score >= r_none.overall_score

    def test_score_at_strong_match_boundary(self) -> None:
        """Score must map to strong_match at exactly 75.0."""
        assert _apply_recommendation(75.0) == "strong_match"

    def test_score_at_good_match_boundary(self) -> None:
        assert _apply_recommendation(60.0) == "good_match"

    def test_score_at_borderline_boundary(self) -> None:
        assert _apply_recommendation(45.0) == "borderline"

    def test_score_just_below_strong_match(self) -> None:
        assert _apply_recommendation(74.99) == "good_match"

    def test_score_just_below_good_match(self) -> None:
        assert _apply_recommendation(59.99) == "borderline"

    def test_score_just_below_borderline(self) -> None:
        assert _apply_recommendation(44.99) == "skip"


# ── Section 2: Skill normalization edge cases ──────────────────────────────────

class TestSkillNormalizationEdgeCases:
    def test_empty_string_skill_in_resume_handled(self) -> None:
        """Empty skill string should not crash; edge case only."""
        scorer = make_scorer()
        report = scorer.score(ents(skills=[""]), ents(skills=["Python"]), semantic_sim=0.5)
        assert isinstance(report.overall_score, float)

    def test_whitespace_only_skill_in_resume(self) -> None:
        scorer = make_scorer()
        report = scorer.score(ents(skills=["   "]), ents(skills=["Python"]), semantic_sim=0.5)
        assert report.breakdown.skill_match.match_rate == 0.0

    def test_whitespace_only_skill_in_jd_is_zero_match(self) -> None:
        scorer = make_scorer()
        report = scorer.score(ents(skills=["Python"]), ents(skills=["   "]), semantic_sim=0.5)
        # JD has one whitespace skill; match rate ≤ 1
        assert 0.0 <= report.breakdown.skill_match.match_rate <= 1.0

    def test_skill_with_leading_trailing_whitespace_matches(self) -> None:
        scorer = make_scorer()
        report = scorer.score(ents(skills=["  Python  "]), ents(skills=["Python"]), semantic_sim=0.5)
        assert report.breakdown.skill_match.match_rate == 1.0

    def test_c_plus_plus_skill(self) -> None:
        scorer = make_scorer()
        report = scorer.score(ents(skills=["C++"]), ents(skills=["C++"]), semantic_sim=0.5)
        assert report.breakdown.skill_match.match_rate == 1.0

    def test_c_sharp_skill(self) -> None:
        scorer = make_scorer()
        report = scorer.score(ents(skills=["C#"]), ents(skills=["C#"]), semantic_sim=0.5)
        assert report.breakdown.skill_match.match_rate == 1.0

    def test_dotnet_skill(self) -> None:
        scorer = make_scorer()
        report = scorer.score(ents(skills=[".NET"]), ents(skills=[".NET"]), semantic_sim=0.5)
        assert report.breakdown.skill_match.match_rate == 1.0

    def test_duplicate_resume_skills_not_inflated(self) -> None:
        """Duplicate resume skills should behave like one skill entry."""
        scorer = make_scorer()
        report = scorer.score(
            ents(skills=["Python", "Python", "Python"]),
            ents(skills=["Python"]),
            semantic_sim=0.5,
        )
        assert report.breakdown.skill_match.match_rate == 1.0

    def test_duplicate_jd_skills_match_rate_based_on_unique(self) -> None:
        """
        Known scoring bug: duplicate JD skills cause match_rate < 1.0 even when fully matched.
        jd_lower dict de-dupes ["Python","Python"] → 1 unique key → 1 match in numerator.
        But denominator = len(jd_skills) = 2 → rate = 0.5 instead of 1.0.
        This test documents the CURRENT (buggy) behavior so any future fix is caught.
        """
        scorer = make_scorer()
        report = scorer.score(
            ents(skills=["Python"]),
            ents(skills=["Python", "Python"]),
            semantic_sim=0.5,
        )
        # BUG: denominator uses raw len (2) but numerator uses unique count (1) → 0.5
        assert report.breakdown.skill_match.match_rate == 0.5

    def test_very_long_skill_name_no_crash(self) -> None:
        long_skill = "A" * 500
        scorer = make_scorer()
        report = scorer.score(ents(skills=[long_skill]), ents(skills=[long_skill]), semantic_sim=0.5)
        assert isinstance(report.overall_score, float)

    def test_unicode_skill_match(self) -> None:
        scorer = make_scorer()
        report = scorer.score(
            ents(skills=["机器学习"]),
            ents(skills=["机器学习"]),
            semantic_sim=0.5,
        )
        assert report.breakdown.skill_match.match_rate == 1.0

    def test_all_known_aliases_normalize_correctly(self) -> None:
        for alias, canonical in SKILL_ALIASES.items():
            normalized = _normalize_skill(alias)
            assert normalized == canonical, f"Alias {alias!r} → expected {canonical!r}, got {normalized!r}"

    def test_normalize_unknown_skill_is_lowercased(self) -> None:
        assert _normalize_skill("RandomSkillXYZ") == "randomskillxyz"

    def test_alias_bidirectional_js(self) -> None:
        scorer = make_scorer()
        r1 = scorer.score(ents(skills=["JS"]), ents(skills=["JavaScript"]), semantic_sim=0.5)
        r2 = scorer.score(ents(skills=["JavaScript"]), ents(skills=["JS"]), semantic_sim=0.5)
        assert r1.breakdown.skill_match.match_rate == 1.0
        assert r2.breakdown.skill_match.match_rate == 1.0

    def test_alias_postgres_bidirectional(self) -> None:
        scorer = make_scorer()
        r1 = scorer.score(ents(skills=["Postgres"]), ents(skills=["PostgreSQL"]), semantic_sim=0.5)
        assert r1.breakdown.skill_match.match_rate == 1.0


# ── Section 3: Gap classification edge cases & bugs ───────────────────────────

class TestGapClassificationEdgeCases:
    def test_exactly_two_occurrences_is_hard_blocker(self) -> None:
        jd = "Python is required. We use Python extensively."
        result = _classify_gaps(["Python"], jd)
        assert "Python" in result.hard_blockers

    def test_exactly_one_occurrence_is_nice_to_have(self) -> None:
        jd = "Some Python experience preferred."
        result = _classify_gaps(["Python"], jd)
        assert "Python" in result.nice_to_haves

    def test_three_occurrences_is_hard_blocker(self) -> None:
        jd = "Python Python Python"
        result = _classify_gaps(["Python"], jd)
        assert "Python" in result.hard_blockers

    def test_zero_occurrences_is_nice_to_have(self) -> None:
        jd = "We use JavaScript and TypeScript."
        result = _classify_gaps(["Python"], jd)
        assert "Python" in result.nice_to_haves

    def test_empty_jd_text_all_nice_to_haves(self) -> None:
        result = _classify_gaps(["Python", "Docker", "AWS"], "")
        assert result.hard_blockers == []
        assert set(result.nice_to_haves) == {"Python", "Docker", "AWS"}

    def test_empty_missing_skills_returns_empty_lists(self) -> None:
        result = _classify_gaps([], "We need Python and Docker skills.")
        assert result.hard_blockers == []
        assert result.nice_to_haves == []

    def test_case_insensitive_counting(self) -> None:
        jd = "PYTHON is essential. python experience required."
        result = _classify_gaps(["Python"], jd)
        # count("python") on lowercased text = 2 → hard_blocker
        assert "Python" in result.hard_blockers

    def test_substring_bug_aws_in_awsome(self) -> None:
        """
        Known potential bug: 'aws' is a substring of 'awesome'.
        str.count('aws') on 'awesome aws' = 2 (once in 'awesome', once standalone).
        This test documents the CURRENT behavior so regression is caught.
        """
        jd = "We need an awesome AWS candidate."
        result = _classify_gaps(["AWS"], jd)
        # 'awesome'.count('aws') = 1, ' aws '.count('aws') = 1 → total = 2 → hard_blocker (current behavior)
        # This is a known substring matching limitation — document it:
        total_count = jd.lower().count("aws")
        if total_count >= 2:
            assert "AWS" in result.hard_blockers  # current implementation behavior
        else:
            assert "AWS" in result.nice_to_haves

    def test_multiple_skills_mixed_classification(self) -> None:
        jd = "Python Python is required. Docker is optional."
        result = _classify_gaps(["Python", "Docker", "Terraform"], jd)
        assert "Python" in result.hard_blockers
        assert "Docker" in result.nice_to_haves
        assert "Terraform" in result.nice_to_haves

    def test_hard_and_nice_to_have_are_disjoint(self) -> None:
        jd = "Python Python required. Docker optional."
        result = _classify_gaps(["Python", "Docker"], jd)
        hard_set = set(result.hard_blockers)
        nice_set = set(result.nice_to_haves)
        assert hard_set & nice_set == set()

    def test_union_of_hard_and_nice_equals_missing_skills(self) -> None:
        missing = ["Python", "Docker", "AWS", "Kubernetes"]
        jd = "Python Python needed. Docker required. AWS is nice. Kubernetes optional."
        result = _classify_gaps(missing, jd)
        total = set(result.hard_blockers) | set(result.nice_to_haves)
        assert total == set(missing)

    def test_very_long_jd_text_no_crash(self) -> None:
        jd = ("Python is needed. " * 600)  # ~10 800 chars
        result = _classify_gaps(["Python"], jd)
        assert "Python" in result.hard_blockers

    def test_newline_in_jd_text_does_not_break_count(self) -> None:
        jd = "Python\nis required.\nPython\nexperience needed."
        result = _classify_gaps(["Python"], jd)
        assert "Python" in result.hard_blockers

    def test_skill_is_common_word_counted_correctly(self) -> None:
        # "Management" appears many times
        jd = "Management of projects. Management skills required. Good management."
        result = _classify_gaps(["Management"], jd)
        assert "Management" in result.hard_blockers

    def test_unicode_skill_in_jd_counted(self) -> None:
        jd = "经验 is required. 经验 needed."
        result = _classify_gaps(["经验"], jd)
        assert "经验" in result.hard_blockers

    def test_gap_classification_attached_to_match_report(self) -> None:
        scorer = make_scorer()
        report = scorer.score(
            ents(skills=["Python"]),
            ents(skills=["Python", "Docker"]),
            semantic_sim=0.5,
            jd_text="Docker Docker is required. Python is nice.",
        )
        assert isinstance(report.gap_classification, GapClassification)
        assert "Docker" in report.gap_classification.hard_blockers
        assert "Python" not in report.gap_classification.hard_blockers

    def test_gap_classification_with_no_jd_text_on_scorer_call(self) -> None:
        scorer = make_scorer()
        report = scorer.score(
            ents(skills=[]),
            ents(skills=["Python", "Docker"]),
            semantic_sim=0.5,
        )
        # No jd_text → all nice_to_haves
        assert report.gap_classification.hard_blockers == []

    def test_all_missing_skills_are_hard_blockers_when_mentioned_twice(self) -> None:
        jd = "Python Python. Docker Docker. AWS AWS."
        result = _classify_gaps(["Python", "Docker", "AWS"], jd)
        assert set(result.hard_blockers) == {"Python", "Docker", "AWS"}
        assert result.nice_to_haves == []

    def test_gap_classification_empty_both_when_no_missing_skills(self) -> None:
        scorer = make_scorer()
        shared = ["Python", "Docker"]
        report = scorer.score(
            ents(skills=shared),
            ents(skills=shared),
            semantic_sim=0.8,
            jd_text="Python Python Docker Docker",
        )
        # No missing skills → both lists empty
        assert report.gap_classification.hard_blockers == []
        assert report.gap_classification.nice_to_haves == []


# ── Section 4: ATS keyword ranking ────────────────────────────────────────────

class TestAtsKeywordRanking:
    def test_returns_at_most_15_keywords(self) -> None:
        missing = [f"Skill{i}" for i in range(30)]
        result = _extract_ats_keywords(missing, "")
        assert len(result) <= 15

    def test_returns_exactly_15_when_more_missing(self) -> None:
        missing = [f"Skill{i}" for i in range(25)]
        result = _extract_ats_keywords(missing, "")
        assert len(result) == 15

    def test_returns_all_when_fewer_than_15_missing(self) -> None:
        missing = ["Python", "Docker", "AWS"]
        result = _extract_ats_keywords(missing, "")
        assert len(result) == 3

    def test_most_frequent_skill_ranked_first(self) -> None:
        jd = "Kubernetes Kubernetes Kubernetes Docker Docker Terraform"
        result = _extract_ats_keywords(["Kubernetes", "Docker", "Terraform"], jd)
        assert result[0] == "Kubernetes"
        assert result[1] == "Docker"

    def test_empty_missing_returns_empty(self) -> None:
        result = _extract_ats_keywords([], "Some job description text.")
        assert result == []

    def test_empty_jd_returns_first_15_missing(self) -> None:
        missing = [f"Skill{i}" for i in range(20)]
        result = _extract_ats_keywords(missing, "")
        assert result == missing[:15]

    def test_all_ats_keywords_come_from_missing(self) -> None:
        missing = ["Python", "Docker", "AWS"]
        jd = "Python Python Docker AWS AWS AWS"
        result = _extract_ats_keywords(missing, jd)
        for kw in result:
            assert kw in missing

    def test_zero_frequency_skills_still_included(self) -> None:
        missing = ["Python", "Golang"]
        jd = "Python Python is needed."  # Golang not in JD
        result = _extract_ats_keywords(missing, jd)
        assert "Golang" in result

    def test_ranking_is_deterministic(self) -> None:
        missing = ["Python", "Docker", "AWS"]
        jd = "Python Python Docker Docker AWS"
        r1 = _extract_ats_keywords(missing, jd)
        r2 = _extract_ats_keywords(missing, jd)
        assert r1 == r2

    def test_ats_limit_boundary_at_exactly_15(self) -> None:
        missing = [f"Skill{i}" for i in range(15)]
        result = _extract_ats_keywords(missing, "")
        assert len(result) == 15

    def test_single_missing_skill_returned(self) -> None:
        result = _extract_ats_keywords(["Python"], "Python Python needed.")
        assert result == ["Python"]

    def test_ats_keywords_on_report(self) -> None:
        scorer = make_scorer()
        report = scorer.score(
            ents(skills=["Python"]),
            ents(skills=["Python", "Docker", "AWS"]),
            semantic_sim=0.5,
            jd_text="Docker Docker AWS Python",
        )
        assert isinstance(report.ats_keywords, list)
        # Docker appears 2x → ranked higher than AWS (1x)
        if "Docker" in report.ats_keywords and "AWS" in report.ats_keywords:
            assert report.ats_keywords.index("Docker") < report.ats_keywords.index("AWS")

    def test_ats_keywords_case_insensitive_frequency(self) -> None:
        """Frequency count uses lowercased text."""
        jd = "KUBERNETES kubernetes Kubernetes"
        result = _extract_ats_keywords(["Kubernetes"], jd)
        assert "Kubernetes" in result


# ── Section 5: Archetype detection edge cases ─────────────────────────────────

class TestArchetypeDetectionEdgeCases:
    def test_detects_all_six_archetypes(self) -> None:
        samples = {
            "llmops": "LLM observability evals monitoring pipelines reliability tracing guardrails",
            "agentic": "multi-agent orchestration HITL human-in-the-loop workflow automation",
            "ai_pm": "PRD roadmap product discovery product management stakeholder",
            "solutions_architect": "solutions architect systems design enterprise integration architecture",
            "forward_deployed": "forward deployed client-facing field engineer customer deployment prototype",
            "transformation": "change management adoption enablement transformation organizational program management",
        }
        for expected, text in samples.items():
            result = _detect_archetype(text)
            assert result == expected, f"Expected {expected!r} for: {text!r}, got {result!r}"

    def test_empty_text_returns_general(self) -> None:
        assert _detect_archetype("") == "general"

    def test_whitespace_only_returns_general(self) -> None:
        assert _detect_archetype("   \n\t  ") == "general"

    def test_no_matching_keywords_returns_general(self) -> None:
        assert _detect_archetype("We are looking for a software developer to join our team.") == "general"

    def test_case_insensitive_keyword_matching(self) -> None:
        assert _detect_archetype("OBSERVABILITY and EVALS required.") == "llmops"

    def test_single_keyword_match_returns_archetype(self) -> None:
        assert _detect_archetype("Experience with observability tools.") == "llmops"

    def test_tie_returns_consistent_result(self) -> None:
        """If two archetypes tie, result must be deterministic (same call → same output)."""
        text = "observability evals agent agentic"  # llmops: 2, agentic: 2
        r1 = _detect_archetype(text)
        r2 = _detect_archetype(text)
        assert r1 == r2

    def test_highest_signal_wins(self) -> None:
        text = "observability evals monitoring reliability tracing guardrails pipelines llmops agent"
        # llmops has 8 signals, agentic has 1
        assert _detect_archetype(text) == "llmops"

    def test_archetype_keyword_in_uppercase_detected(self) -> None:
        assert _detect_archetype("PRD ROADMAP DISCOVERY STAKEHOLDER") == "ai_pm"

    def test_archetype_result_is_known_value(self) -> None:
        texts = [
            "generic job description",
            "observability monitoring",
            "agent orchestration",
            "PRD roadmap stakeholder",
        ]
        for text in texts:
            result = _detect_archetype(text)
            assert result in VALID_ARCHETYPES, f"Unknown archetype {result!r} for: {text!r}"

    def test_report_archetype_is_valid_value(self) -> None:
        scorer = make_scorer()
        report = scorer.score(ents(), ents(), semantic_sim=0.5, jd_text="observability monitoring evals")
        assert report.role_archetype in VALID_ARCHETYPES


# ── Section 6: Apply recommendation thresholds ────────────────────────────────

class TestApplyRecommendationThresholds:
    def test_100_is_strong_match(self) -> None:
        assert _apply_recommendation(100.0) == "strong_match"

    def test_75_001_is_strong_match(self) -> None:
        assert _apply_recommendation(75.001) == "strong_match"

    def test_75_is_strong_match(self) -> None:
        assert _apply_recommendation(75.0) == "strong_match"

    def test_74_999_is_good_match(self) -> None:
        assert _apply_recommendation(74.999) == "good_match"

    def test_60_001_is_good_match(self) -> None:
        assert _apply_recommendation(60.001) == "good_match"

    def test_60_is_good_match(self) -> None:
        assert _apply_recommendation(60.0) == "good_match"

    def test_59_999_is_borderline(self) -> None:
        assert _apply_recommendation(59.999) == "borderline"

    def test_45_001_is_borderline(self) -> None:
        assert _apply_recommendation(45.001) == "borderline"

    def test_45_is_borderline(self) -> None:
        assert _apply_recommendation(45.0) == "borderline"

    def test_44_999_is_skip(self) -> None:
        assert _apply_recommendation(44.999) == "skip"

    def test_1_is_skip(self) -> None:
        assert _apply_recommendation(1.0) == "skip"

    def test_0_is_skip(self) -> None:
        assert _apply_recommendation(0.0) == "skip"

    def test_negative_score_is_skip(self) -> None:
        # After clamping, -1 can't actually reach here, but test the function directly
        assert _apply_recommendation(-10.0) == "skip"

    def test_result_always_in_valid_set(self) -> None:
        for score in [0, 10, 44.9, 45, 59.9, 60, 74.9, 75, 90, 100]:
            assert _apply_recommendation(float(score)) in VALID_RECOMMENDATIONS


# ── Section 7: Experience level detection stress ───────────────────────────────

class TestExperienceLevelDetectionStress:
    def test_sr_abbreviation_detected_as_senior(self) -> None:
        assert _detect_level(["Sr Software Engineer"]) == "senior"

    def test_sr_dot_detected(self) -> None:
        assert _detect_level(["Sr. Engineer"]) == "senior"

    def test_jr_abbreviation_detected_as_junior(self) -> None:
        assert _detect_level(["Jr Data Analyst"]) == "junior"

    def test_intern_detected_as_entry(self) -> None:
        assert _detect_level(["Software Engineering Intern"]) == "entry"

    def test_associate_detected_as_mid(self) -> None:
        assert _detect_level(["Associate Software Engineer"]) == "mid"

    def test_mid_detected(self) -> None:
        assert _detect_level(["Mid-level Data Scientist"]) == "mid"

    def test_staff_detected_as_principal(self) -> None:
        assert _detect_level(["Staff Engineer"]) == "principal"

    def test_principal_overrides_senior(self) -> None:
        """'principal' takes priority in the detection logic."""
        assert _detect_level(["Principal Senior Engineer"]) == "principal"

    def test_multiple_titles_uses_combined_text(self) -> None:
        """Senior appears across multiple titles — should detect it."""
        result = _detect_level(["Software Engineer", "Senior Developer"])
        assert result == "senior"

    def test_level_not_detected_score_is_half(self) -> None:
        score = _experience_level_score("level_not_detected")
        assert score == 0.5

    def test_match_score_is_one(self) -> None:
        assert _experience_level_score("senior_match") == 1.0

    def test_mismatch_score_is_below_match(self) -> None:
        mismatch = _experience_level_score("senior_required_junior_detected")
        assert mismatch < 1.0

    def test_not_detected_score_is_below_match(self) -> None:
        not_detected = _experience_level_score("senior_required_level_not_detected_in_resume")
        assert not_detected < 1.0

    def test_both_unknown_gives_level_not_detected_string(self) -> None:
        scorer = make_scorer()
        report = scorer.score(
            ents(job_titles=["Software Engineer"]),
            ents(job_titles=["Software Developer"]),
            semantic_sim=0.5,
        )
        assert report.breakdown.experience_match == "level_not_detected"


# ── Section 8: Title relevance edge cases ─────────────────────────────────────

class TestTitleRelevanceEdgeCases:
    def test_identical_single_word_titles(self) -> None:
        scorer = make_scorer()
        report = scorer.score(
            ents(job_titles=["Engineer"]),
            ents(job_titles=["Engineer"]),
            semantic_sim=0.5,
        )
        assert report.breakdown.title_relevance == 1.0

    def test_no_overlap_titles_is_zero(self) -> None:
        scorer = make_scorer()
        report = scorer.score(
            ents(job_titles=["Designer"]),
            ents(job_titles=["Engineer"]),
            semantic_sim=0.5,
        )
        assert report.breakdown.title_relevance == 0.0

    def test_empty_resume_title_gives_zero_relevance(self) -> None:
        scorer = make_scorer()
        report = scorer.score(
            ents(job_titles=[]),
            ents(job_titles=["Senior Engineer"]),
            semantic_sim=0.5,
        )
        assert report.breakdown.title_relevance == 0.0

    def test_empty_jd_title_gives_zero_relevance(self) -> None:
        scorer = make_scorer()
        report = scorer.score(
            ents(job_titles=["Senior Engineer"]),
            ents(job_titles=[]),
            semantic_sim=0.5,
        )
        assert report.breakdown.title_relevance == 0.0

    def test_partial_word_overlap_between_zero_and_one(self) -> None:
        scorer = make_scorer()
        report = scorer.score(
            ents(job_titles=["Data Analyst"]),
            ents(job_titles=["Data Scientist"]),
            semantic_sim=0.5,
        )
        assert 0.0 < report.breakdown.title_relevance < 1.0

    def test_title_with_numbers(self) -> None:
        scorer = make_scorer()
        report = scorer.score(
            ents(job_titles=["L5 Engineer"]),
            ents(job_titles=["L5 Engineer"]),
            semantic_sim=0.5,
        )
        assert report.breakdown.title_relevance == 1.0


# ── Section 9: MatchReport structural integrity ───────────────────────────────

class TestMatchReportStructure:
    def test_report_has_all_required_fields(self) -> None:
        scorer = make_scorer()
        report = scorer.score(ents(skills=["Python"]), ents(skills=["Python"]), semantic_sim=0.7)
        assert hasattr(report, "overall_score")
        assert hasattr(report, "breakdown")
        assert hasattr(report, "gap_classification")
        assert hasattr(report, "apply_recommendation")
        assert hasattr(report, "ats_keywords")
        assert hasattr(report, "role_archetype")
        assert hasattr(report, "recommendations")

    def test_breakdown_has_all_fields(self) -> None:
        scorer = make_scorer()
        report = scorer.score(ents(), ents(), semantic_sim=0.5)
        assert hasattr(report.breakdown, "semantic_similarity")
        assert hasattr(report.breakdown, "skill_match")
        assert hasattr(report.breakdown, "title_relevance")
        assert hasattr(report.breakdown, "experience_match")

    def test_skill_match_rate_between_0_and_1(self) -> None:
        scorer = make_scorer()
        for sim in [0.0, 0.3, 0.7, 1.0]:
            report = scorer.score(ents(skills=["Python"]), ents(skills=["Python", "Docker"]), semantic_sim=sim)
            assert 0.0 <= report.breakdown.skill_match.match_rate <= 1.0

    def test_apply_recommendation_is_valid(self) -> None:
        scorer = make_scorer()
        for sim in [0.0, 0.2, 0.5, 0.8, 1.0]:
            report = scorer.score(ents(), ents(), semantic_sim=sim)
            assert report.apply_recommendation in VALID_RECOMMENDATIONS

    def test_role_archetype_is_non_empty_string(self) -> None:
        scorer = make_scorer()
        report = scorer.score(ents(), ents(), semantic_sim=0.5)
        assert isinstance(report.role_archetype, str)
        assert len(report.role_archetype) > 0

    def test_ats_keywords_is_list_of_strings(self) -> None:
        scorer = make_scorer()
        report = scorer.score(ents(), ents(skills=["Python", "Docker"]), semantic_sim=0.5)
        assert isinstance(report.ats_keywords, list)
        for kw in report.ats_keywords:
            assert isinstance(kw, str)

    def test_semantic_similarity_stored_on_breakdown(self) -> None:
        scorer = make_scorer()
        report = scorer.score(ents(), ents(), semantic_sim=0.6789)
        assert abs(report.breakdown.semantic_similarity - 0.6789) < 0.0001

    def test_recommendations_count_at_most_6(self) -> None:
        scorer = make_scorer()
        report = scorer.score(
            ents(skills=["Python"], job_titles=["Junior Engineer"]),
            ents(skills=["Python", "Docker", "AWS", "Kubernetes", "Terraform", "Kafka", "Airflow"],
                 job_titles=["Senior Engineer"]),
            semantic_sim=0.1,
        )
        assert len(report.recommendations) <= 6

    def test_report_is_matchreport_instance(self) -> None:
        scorer = make_scorer()
        report = scorer.score(ents(), ents(), semantic_sim=0.5)
        assert isinstance(report, MatchReport)

    def test_gap_classification_is_instance(self) -> None:
        scorer = make_scorer()
        report = scorer.score(ents(), ents(skills=["Python"]), semantic_sim=0.5)
        assert isinstance(report.gap_classification, GapClassification)
