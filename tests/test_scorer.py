import pytest

from engine.extractor import ResumeEntities
from engine.scorer import (
    MatchReport,
    MatchScorer,
    _apply_recommendation,
    _classify_gaps,
    _detect_archetype,
    _detect_level,
    _experience_level_score,
    _extract_ats_keywords,
    _normalize_skill,
)


def make_scorer() -> MatchScorer:
    return MatchScorer()


def make_entities(
    skills: list[str] | None = None,
    job_titles: list[str] | None = None,
    companies: list[str] | None = None,
    education: list[str] | None = None,
    certifications: list[str] | None = None,
) -> ResumeEntities:
    return ResumeEntities(
        skills=skills or [],
        job_titles=job_titles or [],
        companies=companies or [],
        education=education or [],
        certifications=certifications or [],
    )


class TestMatchScorerPerfectSkillMatch:
    def test_overall_score_is_high(self) -> None:
        scorer = make_scorer()
        shared_skills = ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS", "Git"]
        resume = make_entities(
            skills=shared_skills,
            job_titles=["Senior Software Engineer"],
        )
        jd = make_entities(
            skills=shared_skills,
            job_titles=["Senior Software Engineer"],
        )
        report: MatchReport = scorer.score(resume, jd, semantic_sim=0.90)
        assert report.overall_score >= 70.0

    def test_skill_match_rate_is_one(self) -> None:
        scorer = make_scorer()
        shared_skills = ["Python", "FastAPI", "Docker"]
        resume = make_entities(skills=shared_skills)
        jd = make_entities(skills=shared_skills)
        report = scorer.score(resume, jd, semantic_sim=0.85)
        assert report.breakdown.skill_match.match_rate == 1.0

    def test_no_missing_skills_on_perfect_match(self) -> None:
        scorer = make_scorer()
        shared_skills = ["Python", "SQL", "Git"]
        resume = make_entities(skills=shared_skills)
        jd = make_entities(skills=shared_skills)
        report = scorer.score(resume, jd, semantic_sim=0.80)
        assert report.breakdown.skill_match.missing == []

    def test_all_skills_appear_in_matched(self) -> None:
        scorer = make_scorer()
        shared_skills = ["Python", "Docker", "Kubernetes"]
        resume = make_entities(skills=shared_skills)
        jd = make_entities(skills=shared_skills)
        report = scorer.score(resume, jd, semantic_sim=0.88)
        assert set(report.breakdown.skill_match.matched) == set(shared_skills)


class TestMatchScorerZeroSkillMatch:
    def test_overall_score_is_low(self) -> None:
        scorer = make_scorer()
        resume = make_entities(skills=["Python", "pandas", "NumPy"])
        jd = make_entities(skills=["Kubernetes", "Terraform", "Kafka", "Spark"])
        report = scorer.score(resume, jd, semantic_sim=0.20)
        assert report.overall_score < 50.0

    def test_match_rate_is_zero(self) -> None:
        scorer = make_scorer()
        resume = make_entities(skills=["Python", "pandas"])
        jd = make_entities(skills=["Kubernetes", "Terraform"])
        report = scorer.score(resume, jd, semantic_sim=0.15)
        assert report.breakdown.skill_match.match_rate == 0.0

    def test_matched_list_is_empty(self) -> None:
        scorer = make_scorer()
        resume = make_entities(skills=["React", "TypeScript"])
        jd = make_entities(skills=["Spark", "Kafka", "Airflow"])
        report = scorer.score(resume, jd, semantic_sim=0.10)
        assert report.breakdown.skill_match.matched == []

    def test_all_jd_skills_are_missing(self) -> None:
        scorer = make_scorer()
        jd_skills = ["Kubernetes", "Terraform", "Kafka"]
        resume = make_entities(skills=["Python", "pandas"])
        jd = make_entities(skills=jd_skills)
        report = scorer.score(resume, jd, semantic_sim=0.10)
        assert set(report.breakdown.skill_match.missing) == set(jd_skills)


