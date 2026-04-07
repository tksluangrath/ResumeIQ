"""
Tests for latex_builder.py — parsing, rendering, and optimization.

These tests use the real resume_template.tex from samples/ as fixture data.
No PDF compilation is performed (pdflatex not required to run these tests).
"""

from pathlib import Path

import pytest

from engine.latex_builder import (
    ContactInfo,
    EducationEntry,
    ExperienceEntry,
    ProjectEntry,
    ResumeData,
    TechnicalSkills,
    escape_latex,
    unescape_latex,
    parse_tex_to_resume_data,
    render_latex,
)
from engine.optimizer import optimize
from engine.profile import SkillEntry, UserProfile
from engine.scorer import GapClassification, MatchReport, ScoreBreakdown, SkillMatchResult


def _make_match_report(
    score: float,
    matched: list[str],
    missing: list[str],
    title_relevance: float = 0.65,
    experience_match: str = "level_not_detected",
    recommendations: list[str] | None = None,
) -> MatchReport:
    return MatchReport(
        overall_score=score,
        breakdown=ScoreBreakdown(
            semantic_similarity=round(score / 100, 2),
            skill_match=SkillMatchResult(
                matched=matched,
                missing=missing,
                match_rate=len(matched) / (len(matched) + len(missing)) if (matched or missing) else 0.0,
            ),
            title_relevance=title_relevance,
            experience_match=experience_match,
        ),
        gap_classification=GapClassification(hard_blockers=[], nice_to_haves=missing),
        apply_recommendation="borderline",
        ats_keywords=missing[:15],
        role_archetype="general",
        recommendations=recommendations or [],
    )

SAMPLES_DIR = Path(__file__).parent.parent / "samples"
TEX_FILE = SAMPLES_DIR / "resume_template.tex"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_resume_data() -> ResumeData:
    return ResumeData(
        contact=ContactInfo(
            name="Terrance Luangrath",
            location="Manassas, VA",
            phone="571-332-8954",
            email="tksluangrath@gmail.com",
            linkedin="terranceluangrath",
            github="tksluangrath.github.io",
        ),
        education=[
            EducationEntry(
                institution="University of Virginia",
                location="Charlottesville, VA",
                degree="Master of Science in Data Science; GPA: 4.0",
                dates="Expected Aug. 2026",
                coursework=["Relevant Coursework: Bayesian Machine Learning"],
            )
        ],
        experience=[
            ExperienceEntry(
                title="Junior Data Analyst",
                dates="Jun. 2024 -- May 2025",
                company="ACTFORE",
                location="Reston, VA",
                bullets=[
                    "Processed and analyzed 1TB+ of sensitive data daily",
                    "Developed automated reporting workflows",
                ],
            )
        ],
        projects=[
            ProjectEntry(
                name="AI Course Recommendation Agent",
                technologies="Python, LangChain, Streamlit",
                url="https://github.com/tksluangrath/course-recommendation-agent",
                date="Feb. 2026",
                bullets=["Developed end-to-end AI application integrating LLMs"],
            )
        ],
        skills=TechnicalSkills(
            categories={
                "Programming & Machine Learning": "Python, SQL, scikit-learn",
                "Tools & Platforms": "Git, Docker, Streamlit",
            }
        ),
    )


@pytest.fixture
def sample_match_report() -> MatchReport:
    return _make_match_report(
        score=62.0,
        matched=["Python", "SQL", "Git"],
        missing=["Kubernetes", "AWS", "FastAPI"],
        title_relevance=0.65,
        experience_match="junior_detected_mid_required",
        recommendations=["Add Kubernetes to your skills section", "Highlight AWS experience"],
    )


# ---------------------------------------------------------------------------
# escape_latex tests
# ---------------------------------------------------------------------------

class TestEscapeLatex:
    def test_ampersand(self):
        assert escape_latex("R&D") == r"R\&D"

    def test_percent(self):
        assert escape_latex("99% accuracy") == r"99\% accuracy"

    def test_dollar(self):
        assert escape_latex("$2M revenue") == r"\$2M revenue"

    def test_underscore(self):
        assert escape_latex("my_variable") == r"my\_variable"

    def test_no_change_on_clean_text(self):
        assert escape_latex("Python developer") == "Python developer"

    def test_backslash_not_double_escaped(self):
        result = escape_latex("a\\b")
        assert r"\textbackslash{}" in result
        assert result.count(r"\textbackslash{}") == 1


