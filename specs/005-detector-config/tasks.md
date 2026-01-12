# Tasks: Configurable Detector Selection

**Input**: Design documents from `/specs/005-detector-config/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, quickstart.md

**Tests**: Tests ARE included per existing project conventions (pytest).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Define constants and extend Configuration dataclass

- [x] T001 Add VALID_DETECTORS constant set to src/config.py
- [x] T002 Add `detectors` field to Configuration dataclass in src/config.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core detector parsing function that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Implement `parse_detectors()` function in src/config.py
- [x] T004 [P] Add unit tests for parse_detectors() in tests/unit/test_config.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Enable/Disable Individual Detectors (Priority: P1) 🎯 MVP

**Goal**: Users can enable/disable specific detectors via config.yaml file

**Independent Test**: Configure only `spike` detector, verify only spike alerts are generated

### Tests for User Story 1

- [x] T005 [P] [US1] Add unit tests for YAML detector config parsing in tests/unit/test_config.py
- [x] T006 [P] [US1] Add integration tests for detector enable/disable in tests/integration/test_main.py

### Implementation for User Story 1

- [x] T007 [US1] Update `load_config()` to parse `detectors` field from YAML in src/config.py
- [x] T008 [US1] Update `run_poll_cycle()` to conditionally call detectors based on config in src/main.py
- [x] T009 [US1] Add startup log message showing enabled detectors in src/main.py
- [x] T010 [US1] Update config.example.yaml with detectors configuration example

**Checkpoint**: User Story 1 complete - detector enable/disable via config file works

---

## Phase 4: User Story 2 - Configure Detectors via Environment Variables (Priority: P2)

**Goal**: Docker users can configure detectors using POLYBOTZ_DETECTORS environment variable

**Independent Test**: Set `POLYBOTZ_DETECTORS="spike,lvr"`, verify only those detectors run

### Tests for User Story 2

- [x] T011 [P] [US2] Add unit tests for env var detector parsing in tests/unit/test_config.py
- [x] T012 [P] [US2] Add unit tests for env var precedence over config file in tests/unit/test_config.py

### Implementation for User Story 2

- [x] T013 [US2] Update `load_config_from_env()` to parse POLYBOTZ_DETECTORS in src/config.py
- [x] T014 [US2] Implement env var precedence logic in src/config.py
- [x] T015 [US2] Update Dockerfile with POLYBOTZ_DETECTORS documentation in Dockerfile

**Checkpoint**: User Story 2 complete - detector config via environment variable works

---

## Phase 5: User Story 3 - Detector Documentation in Dedicated Location (Priority: P3)

**Goal**: Comprehensive detector documentation moved from README to docs/ directory

**Independent Test**: docs/detectors.md exists with complete information for all 5 detectors

### Implementation for User Story 3

- [x] T016 [US3] Create docs/ directory structure
- [x] T017 [US3] Create docs/detectors.md with detailed documentation for all 5 detectors
- [x] T018 [US3] Update README.md to reference docs/detectors.md instead of inline detector docs
- [x] T019 [US3] Remove detector details from README.md (keep brief overview with link)

**Checkpoint**: User Story 3 complete - detector documentation in dedicated location

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and cleanup

- [x] T020 Run all tests to verify no regressions
- [x] T021 Run quickstart.md validation scenarios
- [x] T022 [P] Update CLAUDE.md if needed with new configuration patterns (no changes needed - auto-generated)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - US1 (P1): Can start after Phase 2
  - US2 (P2): Depends on US1 (extends same config parsing)
  - US3 (P3): Independent, can run in parallel with US1/US2
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Depends on US1 completion (extends config parsing logic)
- **User Story 3 (P3)**: Independent - can start after Foundational, run in parallel with US1/US2

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Config parsing before main.py changes
- Core implementation before example files
- Story complete before moving to next priority

### Parallel Opportunities

- T004 can run in parallel with T003 (test-first)
- T005, T006 can run in parallel (different test files)
- T011, T012 can run in parallel (same file but independent tests)
- US3 (documentation) can run in parallel with US1/US2 (different files)

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "T005 Add unit tests for YAML detector config parsing in tests/unit/test_config.py"
Task: "T006 Add integration tests for detector enable/disable in tests/integration/test_main.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational (T003-T004)
3. Complete Phase 3: User Story 1 (T005-T010)
4. **STOP and VALIDATE**: Test detector enable/disable via config file
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo (Docker support)
4. Add User Story 3 → Test independently → Deploy/Demo (documentation)
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (config file support)
   - Developer B: User Story 3 (documentation - independent)
3. After US1 complete:
   - Developer A: User Story 2 (extends US1)
4. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Only `spike` and `lvr` detectors are currently implemented; config accepts all 5 names for future-proofing
