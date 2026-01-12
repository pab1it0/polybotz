# Research: Configurable Detector Selection

**Feature**: 005-detector-config
**Date**: 2026-01-12

## Research Tasks

### 1. Detector Configuration Pattern

**Question**: How should detector enable/disable configuration be structured?

**Decision**: Use a `detectors` field in config that accepts a list of detector names, with special values `all` and `none`.

**Rationale**:
- Aligns with existing config.yaml structure (list-based like `slugs`)
- Environment variable can use comma-separated format (consistent with `POLYBOTZ_SLUGS`)
- Special values `all`/`none` provide convenience shortcuts
- Explicit list is clearer than boolean flags per detector

**Alternatives Considered**:
1. Individual boolean flags (`spike_enabled: true`) - More verbose, harder to manage
2. Single string with comma-separated names - Less readable in YAML
3. Nested object with enabled/disabled arrays - Over-engineered

### 2. Environment Variable Precedence

**Question**: How should environment variable interact with config file?

**Decision**: Environment variable `POLYBOTZ_DETECTORS` takes precedence when set.

**Rationale**:
- Consistent with Docker deployment patterns
- Allows runtime override without modifying config files
- Same precedence model used by other config fields

**Alternatives Considered**:
1. Config file always wins - Breaks Docker 12-factor principle
2. Merge both sources - Complex, error-prone

### 3. Invalid Detector Handling

**Question**: What happens when invalid detector name is specified?

**Decision**: Log warning and ignore invalid names, continue with valid ones.

**Rationale**:
- Graceful degradation (Constitution Principle II: Reliability)
- User typos shouldn't crash the bot
- Startup log shows which detectors are active for verification

**Alternatives Considered**:
1. Fail fast on invalid names - Too strict for typos
2. Silently ignore - Hides configuration errors

### 4. Default Behavior

**Question**: What happens when no detector config is specified?

**Decision**: All detectors enabled by default (backward compatible).

**Rationale**:
- Existing configs without `detectors` field continue to work
- New users get full functionality without explicit config
- Explicit is better than implicit for disabling features

**Alternatives Considered**:
1. No detectors enabled by default - Breaking change
2. Require explicit configuration - Poor UX for existing users

### 5. Detector Names

**Question**: What are the canonical detector names?

**Decision**: Use lowercase identifiers matching internal function names:
- `spike` - Price spike detection
- `lvr` - Liquidity-to-Volume Ratio warnings
- `zscore` - Z-score volume anomaly detection (future)
- `mad` - Median Absolute Deviation price anomaly (future)
- `closed` - Closed market detection (future)

**Rationale**:
- Simple, memorable names
- Lowercase for consistency with Python conventions
- Short for easy typing in environment variables

**Note**: Only `spike` and `lvr` are currently implemented. Other detectors (`zscore`, `mad`, `closed`) are placeholders for future features. The configuration system will accept all 5 names but only implemented detectors will function.

## Summary

No technical unknowns remain. The implementation follows existing patterns in the codebase with minimal additions.
