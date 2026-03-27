"""
Tests for engine/matcher.py — SemanticMatcher embeddings and cosine similarity.

Uses the real all-MiniLM-L6-v2 model (module-scoped fixture, loaded once).
No mocking — per project rule: "Don't mock the NLP models".
"""

import numpy as np
import pytest

from engine.matcher import SemanticMatcher


@pytest.fixture(scope="module")
def matcher() -> SemanticMatcher:
    return SemanticMatcher()


# ---------------------------------------------------------------------------
# encode() tests
# ---------------------------------------------------------------------------


class TestEncode:
    def test_returns_numpy_array(self, matcher: SemanticMatcher) -> None:
        result = matcher.encode("Python developer with FastAPI experience.")
        assert isinstance(result, np.ndarray)

    def test_embedding_is_1d(self, matcher: SemanticMatcher) -> None:
        result = matcher.encode("Software engineer with 5 years experience.")
        assert result.ndim == 1

    def test_embedding_dimension_is_384(self, matcher: SemanticMatcher) -> None:
        """all-MiniLM-L6-v2 produces 384-dim embeddings."""
        result = matcher.encode("Machine learning engineer.")
        assert result.shape == (384,)

    def test_embedding_dtype_is_float(self, matcher: SemanticMatcher) -> None:
        result = matcher.encode("Data scientist with Python and SQL skills.")
        assert np.issubdtype(result.dtype, np.floating)

    def test_empty_string_raises_value_error(self, matcher: SemanticMatcher) -> None:
        with pytest.raises(ValueError, match="empty"):
            matcher.encode("")

    def test_whitespace_only_raises_value_error(self, matcher: SemanticMatcher) -> None:
        with pytest.raises(ValueError, match="empty"):
            matcher.encode("   \n\t  ")

    def test_same_text_produces_same_embedding(self, matcher: SemanticMatcher) -> None:
        text = "Senior Python Engineer with Docker and Kubernetes."
        emb_a = matcher.encode(text)
        emb_b = matcher.encode(text)
        np.testing.assert_array_almost_equal(emb_a, emb_b)

    def test_different_texts_produce_different_embeddings(
        self, matcher: SemanticMatcher
    ) -> None:
        emb_a = matcher.encode("Python developer with FastAPI.")
        emb_b = matcher.encode("Chef with experience in French cuisine.")
        assert not np.allclose(emb_a, emb_b)


# ---------------------------------------------------------------------------
# similarity() tests
# ---------------------------------------------------------------------------


class TestSimilarity:
    def test_returns_float(self, matcher: SemanticMatcher) -> None:
        score = matcher.similarity(
            "Python developer.", "Software engineer with Python experience."
        )
        assert isinstance(score, float)

    def test_score_in_zero_to_one_range(self, matcher: SemanticMatcher) -> None:
        score = matcher.similarity(
            "FastAPI backend engineer.", "Python web development with REST APIs."
        )
        assert 0.0 <= score <= 1.0

    def test_identical_texts_score_near_one(self, matcher: SemanticMatcher) -> None:
        text = (
            "Senior Software Engineer with 7 years of Python, FastAPI, "
            "PostgreSQL, Docker, and AWS experience."
        )
        score = matcher.similarity(text, text)
        assert score > 0.99

    def test_high_similarity_for_related_texts(self, matcher: SemanticMatcher) -> None:
        resume = (
            "Python backend developer with FastAPI, PostgreSQL, and REST API design. "
            "5 years building microservices on AWS."
        )
        jd = (
            "We need a Python engineer experienced with FastAPI, relational databases, "
            "and cloud infrastructure (AWS or GCP)."
        )
        score = matcher.similarity(resume, jd)
        assert score > 0.70, f"Expected high similarity, got {score:.3f}"

    def test_low_similarity_for_unrelated_texts(self, matcher: SemanticMatcher) -> None:
        resume = "Python developer with machine learning and data science skills."
        jd = "Executive chef required for fine dining restaurant. Culinary degree preferred."
        score = matcher.similarity(resume, jd)
        assert score < 0.50, f"Expected low similarity, got {score:.3f}"

    def test_similarity_is_symmetric(self, matcher: SemanticMatcher) -> None:
        text_a = "Senior data engineer with Spark and Kafka."
        text_b = "Data pipeline engineer using Apache Kafka and Spark Streaming."
        score_ab = matcher.similarity(text_a, text_b)
        score_ba = matcher.similarity(text_b, text_a)
        assert abs(score_ab - score_ba) < 1e-5

    def test_score_never_below_zero(self, matcher: SemanticMatcher) -> None:
        """Clamp ensures negative raw cosine similarities return 0.0."""
        score = matcher.similarity(
            "Python developer.", "Experienced Java enterprise architect."
        )
        assert score >= 0.0

    def test_score_never_above_one(self, matcher: SemanticMatcher) -> None:
        score = matcher.similarity("Docker Kubernetes AWS DevOps.", "Docker Kubernetes AWS DevOps.")
        assert score <= 1.0

    def test_partial_overlap_score_between_bounds(self, matcher: SemanticMatcher) -> None:
        """Partial skill overlap should score somewhere in the middle."""
        resume = "Python and SQL developer."
        jd = "Python, SQL, Docker, Kubernetes, and Kafka required."
        score = matcher.similarity(resume, jd)
        assert 0.3 < score < 0.95
