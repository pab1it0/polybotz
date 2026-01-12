"""Tests for src/config.py."""

import pytest
import os

from src.config import (
    Configuration,
    ConfigurationError,
    _substitute_env_vars,
    _process_yaml_values,
    load_config,
    load_config_from_env,
    validate_config,
)


class TestSubstituteEnvVars:
    """Tests for _substitute_env_vars function."""

    def test_substitute_single_var(self, monkeypatch):
        """Test substituting a single environment variable."""
        monkeypatch.setenv("TEST_VAR", "test_value")
        result = _substitute_env_vars("${TEST_VAR}")
        assert result == "test_value"

    def test_substitute_multiple_vars(self, monkeypatch):
        """Test substituting multiple environment variables."""
        monkeypatch.setenv("VAR1", "value1")
        monkeypatch.setenv("VAR2", "value2")
        result = _substitute_env_vars("${VAR1}-${VAR2}")
        assert result == "value1-value2"

    def test_substitute_var_in_string(self, monkeypatch):
        """Test substituting variable within text."""
        monkeypatch.setenv("NAME", "World")
        result = _substitute_env_vars("Hello ${NAME}!")
        assert result == "Hello World!"

    def test_missing_var_keeps_original(self, monkeypatch):
        """Test that missing variables keep original placeholder."""
        monkeypatch.delenv("MISSING_VAR", raising=False)
        result = _substitute_env_vars("${MISSING_VAR}")
        assert result == "${MISSING_VAR}"

    def test_no_substitution_needed(self):
        """Test string without variables."""
        result = _substitute_env_vars("plain string")
        assert result == "plain string"

    def test_empty_string(self):
        """Test empty string."""
        result = _substitute_env_vars("")
        assert result == ""

    def test_partial_match(self, monkeypatch):
        """Test string with partial pattern (not a variable)."""
        result = _substitute_env_vars("${}")
        assert result == "${}"

    def test_nested_braces(self, monkeypatch):
        """Test handling of nested braces."""
        monkeypatch.setenv("OUTER", "outer_value")
        result = _substitute_env_vars("${OUTER}")
        assert result == "outer_value"


class TestProcessYamlValues:
    """Tests for _process_yaml_values function."""

    def test_process_string_value(self, monkeypatch):
        """Test processing string with env var."""
        monkeypatch.setenv("TOKEN", "secret123")
        data = {"key": "${TOKEN}"}
        result = _process_yaml_values(data)
        assert result["key"] == "secret123"

    def test_process_nested_dict(self, monkeypatch):
        """Test processing nested dictionary."""
        monkeypatch.setenv("NESTED_VAR", "nested_value")
        data = {"outer": {"inner": "${NESTED_VAR}"}}
        result = _process_yaml_values(data)
        assert result["outer"]["inner"] == "nested_value"

    def test_process_list(self, monkeypatch):
        """Test processing list values."""
        monkeypatch.setenv("ITEM", "item_value")
        data = {"list": ["static", "${ITEM}"]}
        result = _process_yaml_values(data)
        assert result["list"] == ["static", "item_value"]

    def test_process_non_string_values(self):
        """Test that non-string values pass through."""
        data = {"int": 42, "float": 3.14, "bool": True, "none": None}
        result = _process_yaml_values(data)
        assert result["int"] == 42
        assert result["float"] == 3.14
        assert result["bool"] is True
        assert result["none"] is None

    def test_process_mixed_list(self, monkeypatch):
        """Test list with mixed types."""
        monkeypatch.setenv("VAR", "var_value")
        data = {"mixed": ["string", 123, "${VAR}", True]}
        result = _process_yaml_values(data)
        assert result["mixed"] == ["string", 123, "var_value", True]


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_valid_config(self, tmp_path, valid_config_yaml):
        """Test loading a valid config file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(valid_config_yaml)

        config = load_config(config_file)

        assert config.slugs == ["test-slug-one", "test-slug-two"]
        assert config.poll_interval == 60
        assert config.spike_threshold == 5.0
        assert config.telegram_bot_token == "test-bot-token"
        assert config.telegram_chat_id == "test-chat-id"

    def test_load_config_with_env_vars(self, tmp_path, config_with_env_vars_yaml, monkeypatch):
        """Test loading config with environment variable substitution."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "env-token-123")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "env-chat-456")

        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_with_env_vars_yaml)

        config = load_config(config_file)

        assert config.telegram_bot_token == "env-token-123"
        assert config.telegram_chat_id == "env-chat-456"

    def test_load_missing_file_falls_back_to_env(self, tmp_path):
        """Test loading non-existent config file falls back to env vars."""
        # When file doesn't exist and env vars aren't set, validation fails
        with pytest.raises(ConfigurationError) as exc_info:
            load_config(tmp_path / "missing.yaml")
        # Should fail validation due to missing required env vars
        assert "slugs" in str(exc_info.value) or "telegram" in str(exc_info.value)

    def test_load_empty_file(self, tmp_path):
        """Test loading empty config file."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        with pytest.raises(ConfigurationError) as exc_info:
            load_config(config_file)
        assert "empty" in str(exc_info.value)

    def test_load_config_default_values(self, tmp_path):
        """Test config uses defaults for missing values."""
        config_yaml = """
