# Polybotz

A Python bot that periodically monitors Polymarket's market events, detects anomalous spikes, and sends real-time alerts. Uses the [Polymarket Gamma API](https://gamma-api.polymarket.com) to fetch market data.

## Features

- Monitor multiple Polymarket events by slug
- Detect price spikes exceeding configurable threshold
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

telegram:
  bot_token: "${TELEGRAM_BOT_TOKEN}"
  chat_id: "${TELEGRAM_CHAT_ID}"
```

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
4. Send Telegram alerts for detected spikes

Press `Ctrl+C` to gracefully stop the bot.

## Finding Event Slugs

1. Go to [Polymarket](https://polymarket.com)
2. Find an event you want to monitor
3. Copy the slug from the URL: `https://polymarket.com/event/{slug}`