class TestMatchScorerRecommendations:
    def test_missing_skills_appear_in_recommendations(self) -> None:
        scorer = make_scorer()
        resume = make_entities(skills=["Python"])
        jd = make_entities(skills=["Python", "Kubernetes", "Terraform", "Kafka"])
        report = scorer.score(resume, jd, semantic_sim=0.50)
        recs_text = " ".join(report.recommendations)
        assert "Kubernetes" in recs_text or "Terraform" in recs_text or "Kafka" in recs_text

    def test_recommendations_list_is_not_empty_when_skills_missing(self) -> None:
        scorer = make_scorer()
        resume = make_entities(skills=[])
        jd = make_entities(skills=["Python", "Docker", "AWS"])
        report = scorer.score(resume, jd, semantic_sim=0.30)
        assert len(report.recommendations) > 0

    def test_recommendations_capped_at_six(self) -> None:
        scorer = make_scorer()
        resume = make_entities(skills=["Python"])
        jd = make_entities(
            skills=["Kubernetes", "Terraform", "Kafka", "Spark", "Airflow", "Redis"]
        )
        report = scorer.score(resume, jd, semantic_sim=0.20)
        assert len(report.recommendations) <= 6

    def test_no_recommendations_for_perfect_match(self) -> None:
        scorer = make_scorer()
        shared = ["Python", "FastAPI", "Docker"]
        resume = make_entities(
            skills=shared,
            job_titles=["Senior Engineer"],
        )
        jd = make_entities(
            skills=shared,
            job_titles=["Senior Engineer"],
        )
        report = scorer.score(resume, jd, semantic_sim=0.95)
        assert len(report.recommendations) == 0

    def test_strengths_recommendation_present_on_partial_match(self) -> None:
        scorer = make_scorer()
        shared = ["Python", "Docker", "AWS"]
        resume = make_entities(skills=shared)
        jd = make_entities(skills=shared + ["Kubernetes"])
        report = scorer.score(resume, jd, semantic_sim=0.75)
        recs_text = " ".join(report.recommendations)
        assert "Strong skill alignment" in recs_text


class TestMatchScorerScoreRange:
    def test_overall_score_never_below_zero(self) -> None:
        scorer = make_scorer()
        resume = make_entities(skills=[])
        jd = make_entities(skills=["Python", "Kubernetes"])
        report = scorer.score(resume, jd, semantic_sim=0.0)
        assert report.overall_score >= 0.0

    def test_overall_score_never_above_100(self) -> None:
        scorer = make_scorer()
        shared = ["Python", "FastAPI", "Docker", "AWS", "Git"]
        resume = make_entities(skills=shared, job_titles=["Senior Engineer"])
        jd = make_entities(skills=shared, job_titles=["Senior Engineer"])
        report = scorer.score(resume, jd, semantic_sim=1.0)
        assert report.overall_score <= 100.0

    def test_semantic_similarity_stored_correctly(self) -> None:
        scorer = make_scorer()
        resume = make_entities(skills=["Python"])
        jd = make_entities(skills=["Python"])
        report = scorer.score(resume, jd, semantic_sim=0.73)
        assert abs(report.breakdown.semantic_similarity - 0.73) < 0.001


class TestSkillMatchCaseInsensitive:
    def test_python_lowercase_matches_uppercase(self) -> None:
        scorer = make_scorer()
        resume = make_entities(skills=["python"])
        jd = make_entities(skills=["Python"])
        report = scorer.score(resume, jd, semantic_sim=0.80)
        assert report.breakdown.skill_match.match_rate == 1.0

    def test_mixed_case_skills_matched(self) -> None:
        scorer = make_scorer()
        resume = make_entities(skills=["DOCKER", "fastapi"])
        jd = make_entities(skills=["Docker", "FastAPI"])
        report = scorer.score(resume, jd, semantic_sim=0.80)
        assert report.breakdown.skill_match.match_rate == 1.0

    def test_empty_jd_skills_returns_zero_match_rate(self) -> None:
        scorer = make_scorer()
        resume = make_entities(skills=["Python", "SQL"])
        jd = make_entities(skills=[])
        report = scorer.score(resume, jd, semantic_sim=0.50)
        assert report.breakdown.skill_match.match_rate == 0.0

    def test_partial_skill_overlap_correct_rate(self) -> None:
        scorer = make_scorer()
        resume = make_entities(skills=["Python", "SQL"])
        jd = make_entities(skills=["Python", "SQL", "Docker", "AWS"])
        report = scorer.score(resume, jd, semantic_sim=0.60)
        assert abs(report.breakdown.skill_match.match_rate - 0.5) < 0.001


