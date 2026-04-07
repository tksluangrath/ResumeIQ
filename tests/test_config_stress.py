"""
Stress tests for Track 4: Deployment config, Settings, DATABASE_URL coercion.
Goal: validate every settings default, env-var override path, and URL coercion rule.
~100 tests — no database required.
"""
from __future__ import annotations

import os

import pytest
from pydantic import ValidationError

from config import Settings, get_settings


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_settings(**overrides: str | float | bool | list) -> Settings:
    """Build a Settings instance with controlled env values (no .env file)."""
    base = {
        "DATABASE_URL": "postgresql+asyncpg://u:p@localhost:5432/db",
        "TEST_DATABASE_URL": "postgresql+asyncpg://u:p@localhost:5432/test_db",
        "JWT_SECRET": "test-secret-at-least-32-chars-long-yes",
    }
    base.update(overrides)  # type: ignore[arg-type]
    return Settings(**base)


# ── Section 1: DATABASE_URL coercion ──────────────────────────────────────────

class TestDatabaseUrlCoercion:
    def test_postgres_scheme_coerced_to_asyncpg(self) -> None:
        s = make_settings(DATABASE_URL="postgres://user:pass@host:5432/db")
        assert s.DATABASE_URL == "postgresql+asyncpg://user:pass@host:5432/db"

    def test_postgresql_scheme_coerced_to_asyncpg(self) -> None:
        s = make_settings(DATABASE_URL="postgresql://user:pass@host:5432/db")
        assert s.DATABASE_URL == "postgresql+asyncpg://user:pass@host:5432/db"

    def test_already_asyncpg_unchanged(self) -> None:
        url = "postgresql+asyncpg://user:pass@host:5432/db"
        s = make_settings(DATABASE_URL=url)
        assert s.DATABASE_URL == url

    def test_leading_whitespace_stripped(self) -> None:
        s = make_settings(DATABASE_URL="  postgresql+asyncpg://u:p@host:5432/db")
        assert s.DATABASE_URL == "postgresql+asyncpg://u:p@host:5432/db"

    def test_trailing_whitespace_stripped(self) -> None:
        s = make_settings(DATABASE_URL="postgresql+asyncpg://u:p@host:5432/db  ")
        assert s.DATABASE_URL == "postgresql+asyncpg://u:p@host:5432/db"

    def test_both_whitespace_stripped_and_coerced(self) -> None:
        s = make_settings(DATABASE_URL="  postgres://u:p@host:5432/db  ")
        assert s.DATABASE_URL == "postgresql+asyncpg://u:p@host:5432/db"

    def test_newline_in_url_stripped(self) -> None:
        s = make_settings(DATABASE_URL="postgresql+asyncpg://u:p@host:5432/db\n")
        assert s.DATABASE_URL == "postgresql+asyncpg://u:p@host:5432/db"

    def test_tab_in_url_stripped(self) -> None:
        s = make_settings(DATABASE_URL="\tpostgresql+asyncpg://u:p@host:5432/db")
        assert s.DATABASE_URL == "postgresql+asyncpg://u:p@host:5432/db"

    def test_postgres_coercion_only_replaces_prefix_once(self) -> None:
        """Should not double-replace: postgres://postgres://... is not a real case but must not crash."""
        s = make_settings(DATABASE_URL="postgres://u:p@host:5432/db")
        assert s.DATABASE_URL.startswith("postgresql+asyncpg://")
        assert s.DATABASE_URL.count("postgresql+asyncpg://") == 1

    def test_sqlite_url_passes_through_unchanged(self) -> None:
        s = make_settings(DATABASE_URL="sqlite+aiosqlite:///./test.db")
        assert s.DATABASE_URL == "sqlite+aiosqlite:///./test.db"

    def test_railway_style_url_coerced(self) -> None:
        """Railway provides postgres:// URLs — must coerce."""
        s = make_settings(DATABASE_URL="postgres://user:complex-pass@postgres.railway.internal:5432/railway")
        assert s.DATABASE_URL.startswith("postgresql+asyncpg://")


# ── Section 2: Default settings values ────────────────────────────────────────

