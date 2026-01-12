# Implementation Plan: Configurable Detector Selection

**Branch**: `005-detector-config` | **Date**: 2026-01-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-detector-config/spec.md`

## Summary

Enable users to selectively enable/disable individual detectors (spike, lvr, zscore, mad, closed) via configuration file or environment variables. Move detector documentation from README to a dedicated `docs/` directory.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: pyyaml (existing), httpx (existing)
**Storage**: N/A (stateless, config at startup)
**Testing**: pytest
**Target Platform**: Linux server, Docker container
**Project Type**: single
**Performance Goals**: N/A (config parsing happens once at startup)
**Constraints**: Backward compatible - existing configs must work unchanged
**Scale/Scope**: 5 detectors, simple configuration parsing

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity First | PASS | Minimal config extension, no new abstractions |
| II. Reliability | PASS | Malformed config falls back to all-enabled default |
| III. Minimal Dependencies | PASS | No new dependencies required |

**Technology Constraints Compliance:**
- Language: Python 3.10+ ✓
- Package manager: uv ✓
- API: Polymarket Gamma API ✓
- Alerts: stdout/stderr (extensible) ✓

## Project Structure

### Documentation (this feature)

```text
specs/005-detector-config/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── config.py            # Extend Configuration dataclass with detectors field
├── main.py              # Conditional detector invocation based on config
├── detector.py          # Existing detector functions (no changes)
└── models.py            # Existing models (no changes)

tests/
├── unit/
│   └── test_config.py   # Tests for detector config parsing
└── integration/
    └── test_main.py     # Tests for detector enable/disable behavior

docs/
└── detectors.md         # New: detailed detector documentation
```

**Structure Decision**: Single project structure. Changes confined to config parsing and main polling loop. New `docs/` directory for documentation.

## Complexity Tracking

No violations - implementation uses existing patterns and adds minimal code.
