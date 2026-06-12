from meks.config import Settings


LLM_ENV_VARS = [
    "MEKS_CLOUD_API_KEY",
    "MEKS_OPENAI_API_KEY",
    "MEKS_CODEX_API_KEY",
    "OPENAI_API_KEY",
    "CODEX_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_MODEL",
    "OPENAI_WIRE_API",
]


def _clear_llm_env(monkeypatch):
    for name in LLM_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def test_settings_reads_codex_api_key_env(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("CODEX_API_KEY", "codex-test-key")

    settings = Settings(_env_file=None, secret_key="test")

    assert settings.effective_cloud_api_key == "codex-test-key"


def test_settings_prefers_explicit_meks_cloud_key(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("CODEX_API_KEY", "codex-test-key")
    monkeypatch.setenv("MEKS_CLOUD_API_KEY", "meks-cloud-key")

    settings = Settings(_env_file=None, secret_key="test")

    assert settings.effective_cloud_api_key == "meks-cloud-key"


def test_settings_accepts_openai_base_and_model_env(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.example/v1/")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    monkeypatch.setenv("OPENAI_WIRE_API", "responses")

    settings = Settings(_env_file=None, secret_key="test")

    assert settings.effective_cloud_api_base == "https://api.openai.example"
    assert settings.effective_cloud_model == "gpt-test"
    assert settings.effective_cloud_wire_api == "responses"