slugs:
  - "test-slug"
telegram:
  bot_token: "token"
  chat_id: "chatid"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_yaml)

        config = load_config(config_file)

        assert config.poll_interval == 60
        assert config.spike_threshold == 5.0


class TestLoadConfigFromEnv:
    """Tests for load_config_from_env function."""

    def test_load_from_env_all_vars(self, monkeypatch):
        """Test loading config entirely from environment variables."""
        monkeypatch.setenv("POLYBOTZ_SLUGS", "slug1,slug2,slug3")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "env-token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "env-chat")
        monkeypatch.setenv("POLYBOTZ_POLL_INTERVAL", "30")
        monkeypatch.setenv("POLYBOTZ_SPIKE_THRESHOLD", "3.5")
        monkeypatch.setenv("POLYBOTZ_LVR_THRESHOLD", "5.0")

        config = load_config_from_env()

        assert config.slugs == ["slug1", "slug2", "slug3"]
        assert config.telegram_bot_token == "env-token"
        assert config.telegram_chat_id == "env-chat"
        assert config.poll_interval == 30
        assert config.spike_threshold == 3.5
        assert config.lvr_threshold == 5.0

    def test_load_from_env_defaults(self, monkeypatch):
        """Test loading config uses defaults for optional vars."""
        monkeypatch.setenv("POLYBOTZ_SLUGS", "test-slug")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")

        config = load_config_from_env()

        assert config.slugs == ["test-slug"]
        assert config.poll_interval == 60
        assert config.spike_threshold == 5.0
        assert config.lvr_threshold == 8.0

    def test_load_from_env_missing_required(self, monkeypatch):
        """Test loading from env fails when required vars missing."""
        # Only set some vars, missing POLYBOTZ_SLUGS
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")

        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_env()
        assert "slugs" in str(exc_info.value)

    def test_load_from_env_comma_separated_slugs(self, monkeypatch):
        """Test slug parsing handles whitespace correctly."""
        monkeypatch.setenv("POLYBOTZ_SLUGS", " slug1 , slug2 , slug3 ")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")

        config = load_config_from_env()

        assert config.slugs == ["slug1", "slug2", "slug3"]