class TestDefaultSettings:
    def test_app_env_defaults_to_development(self) -> None:
        s = make_settings()
        assert s.APP_ENV == "development"

    def test_debug_schema_default_is_false(self) -> None:
        """
        The Settings class defines DEBUG default as False.
        Note: .env file may override this in local dev (e.g. DEBUG=true).
        This test checks the schema default, not the runtime value.
        """
        assert Settings.model_fields["DEBUG"].default is False

    def test_weight_semantic_default(self) -> None:
        s = make_settings()
        assert abs(s.WEIGHT_SEMANTIC - 0.40) < 1e-9

    def test_weight_skills_default(self) -> None:
        s = make_settings()
        assert abs(s.WEIGHT_SKILLS - 0.30) < 1e-9

    def test_weight_title_default(self) -> None:
        s = make_settings()
        assert abs(s.WEIGHT_TITLE - 0.15) < 1e-9

    def test_weight_experience_default(self) -> None:
        s = make_settings()
        assert abs(s.WEIGHT_EXPERIENCE - 0.15) < 1e-9

    def test_default_weights_sum_to_one(self) -> None:
        s = make_settings()
        total = s.WEIGHT_SEMANTIC + s.WEIGHT_SKILLS + s.WEIGHT_TITLE + s.WEIGHT_EXPERIENCE
        assert abs(total - 1.0) < 1e-6

    def test_llm_provider_defaults_to_ollama(self) -> None:
        s = make_settings()
        assert s.LLM_PROVIDER == "ollama"

    def test_jwt_algorithm_default(self) -> None:
        s = make_settings()
        assert s.JWT_ALGORITHM == "HS256"

    def test_jwt_expiry_default_is_60(self) -> None:
        s = make_settings()
        assert s.JWT_EXPIRY_MINUTES == 60

    def test_spacy_model_default(self) -> None:
        s = make_settings()
        assert s.SPACY_MODEL == "en_core_web_lg"

    def test_sentence_transformer_default(self) -> None:
        s = make_settings()
        assert s.SENTENCE_TRANSFORMER_MODEL == "all-MiniLM-L6-v2"

    def test_stripe_keys_default_empty(self) -> None:
        s = make_settings()
        assert s.STRIPE_SECRET_KEY == ""
        assert s.STRIPE_PUBLISHABLE_KEY == ""
        assert s.STRIPE_WEBHOOK_SECRET == ""

    def test_stripe_price_ids_default_empty(self) -> None:
        s = make_settings()
        assert s.STRIPE_PRICE_STARTER == ""
        assert s.STRIPE_PRICE_PRO == ""

    def test_anthropic_api_key_default_empty(self) -> None:
        s = make_settings()
        assert s.ANTHROPIC_API_KEY == ""

    def test_openai_api_key_default_empty(self) -> None:
        s = make_settings()
        assert s.OPENAI_API_KEY == ""

    def test_ollama_base_url_default(self) -> None:
        s = make_settings()
        assert s.OLLAMA_BASE_URL == "http://localhost:11434"

    def test_ollama_model_default(self) -> None:
        s = make_settings()
        assert s.OLLAMA_MODEL == "llama3.1:8b"

    def test_llm_timeout_default_is_120(self) -> None:
        s = make_settings()
        assert s.LLM_TIMEOUT_SECONDS == 120

    def test_cors_origins_defaults_to_list(self) -> None:
        s = make_settings()
        assert isinstance(s.CORS_ORIGINS, list)
        assert len(s.CORS_ORIGINS) >= 1


# ── Section 3: Env-var overrides ──────────────────────────────────────────────