class TestTitleRelevance:
    def test_identical_titles_full_score(self) -> None:
        scorer = make_scorer()
        resume = make_entities(job_titles=["Data Scientist"])
        jd = make_entities(job_titles=["Data Scientist"])
        report = scorer.score(resume, jd, semantic_sim=0.70)
        assert report.breakdown.title_relevance == 1.0

    def test_no_titles_zero_relevance(self) -> None:
        scorer = make_scorer()
        resume = make_entities(job_titles=[])
        jd = make_entities(job_titles=[])
        report = scorer.score(resume, jd, semantic_sim=0.70)
        assert report.breakdown.title_relevance == 0.0

    def test_partial_title_overlap(self) -> None:
        scorer = make_scorer()
        resume = make_entities(job_titles=["Data Analyst"])
        jd = make_entities(job_titles=["Data Scientist"])
        report = scorer.score(resume, jd, semantic_sim=0.60)
        # "data" overlaps, "analyst" != "scientist" → partial overlap
        assert 0 < report.breakdown.title_relevance < 1.0


class TestExperienceLevelDetection:
    def test_detect_senior(self) -> None:
        assert _detect_level(["Senior Software Engineer"]) == "senior"

    def test_detect_junior(self) -> None:
        assert _detect_level(["Junior Data Analyst"]) == "junior"

    def test_detect_lead(self) -> None:
        assert _detect_level(["Tech Lead"]) == "lead"

    def test_detect_principal(self) -> None:
        assert _detect_level(["Principal Engineer"]) == "principal"

    def test_detect_unknown(self) -> None:
        assert _detect_level(["Software Engineer"]) == "unknown"

    def test_detect_level_empty_list(self) -> None:
        assert _detect_level([]) == "unknown"

    def test_experience_score_match(self) -> None:
        assert _experience_level_score("senior_match") == 1.0

    def test_experience_score_mismatch(self) -> None:
        score = _experience_level_score("senior_required_junior_detected")
        assert score < 1.0

    def test_experience_score_not_detected(self) -> None:
        score = _experience_level_score("senior_required_level_not_detected_in_resume")
        assert 0 < score < 1.0


class TestSkillAliasNormalization:
    def test_js_matches_javascript(self) -> None:
        scorer = make_scorer()
        report = scorer.score(make_entities(skills=["JS"]), make_entities(skills=["JavaScript"]), semantic_sim=0.5)
        assert report.breakdown.skill_match.match_rate == 1.0

    def test_postgres_matches_postgresql(self) -> None:
        scorer = make_scorer()
        report = scorer.score(make_entities(skills=["Postgres"]), make_entities(skills=["PostgreSQL"]), semantic_sim=0.5)
        assert report.breakdown.skill_match.match_rate == 1.0

    def test_k8s_matches_kubernetes(self) -> None:
        scorer = make_scorer()
        report = scorer.score(make_entities(skills=["k8s"]), make_entities(skills=["Kubernetes"]), semantic_sim=0.5)
        assert report.breakdown.skill_match.match_rate == 1.0

    def test_ml_matches_machine_learning(self) -> None:
        scorer = make_scorer()
        report = scorer.score(make_entities(skills=["ML"]), make_entities(skills=["Machine Learning"]), semantic_sim=0.5)
        assert report.breakdown.skill_match.match_rate == 1.0

    def test_node_matches_nodejs(self) -> None:
        scorer = make_scorer()
        report = scorer.score(make_entities(skills=["Node"]), make_entities(skills=["Node.js"]), semantic_sim=0.5)
        assert report.breakdown.skill_match.match_rate == 1.0

    def test_alias_bidirectional(self) -> None:
        scorer = make_scorer()
        report = scorer.score(make_entities(skills=["JavaScript"]), make_entities(skills=["JS"]), semantic_sim=0.5)
        assert report.breakdown.skill_match.match_rate == 1.0

    def test_normalize_skill_unknown_passthrough(self) -> None:
        assert _normalize_skill("Python") == "python"

    def test_normalize_skill_known_alias(self) -> None:
        assert _normalize_skill("k8s") == "kubernetes"


class TestApplyRecommendation:
    def test_strong_match_at_75(self) -> None:
        assert _apply_recommendation(75.0) == "strong_match"

    def test_strong_match_above_75(self) -> None:
        assert _apply_recommendation(90.0) == "strong_match"

    def test_good_match_at_60(self) -> None:
        assert _apply_recommendation(60.0) == "good_match"

    def test_good_match_at_74(self) -> None:
        assert _apply_recommendation(74.9) == "good_match"

    def test_borderline_at_45(self) -> None:
        assert _apply_recommendation(45.0) == "borderline"

    def test_borderline_at_59(self) -> None:
        assert _apply_recommendation(59.9) == "borderline"

    def test_skip_below_45(self) -> None:
        assert _apply_recommendation(44.9) == "skip"

    def test_skip_at_zero(self) -> None:
        assert _apply_recommendation(0.0) == "skip"

    def test_report_contains_apply_recommendation(self) -> None:
        scorer = make_scorer()
        shared = ["Python", "FastAPI", "Docker", "AWS", "Git"]
        report = scorer.score(
            make_entities(skills=shared, job_titles=["Senior Engineer"]),
            make_entities(skills=shared, job_titles=["Senior Engineer"]),
            semantic_sim=0.95,
        )
        assert report.apply_recommendation in ("strong_match", "good_match", "borderline", "skip")


