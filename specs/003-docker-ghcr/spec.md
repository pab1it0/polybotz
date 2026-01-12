# Feature Specification: Docker Container with GitHub Container Registry

**Feature Branch**: `003-docker-ghcr`
**Created**: 2026-01-12
**Status**: Draft
**Input**: User description: "Dockerize the project including pushing the image to Github Container registry"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Build Container Image Locally (Priority: P1)

A developer wants to build the polybotz application as a Docker container on their local machine to test deployment or run in a containerized environment.

**Why this priority**: This is the foundational capability that enables all other container-based workflows. Without a working container build, no other container operations are possible.

**Independent Test**: Can be fully tested by running a single build command and verifying the resulting image runs successfully with a valid configuration.

**Acceptance Scenarios**:

1. **Given** the developer has Docker installed and is in the project root, **When** they run the container build command, **Then** a container image is created successfully with the application ready to run.
2. **Given** a built container image exists, **When** the developer runs the container with required environment variables and config, **Then** the bot starts and begins monitoring configured markets.
3. **Given** a built container image exists, **When** the developer runs the container without required configuration, **Then** the container exits with a clear error message indicating what configuration is missing.

---

### User Story 2 - Automated Container Publishing (Priority: P2)

A maintainer wants container images to be automatically built and published to GitHub Container Registry when code is merged to the main branch, enabling seamless deployment and distribution.

**Why this priority**: Automation eliminates manual publishing steps and ensures consistent, traceable releases. This depends on having a working Dockerfile (P1).

**Independent Test**: Can be fully tested by merging code to main branch and verifying a new container image appears in GitHub Container Registry.

**Acceptance Scenarios**:

1. **Given** code is pushed to the main branch, **When** the automated pipeline runs, **Then** a container image is built and published to GitHub Container Registry with appropriate tags.
2. **Given** the automated build completes, **When** a user pulls the published image, **Then** the image runs identically to a locally built image.
3. **Given** a release tag is created, **When** the automated pipeline runs, **Then** the container image is tagged with both the version number and "latest".

---

### User Story 3 - Pull and Run Published Image (Priority: P3)

An operator wants to pull the pre-built container image from GitHub Container Registry and run it without needing to build locally, simplifying deployment.

**Why this priority**: This enables end-users to deploy without development tooling. Depends on automated publishing (P2) being functional.

**Independent Test**: Can be fully tested by pulling the image from GHCR and running it with a configuration file.

**Acceptance Scenarios**:

1. **Given** the container image is published to GHCR, **When** an operator pulls and runs the image with proper configuration, **Then** the bot starts monitoring markets successfully.
2. **Given** an operator has the container running, **When** market conditions trigger alerts, **Then** Telegram notifications are sent correctly.

---

### Edge Cases

- What happens when the container is run without mounting a config file? The container should exit gracefully with a clear error message.
- What happens when Telegram credentials are invalid? The container should log the authentication failure and continue attempting reconnection.
- What happens when network connectivity is lost during polling? The container should implement retry logic and not crash.
- What happens when the base image has security vulnerabilities? The build should use a minimal, regularly-updated base image.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a container image that runs the polybotz application without requiring Python installation on the host
- **FR-002**: System MUST accept configuration via mounted YAML file at a standard container path
- **FR-003**: System MUST accept Telegram credentials via environment variables
- **FR-004**: System MUST exit with non-zero code and descriptive error when required configuration is missing
- **FR-005**: System MUST run as a non-root user inside the container for security
- **FR-006**: System MUST produce a container image smaller than 200MB to minimize transfer and storage overhead
- **FR-007**: System MUST support automated building and publishing via GitHub Actions when code is pushed to main branch
- **FR-008**: System MUST tag published images with the git commit SHA for traceability
- **FR-009**: System MUST tag published images with "latest" when publishing from main branch
- **FR-010**: System MUST tag published images with semantic version when a version tag is pushed
- **FR-011**: System MUST make the container image publicly pullable from GitHub Container Registry

### Key Entities

- **Container Image**: The packaged application artifact containing Python runtime, dependencies, and application code
- **Configuration File**: YAML file containing event slugs, polling intervals, and alert thresholds (mounted at runtime)
- **Environment Variables**: Telegram bot token and chat ID passed at container runtime

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can build a working container image in under 3 minutes on standard hardware
- **SC-002**: The container image size is under 200MB
- **SC-003**: Container starts and begins polling within 10 seconds of launch with valid configuration
- **SC-004**: Automated builds complete within 5 minutes of code push to main branch
- **SC-005**: Published images can be pulled and started by any user with a valid configuration
- **SC-006**: Container runs successfully for 24+ hours without memory leaks or crashes under normal operation

## Assumptions

- The repository is hosted on GitHub and has GitHub Actions enabled
- The repository owner has enabled GitHub Container Registry (GHCR) for the repository
- Users deploying the container have Docker or a compatible container runtime installed
- The application's existing async design is compatible with container process lifecycle
- Python 3.10+ slim base image is sufficient for all dependencies (no native compilation required)
