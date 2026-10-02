<!--
Sync Impact Report
- Version change: unversioned scaffold -> 1.0.0
- Modified principles: placeholder principles -> ten project-specific principles
- Added sections: Technical Constraints; Development Workflow and Quality Gates
- Removed sections: none
- Follow-up TODOs: none
-->

# HSS Study Voice Constitution

## Core Principles

### I. Spec-Driven Development

Every relevant feature MUST follow the sequence `specify -> clarify -> plan -> tasks ->
implementation -> review`. Implementation MUST NOT begin before scope, requirements, acceptance
criteria, and significant technical decisions are documented. When clarification finds no open
questions, that result MUST still be recorded before planning. This keeps implementation aligned
with an agreed outcome and makes scope changes visible.

### II. Local-First Ownership

The VPS MAY process text and audio, but MUST NOT serve as the user's permanent library. During the
MVP, source text, generated audio, playback progress, and associated metadata MUST be retained on
the user's device. Server-side copies MUST be temporary and removed when processing no longer
requires them. This protects user ownership and limits unnecessary retention of study material.

### III. Simple and Modular Backend

The backend MUST use Python and FastAPI, Piper TTS MUST remain the primary speech provider, and
FFmpeg MUST handle required audio processing and conversion. Responsibilities MUST remain divided
into focused, independently testable components. Queues, Redis, Celery, or additional
infrastructure MUST NOT be introduced without a documented, measured need that the current design
cannot satisfy.

### IV. Mandatory Tests

Every change MUST preserve all applicable existing tests. New domain rules and pipeline behavior
MUST have unit tests, and changes that depend on real component interaction MUST have integration
coverage. A change MUST NOT be considered complete while required tests fail or relevant new
behavior lacks automated verification. This establishes regression safety as a delivery gate.

### V. Incremental Pipeline Compatibility

The established `normalization -> chunking -> TTS -> WAV -> concatenation -> MP3` pipeline MUST
evolve incrementally. Existing contracts and behavior MUST be preserved unless an approved
specification explicitly defines a breaking change and migration. Rewrites MUST NOT replace
targeted extensions when the current pipeline can support the requirement safely.

### VI. Security by Default

All external input MUST be validated, and text size MUST be limited by an explicit configured
boundary. File operations MUST prevent path traversal and remain within approved locations. User
content MUST never be executed, and logs MUST NOT contain complete submitted text. Security
controls MUST be covered by tests wherever their behavior can be exercised automatically.

### VII. No Overengineering

Each solution MUST be the simplest design that fully satisfies the current approved scope.
Capabilities intended only for possible future use MUST NOT be implemented in advance. New
abstractions, dependencies, services, and infrastructure MUST have an immediate use case and a
documented justification.

### VIII. Phase-Bounded Delivery

Every project phase MUST define its own scope, exclusions, acceptance criteria, and validation
before implementation. Work from separate phases MUST NOT be mixed unless the governing plan
documents the dependency. Each independently reversible phase MUST use an isolated commit; an
exception is permitted only when separation would leave the repository invalid and MUST be noted
in the plan or review.

### IX. Architecture Ready for Evolution

Providers and pipeline components MUST expose small, explicit interfaces and MUST avoid coupling
callers to provider-specific details. Extension points MUST be introduced when required by current
scope, not through speculative frameworks. A component MUST remain replaceable or independently
testable when it represents an external provider or a distinct pipeline responsibility.

### X. Explicit Technical Decisions

Architecturally significant changes MUST be documented in the feature specification or plan before
implementation. The record MUST state the decision, rationale, affected contracts, alternatives
considered when relevant, and compatibility consequences. Code review MUST reject undocumented
architectural changes.

## Technical Constraints

- The supported backend stack is Python with FastAPI, Piper TTS, and FFmpeg.
- MVP user artifacts MUST remain local to the user's device; remote processing storage is temporary.
- Text and audio processing MUST be deterministic for equivalent inputs and configuration wherever
  provider behavior permits.
- Temporary files MUST be cleaned after success and failure.
- Additional operational infrastructure requires evidence, an approved plan, and tests covering
  the resulting integration.
- Security boundaries for input size, filesystem access, execution, and logging are mandatory
  acceptance criteria for affected features.

## Development Workflow and Quality Gates

1. `specify` defines user value, scope, exclusions, requirements, and measurable outcomes.
2. `clarify` resolves material ambiguity or records that no clarification remains.
3. `plan` documents design decisions, compatibility impact, security considerations, and testing.
4. `tasks` divides work into bounded, verifiable units that preserve a usable pipeline.
5. Implementation follows the approved artifacts and does not add unplanned future capabilities.
6. Review verifies scope, architecture, security, compatibility, and automated test results.

No phase may pass its quality gate with unresolved mandatory requirements, failing applicable
tests, undocumented architectural changes, or known regressions in the established pipeline.

## Governance

This constitution governs all project specifications, plans, tasks, implementation, and reviews.
When another project document conflicts with it, this constitution takes precedence.

Amendments MUST be proposed as an explicit documentation change that describes the motivation and
impact on active or completed work. Approval requires review of affected specifications, plans,
tests, and migration needs. The amendment date and version MUST be updated when accepted.

Constitution versions follow semantic versioning:

- MAJOR for removal or incompatible redefinition of a principle or governance rule.
- MINOR for a new principle, section, or materially expanded obligation.
- PATCH for clarification or wording changes that do not alter obligations.

Every feature review and code review MUST include a constitution compliance check. Any justified
exception MUST be documented in the governing plan, limited in scope and duration, and approved
before implementation.

**Version**: 1.0.0 | **Ratified**: 2026-10-01 | **Last Amended**: 2026-10-01