class TestGapClassification:
    def test_hard_blocker_when_skill_appears_twice(self) -> None:
        jd_text = "We need Python experience. Python is required for this role."
        result = _classify_gaps(["Python"], jd_text)
        assert "Python" in result.hard_blockers
        assert "Python" not in result.nice_to_haves

    def test_nice_to_have_when_skill_appears_once(self) -> None:
        jd_text = "Experience with Docker is a plus."
        result = _classify_gaps(["Docker"], jd_text)
        assert "Docker" in result.nice_to_haves
        assert "Docker" not in result.hard_blockers

    def test_empty_jd_text_puts_all_in_nice_to_haves(self) -> None:
        result = _classify_gaps(["Python", "Docker"], "")
        assert result.hard_blockers == []
        assert set(result.nice_to_haves) == {"Python", "Docker"}

    def test_empty_missing_skills(self) -> None:
        result = _classify_gaps([], "Some job description text.")
        assert result.hard_blockers == []
        assert result.nice_to_haves == []

    def test_report_contains_gap_classification(self) -> None:
        scorer = make_scorer()
        resume = make_entities(skills=["Python"])
        jd = make_entities(skills=["Python", "Kubernetes", "Terraform"])
        report = scorer.score(resume, jd, semantic_sim=0.50)
        assert hasattr(report.gap_classification, "hard_blockers")
        assert hasattr(report.gap_classification, "nice_to_haves")


class TestAtsKeywords:
    def test_returns_missing_skills_limited_to_15(self) -> None:
        missing = [f"Skill{i}" for i in range(20)]
        result = _extract_ats_keywords(missing, "")
        assert len(result) <= 15

    def test_more_frequent_skills_ranked_first(self) -> None:
        jd_text = "Kubernetes Kubernetes Kubernetes. Docker Docker. Terraform."
        result = _extract_ats_keywords(["Kubernetes", "Docker", "Terraform"], jd_text)
        assert result[0] == "Kubernetes"
        assert result[1] == "Docker"

    def test_empty_missing_returns_empty(self) -> None:
        result = _extract_ats_keywords([], "Some job description text.")
        assert result == []

    def test_report_contains_ats_keywords(self) -> None:
        scorer = make_scorer()
        resume = make_entities(skills=["Python"])
        jd = make_entities(skills=["Python", "Kubernetes", "Terraform"])
        report = scorer.score(resume, jd, semantic_sim=0.50)
        assert isinstance(report.ats_keywords, list)


class TestRoleArchetypeDetection:
    def test_detects_llmops(self) -> None:
        jd = "We need someone experienced in LLM observability, evals, and monitoring pipelines."
        assert _detect_archetype(jd) == "llmops"

    def test_detects_agentic(self) -> None:
        jd = "Build multi-agent systems with orchestration and HITL workflows."
        assert _detect_archetype(jd) == "agentic"

    def test_detects_ai_pm(self) -> None:
        jd = "Manage the AI product roadmap, write PRDs, and run product discovery sessions."
        assert _detect_archetype(jd) == "ai_pm"

    def test_detects_transformation(self) -> None:
        jd = "Lead AI adoption and change management across the organization."
        assert _detect_archetype(jd) == "transformation"

    def test_returns_general_for_no_signals(self) -> None:
        jd = "We are looking for a software developer to join our team."
        assert _detect_archetype(jd) == "general"

    def test_returns_general_for_empty_text(self) -> None:
        assert _detect_archetype("") == "general"

    def test_report_contains_role_archetype(self) -> None:
        scorer = make_scorer()
        resume = make_entities(skills=["Python"])
        jd = make_entities(skills=["Python"])
        report = scorer.score(
            resume, jd, semantic_sim=0.70,
            jd_text="Build multi-agent orchestration systems.",
        )
        assert report.role_archetype == "agentic"