# ---------------------------------------------------------------------------
# render_latex tests
# ---------------------------------------------------------------------------

class TestRenderLatex:
    def test_name_in_output(self, sample_resume_data):
        tex = render_latex(sample_resume_data)
        assert "Terrance Luangrath" in tex

    def test_email_in_output(self, sample_resume_data):
        tex = render_latex(sample_resume_data)
        assert "tksluangrath@gmail.com" in tex

    def test_experience_company_in_output(self, sample_resume_data):
        tex = render_latex(sample_resume_data)
        assert "ACTFORE" in tex

    def test_project_name_in_output(self, sample_resume_data):
        tex = render_latex(sample_resume_data)
        assert "AI Course Recommendation Agent" in tex

    def test_skills_category_in_output(self, sample_resume_data):
        tex = render_latex(sample_resume_data)
        assert "Programming" in tex

    def test_output_is_valid_latex_document(self, sample_resume_data):
        tex = render_latex(sample_resume_data)
        assert r"\begin{document}" in tex
        assert r"\end{document}" in tex

    def test_jinja_delimiters_not_in_output(self, sample_resume_data):
        tex = render_latex(sample_resume_data)
        assert "<<" not in tex
        assert ">>" not in tex
        assert "<%" not in tex


# ---------------------------------------------------------------------------
# parse_tex_to_resume_data tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not TEX_FILE.exists(), reason="resume_template.tex not in samples/")
class TestParseTexToResumeData:
    def test_name_parsed(self):
        data = parse_tex_to_resume_data(TEX_FILE)
        assert "Terrance" in data.contact.name

    def test_email_parsed(self):
        data = parse_tex_to_resume_data(TEX_FILE)
        assert "tksluangrath@gmail.com" in data.contact.email

    def test_education_count(self):
        data = parse_tex_to_resume_data(TEX_FILE)
        assert len(data.education) == 2

    def test_uva_in_education(self):
        data = parse_tex_to_resume_data(TEX_FILE)
        institutions = [e.institution for e in data.education]
        assert any("Virginia" in i for i in institutions)

    def test_experience_has_bullets(self):
        data = parse_tex_to_resume_data(TEX_FILE)
        for job in data.experience:
            assert len(job.bullets) > 0

    def test_projects_parsed(self):
        data = parse_tex_to_resume_data(TEX_FILE)
        assert len(data.projects) >= 1

    def test_skills_categories_not_empty(self):
        data = parse_tex_to_resume_data(TEX_FILE)
        assert len(data.skills.categories) > 0

    def test_round_trip_renders(self):
        """Parse the .tex then re-render — should produce valid LaTeX."""
        data = parse_tex_to_resume_data(TEX_FILE)
        tex = render_latex(data)
        assert r"\begin{document}" in tex
        assert "Terrance" in tex


# ---------------------------------------------------------------------------
# optimizer tests
# ---------------------------------------------------------------------------

class TestOptimizer:
    def test_missing_skills_injected(self, sample_resume_data, sample_match_report):
        result = optimize(sample_match_report, sample_resume_data)
        assert len(result.injected_skills) > 0
        all_skills = " ".join(result.resume.skills.categories.values())
        for skill in result.injected_skills:
            assert skill in all_skills

    def test_no_duplicate_skills(self, sample_resume_data, sample_match_report):
        result = optimize(sample_match_report, sample_resume_data)
        for items in result.resume.skills.categories.values():
            skill_list = [s.strip() for s in items.split(",")]
            assert len(skill_list) == len(set(skill_list))

    def test_notes_generated(self, sample_resume_data, sample_match_report):
        result = optimize(sample_match_report, sample_resume_data)
        assert len(result.notes) > 0

    def test_already_present_skills_not_re_added(self, sample_resume_data):
        report = _make_match_report(
            score=80.0,
            matched=["Python"],
            missing=["Python"],   # already in the resume
            title_relevance=0.8,
            experience_match="matched",
        )
        result = optimize(report, sample_resume_data)
        assert "Python" not in result.injected_skills

    def test_no_new_categories_created(self, sample_resume_data, sample_match_report):
        """Optimizer must never create new skill categories beyond what's already on the resume."""
        original_count = len(sample_resume_data.skills.categories)
        result = optimize(sample_match_report, sample_resume_data)
        assert len(result.resume.skills.categories) == original_count

    def test_profile_filters_unconfirmed_skills(self, sample_resume_data, sample_match_report):
        """With a profile, only skills in the profile are injected."""
        profile = UserProfile(
            skills=[SkillEntry(name="Kubernetes", proficiency="intermediate")]
            # AWS and FastAPI are NOT in this profile
        )
        result = optimize(sample_match_report, sample_resume_data, profile=profile)
        assert "Kubernetes" in result.injected_skills
        assert "AWS" not in result.injected_skills
        assert "FastAPI" not in result.injected_skills

    def test_profile_unconfirmed_skills_noted(self, sample_resume_data, sample_match_report):
        """Unconfirmed skills should appear in notes, not in injected_skills."""
        profile = UserProfile(skills=[])
        result = optimize(sample_match_report, sample_resume_data, profile=profile)
        assert len(result.injected_skills) == 0
        assert any("not in your profile" in note for note in result.notes)


