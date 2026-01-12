"""Configuration loading and validation for Polybotz."""

import os
import re
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Configuration:
    """User-provided settings for the service."""

    slugs: list[str]
    poll_interval: int
    spike_threshold: float
    telegram_bot_token: str
    telegram_chat_id: str
    lvr_threshold: float = 8.0


class ConfigurationError(Exception):
    """Raised when configuration is invalid."""

    pass


def _substitute_env_vars(value: str) -> str:
    """Substitute ${VAR} patterns with environment variable values."""
    pattern = r"\$\{([^}]+)\}"

    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        env_value = os.environ.get(var_name)
        if env_value is None:
            return match.group(0)  # Keep original if not found
        return env_value

    return re.sub(pattern, replacer, value)


def _process_yaml_values(data: dict) -> dict:
    """Recursively process YAML values to substitute environment variables."""
    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = _substitute_env_vars(value)
        elif isinstance(value, dict):
            result[key] = _process_yaml_values(value)
        elif isinstance(value, list):
            result[key] = [
                _substitute_env_vars(item) if isinstance(item, str) else item
                for item in value
            ]
        else:
            result[key] = value
    return result


def load_config_from_env() -> Configuration:
    """Load configuration entirely from environment variables.

    Environment variables:
        POLYBOTZ_SLUGS: Comma-separated list of event slugs (required)
        POLYBOTZ_POLL_INTERVAL: Seconds between polls (default: 60)
        POLYBOTZ_SPIKE_THRESHOLD: Percentage for spike alerts (default: 5.0)
        POLYBOTZ_LVR_THRESHOLD: LVR threshold for warnings (default: 8.0)
        TELEGRAM_BOT_TOKEN: Telegram bot API token (required)
        TELEGRAM_CHAT_ID: Telegram chat ID (required)
    """
    slugs_str = os.environ.get("POLYBOTZ_SLUGS", "")
    slugs = [s.strip() for s in slugs_str.split(",") if s.strip()]

    try:
        poll_interval = int(os.environ.get("POLYBOTZ_POLL_INTERVAL", "60"))
    except ValueError:
        poll_interval = 60

    try:
        spike_threshold = float(os.environ.get("POLYBOTZ_SPIKE_THRESHOLD", "5.0"))
    except ValueError:
        spike_threshold = 5.0

    try:
        lvr_threshold = float(os.environ.get("POLYBOTZ_LVR_THRESHOLD", "8.0"))
    except ValueError:
        lvr_threshold = 8.0

    config = Configuration(
        slugs=slugs,
        poll_interval=poll_interval,
        spike_threshold=spike_threshold,
        telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.environ.get("TELEGRAM_CHAT_ID", ""),
        lvr_threshold=lvr_threshold,
    )

    validate_config(config)
    return config


def load_config(config_path: str | Path | None = None) -> Configuration:
    """Load configuration from YAML file or environment variables.

    If config_path is provided and exists, load from YAML file.
    Otherwise, fall back to environment variables.
    """
    # If no path provided, check for default config.yaml
    if config_path is None:
        config_path = Path("config.yaml")
    else:
        config_path = Path(config_path)

    # If config file exists, load from it
    if config_path.exists():
        with open(config_path) as f:
            raw_data = yaml.safe_load(f)

        if raw_data is None:
            raise ConfigurationError("Configuration file is empty")

        data = _process_yaml_values(raw_data)

        # Extract telegram config
        telegram = data.get("telegram", {})

        config = Configuration(
            slugs=data.get("slugs", []),
            poll_interval=data.get("poll_interval", 60),
            spike_threshold=data.get("spike_threshold", 5.0),
            telegram_bot_token=telegram.get("bot_token", ""),
            telegram_chat_id=telegram.get("chat_id", ""),
            lvr_threshold=data.get("lvr_threshold", 8.0),
        )

        validate_config(config)
        return config

    # No config file - try environment variables
    return load_config_from_env()


def validate_config(config: Configuration) -> None:
    """Validate configuration per data-model.md rules."""
    errors = []

    # slugs: Non-empty list, each slug non-empty string
    if not config.slugs:
        errors.append("slugs: must be a non-empty list")
    else:
        for i, slug in enumerate(config.slugs):
            if not slug or not isinstance(slug, str):
                errors.append(f"slugs[{i}]: must be a non-empty string")

    # poll_interval: Positive integer, minimum 10 seconds
    if not isinstance(config.poll_interval, int) or config.poll_interval < 10:
        errors.append("poll_interval: must be a positive integer >= 10")

    # spike_threshold: Positive float, 0.1 to 100.0
    if not isinstance(config.spike_threshold, (int, float)):
        errors.append("spike_threshold: must be a number")
    elif config.spike_threshold < 0.1 or config.spike_threshold > 100.0:
        errors.append("spike_threshold: must be between 0.1 and 100.0")

    # lvr_threshold: Positive float, 0.1 to 100.0
    if not isinstance(config.lvr_threshold, (int, float)):
        errors.append("lvr_threshold: must be a number")
    elif config.lvr_threshold < 0.1 or config.lvr_threshold > 100.0:
        errors.append("lvr_threshold: must be between 0.1 and 100.0")

    # telegram_bot_token: Non-empty string
    if not config.telegram_bot_token:
        errors.append("telegram.bot_token: must be a non-empty string")

    # telegram_chat_id: Non-empty string
    if not config.telegram_chat_id:
        errors.append("telegram.chat_id: must be a non-empty string")

    if errors:
        raise ConfigurationError("Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors))
