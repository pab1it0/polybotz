# Detector Reference

This document provides detailed information about all available detectors in Polybotz.

## Overview

Polybotz uses modular detectors to identify different types of market anomalies. Each detector analyzes market data and triggers alerts when specific conditions are met. All detectors can be individually enabled or disabled via configuration.

### Available Detectors

| Detector | Status | Description | Configuration |
|----------|--------|-------------|---------------|
| `spike` | Active | Price spike detection | `spike_threshold` |
| `lvr` | Active | Liquidity-to-Volume Ratio analysis | `lvr_threshold` |
| `zscore` | Active | Z-score based volume anomaly detection | `zscore_threshold` |
| `mad` | Active | Median Absolute Deviation price anomaly | `mad_multiplier` |
| `closed` | Active | Closed market detection | None |

---

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
**Dependency**: Requires `spike` detector to be enabled (only runs when spike is detected)

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

## Z-Score Detector

**Name**: `zscore`
**Status**: Active
**Configuration**: `zscore_threshold`

### Description

Detects volume anomalies using statistical z-score analysis based on MAD (Median Absolute Deviation). Uses the CLOB API to fetch real-time order book data.

### How It Works

1. Maintains rolling windows of volume data (1-hour and 4-hour)
2. Calculates MAD-based z-scores using the scaling constant 1.4826
3. Triggers alert when volume z-score exceeds `zscore_threshold`
4. Requires minimum 30 observations before triggering alerts (warm-up period)

### Configuration

```yaml
# In config.yaml
zscore_threshold: 3.5  # Z-score value (default: 3.5)
```

Or via environment variable:
```bash
POLYBOTZ_ZSCORE_THRESHOLD=3.5
```

### Alert Format

```
Z-SCORE ALERT: Volume Spike
Market: {Token ID}
Z-Score: 4.2 (threshold: 3.5)
Current Volume: 50,000
```

### Use Cases

- Detect unusual trading activity
- Identify potential market manipulation
- Monitor for sudden volume surges

---

## MAD Detector

**Name**: `mad`
**Status**: Active
**Configuration**: `mad_multiplier`

### Description

Uses Median Absolute Deviation for robust price anomaly detection. MAD is more resistant to outliers than standard deviation-based methods. Uses the CLOB API to fetch real-time order book data.

### How It Works

1. Maintains rolling windows of price data (1-hour and 4-hour)
2. Calculates MAD (Median Absolute Deviation) of prices
3. Triggers alert when price deviation exceeds `mad_multiplier × MAD`
4. Requires minimum 30 observations before triggering alerts (warm-up period)

### Configuration

```yaml
# In config.yaml
mad_multiplier: 3.0  # MAD multiplier (default: 3.0)
```

Or via environment variable:
```bash
POLYBOTZ_MAD_MULTIPLIER=3.0
```

### Alert Format

```
MAD ALERT: Price Anomaly
Market: {Token ID}
Deviation: 3.5x MAD (threshold: 3.0)
Current Price: 0.75
```

### Use Cases

- Detect abnormal price movements
- Identify outlier-resistant price anomalies
- Monitor for price manipulation attempts

---

## Closed Detector

**Name**: `closed`
**Status**: Active
**Configuration**: None (no threshold)

### Description

Detects when markets transition from open to closed. Automatically removes fully-closed events from monitoring to save API calls.

### How It Works

1. Compares current market state with previous poll
2. Detects transitions from `is_closed=False` to `is_closed=True`
3. Sends one-time alert when a market closes
4. Removes events from monitoring when all markets are closed

### Alert Format

```
MARKET CLOSED: {Event Title}
Market: {Market Question}
Outcome: {Outcome Name}
Final Price: 0.9500
Time: 2024-01-15 12:30:00 UTC
```

### Use Cases

- Track market resolutions and outcomes
- Get notified when monitored markets close
- Automatic cleanup of closed events

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
  - zscore
  - mad
  - closed
```

Special values:
- `all` - Enable all detectors (default)
- `none` - Disable all detectors (monitoring only mode)
- Omit field - Enable all detectors (backward compatible)

#### Environment Variable

```bash
# Comma-separated list
POLYBOTZ_DETECTORS="spike,lvr,zscore,mad,closed"

# Enable all
POLYBOTZ_DETECTORS="all"

# Disable all
POLYBOTZ_DETECTORS="none"
```

**Note**: Environment variable takes precedence over config file setting.

### Detector Dependencies

| Detector | Depends On |
|----------|------------|
| `spike` | None |
| `lvr` | `spike` (only runs when spike is detected) |
| `zscore` | None (requires CLOB token IDs) |
| `mad` | None (requires CLOB token IDs) |
| `closed` | None |

### Example Configurations

#### Monitor Spikes Only
```yaml
detectors:
  - spike
```

#### Full Analysis (All Detectors)
```yaml
detectors: all
```

#### Gamma API Only (No CLOB)
```yaml
detectors:
  - spike
  - lvr
  - closed
```

#### CLOB Statistical Only
```yaml
detectors:
  - zscore
  - mad
```

#### Monitoring Only (No Alerts)
```yaml
detectors: none
```

---

## Warm-up Period

The statistical detectors (`zscore` and `mad`) require a minimum of 30 observations before triggering alerts. During warm-up, the bot logs progress:

```
CLOB warm-up: 15/20 markets have sufficient data (need 30 observations)
```

---

## Test Coverage

All detectors have comprehensive unit tests:

| Detector | Test Classes | Tests |
|----------|--------------|-------|
| `spike` | TestDetectSpike, TestDetectAllSpikes | 20 |
| `lvr` | TestCalculateLvr, TestClassifyLvrHealth, TestDetectLiquidityWarning, TestDetectAllLiquidityWarnings | 27 |
| `zscore` | TestDetectZScoreAlert, TestDetectAllZScoreAlerts | 4 |
| `mad` | TestDetectMADAlert, TestDetectAllMADAlerts | 4 |
| `closed` | TestDetectClosedMarkets | 9 |

Run detector tests:
```bash
uv run pytest tests/unit/test_detector.py -v
```

---

## Adding New Detectors

To add a new detector:

1. Add detector name to `VALID_DETECTORS` in `src/config.py`
2. Implement detection logic in `src/detector.py`
3. Add alerting logic in `src/alerter.py`
4. Update `run_poll_cycle()` in `src/main.py` with detector gating:
   ```python
   if "new_detector" in config.detectors:
       # Detection logic here
   ```
5. Add tests in `tests/unit/test_detector.py`
6. Update this documentation