# ---------------------------------------------------------------------------
# unescape_latex tests
# ---------------------------------------------------------------------------

class TestUnescapeLatex:
    def test_ampersand(self):
        assert unescape_latex(r"R\&D") == "R&D"

    def test_percent(self):
        assert unescape_latex(r"99\% accuracy") == "99% accuracy"

    def test_roundtrip(self):
        """unescape then escape should be identity for plain strings."""
        from engine.latex_builder import escape_latex
        original = "Programming & Machine Learning"
        assert unescape_latex(escape_latex(original)) == original

    def test_category_key_unescaped(self):
        """Skills parsed from .tex source should have plain & not \\&."""
        data = parse_tex_to_resume_data(TEX_FILE) if TEX_FILE.exists() else None
        if data is None:
            pytest.skip("resume_template.tex not in samples/")
        for key in data.skills.categories:
            assert r"\&" not in key, f"Category key still contains LaTeX escape: {key!r}"

    def test_render_skills_no_literal_backslash_amp(self):
        """After round-trip parse → render, the PDF source should have \\& not \\\\&."""
        if not TEX_FILE.exists():
            pytest.skip("resume_template.tex not in samples/")
        data = parse_tex_to_resume_data(TEX_FILE)
        tex = render_latex(data)
        # Every & in a category name should be preceded by exactly one backslash
        import re
        # Find all occurrences of backslash sequences before &
        double_escaped = re.findall(r"\\textbackslash\{\}\\&", tex)
        assert len(double_escaped) == 0, "Double-escaped \\& found in rendered LaTeX"


# ---------------------------------------------------------------------------
# UserProfile tests
# ---------------------------------------------------------------------------