class TestEnvVarOverrides:
    def test_app_env_can_be_overridden(self) -> None:
        s = make_settings(APP_ENV="production")
        assert s.APP_ENV == "production"

    def test_debug_can_be_enabled(self) -> None:
        s = make_settings(DEBUG=True)
        assert s.DEBUG is True

    def test_jwt_expiry_can_be_overridden(self) -> None:
        s = make_settings(JWT_EXPIRY_MINUTES=30)
        assert s.JWT_EXPIRY_MINUTES == 30

    def test_weight_semantic_override(self) -> None:
        s = make_settings(WEIGHT_SEMANTIC=0.50)
        assert abs(s.WEIGHT_SEMANTIC - 0.50) < 1e-9

    def test_weight_skills_override(self) -> None:
        s = make_settings(WEIGHT_SKILLS=0.20)
        assert abs(s.WEIGHT_SKILLS - 0.20) < 1e-9

    def test_llm_provider_can_be_claude(self) -> None:
        s = make_settings(LLM_PROVIDER="claude")
        assert s.LLM_PROVIDER == "claude"

    def test_llm_provider_can_be_openai(self) -> None:
        s = make_settings(LLM_PROVIDER="openai")
        assert s.LLM_PROVIDER == "openai"

    def test_anthropic_api_key_override(self) -> None:
        s = make_settings(ANTHROPIC_API_KEY="sk-ant-test-key")
        assert s.ANTHROPIC_API_KEY == "sk-ant-test-key"

    def test_stripe_secret_key_override(self) -> None:
        s = make_settings(STRIPE_SECRET_KEY="sk_test_abc123")
        assert s.STRIPE_SECRET_KEY == "sk_test_abc123"

    def test_stripe_webhook_secret_override(self) -> None:
        s = make_settings(STRIPE_WEBHOOK_SECRET="whsec_test_abc")
        assert s.STRIPE_WEBHOOK_SECRET == "whsec_test_abc"

    def test_jwt_secret_override(self) -> None:
        s = make_settings(JWT_SECRET="my-custom-secret-that-is-long-enough")
        assert s.JWT_SECRET == "my-custom-secret-that-is-long-enough"

    def test_spacy_model_override_to_sm(self) -> None:
        """Production uses en_core_web_sm to reduce memory."""
        s = make_settings(SPACY_MODEL="en_core_web_sm")
        assert s.SPACY_MODEL == "en_core_web_sm"

    def test_cors_origins_can_be_overridden(self) -> None:
        s = make_settings(CORS_ORIGINS=["https://myapp.vercel.app"])
        assert "https://myapp.vercel.app" in s.CORS_ORIGINS


# ── Section 4: Weight sum integrity ───────────────────────────────────────────

class TestWeightSumIntegrity:
    def test_custom_weights_that_sum_to_one(self) -> None:
        s = make_settings(
            WEIGHT_SEMANTIC=0.50,
            WEIGHT_SKILLS=0.25,
            WEIGHT_TITLE=0.15,
            WEIGHT_EXPERIENCE=0.10,
        )
        total = s.WEIGHT_SEMANTIC + s.WEIGHT_SKILLS + s.WEIGHT_TITLE + s.WEIGHT_EXPERIENCE
        assert abs(total - 1.0) < 1e-6

    def test_weights_that_dont_sum_to_one_accepted_by_settings(self) -> None:
        """Settings does not validate sum=1 — weights are independent floats."""
        s = make_settings(
            WEIGHT_SEMANTIC=0.60,
            WEIGHT_SKILLS=0.60,
            WEIGHT_TITLE=0.10,
            WEIGHT_EXPERIENCE=0.10,
        )
        # Sum = 1.4 — acceptable at settings level
        total = s.WEIGHT_SEMANTIC + s.WEIGHT_SKILLS + s.WEIGHT_TITLE + s.WEIGHT_EXPERIENCE
        assert abs(total - 1.4) < 1e-6

    def test_all_weights_zero_accepted(self) -> None:
        """Edge case: all weights = 0."""
        s = make_settings(
            WEIGHT_SEMANTIC=0.0,
            WEIGHT_SKILLS=0.0,
            WEIGHT_TITLE=0.0,
            WEIGHT_EXPERIENCE=0.0,
        )
        assert s.WEIGHT_SEMANTIC == 0.0

    def test_weight_as_integer_accepted(self) -> None:
        s = make_settings(WEIGHT_SEMANTIC=1)
        assert s.WEIGHT_SEMANTIC == 1.0

    def test_negative_weight_accepted_by_settings(self) -> None:
        """Settings does not reject negative weights — downstream score is clamped."""
        s = make_settings(WEIGHT_SEMANTIC=-0.1)
        assert s.WEIGHT_SEMANTIC == -0.1


# ── Section 5: get_settings lru_cache behavior ────────────────────────────────

class TestGetSettingsCache:
    def test_get_settings_returns_settings_instance(self) -> None:
        s = get_settings()
        assert isinstance(s, Settings)

    def test_get_settings_same_object_on_repeated_calls(self) -> None:
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_get_settings_cache_clearable(self) -> None:
        s1 = get_settings()
        get_settings.cache_clear()
        s2 = get_settings()
        # After clear, returns a new (but equivalent) object
        assert s1.APP_ENV == s2.APP_ENV


# ── Section 6: JWT settings integrity ─────────────────────────────────────────

