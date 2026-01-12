# Tasks: Docker Container with GitHub Container Registry

**Input**: Design documents from `/specs/003-docker-ghcr/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Not requested in specification. No test tasks included.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Container files**: Repository root (Dockerfile, .dockerignore)
- **CI/CD workflow**: `.github/workflows/`
- **Documentation**: `README.md` (existing)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create container build exclusions and verify existing structure

- [x] T001 [P] Create .dockerignore file at repository root
- [x] T002 [P] Verify pyproject.toml has correct entry point for container execution

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core container configuration that MUST be complete before any user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Create multi-stage Dockerfile at repository root with builder and runtime stages
- [x] T004 Configure builder stage: python:3.10-slim-bookworm base, uv installation, dependency installation
- [x] T005 Configure runtime stage: slim base, non-root user polybotz (UID 1000), copy venv and source
- [x] T006 Set WORKDIR to /app and configure CMD to run python -m src
- [x] T007 Verify image builds successfully with `docker build -t polybotz:test .`

**Checkpoint**: Foundation ready - Dockerfile builds successfully, user story implementation can begin

---

## Phase 3: User Story 1 - Build Container Image Locally (Priority: P1) 🎯 MVP

**Goal**: Developer can build and run the polybotz container locally with proper configuration handling

**Independent Test**: Run `docker build` then `docker run` with config.yaml mounted and env vars set; verify bot starts polling

### Implementation for User Story 1

- [x] T008 [US1] Add config mount path /app/config.yaml and document in Dockerfile comments
- [x] T009 [US1] Configure environment variable passthrough for TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
- [x] T010 [US1] Verify container exits with clear error when config.yaml is not mounted
- [x] T011 [US1] Verify container exits with clear error when Telegram env vars are missing
- [x] T012 [US1] Verify container starts and polls when valid config and env vars provided
- [x] T013 [US1] Verify image size is under 200MB with `docker images polybotz:test`

**Checkpoint**: User Story 1 complete - developers can build and run containers locally

---

## Phase 4: User Story 2 - Automated Container Publishing (Priority: P2)

**Goal**: Container images are automatically built and published to GHCR on main branch push and version tags

**Independent Test**: Push to main branch; verify image appears at ghcr.io/OWNER/polybotz with correct tags

### Implementation for User Story 2

- [x] T014 [US2] Create .github/workflows/docker-publish.yml with name and trigger configuration
- [x] T015 [US2] Configure workflow triggers: push to main branch and version tags (v*.*.*)
- [x] T016 [US2] Add job: checkout, setup QEMU for multi-arch, setup Docker Buildx
- [x] T017 [US2] Add step: Login to GHCR using GITHUB_TOKEN
- [x] T018 [US2] Add step: Docker metadata-action for automatic tag generation (main, sha, version, latest)
- [x] T019 [US2] Add step: Build and push with docker/build-push-action for linux/amd64,linux/arm64
- [x] T020 [US2] Configure image to be publicly pullable (packages settings note in workflow comments)

**Checkpoint**: User Story 2 complete - automated publishing configured

---

## Phase 5: User Story 3 - Pull and Run Published Image (Priority: P3)

**Goal**: Operators can pull pre-built image from GHCR and run without building locally

**Independent Test**: Pull image from ghcr.io/OWNER/polybotz:latest; run with config; verify bot operates correctly

### Implementation for User Story 3

- [x] T021 [US3] Add Docker usage section to README.md with pull and run commands
- [x] T022 [US3] Document required volume mount (-v) for config.yaml in README.md
- [x] T023 [US3] Document required environment variables (-e) in README.md
- [x] T024 [US3] Add troubleshooting section for common container issues in README.md

**Checkpoint**: User Story 3 complete - operators have documentation to deploy

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final verification and cleanup

- [x] T025 [P] Run full build and verify image size meets <200MB requirement
- [x] T026 [P] Verify multi-arch build works (if arm64 hardware available) or trust CI
- [x] T027 Update quickstart.md with final verified commands from README.md
- [ ] T028 Create git commit with all container-related files

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational - builds on working Dockerfile
- **User Story 2 (Phase 4)**: Depends on Foundational - needs working Dockerfile to publish
- **User Story 3 (Phase 5)**: Depends on User Story 2 - needs published images to document
- **Polish (Phase 6)**: Depends on all user stories complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent of US1 (same Dockerfile)
- **User Story 3 (P3)**: Depends on User Story 2 - Needs published images to exist for documentation

### Within Each Phase

- Tasks without dependencies can run in parallel
- T003-T006 are sequential (building the Dockerfile)
- T014-T020 are sequential (building the workflow file)

### Parallel Opportunities

**Phase 1** (fully parallel):
```
T001 (.dockerignore) || T002 (verify pyproject.toml)
```

**Phase 3-4** (can run in parallel after Foundational):
```
User Story 1 (T008-T013) || User Story 2 (T014-T020)
```

**Phase 6** (partially parallel):
```
T025 (verify size) || T026 (verify multi-arch)
```

---

## Parallel Example: Setup Phase

```bash
# Launch both setup tasks together:
Task: "Create .dockerignore file at repository root"
Task: "Verify pyproject.toml has correct entry point for container execution"
```

## Parallel Example: User Stories 1 and 2

```bash
# After Foundational complete, both can run in parallel:
# Developer A: User Story 1 (container runtime config)
# Developer B: User Story 2 (CI/CD workflow)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (.dockerignore, verify pyproject.toml)
2. Complete Phase 2: Foundational (working Dockerfile)
3. Complete Phase 3: User Story 1 (local build and run)
4. **STOP and VALIDATE**: Build container, run with config, verify bot works
5. Can use locally even without automated publishing

### Incremental Delivery

1. Setup + Foundational → Working Dockerfile
2. Add User Story 1 → Local container development ready (MVP!)
3. Add User Story 2 → Automated publishing on merge
4. Add User Story 3 → Documentation for operators
5. Each story adds value without breaking previous stories

### Single Developer Strategy

1. Complete all phases sequentially in priority order
2. Validate at each checkpoint before proceeding
3. Polish phase ensures everything is production-ready

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- User Story 3 depends on User Story 2 (needs published images)
- No test tasks - not requested in specification
- Commit after each phase or logical group
- Verify image size (<200MB) at multiple checkpoints
