# Detector Reference

This document provides detailed information about all available detectors in Polybotz.

## Overview

Polybotz uses modular detectors to identify different types of market anomalies. Each detector analyzes market data and triggers alerts when specific conditions are met.

### Currently Implemented

| Detector | Status | Description |
|----------|--------|-------------|
| `spike` | Active | Price spike detection |
| `lvr` | Active | Liquidity-to-Volume Ratio analysis |

### Planned (Not Yet Implemented)

| Detector | Status | Description |
|----------|--------|-------------|
| `zscore` | Planned | Z-score based volume anomaly detection |
| `mad` | Planned | Median Absolute Deviation price anomaly |
| `closed` | Planned | Closed market detection |

## Spike Detector

**Name**: `spike`
**Status**: Active
**Configuration**: `spike_threshold`

### Description

Detects significant price changes between polling intervals. When a market outcome's price changes by more than the configured threshold, a spike alert is triggered.

### How It Works

1. Compares current price to previous poll's price
2. Calculates percentage change: `|current - previous| / previous * 100`
3. Triggers alert if change exceeds `spike_threshold`

### Configuration

```yaml
# In config.yaml
spike_threshold: 5.0  # Percentage (default: 5.0)
```

Or via environment variable:
```bash
POLYBOTZ_SPIKE_THRESHOLD=5.0
```

### Alert Format

```
SPIKE ALERT: {Event Title}
Outcome: {Outcome Name}
Change: +12.5% (0.45 -> 0.57)
```

### Use Cases

- Detect breaking news impact on markets
- Identify potential manipulation attempts
- Monitor significant sentiment shifts

---

## LVR Detector

**Name**: `lvr`
**Status**: Active
**Configuration**: `lvr_threshold`
**Dependency**: Requires `spike` detector to be enabled

### Description

Analyzes the Liquidity-to-Volume Ratio (LVR) when price spikes occur. High LVR indicates that recent trading volume significantly exceeds available liquidity, suggesting potential liquidity risks.

### How It Works

1. Only runs when `spike` detector triggers an alert
2. Calculates LVR: `24h Volume / Total Liquidity`
3. Classifies liquidity health based on LVR value
4. Triggers warning if LVR exceeds `lvr_threshold`

### LVR Formula

```
LVR = 24h Volume / Total Liquidity
```

Where:
- **24h Volume**: Total trading volume in the last 24 hours
- **Total Liquidity**: Sum of available liquidity across all outcomes

### Health Classification

| LVR Range | Status | Meaning |
|-----------|--------|---------|
| < 2.0 | Healthy | Normal liquidity conditions |
| 2.0 - 10.0 | Elevated | Moderate trading pressure |
| >= 10.0 | High Risk | Severe liquidity imbalance |

### Configuration

```yaml
# In config.yaml
lvr_threshold: 8.0  # LVR value (default: 8.0)
```

Or via environment variable:
```bash
POLYBOTZ_LVR_THRESHOLD=8.0
```

### Alert Format

```
LIQUIDITY WARNING: {Event Title}
LVR: 12.5 (High Risk)
Volume: $125,000 / Liquidity: $10,000
Triggered by: +8.2% spike on {Outcome Name}
```

### Use Cases

- Identify thin markets vulnerable to slippage
- Detect potential liquidity-driven price movements
- Monitor market health during high volatility

---

## Z-Score Detector (Planned)

**Name**: `zscore`
**Status**: Planned (not yet implemented)

### Description

Will detect volume anomalies using statistical z-score analysis. Useful for identifying unusual trading activity that may indicate market manipulation or significant news events.

### Planned Features

- Rolling window volume analysis
- Configurable z-score threshold
- Historical baseline calculation

---

## MAD Detector (Planned)

**Name**: `mad`
**Status**: Planned (not yet implemented)

### Description

Will use Median Absolute Deviation for robust price anomaly detection. MAD is more resistant to outliers than standard deviation-based methods.

### Planned Features

- Rolling price analysis
- Configurable MAD multiplier threshold
- Outlier-resistant anomaly detection

---

## Closed Market Detector (Planned)

**Name**: `closed`
**Status**: Planned (not yet implemented)

### Description

Will detect when markets are about to close or have recently closed. Useful for tracking market resolutions and outcomes.

### Planned Features

- Resolution date monitoring
- Pre-closure alerts
- Final outcome notifications

---

## Configuration

### Enabling/Disabling Detectors

You can selectively enable detectors via config file or environment variable.

#### Config File

```yaml
# In config.yaml
detectors:
  - spike
  - lvr
  # - zscore  # Uncomment when implemented
  # - mad     # Uncomment when implemented
  # - closed  # Uncomment when implemented
```

Special values:
- `all` - Enable all detectors
- `none` - Disable all detectors (monitoring only mode)
- Omit field - Enable all detectors (backward compatible)

#### Environment Variable

```bash
# Comma-separated list
POLYBOTZ_DETECTORS="spike,lvr"

# Enable all
POLYBOTZ_DETECTORS="all"

# Disable all
POLYBOTZ_DETECTORS="none"
```

**Note**: Environment variable takes precedence over config file setting.

### Detector Dependencies

Some detectors depend on others:

| Detector | Depends On |
|----------|------------|
| `spike` | None |
| `lvr` | `spike` (only runs when spike is detected) |
| `zscore` | None (planned) |
| `mad` | None (planned) |
| `closed` | None (planned) |

### Example Configurations

#### Monitor Spikes Only
```yaml
detectors:
  - spike
```

#### Full Analysis (Spike + LVR)
```yaml
detectors:
  - spike
  - lvr
```

#### Monitoring Only (No Alerts)
```yaml
detectors: none
```

---

## Adding New Detectors

To add a new detector:

1. Add detector name to `VALID_DETECTORS` in `src/config.py`
2. Implement detection logic in `src/detector.py`
3. Add alerting logic in `src/alerter.py`
4. Update `run_poll_cycle()` in `src/main.py` to call the new detector
5. Add tests in `tests/unit/test_detector.py`
6. Update this documentation
