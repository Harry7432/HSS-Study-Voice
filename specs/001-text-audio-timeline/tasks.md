---

description: "Implementation tasks for the text-audio synchronization timeline"
---

# Tasks: Timeline de sincronizacao texto-audio

**Input**: Design documents from `/specs/001-text-audio-timeline/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`,
`quickstart.md`

**Tests**: Required by FR-021 and the project constitution. Test tasks precede implementation and
must fail for the intended reason before production code is changed.

**Organization**: Tasks are grouped by user story so each increment can be implemented and
validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it changes different files and has no incomplete dependency.
- **[Story]**: Maps the task to a user story from `spec.md`.
- Every task includes the exact target path.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish a known regression baseline and reusable deterministic audio fixtures.

- [x] T001 Run the existing suite under `backend/tests/` and record baseline pass/skip results in `specs/001-text-audio-timeline/quickstart.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Provide deterministic WAV fixtures shared by all timeline and publication tests.

**CRITICAL**: No user story implementation starts until this phase is complete.

- [x] T002 Create reusable WAV builders with configurable frame count, sample rate, channels, and sample width in `backend/tests/conftest.py`

**Checkpoint**: Tests can create valid and intentionally incompatible WAV segments without Piper or FFmpeg.

---

## Phase 3: User Story 1 - Localizar frases no audio (Priority: P1) MVP

**Goal**: Generate one canonical timeline entry per logical sentence with exact PCM sample limits.

**Independent Test**: Prepare text with several known sentences, generate deterministic WAVs, and
verify that every sentence appears once in order with contiguous ranges from zero through the exact
merged-WAV frame count.

### Tests for User Story 1

- [x] T003 [P] [US1] Add failing tests for canonical sentence extraction before grouping, repeated text identity, and oversized-sentence fragments in `backend/tests/unit/test_chunker.py`
- [x] T004 [P] [US1] Add failing tests for the structured preprocessing entry point while preserving `process() -> list[str]` behavior in `backend/tests/unit/test_pipeline.py`
- [x] T005 [P] [US1] Add failing tests for timeline v1 required fields, half-open contiguous ranges, 22050 Hz, positive totals, and merged-frame equality in `backend/tests/unit/test_timeline.py`
- [x] T006 [P] [US1] Add failing orchestrator tests for fragment rendering order, real WAV frame accounting, one MP3 export, and `timeline_path` result metadata in `backend/tests/unit/test_audio_orchestrator.py`

### Implementation for User Story 1

- [ ] T007 [P] [US1] Implement immutable `PreparedDocument`, `PreparedChunk`, `PreparedSentence`, and `SynthesisFragment` models in `backend/app/services/text/models.py` with non-empty collections/text, zero-based positional indices, bounded fragment text, temporary WAV path, and positive frame-count rules from `data-model.md`
- [ ] T008 [US1] Refactor sentence extraction and hard splitting in `backend/app/services/text/chunker.py` so canonical sentences are created before chunk grouping while existing `chunk()` outputs remain unchanged
- [ ] T009 [US1] Add the explicit structured preparation flow to `backend/app/services/text/pipeline.py` while preserving the current `process()` contract
- [ ] T010 [P] [US1] Implement timeline v1 domain models, sidecar naming, sample-range validation, UTF-8 serialization, and merged-frame verification in `backend/app/services/audio/timeline.py` with `schema_version == 1`, 64-character lowercase SHA-256, `sample_rate_hz == 22050`, positive `total_samples`, basename-only lowercase `.mp3`, and sample integers at most `9007199254740991`
- [ ] T011 [P] [US1] Extend ordered fragment rendering in `backend/app/services/audio/renderer.py` without changing the existing `render_chunks()` contract or Piper provider interface
- [ ] T012 [US1] Add synchronized generation to `backend/app/services/audio/orchestrator.py` by flattening prepared fragments, reading actual WAV frames, verifying the merged total, exporting exactly one MP3, writing `<stem>.timeline.json`, and adding trailing/defaulted `timeline_path` metadata without removing existing `AudioResult` fields
- [ ] T013 [US1] Add a real Piper/FFmpeg sentence-timeline scenario with dependency skip guards in `backend/tests/integration/test_audio_pipeline.py`

**Checkpoint**: User Story 1 independently produces exact sentence ranges for one logical chunk and preserves all legacy calls.

---

## Phase 4: User Story 2 - Preservar o contexto dos chunks (Priority: P2)

**Goal**: Preserve ordered chunk parents and derive each chunk interval exactly from its sentences.

**Independent Test**: Prepare multiple chunks containing known, repeated, and fragmented logical
sentences; verify positional identities, parent membership, order, and chunk bounds equal the first
and last child boundaries.

### Tests for User Story 2

- [ ] T014 [P] [US2] Add failing tests for multi-chunk ordering, zero-based chunk/sentence indices, repeated sentence text, and aggregate chunk limits in `backend/tests/unit/test_timeline.py`
- [ ] T015 [P] [US2] Add failing tests for multi-chunk packing and one logical sentence retaining identity across internal fragments in `backend/tests/unit/test_chunker.py` and `backend/tests/unit/test_pipeline.py`

### Implementation for User Story 2

- [ ] T016 [US2] Enforce `PreparedChunk.index` and `PreparedSentence.index` equality with collection position and keep every prepared chunk/sentence collection non-empty in `backend/app/services/text/models.py`
- [ ] T017 [US2] Implement sentence-aware chunk packing and fragment-to-parent mapping in `backend/app/services/text/chunker.py` and expose it through `backend/app/services/text/pipeline.py`
- [ ] T018 [US2] Implement ordered `TimelineChunk` aggregation in `backend/app/services/audio/timeline.py` so each chunk starts at its first sentence, ends at its last sentence, and begins where the prior chunk ends
- [ ] T019 [US2] Preserve chunk/sentence/fragment positional mappings through rendering and frame accumulation in `backend/app/services/audio/orchestrator.py`
- [ ] T020 [US2] Extend the real pipeline integration scenario to multiple chunks and a fragmented logical sentence in `backend/tests/integration/test_audio_pipeline.py`

**Checkpoint**: User Stories 1 and 2 produce a complete hierarchical timeline and remain independently testable.

---

## Phase 5: User Story 3 - Verificar a correspondencia com o MP3 (Priority: P3)

**Goal**: Bind the timeline to the exact final MP3 and publish or roll back the pair as one operation.

**Independent Test**: Recompute the hash for the generated MP3, reject an altered MP3, inject
failures at each publication step, and verify that either the complete new pair or the previous pair
remains available byte-for-byte.

### Tests for User Story 3

- [ ] T021 [P] [US3] Add failing tests for final-byte SHA-256 binding, tampered-MP3 mismatch, lowercase digest format, lowercase `.mp3` validation, and sidecar derivation in `backend/tests/unit/test_timeline.py`
- [ ] T022 [P] [US3] Add failing publication tests for pre-commit failure, first/second replace failure, exact rollback of complete or partial prior state, cleanup, and retained recovery backups when rollback fails in `backend/tests/unit/test_audio_orchestrator.py`

### Implementation for User Story 3

- [ ] T023 [US3] Finalize SHA-256 calculation after MP3 completion and strict timeline serialization/validation in `backend/app/services/audio/timeline.py`
- [ ] T024 [US3] Implement same-directory staging, previous-state backups, MP3-then-timeline `os.replace`, compensating rollback, cleanup, and dedicated rollback failure reporting in `backend/app/services/audio/orchestrator.py`
- [ ] T025 [US3] Add real regeneration coverage that replaces an existing pair and verifies published SHA-256 plus staging/backup cleanup in `backend/tests/integration/test_audio_pipeline.py`

**Checkpoint**: All three user stories are functional; consumers can verify the exact MP3 and never receive a reported partial pair.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verify compatibility, performance, documentation, and full-pipeline quality gates.

- [ ] T026 [P] Add regression tests for unchanged `chunk()`, `process()`, `generate_mp3()` arguments, existing `AudioResult` fields, voice, speed, and bitrate forwarding in `backend/tests/unit/test_pipeline.py` and `backend/tests/unit/test_audio_orchestrator.py`
- [ ] T027 [P] Create a repeatable baseline-versus-timeline 60-minute benchmark that excludes initial voice download and reports percentage overhead in `backend/scripts/benchmark_timeline.py`
- [ ] T028 [P] Document synchronized generation, sidecar discovery, PCM-domain timing, SHA verification, and MP3 decoder delay limitations in `backend/README.md`
- [ ] T029 Run all commands and inspect all expected outcomes from `specs/001-text-audio-timeline/quickstart.md`, record the measured performance result there, and confirm the full suite under `backend/tests/` passes or skips only guarded external dependencies

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on T001 and blocks all user stories.
- **User Story 1 (Phase 3)**: Depends on T002 and establishes the MVP timeline primitives.
- **User Story 2 (Phase 4)**: Depends on User Story 1 because it extends sentence timing into chunk hierarchy.
- **User Story 3 (Phase 5)**: Depends on User Story 1 timeline output; it may proceed in parallel with User Story 2 after Phase 3.
- **Polish (Phase 6)**: Depends on all selected user stories.

### User Story Dependency Graph

```text
Setup -> Foundational -> US1 (MVP) -> US2
                              └-----> US3
