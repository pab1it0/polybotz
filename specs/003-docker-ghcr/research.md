# Research: Docker Container with GitHub Container Registry

**Feature**: 003-docker-ghcr
**Date**: 2026-01-12

## Research Tasks

### 1. Python Container Base Image Selection

**Context**: Need to select a base image that supports Python 3.10+, keeps image size under 200MB, and receives regular security updates.

**Decision**: `python:3.10-slim-bookworm`

**Rationale**:
- Official Python image with Debian Bookworm (stable, long-term support)
- Slim variant removes unnecessary packages, keeping base at ~45MB
- Python 3.10 matches project's minimum required version
- Regular security updates via Docker Hub official images
- Includes pip and standard library, no compilation tools needed

**Alternatives Considered**:
- `python:3.10-alpine`: Smaller (~17MB) but musl libc can cause compatibility issues with some Python packages; slower pip installs due to compilation
- `python:3.10-bookworm` (full): Includes build tools (~350MB), unnecessary for runtime
- `distroless/python3`: Minimal attack surface but harder to debug, no shell access

### 2. Multi-Stage Build Strategy

**Context**: Need to minimize final image size while using uv for dependency management.

**Decision**: Two-stage build with uv in builder, runtime-only in final image

**Rationale**:
- Stage 1 (builder): Install uv, create venv, install dependencies
- Stage 2 (runtime): Copy only venv and source code
- Eliminates uv, pip, and build artifacts from final image
- Achieves target <200MB with room to spare (~80-100MB expected)

**Alternatives Considered**:
- Single-stage with cleanup: Harder to maintain, leaves layer bloat
- Three-stage (deps, build, runtime): Overcomplicated for pure Python project
- Pre-built wheel cache: Premature optimization for this project size

### 3. Non-Root User Implementation

**Context**: FR-005 requires running as non-root for security.

**Decision**: Create dedicated `polybotz` user with UID 1000

**Rationale**:
- UID 1000 is conventional for container users, avoids permission issues with mounted volumes
- User created in final stage only (not in builder)
- Home directory at `/app` where application lives
- No sudo or elevated privileges available

**Alternatives Considered**:
- UID 65534 (nobody): Works but less conventional, can conflict with host nobody user
- Dynamic UID via entrypoint: Adds complexity, not needed for this use case

### 4. Configuration Mount Path

**Context**: FR-002 requires config via mounted YAML file at standard path.

**Decision**: Mount config at `/app/config.yaml`

**Rationale**:
- `/app` is the working directory, keeps paths simple
- Matches existing local development pattern (`config.yaml` in project root)
- Single, predictable location documented in quickstart
- Environment variable `CONFIG_PATH` as optional override

**Alternatives Considered**:
- `/etc/polybotz/config.yaml`: More "system-like" but adds path complexity
- `/config/config.yaml`: Dedicated volume mount point, but overkill for single file

### 5. GitHub Actions Workflow Design

**Context**: FR-007 through FR-011 require automated building and publishing with specific tagging.

**Decision**: Single workflow file with conditional steps for different trigger types

**Rationale**:
- Triggers: push to main, push of version tags (v*.*.*)
- Uses `docker/build-push-action` for efficient caching
- Uses `docker/metadata-action` for automatic tag generation
- Leverages GHCR's free public image hosting
- Uses `GITHUB_TOKEN` for authentication (no secrets setup needed)

**Tagging Strategy**:
- Main branch push: `ghcr.io/OWNER/polybotz:main`, `ghcr.io/OWNER/polybotz:sha-abc1234`
- Version tag (v1.2.3): `ghcr.io/OWNER/polybotz:1.2.3`, `ghcr.io/OWNER/polybotz:latest`

**Alternatives Considered**:
- Separate workflows for main vs tags: Duplicates logic unnecessarily
- Docker Hub instead of GHCR: Requires external account, GHCR integrates better with GitHub
- Manual workflow dispatch: Doesn't meet "automated" requirement

### 6. Multi-Architecture Support

**Context**: Users may run containers on different CPU architectures.

**Decision**: Build for linux/amd64 and linux/arm64

**Rationale**:
- amd64: Standard cloud/server architecture
- arm64: Mac M1/M2 development, AWS Graviton, growing server adoption
- GitHub Actions has arm64 runners available
- Docker buildx handles cross-compilation automatically

**Alternatives Considered**:
- amd64 only: Simpler but excludes growing arm64 user base
- Include armv7: Rarely used for Python server apps, adds build time

### 7. Container Health Check

**Context**: Operators need to verify container is running correctly.

**Decision**: No HEALTHCHECK in Dockerfile; rely on process exit codes

**Rationale**:
- The bot is a long-running polling process, not an HTTP server
- Exit code 0 = graceful shutdown, non-zero = error
- Container orchestrators (Docker Compose, Kubernetes) can use process status
- Adding HTTP healthcheck endpoint would be over-engineering for a simple bot

**Alternatives Considered**:
- HEALTHCHECK with file touch: Adds complexity, process supervision is sufficient
- HTTP healthcheck endpoint: Requires code changes, violates Simplicity First principle

## Summary

All research questions resolved. Key decisions:
- Base image: `python:3.10-slim-bookworm`
- Multi-stage build with uv in builder stage
- Non-root user `polybotz` (UID 1000)
- Config mount at `/app/config.yaml`
- Single GitHub Actions workflow with metadata-driven tagging
- Multi-arch builds (amd64 + arm64)
- No in-container health checks (rely on process status)
