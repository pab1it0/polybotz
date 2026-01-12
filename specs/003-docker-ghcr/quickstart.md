# Quickstart: Docker Container with GitHub Container Registry

**Feature**: 003-docker-ghcr
**Date**: 2026-01-12

## Prerequisites

- Docker 20.10+ installed
- Telegram bot token (from @BotFather)
- Telegram chat ID for alerts

## Option 1: Pull Pre-built Image (Recommended)

```bash
# Pull the latest image
docker pull ghcr.io/pab1it0/polybotz:latest
```

### Using Config File

```bash
# Create your config file
cp config.example.yaml config.yaml
# Edit config.yaml with your settings

# Run the container
docker run -d \
  --name polybotz \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -e TELEGRAM_BOT_TOKEN="your-bot-token" \
  -e TELEGRAM_CHAT_ID="your-chat-id" \
  ghcr.io/pab1it0/polybotz:latest
```

### Using Environment Variables Only (No Config File)

```bash
docker run -d \
  --name polybotz \
  -e POLYBOTZ_SLUGS="slug1,slug2,slug3" \
  -e TELEGRAM_BOT_TOKEN="your-bot-token" \
  -e TELEGRAM_CHAT_ID="your-chat-id" \
  -e POLYBOTZ_POLL_INTERVAL="60" \
  -e POLYBOTZ_SPIKE_THRESHOLD="5.0" \
  -e POLYBOTZ_LVR_THRESHOLD="8.0" \
  ghcr.io/pab1it0/polybotz:latest
```

## Option 2: Build Locally

```bash
# Clone the repository
git clone https://github.com/pab1it0/polybotz.git
cd polybotz

# Build the image
docker build -t polybotz:local .

# Run with config file
docker run -d \
  --name polybotz \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -e TELEGRAM_BOT_TOKEN="your-bot-token" \
  -e TELEGRAM_CHAT_ID="your-chat-id" \
  polybotz:local

# Or run with environment variables only
docker run -d \
  --name polybotz \
  -e POLYBOTZ_SLUGS="slug1,slug2" \
  -e TELEGRAM_BOT_TOKEN="your-bot-token" \
  -e TELEGRAM_CHAT_ID="your-chat-id" \
  polybotz:local
```

## Configuration

The container supports two configuration modes:

**Option 1: Config file** - Mount `config.yaml` to `/app/config.yaml`

**Option 2: Environment variables only** - No config file needed

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POLYBOTZ_SLUGS` | Yes* | - | Comma-separated list of event slugs |
| `TELEGRAM_BOT_TOKEN` | Yes | - | Telegram bot API token |
| `TELEGRAM_CHAT_ID` | Yes | - | Telegram chat ID for alerts |
| `POLYBOTZ_POLL_INTERVAL` | No | 60 | Seconds between polls |
| `POLYBOTZ_SPIKE_THRESHOLD` | No | 5.0 | Percentage for spike alerts |
| `POLYBOTZ_LVR_THRESHOLD` | No | 8.0 | LVR threshold for warnings |

*Required only when not using a config file

### Config File Format

Mount your `config.yaml` to `/app/config.yaml` inside the container.

Example config:
```yaml
slugs:
  - "will-trump-win-the-2024-us-presidential-election"
  - "bitcoin-above-100000-on-december-31"

poll_interval: 60
spike_threshold: 5.0
lvr_threshold: 8.0

telegram:
  bot_token: "${TELEGRAM_BOT_TOKEN}"
  chat_id: "${TELEGRAM_CHAT_ID}"
```

## Container Operations

```bash
# View logs
docker logs -f polybotz

# Stop the container
docker stop polybotz

# Start again
docker start polybotz

# Remove container
docker rm polybotz
```

## Troubleshooting

### Container exits immediately

Check logs for configuration errors:
```bash
docker logs polybotz
```

Common issues:
- Missing configuration - either mount `config.yaml` or set `POLYBOTZ_SLUGS` environment variable
- Missing Telegram credentials - verify `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are set
- Invalid event slugs - check slugs exist on Polymarket

### Permission denied on config file

Ensure the config file is readable:
```bash
chmod 644 config.yaml
```

### Image not found

For private repositories or during initial setup:
```bash
# Authenticate to GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
```

## Version Tags

| Tag | Description |
|-----|-------------|
| `latest` | Most recent stable release |
| `main` | Latest main branch build |
| `1.2.3` | Specific version release |
| `sha-abc1234` | Specific commit build |