US2 + US3 -> Polish
```

### Within Each User Story

- Write the listed tests first and confirm they fail for the missing behavior.
- Implement models before transformations and transformations before orchestration.
- Verify the independent test before moving to the next story.
- Do not combine task commits across phases unless separation would leave the repository invalid.

### Parallel Opportunities

- T003, T004, T005, and T006 can be written in parallel in separate test files.
- T007, T010, and T011 can proceed in parallel after their corresponding failing tests exist.
- T014 and T015 can be written in parallel.
- T021 and T022 can be written in parallel.
- After US1, US2 and US3 can be assigned in parallel, with coordination on `timeline.py` and `orchestrator.py`.
- T026, T027, and T028 can proceed in parallel after all story implementations.

---

## Parallel Example: User Story 1

```text
Task T003: Add canonical sentence and fragmentation tests in backend/tests/unit/test_chunker.py
Task T004: Add structured pipeline compatibility tests in backend/tests/unit/test_pipeline.py
Task T005: Add timeline range/contract tests in backend/tests/unit/test_timeline.py
Task T006: Add synchronized orchestrator tests in backend/tests/unit/test_audio_orchestrator.py

After tests fail:
Task T007: Implement prepared text models in backend/app/services/text/models.py
Task T010: Implement timeline domain/serialization in backend/app/services/audio/timeline.py
Task T011: Extend fragment rendering in backend/app/services/audio/renderer.py
```

## Parallel Example: User Story 2

```text
Task T014: Add chunk aggregation tests in backend/tests/unit/test_timeline.py
Task T015: Add structured chunk packing tests in backend/tests/unit/test_chunker.py and backend/tests/unit/test_pipeline.py
```

## Parallel Example: User Story 3

```text
Task T021: Add SHA/sidecar contract tests in backend/tests/unit/test_timeline.py
Task T022: Add atomic publication and rollback tests in backend/tests/unit/test_audio_orchestrator.py
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Complete T001-T002.
2. Complete T003-T013 test-first.
3. Stop and run the User Story 1 independent test.
4. Confirm legacy text and MP3 generation remain green.

### Incremental Delivery

1. **US1**: Deliver exact sentence timing and a valid timeline for one logical chunk.
2. **US2**: Add complete chunk hierarchy and fragmented-sentence identity.
3. **US3**: Add final MP3 verification and recoverable pair publication.
4. **Polish**: Run compatibility, documentation, performance, and full-suite gates.

### Parallel Team Strategy

After T002 and the US1 checkpoint:

- Developer A can implement US2 hierarchy.
- Developer B can implement US3 binding/publication.
- Both coordinate before editing `backend/app/services/audio/timeline.py` or
  `backend/app/services/audio/orchestrator.py` concurrently.

## Notes

- `[P]` means different files and no incomplete dependency at that point.
- Story labels provide traceability to `spec.md`.
- Tests are mandatory and precede implementation.
- No task adds frontend, API, word-level timing, queues, Redis, Celery, or remote persistence.
- Commit after each task or cohesive task group while preserving a valid repository state.
