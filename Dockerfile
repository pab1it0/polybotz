# Stage 1: Builder - Install dependencies using uv
FROM python:3.10-slim-bookworm AS builder

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files (README.md needed by hatchling for package metadata)
COPY pyproject.toml README.md ./

# Create virtual environment and install dependencies
RUN uv venv /app/.venv && \
    . /app/.venv/bin/activate && \
    uv pip install --no-cache-dir .

# Stage 2: Runtime - Minimal production image
FROM python:3.10-slim-bookworm AS runtime

# Create non-root user for security (UID 1000)
RUN groupadd --gid 1000 polybotz && \
    useradd --uid 1000 --gid 1000 --home-dir /app --create-home polybotz

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application source code
COPY src/ /app/src/

# Set ownership to non-root user
RUN chown -R polybotz:polybotz /app

# Switch to non-root user
USER polybotz

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Configuration Options:
#
# Option 1: Mount config.yaml file
#   docker run -v $(pwd)/config.yaml:/app/config.yaml:ro \
#     -e TELEGRAM_BOT_TOKEN="..." \
#     -e TELEGRAM_CHAT_ID="..." \
#     ghcr.io/pab1it0/polybotz:latest
#
# Option 2: Environment variables only (no config file needed)
#   docker run \
#     -e POLYBOTZ_SLUGS="slug1,slug2,slug3" \
#     -e TELEGRAM_BOT_TOKEN="..." \
#     -e TELEGRAM_CHAT_ID="..." \
#     -e POLYBOTZ_POLL_INTERVAL="60" \
#     -e POLYBOTZ_SPIKE_THRESHOLD="5.0" \
#     -e POLYBOTZ_LVR_THRESHOLD="8.0" \
#     -e POLYBOTZ_ZSCORE_THRESHOLD="3.5" \
#     -e POLYBOTZ_MAD_MULTIPLIER="3.0" \
#     -e POLYBOTZ_DETECTORS="spike,lvr" \
#     ghcr.io/pab1it0/polybotz:latest
#
# Environment Variables:
#   POLYBOTZ_SLUGS          - Comma-separated event slugs (required)
#   TELEGRAM_BOT_TOKEN      - Telegram bot API token (required)
#   TELEGRAM_CHAT_ID        - Telegram chat ID (required)
#   POLYBOTZ_POLL_INTERVAL  - Seconds between polls (default: 60)
#   POLYBOTZ_SPIKE_THRESHOLD - Percentage for spike alerts (default: 5.0)
#   POLYBOTZ_LVR_THRESHOLD  - LVR threshold for warnings (default: 8.0)
#   POLYBOTZ_ZSCORE_THRESHOLD - Z-score threshold for volume alerts (default: 3.5)
#   POLYBOTZ_MAD_MULTIPLIER - MAD multiplier for price alerts (default: 3.0)
#   POLYBOTZ_DETECTORS      - Detectors to enable: "all", "none", or comma-separated
#                             list like "spike,lvr" (default: all)
#                             Note: Overrides config file setting when set
#
# Note: CLOB token IDs are auto-extracted from monitored events.
# To override, set POLYBOTZ_CLOB_TOKEN_IDS="token1,token2"

# Run the application
CMD ["python", "-m", "src"]
