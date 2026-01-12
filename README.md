# Polybot-Z

A Python bot that periodically monitors Polymarket's market events, detects anomalous spikes and liquidity imbalances, and sends real-time alerts. Uses the [Polymarket Gamma API](https://gamma-api.polymarket.com) to fetch market data.

## Features

- Monitor multiple Polymarket events by slug
- Detect price spikes exceeding configurable threshold
- LVR (Liquidity-to-Volume Ratio) analysis for liquidity imbalance detection
- Liquidity warnings when price spikes coincide with high LVR
- Health classification (Healthy/Elevated/High Risk) based on LVR levels
- **Z-Score/MAD statistical detection** via CLOB API for volume spikes and price anomalies
- **Closed event detection** with automatic removal from monitoring
- Send alerts via Telegram
- Graceful error handling and retry logic
- Configurable polling interval

## Prerequisites

- Python 3.10+
- uv package manager
- Telegram bot token (from @BotFather)

## Installation

```bash
# Clone the repository
git clone https://github.com/your-username/polybotz.git
cd polybotz

# Create virtual environment and install
uv venv
source .venv/bin/activate
uv pip install -e .
```

## Configuration

1. Copy the example config:
```bash
cp config.example.yaml config.yaml
```

2. Edit `config.yaml` with your settings:
```yaml
slugs:
  - "will-trump-win-the-2024-us-presidential-election"
  - "bitcoin-above-100000-on-december-31"

poll_interval: 60
spike_threshold: 5.0
lvr_threshold: 8.0
zscore_threshold: 3.5
mad_multiplier: 3.0

telegram:
  bot_token: "${TELEGRAM_BOT_TOKEN}"
  chat_id: "${TELEGRAM_CHAT_ID}"
```

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `slugs` | - | List of Polymarket event slugs to monitor |
| `poll_interval` | 60 | Seconds between API polls (minimum: 10) |
| `spike_threshold` | 5.0 | Percentage change to trigger spike alert |
| `lvr_threshold` | 8.0 | LVR threshold for liquidity warnings |
| `zscore_threshold` | 3.5 | Z-score threshold for volume spike alerts |
| `mad_multiplier` | 3.0 | MAD multiplier for price anomaly alerts |
| `clob_token_ids` | - | Optional: Override CLOB token IDs (auto-detected from events) |

3. Set environment variables for Telegram:
```bash
export TELEGRAM_BOT_TOKEN="your-bot-token"
export TELEGRAM_CHAT_ID="your-chat-id"
```

## Usage

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the bot
python -m src
```

The bot will:
1. Validate configured event slugs against Polymarket API
2. Start polling at the configured interval
3. Detect price spikes exceeding the threshold
4. Analyze LVR for liquidity imbalances on spike events
5. Send Telegram alerts for spikes and liquidity warnings

Press `Ctrl+C` to gracefully stop the bot.

## LVR Liquidity Detection

The bot calculates the Liquidity-to-Volume Ratio (LVR) to identify potential liquidity risks:

```
LVR = 24h Volume / Total Liquidity
```

### Health Classification

| LVR Range | Status | Meaning |
|-----------|--------|---------|
| < 2.0 | Healthy | Normal liquidity conditions |
| 2.0 - 10.0 | Elevated | Moderate trading pressure |
| >= 10.0 | High Risk | Severe liquidity imbalance |

### Liquidity Warnings

A **Liquidity Warning** is triggered when both conditions are met:
1. Price change exceeds `spike_threshold`
2. LVR exceeds `lvr_threshold`

This helps identify price movements that may be driven by low liquidity rather than genuine market sentiment.

## Z-Score/MAD Statistical Detection

The bot uses the [Polymarket CLOB API](https://clob.polymarket.com) to fetch real-time order book data and applies statistical methods to detect anomalies.

### How It Works

1. **Rolling Windows**: Maintains 1-hour and 4-hour rolling windows of price and volume data
2. **MAD Calculation**: Uses Median Absolute Deviation for robust outlier detection
3. **Z-Score**: Calculates MAD-based Z-scores using the scaling constant 1.4826

### Alert Types

**Z-Score Alert** (Volume Spikes)
- Triggers when volume Z-score exceeds `zscore_threshold`
- Detects unusual trading activity

**MAD Alert** (Price Anomalies)
- Triggers when price deviation exceeds `mad_multiplier × MAD`
- Detects abnormal price movements

### Warm-up Period

The statistical detection requires a minimum of 30 observations before triggering alerts. During warm-up, the bot logs progress:
```
CLOB warm-up: 15/2 markets have sufficient data (need 30 observations)
```

## Closed Event Detection

The bot automatically detects when markets transition from open to closed:

- **One-time alert**: Sends a Telegram notification when a market closes
- **Auto-removal**: Removes fully-closed events from monitoring to save API calls
- **Final price**: Includes the resolved price in the alert

### Alert Format

```
✅ Market Closed

