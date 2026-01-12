# Feature Specification: Configurable Detector Selection

**Feature Branch**: `005-detector-config`
**Created**: 2026-01-12
**Status**: Draft
**Input**: User description: "Enable choosing the detectors and move the detectors documentation from README to docs/ directory"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Enable/Disable Individual Detectors (Priority: P1)

As a user, I want to enable or disable specific detectors so that I can customize which types of alerts I receive based on my monitoring needs.

**Why this priority**: This is the core functionality of the feature. Users need control over which detectors run to avoid alert fatigue and focus on signals relevant to their trading strategy.

**Independent Test**: Can be fully tested by configuring different detector combinations and verifying only enabled detectors generate alerts.

**Acceptance Scenarios**:

1. **Given** a configuration with only `spike` detector enabled, **When** the bot polls markets, **Then** only price spike alerts are generated (no LVR, Z-score, MAD, or closed market alerts).

2. **Given** a configuration with `spike` and `lvr` detectors enabled but `zscore` and `mad` disabled, **When** markets show both price spikes and volume anomalies, **Then** only spike and liquidity warnings are sent.

3. **Given** a configuration with all detectors disabled, **When** the bot polls markets, **Then** no alerts are generated but polling continues normally.

4. **Given** a configuration with no detector settings specified, **When** the bot starts, **Then** all detectors are enabled by default (backward compatible).

---

### User Story 2 - Configure Detectors via Environment Variables (Priority: P2)

As a user deploying via Docker, I want to configure which detectors are enabled using environment variables so that I don't need to mount a config file for simple setups.

**Why this priority**: Docker/container deployments are common and environment variable configuration provides flexibility without file mounts.

**Independent Test**: Can be fully tested by starting the bot with different environment variable combinations and verifying detector behavior.

**Acceptance Scenarios**:

1. **Given** environment variable `POLYBOTZ_DETECTORS="spike,lvr"`, **When** the bot starts, **Then** only spike and LVR detectors are active.

2. **Given** environment variable `POLYBOTZ_DETECTORS="all"`, **When** the bot starts, **Then** all detectors are enabled.

3. **Given** environment variable `POLYBOTZ_DETECTORS="none"`, **When** the bot starts, **Then** no detectors are enabled (monitoring only mode).

4. **Given** both config file and environment variable specify detectors, **When** the bot starts, **Then** environment variable takes precedence.

---

### User Story 3 - Detector Documentation in Dedicated Location (Priority: P3)

As a user, I want comprehensive detector documentation in a dedicated docs folder so that I can understand each detector's behavior, thresholds, and use cases without scrolling through a long README.

**Why this priority**: Documentation improvements enhance usability but don't affect core functionality. Can be done independently of code changes.

**Independent Test**: Can be verified by checking docs folder contains complete detector documentation with all required sections.

**Acceptance Scenarios**:

1. **Given** a user navigating to the docs folder, **When** they look for detector information, **Then** they find a dedicated file explaining all available detectors.

2. **Given** the detector documentation, **When** a user reads it, **Then** they can understand each detector's purpose, configuration options, and alert format.

3. **Given** the README, **When** a user reads the Features section, **Then** they see a brief overview with a link to detailed documentation.

---

### Edge Cases

- What happens when an invalid detector name is specified? System logs a warning and ignores the invalid detector, continuing with valid ones.
- How does the system behave if detector configuration is malformed? System falls back to all detectors enabled and logs a warning.
- What happens when a detector is disabled mid-operation? Not supported; detector configuration is only read at startup.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support enabling/disabling individual detectors: `spike`, `lvr`, `zscore`, `mad`, `closed`
- **FR-002**: System MUST provide a `detectors` configuration option in config.yaml accepting a list of detector names
- **FR-003**: System MUST support `POLYBOTZ_DETECTORS` environment variable as comma-separated list of detector names
- **FR-004**: System MUST accept special values `all` (enable all) and `none` (disable all) for detector configuration
- **FR-005**: System MUST default to all detectors enabled when no detector configuration is specified
- **FR-006**: Environment variable configuration MUST take precedence over config file when both are present
- **FR-007**: System MUST log which detectors are enabled at startup
- **FR-008**: System MUST ignore invalid detector names with a warning log
- **FR-009**: System MUST create a `docs/` directory containing detector documentation
- **FR-010**: README MUST be updated to reference the detailed documentation in `docs/`

### Key Entities

- **Detector**: A monitoring algorithm that analyzes market data and generates alerts. Has a name (identifier), enabled state, and associated configuration parameters.
- **Detector Configuration**: User settings specifying which detectors to enable and their individual thresholds.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can selectively enable/disable detectors with a single configuration change
- **SC-002**: All 5 detector types (spike, lvr, zscore, mad, closed) can be individually controlled
- **SC-003**: Docker users can configure detectors without mounting config files using environment variables
- **SC-004**: Existing configurations without detector settings continue to work (100% backward compatibility)
- **SC-005**: Detector documentation is complete, covering purpose, configuration, alert format, and examples for each detector
- **SC-006**: README length reduced by moving detector details to dedicated docs

## Assumptions

- Detector configuration is read once at startup; runtime changes require restart
- The five existing detectors (spike, lvr, zscore, mad, closed) are the complete set; no new detectors are added in this feature
- Documentation follows existing project conventions (Markdown format)
- The `docs/` directory does not currently exist and will be created as part of this feature
