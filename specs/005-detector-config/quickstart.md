# Quickstart: Configurable Detector Selection

## Overview

This feature allows you to enable or disable specific detectors to customize which alerts you receive.

## Available Detectors

| Detector | Description |
|----------|-------------|
| `spike` | Price spike detection (implemented) |
| `lvr` | Liquidity-to-Volume Ratio warnings (implemented) |
| `zscore` | Z-score volume anomaly detection (future) |
| `mad` | Median Absolute Deviation price anomaly (future) |
| `closed` | Closed market detection (future) |

## Configuration

### Option 1: Config File (config.yaml)

```yaml
# Enable specific detectors
detectors:
  - spike
  - lvr

# Or enable all (default)
detectors: all

# Or disable all (monitoring only)
detectors: none
```

### Option 2: Environment Variable

```bash
# Enable specific detectors
export POLYBOTZ_DETECTORS="spike,lvr"

# Enable all
export POLYBOTZ_DETECTORS="all"

# Disable all
export POLYBOTZ_DETECTORS="none"
```

### Option 3: Docker

```bash
docker run -d \
  --name polybotz \
  -e POLYBOTZ_DETECTORS="spike,lvr" \
  -e POLYBOTZ_SLUGS="event-slug" \
  -e TELEGRAM_BOT_TOKEN="your-token" \
  -e TELEGRAM_CHAT_ID="your-chat-id" \
  ghcr.io/pab1it0/polybotz:latest
```

## Precedence

Environment variable > Config file > Default (all enabled)

## Verification

At startup, the bot logs which detectors are enabled:

```
2026-01-12 12:00:00 [INFO] polybotz: Enabled detectors: spike, lvr
```

## Examples

### Monitor Only Price Spikes

```yaml
detectors:
  - spike
```

### Monitor Spikes with Liquidity Warnings

```yaml
detectors:
  - spike
  - lvr
```

### Disable All Alerts (Data Collection Only)

```yaml
detectors: none
```

## Documentation

See [docs/detectors.md](../../docs/detectors.md) for detailed documentation on each detector's behavior and configuration.