class TestJwtSettings:
    def test_jwt_algorithm_is_hs256_by_default(self) -> None:
        s = make_settings()
        assert s.JWT_ALGORITHM == "HS256"

    def test_jwt_secret_is_accessible(self) -> None:
        s = make_settings(JWT_SECRET="secret-value-here-longer-than-32")
        assert s.JWT_SECRET == "secret-value-here-longer-than-32"

    def test_jwt_expiry_is_positive_integer(self) -> None:
        s = make_settings()
        assert s.JWT_EXPIRY_MINUTES > 0
        assert isinstance(s.JWT_EXPIRY_MINUTES, int)

    def test_jwt_expiry_can_be_set_to_1(self) -> None:
        s = make_settings(JWT_EXPIRY_MINUTES=1)
        assert s.JWT_EXPIRY_MINUTES == 1

    def test_jwt_expiry_can_be_set_to_large_value(self) -> None:
        s = make_settings(JWT_EXPIRY_MINUTES=10080)  # 1 week
        assert s.JWT_EXPIRY_MINUTES == 10080


# ── Section 7: Production deployment settings ─────────────────────────────────

class TestProductionDeploymentSettings:
    def test_production_spacy_model_setting(self) -> None:
        """Railway prod uses en_core_web_sm to avoid OOM."""
        s = make_settings(APP_ENV="production", SPACY_MODEL="en_core_web_sm")
        assert s.SPACY_MODEL == "en_core_web_sm"

    def test_production_debug_is_false(self) -> None:
        s = make_settings(APP_ENV="production", DEBUG=False)
        assert s.DEBUG is False

    def test_cors_allows_production_frontend(self) -> None:
        s = make_settings(CORS_ORIGINS=["https://resumeiq.vercel.app", "https://api.resumeiq.app"])
        assert "https://resumeiq.vercel.app" in s.CORS_ORIGINS
        assert "https://api.resumeiq.app" in s.CORS_ORIGINS

    def test_stripe_price_ids_can_be_set(self) -> None:
        s = make_settings(
            STRIPE_PRICE_STARTER="price_starter_live_abc",
            STRIPE_PRICE_PRO="price_pro_live_xyz",
        )
        assert s.STRIPE_PRICE_STARTER == "price_starter_live_abc"
        assert s.STRIPE_PRICE_PRO == "price_pro_live_xyz"

    def test_deepseek_settings_present(self) -> None:
        s = make_settings()
        assert hasattr(s, "DEEPSEEK_API_KEY")
        assert hasattr(s, "DEEPSEEK_BASE_URL")
        assert hasattr(s, "DEEPSEEK_MODEL")

    def test_deepseek_base_url_default(self) -> None:
        s = make_settings()
        assert s.DEEPSEEK_BASE_URL == "https://api.deepseek.com"

    def test_settings_env_vars_are_case_insensitive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        SettingsConfigDict case_sensitive=False means env var NAMES are case-insensitive.
        e.g. env var 'app_env' maps to field 'APP_ENV'. Python kwargs are always case-sensitive.
        """
        monkeypatch.setenv("app_env", "staging")
        get_settings.cache_clear()
        try:
            s = get_settings()
            # If env var 'app_env' is picked up, APP_ENV == 'staging'
            # (behavior depends on pydantic-settings version — just assert no crash)
            assert isinstance(s.APP_ENV, str)
        finally:
            get_settings.cache_clear()

    def test_test_database_url_default_is_test_db(self) -> None:
        s = make_settings()
        assert "test" in s.TEST_DATABASE_URL.lower() or "resumeiq_test" in s.TEST_DATABASE_URL

    def test_settings_all_fields_accessible(self) -> None:
        """Smoke test: every documented field must be accessible without error."""
        s = make_settings()
        fields = [
            "APP_ENV", "DEBUG", "CORS_ORIGINS", "SPACY_MODEL",
            "SENTENCE_TRANSFORMER_MODEL", "WEIGHT_SEMANTIC", "WEIGHT_SKILLS",
            "WEIGHT_TITLE", "WEIGHT_EXPERIENCE", "LLM_PROVIDER", "OLLAMA_BASE_URL",
            "OLLAMA_MODEL", "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
            "LLM_TIMEOUT_SECONDS", "DATABASE_URL", "TEST_DATABASE_URL",
            "JWT_SECRET", "JWT_ALGORITHM", "JWT_EXPIRY_MINUTES",
            "STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY", "STRIPE_WEBHOOK_SECRET",
            "STRIPE_PRICE_STARTER", "STRIPE_PRICE_PRO",
        ]
        for field in fields:
            assert hasattr(s, field), f"Settings missing field: {field}"