Event: Example Event Name
Market: Will this happen?
Outcome: Yes
Final Price: 0.9500
Time: 2024-01-15 12:30:00 UTC
```

## Finding Event Slugs

1. Go to [Polymarket](https://polymarket.com)
2. Find an event you want to monitor
3. Copy the slug from the URL: `https://polymarket.com/event/{slug}`

## Docker

### Pull and Run

```bash
# Pull the latest image
docker pull ghcr.io/pab1it0/polybotz:latest
```

#### Option 1: Using Config File

```bash
docker run -d \
  --name polybotz \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -e TELEGRAM_BOT_TOKEN="your-bot-token" \
  -e TELEGRAM_CHAT_ID="your-chat-id" \
  ghcr.io/pab1it0/polybotz:latest
```

#### Option 2: Environment Variables Only (No Config File)

```bash
docker run -d \
  --name polybotz \
  -e POLYBOTZ_SLUGS="slug1,slug2,slug3" \
  -e TELEGRAM_BOT_TOKEN="your-bot-token" \
  -e TELEGRAM_CHAT_ID="your-chat-id" \
  -e POLYBOTZ_POLL_INTERVAL="60" \
  -e POLYBOTZ_SPIKE_THRESHOLD="5.0" \
  -e POLYBOTZ_LVR_THRESHOLD="8.0" \
  -e POLYBOTZ_ZSCORE_THRESHOLD="3.5" \
  -e POLYBOTZ_MAD_MULTIPLIER="3.0" \
  ghcr.io/pab1it0/polybotz:latest
```

### Build Locally

```bash
# Build the image
docker build -t polybotz:local .

# Run with environment variables only
docker run -d \
  --name polybotz \
  -e POLYBOTZ_SLUGS="slug1,slug2" \
  -e TELEGRAM_BOT_TOKEN="your-bot-token" \
  -e TELEGRAM_CHAT_ID="your-chat-id" \
  polybotz:local
```

### Container Configuration

The container supports two configuration modes:

**Option 1: Config file** - Mount `config.yaml` to `/app/config.yaml`

**Option 2: Environment variables only** - No config file needed

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POLYBOTZ_SLUGS` | Yes* | - | Comma-separated list of event slugs |
| `TELEGRAM_BOT_TOKEN` | Yes | - | Telegram bot API token |
| `TELEGRAM_CHAT_ID` | Yes | - | Telegram chat ID for alerts |
| `POLYBOTZ_POLL_INTERVAL` | No | 60 | Seconds between polls |
| `POLYBOTZ_SPIKE_THRESHOLD` | No | 5.0 | Percentage for spike alerts |
| `POLYBOTZ_LVR_THRESHOLD` | No | 8.0 | LVR threshold for warnings |
| `POLYBOTZ_ZSCORE_THRESHOLD` | No | 3.5 | Z-score threshold for volume alerts |
| `POLYBOTZ_MAD_MULTIPLIER` | No | 3.0 | MAD multiplier for price alerts |

*Required only when not using a config file

### Container Operations

```bash
# View logs
docker logs -f polybotz

# Stop the container
docker stop polybotz

# Start the container
docker start polybotz

# Remove the container
docker rm polybotz
```

### Troubleshooting

**Container exits immediately**

Check logs for configuration errors:
```bash
docker logs polybotz
```

Common issues:
- Missing configuration - either mount `config.yaml` or set `POLYBOTZ_SLUGS` environment variable
- Missing Telegram credentials - verify `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are set
- Invalid event slugs - check slugs exist on Polymarket

**Permission denied on config file**

Ensure the config file is readable:
```bash
chmod 644 config.yaml
```

### Image Tags

| Tag | Description |
|-----|-------------|
| `latest` | Most recent stable release |
| `main` | Latest main branch build |
| `X.Y.Z` | Specific version release |
| `sha-XXXXXXX` | Specific commit build |