class TestUserProfile:
    def test_has_skill_case_insensitive(self):
        profile = UserProfile(skills=[SkillEntry(name="Python")])
        assert profile.has_skill("python")
        assert profile.has_skill("PYTHON")
        assert not profile.has_skill("Java")

    def test_confirmed_skill_names(self):
        profile = UserProfile(skills=[
            SkillEntry(name="Python"),
            SkillEntry(name="SQL"),
        ])
        names = profile.confirmed_skill_names()
        assert "Python" in names
        assert "SQL" in names

    def test_find_evidence_from_work(self):
        profile = UserProfile(
            work_history=[
                {
                    "company": "Acme",
                    "title": "Engineer",
                    "dates": "2022-2024",
                    "technologies": ["FastAPI", "Python"],
                    "accomplishments": ["Deployed FastAPI service serving 1000 req/s"],
                }
            ]
        )
        evidence = profile.find_evidence("FastAPI")
        assert len(evidence) == 1
        assert "1000 req/s" in evidence[0]

    def test_find_evidence_from_project(self):
        profile = UserProfile(
            projects=[
                {
                    "name": "ML Pipeline",
                    "description": "End-to-end ML",
                    "technologies": ["PyTorch"],
                    "outcomes": ["Achieved 95% accuracy"],
                }
            ]
        )
        evidence = profile.find_evidence("PyTorch")
        assert len(evidence) == 1
        assert "95% accuracy" in evidence[0]

    def test_from_json_roundtrip(self, tmp_path):
        profile = UserProfile(
            full_name="Test User",
            target_roles=["Data Scientist"],
            skills=[SkillEntry(name="Python", proficiency="expert")],
        )
        json_path = tmp_path / "profile.json"
        profile.to_json(json_path)
        loaded = UserProfile.from_json(json_path)
        assert loaded.full_name == "Test User"
        assert loaded.has_skill("Python")

    def test_sample_profile_loads(self):
        sample_path = Path(__file__).parent.parent / "samples" / "sample_profile.json"
        if not sample_path.exists():
            pytest.skip("sample_profile.json not in samples/")
        profile = UserProfile.from_json(sample_path)
        assert profile.full_name == "Terrance Luangrath"
        assert profile.has_skill("Python")
        assert len(profile.work_history) > 0

    def test_find_evidence_no_match_returns_empty(self):
        profile = UserProfile(
            work_history=[
                {
                    "company": "Acme",
                    "title": "Engineer",
                    "dates": "2022-2024",
                    "technologies": ["Python"],
                    "accomplishments": ["Built pipeline"],
                }
            ]
        )
        evidence = profile.find_evidence("Kubernetes")
        assert evidence == []

    def test_profile_empty_skills_has_skill_false(self):
        profile = UserProfile(skills=[])
        assert not profile.has_skill("Python")

    def test_profile_target_roles_in_notes(self, sample_resume_data, sample_match_report):
        profile = UserProfile(
            target_roles=["Data Scientist", "ML Engineer"],
            skills=[SkillEntry(name="Kubernetes")],
        )
        result = optimize(sample_match_report, sample_resume_data, profile=profile)
        combined_notes = " ".join(result.notes)
        assert "Data Scientist" in combined_notes or "ML Engineer" in combined_notes


# ---------------------------------------------------------------------------
# Additional unescape_latex edge cases
# ---------------------------------------------------------------------------

class TestUnescapeLatexEdgeCases:
    def test_hash(self):
        assert unescape_latex(r"\#include") == "#include"

    def test_dollar(self):
        assert unescape_latex(r"\$100") == "$100"

    def test_underscore(self):
        assert unescape_latex(r"my\_var") == "my_var"

    def test_tilde(self):
        assert unescape_latex(r"\textasciitilde{}") == "~"

    def test_caret(self):
        assert unescape_latex(r"\textasciicircum{}") == "^"

    def test_multiple_escapes_in_one_string(self):
        result = unescape_latex(r"Cost: \$50 \& 20\% off")
        assert result == "Cost: $50 & 20% off"

    def test_plain_string_unchanged(self):
        s = "no special chars here"
        assert unescape_latex(s) == s

    def test_backslash_roundtrip(self):
        original = "C:\\Users\\file"
        assert unescape_latex(escape_latex(original)) == original


# ---------------------------------------------------------------------------
# Additional optimizer edge cases
# ---------------------------------------------------------------------------

class TestOptimizerEdgeCases:
    def test_no_missing_skills_nothing_injected(self, sample_resume_data):
        report = _make_match_report(
            score=90.0,
            matched=["Python", "SQL", "Git"],
            missing=[],
            title_relevance=0.85,
            experience_match="senior_match",
        )
        result = optimize(report, sample_resume_data)
        assert result.injected_skills == []

    def test_weak_bullet_flagged(self, sample_match_report):
        resume = ResumeData(
            contact=ContactInfo(
                name="Test",
                location="VA",
                phone="555-0000",
                email="test@test.com",
            ),
            education=[],
            experience=[
                ExperienceEntry(
                    title="Analyst",
                    dates="2022-2024",
                    company="Corp",
                    location="VA",
                    bullets=["Responsible for generating reports"],
                )
            ],
            projects=[],
            skills=TechnicalSkills(categories={"Tools": "Python"}),
        )
        result = optimize(sample_match_report, resume)
        assert any("responsible for" in w["bullet"].lower() for w in result.weak_bullets)

    def test_skill_injected_into_existing_category_only(self, sample_resume_data):
        """Injected skill should land in one of the original category keys."""
        original_keys = set(sample_resume_data.skills.categories.keys())
        report = _make_match_report(
            score=40.0,
            matched=[],
            missing=["SomeUnknownTool"],
            title_relevance=0.3,
            experience_match="level_not_detected",
        )
        result = optimize(report, sample_resume_data)
        result_keys = set(result.resume.skills.categories.keys())
        assert result_keys == original_keys