class TestValidateConfig:
    """Tests for validate_config function."""

    def test_validate_valid_config(self, valid_config):
        """Test validation passes for valid config."""
        validate_config(valid_config)

    def test_validate_empty_slugs(self):
        """Test validation fails for empty slugs."""
        config = Configuration(
            slugs=[],
            poll_interval=60,
            spike_threshold=5.0,
            telegram_bot_token="token",
            telegram_chat_id="chatid",
        )
        with pytest.raises(ConfigurationError) as exc_info:
            validate_config(config)
        assert "slugs" in str(exc_info.value)

    def test_validate_invalid_slug_entry(self):
        """Test validation fails for empty string slug."""
        config = Configuration(
            slugs=["valid-slug", ""],
            poll_interval=60,
            spike_threshold=5.0,
            telegram_bot_token="token",
            telegram_chat_id="chatid",
        )
        with pytest.raises(ConfigurationError) as exc_info:
            validate_config(config)
        assert "slugs[1]" in str(exc_info.value)

    def test_validate_poll_interval_too_small(self):
        """Test validation fails for poll_interval < 10."""
        config = Configuration(
            slugs=["slug"],
            poll_interval=5,
            spike_threshold=5.0,
            telegram_bot_token="token",
            telegram_chat_id="chatid",
        )
        with pytest.raises(ConfigurationError) as exc_info:
            validate_config(config)
        assert "poll_interval" in str(exc_info.value)

    def test_validate_poll_interval_minimum(self):
        """Test poll_interval at minimum (10) is valid."""
        config = Configuration(
            slugs=["slug"],
            poll_interval=10,
            spike_threshold=5.0,
            telegram_bot_token="token",
            telegram_chat_id="chatid",
        )
        validate_config(config)

    def test_validate_spike_threshold_too_small(self):
        """Test validation fails for spike_threshold < 0.1."""
        config = Configuration(
            slugs=["slug"],
            poll_interval=60,
            spike_threshold=0.05,
            telegram_bot_token="token",
            telegram_chat_id="chatid",
        )
        with pytest.raises(ConfigurationError) as exc_info:
            validate_config(config)
        assert "spike_threshold" in str(exc_info.value)

    def test_validate_spike_threshold_too_large(self):
        """Test validation fails for spike_threshold > 100."""
        config = Configuration(
            slugs=["slug"],
            poll_interval=60,
            spike_threshold=150.0,
            telegram_bot_token="token",
            telegram_chat_id="chatid",
        )
        with pytest.raises(ConfigurationError) as exc_info:
            validate_config(config)
        assert "spike_threshold" in str(exc_info.value)

    def test_validate_spike_threshold_at_bounds(self):
        """Test spike_threshold at valid boundaries."""
        config_low = Configuration(
            slugs=["slug"],
            poll_interval=60,
            spike_threshold=0.1,
            telegram_bot_token="token",
            telegram_chat_id="chatid",
        )
        validate_config(config_low)

        config_high = Configuration(
            slugs=["slug"],
            poll_interval=60,
            spike_threshold=100.0,
            telegram_bot_token="token",
            telegram_chat_id="chatid",
        )
        validate_config(config_high)

    def test_validate_missing_bot_token(self):
        """Test validation fails for empty bot_token."""
        config = Configuration(
            slugs=["slug"],
            poll_interval=60,
            spike_threshold=5.0,
            telegram_bot_token="",
            telegram_chat_id="chatid",
        )
        with pytest.raises(ConfigurationError) as exc_info:
            validate_config(config)
        assert "bot_token" in str(exc_info.value)

    def test_validate_missing_chat_id(self):
        """Test validation fails for empty chat_id."""
        config = Configuration(
            slugs=["slug"],
            poll_interval=60,
            spike_threshold=5.0,
            telegram_bot_token="token",
            telegram_chat_id="",
        )
        with pytest.raises(ConfigurationError) as exc_info:
            validate_config(config)
        assert "chat_id" in str(exc_info.value)

    def test_validate_multiple_errors(self):
        """Test validation reports multiple errors."""
        config = Configuration(
            slugs=[],
            poll_interval=5,
            spike_threshold=200.0,
            telegram_bot_token="",
            telegram_chat_id="",
        )
        with pytest.raises(ConfigurationError) as exc_info:
            validate_config(config)
        error_msg = str(exc_info.value)
        assert "slugs" in error_msg
        assert "poll_interval" in error_msg
        assert "spike_threshold" in error_msg
        assert "bot_token" in error_msg
        assert "chat_id" in error_msg

    def test_validate_lvr_threshold_default(self):
        """Test default lvr_threshold value is valid."""
        config = Configuration(
            slugs=["slug"],
            poll_interval=60,
            spike_threshold=5.0,
            telegram_bot_token="token",
            telegram_chat_id="chatid",
        )
        assert config.lvr_threshold == 8.0
        validate_config(config)

    def test_validate_lvr_threshold_custom(self):
        """Test custom lvr_threshold value is valid."""
        config = Configuration(
            slugs=["slug"],
            poll_interval=60,
            spike_threshold=5.0,
            telegram_bot_token="token",
            telegram_chat_id="chatid",
            lvr_threshold=15.0,
        )
        validate_config(config)

    def test_validate_lvr_threshold_too_small(self):
        """Test validation fails for lvr_threshold < 0.1."""
        config = Configuration(
            slugs=["slug"],
            poll_interval=60,
            spike_threshold=5.0,
            telegram_bot_token="token",
            telegram_chat_id="chatid",
            lvr_threshold=0.05,
        )
        with pytest.raises(ConfigurationError) as exc_info:
            validate_config(config)
        assert "lvr_threshold" in str(exc_info.value)

    def test_validate_lvr_threshold_too_large(self):
        """Test validation fails for lvr_threshold > 100."""
        config = Configuration(
            slugs=["slug"],
            poll_interval=60,
            spike_threshold=5.0,
            telegram_bot_token="token",
            telegram_chat_id="chatid",
            lvr_threshold=150.0,
        )
        with pytest.raises(ConfigurationError) as exc_info:
            validate_config(config)
        assert "lvr_threshold" in str(exc_info.value)

    def test_validate_lvr_threshold_at_bounds(self):
        """Test lvr_threshold at valid boundaries."""
        config_low = Configuration(
            slugs=["slug"],
            poll_interval=60,
            spike_threshold=5.0,
            telegram_bot_token="token",
            telegram_chat_id="chatid",
            lvr_threshold=0.1,
        )
        validate_config(config_low)

        config_high = Configuration(
            slugs=["slug"],
            poll_interval=60,
            spike_threshold=5.0,
            telegram_bot_token="token",
            telegram_chat_id="chatid",
            lvr_threshold=100.0,
        )
        validate_config(config_high)


