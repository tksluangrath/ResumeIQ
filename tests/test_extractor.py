import pytest

from engine.extractor import EntityExtractor, ResumeEntities, _dedupe


@pytest.fixture(scope="module")
def extractor() -> EntityExtractor:
    return EntityExtractor()


class TestKnownSkillExtraction:
    def test_python_extracted_from_text(self, extractor: EntityExtractor) -> None:
        text = "I have 5 years of experience with Python and SQL databases."
        result = extractor.extract(text)
        skill_lower = [s.lower() for s in result.skills]
        assert "python" in skill_lower

    def test_multiple_skills_extracted(self, extractor: EntityExtractor) -> None:
        text = (
            "Proficient in Python, FastAPI, Docker, and PostgreSQL. "
            "Experience with AWS and Kubernetes deployments."
        )
        result = extractor.extract(text)
        skill_lower = [s.lower() for s in result.skills]
        assert "python" in skill_lower
        assert "docker" in skill_lower
        assert "postgresql" in skill_lower

    def test_all_seed_skills_detectable(self, extractor: EntityExtractor) -> None:
        text = (
            "Skills: Python, FastAPI, SQL, PostgreSQL, Docker, Kubernetes, "
            "AWS, GCP, React, TypeScript, JavaScript, Git, Linux, Redis, MongoDB"
        )
        result = extractor.extract(text)
        skill_lower = [s.lower() for s in result.skills]
        for expected in ("python", "docker", "aws", "react", "git", "linux"):
            assert expected in skill_lower, f"Expected skill '{expected}' not found"

    def test_skills_returned_as_list_of_strings(self, extractor: EntityExtractor) -> None:
        text = "Python developer with NumPy and pandas experience."
        result = extractor.extract(text)
        assert isinstance(result.skills, list)
        assert all(isinstance(s, str) for s in result.skills)

    def test_result_is_resume_entities_model(self, extractor: EntityExtractor) -> None:
        text = "Python and Docker experience."
        result = extractor.extract(text)
        assert isinstance(result, ResumeEntities)


class TestEmptyTextHandling:
    def test_empty_string_returns_empty_lists(self, extractor: EntityExtractor) -> None:
        result = extractor.extract("")
        assert result.skills == []
        assert result.job_titles == []
        assert result.companies == []
        assert result.education == []
        assert result.certifications == []

    def test_whitespace_only_returns_empty_lists(self, extractor: EntityExtractor) -> None:
        result = extractor.extract("   \n\t  ")
        assert result.skills == []
        assert result.job_titles == []

    def test_no_skills_text_returns_empty_skills(self, extractor: EntityExtractor) -> None:
        text = "I enjoy hiking, cooking, and reading novels on weekends."
        result = extractor.extract(text)
        assert result.skills == []


class TestDeduplication:
    def test_duplicate_skills_removed(self, extractor: EntityExtractor) -> None:
        text = "Python developer. Experienced in Python. Python is my primary language."
        result = extractor.extract(text)
        skill_lower = [s.lower() for s in result.skills]
        python_count = skill_lower.count("python")
        assert python_count == 1

    def test_dedupe_helper_removes_exact_duplicates(self) -> None:
        items = ["Python", "Docker", "Python", "AWS", "Docker"]
        result = _dedupe(items)
        assert result.count("Python") == 1
        assert result.count("Docker") == 1

    def test_dedupe_helper_is_case_insensitive(self) -> None:
        items = ["Python", "python", "PYTHON", "Docker"]
        result = _dedupe(items)
        assert len([x for x in result if x.lower() == "python"]) == 1

    def test_dedupe_preserves_order(self) -> None:
        items = ["AWS", "Docker", "Python", "Docker", "AWS"]
        result = _dedupe(items)
        assert result == ["AWS", "Docker", "Python"]

    def test_dedupe_removes_empty_strings(self) -> None:
        items = ["Python", "", "Docker", "  ", "AWS"]
        result = _dedupe(items)
        assert "" not in result
        assert "  " not in result

    def test_no_duplicates_in_extracted_skills(self, extractor: EntityExtractor) -> None:
        text = (
            "FastAPI is a Python framework. "
            "I use Python daily. "
            "FastAPI powers our microservices."
        )
        result = extractor.extract(text)
        skill_lower = [s.lower() for s in result.skills]
        assert len(skill_lower) == len(set(skill_lower))


class TestEntityExtractionFields:
    def test_all_fields_present_in_result(self, extractor: EntityExtractor) -> None:
        text = "Senior Python Engineer at Acme Corp."
        result = extractor.extract(text)
        assert hasattr(result, "skills")
        assert hasattr(result, "job_titles")
        assert hasattr(result, "companies")
        assert hasattr(result, "education")
        assert hasattr(result, "certifications")

    def test_certifications_extracted_from_cert_line(self, extractor: EntityExtractor) -> None:
        text = (
            "John Doe\n"
            "AWS Certified Solutions Architect\n"
            "Python developer with 3 years experience."
        )
        result = extractor.extract(text)
        assert len(result.certifications) > 0
        cert_text = " ".join(result.certifications).lower()
        assert "certified" in cert_text or "aws" in cert_text
