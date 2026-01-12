# Data Model: Configurable Detector Selection

**Feature**: 005-detector-config
**Date**: 2026-01-12

## Entities

### Configuration (Extended)

The existing `Configuration` dataclass is extended with a `detectors` field.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| detectors | set[str] | {"spike", "lvr", "zscore", "mad", "closed"} | Set of enabled detector names |

**Validation Rules**:
- Valid detector names: `spike`, `lvr`, `zscore`, `mad`, `closed`
- Invalid names are logged as warnings and ignored
- Empty set after validation means no detectors enabled (monitoring-only mode)
- If no detectors config specified, defaults to all enabled

### DetectorName (Enum/Constants)

Valid detector identifiers:

| Name | Description | Implementation Status |
|------|-------------|-----------------------|
| `spike` | Price spike detection | Implemented |
| `lvr` | Liquidity-to-Volume Ratio warnings | Implemented |
| `zscore` | Z-score volume anomaly detection | Future |
| `mad` | Median Absolute Deviation price anomaly | Future |
| `closed` | Closed market detection | Future |

## Configuration Sources

### YAML Config File

```yaml
# Option 1: Explicit list
detectors:
  - spike
  - lvr

# Option 2: Enable all (default)
detectors: all

# Option 3: Disable all (monitoring only)
detectors: none

# Option 4: Omit field entirely (defaults to all)
# (no detectors field)
```

### Environment Variable

```bash
# Comma-separated list
POLYBOTZ_DETECTORS="spike,lvr"

# Enable all
POLYBOTZ_DETECTORS="all"

# Disable all
POLYBOTZ_DETECTORS="none"
```

**Precedence**: Environment variable > Config file > Default (all enabled)

## State Transitions

Configuration is read-only after startup. No runtime state transitions.

```
[Startup] -> Parse Config -> Validate Detectors -> Log Enabled Detectors -> [Run]
                                |
                         Invalid names: Log warning, filter out
```

## Relationships

```
Configuration
    └── detectors: set[str]
            │
            ├── Used by: run_poll_cycle() to conditionally call detectors
            └── Logged at: startup for user visibility
```

## Validation

### Detector Name Validation

```python
VALID_DETECTORS = {"spike", "lvr", "zscore", "mad", "closed"}

def parse_detectors(value: str | list[str] | None) -> set[str]:
    """
    Parse detector configuration to a set of enabled detector names.

    Args:
        value: "all", "none", comma-separated string, or list

    Returns:
        Set of valid detector names to enable
    """
    if value is None:
        return VALID_DETECTORS.copy()  # All enabled by default

    if value == "all":
        return VALID_DETECTORS.copy()

    if value == "none":
        return set()

    if isinstance(value, str):
        names = {s.strip().lower() for s in value.split(",")}
    else:
        names = {s.strip().lower() for s in value}

    valid = names & VALID_DETECTORS
    invalid = names - VALID_DETECTORS

    if invalid:
        logger.warning(f"Invalid detector names ignored: {invalid}")

    return valid
```