class TestLoadConfigWithLvr:
    """Tests for loading config with lvr_threshold."""

    def test_load_config_default_lvr_threshold(self, tmp_path):
        """Test config uses default lvr_threshold when not specified."""
        config_yaml = """
slugs:
  - "test-slug"
telegram:
  bot_token: "token"
  chat_id: "chatid"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_yaml)

        config = load_config(config_file)

        assert config.lvr_threshold == 8.0

    def test_load_config_custom_lvr_threshold(self, tmp_path):
        """Test loading config with custom lvr_threshold."""
        config_yaml = """
slugs:
  - "test-slug"
poll_interval: 60
spike_threshold: 5.0
lvr_threshold: 12.5
telegram:
  bot_token: "token"
  chat_id: "chatid"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_yaml)

        config = load_config(config_file)

        assert config.lvr_threshold == 12.5

    def test_load_config_invalid_lvr_threshold(self, tmp_path):
        """Test loading config with invalid lvr_threshold raises error."""
        config_yaml = """
slugs:
  - "test-slug"
lvr_threshold: 200.0
telegram:
  bot_token: "token"
  chat_id: "chatid"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_yaml)

        with pytest.raises(ConfigurationError) as exc_info:
            load_config(config_file)
        assert "lvr_threshold" in str(exc_info.value)
