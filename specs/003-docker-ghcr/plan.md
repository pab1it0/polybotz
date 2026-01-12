# Implementation Plan: Docker Container with GitHub Container Registry

**Branch**: `003-docker-ghcr` | **Date**: 2026-01-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-docker-ghcr/spec.md`

## Summary

Containerize the polybotz Python application for portable deployment and automated publishing to GitHub Container Registry. The implementation adds a Dockerfile using multi-stage builds for minimal image size (<200MB), runs as non-root user for security, and includes a GitHub Actions workflow for automated building and publishing on main branch pushes and version tags.

## Technical Context

**Language/Version**: Python 3.10+ (matches existing project)
**Primary Dependencies**: Docker (build tool), GitHub Actions (CI/CD)
**Storage**: N/A (stateless application, config mounted at runtime)
**Testing**: pytest (existing), container smoke tests
**Target Platform**: Linux containers (amd64/arm64)
**Project Type**: Single project with container packaging
**Performance Goals**: Build <3 min, startup <10 sec, image <200MB
**Constraints**: Non-root execution, public GHCR access, graceful config error handling
**Scale/Scope**: Single container image, single workflow file

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity First | PASS | Single Dockerfile, single workflow file, no orchestration complexity |
| II. Reliability | PASS | Container inherits existing retry logic; adds graceful startup error handling |
| III. Minimal Dependencies | PASS | Docker is standard tooling, no new runtime dependencies added to app |

**Technology Constraints Check**:
- Language: Python 3.10+ - COMPLIANT (container uses same Python version)
- Package manager: uv - COMPLIANT (container build uses uv for dependency installation)
- No new application dependencies added

**Gate Result**: PASS - No violations. Proceeding to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/003-docker-ghcr/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (minimal - no data entities)
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (N/A - no API contracts)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
# Existing structure (unchanged)
src/
├── __init__.py
├── __main__.py
├── alerter.py
├── config.py
├── detector.py
├── main.py
├── models.py
└── poller.py

tests/
└── [existing tests]

# New files for this feature
Dockerfile              # Multi-stage build for Python app
.dockerignore           # Exclude unnecessary files from build context
.github/workflows/
├── tests.yml           # Existing
└── docker-publish.yml  # New: Build and push to GHCR
```

**Structure Decision**: Single project structure maintained. Container packaging adds Dockerfile at root and new workflow file. No source code changes required.

## Complexity Tracking

> No violations to justify - all constitution checks passed.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | - | - |
