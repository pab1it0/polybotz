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


def load_config(config_path: str | Path) -> Configuration:
    """Load configuration from YAML file with environment variable substitution."""
    config_path = Path(config_path)

    if not config_path.exists():
        raise ConfigurationError(f"Configuration file not found: {config_path}")

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
    )

    validate_config(config)
    return config


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

    # telegram_bot_token: Non-empty string
    if not config.telegram_bot_token:
        errors.append("telegram.bot_token: must be a non-empty string")

    # telegram_chat_id: Non-empty string
    if not config.telegram_chat_id:
        errors.append("telegram.chat_id: must be a non-empty string")

    if errors:
        raise ConfigurationError("Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors))
