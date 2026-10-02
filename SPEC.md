# HSS Study Voice — Product Specification

Status: Initial specification

## 1. Overview

HSS Study Voice is a local text-to-speech service designed to convert study materials into audio for easier learning and review. The system accepts raw or Markdown-formatted text, normalizes it for speech, splits it into TTS-friendly chunks, renders audio with a speech engine, and exports the final result as an MP3 file.

The project is implemented as a Python backend using FastAPI and is intended to run locally, without requiring a remote speech API.

## 2. Goals

- Convert educational text into spoken audio.
- Support Markdown and plain-text input with clean spoken output.
- Chunk long content into manageable segments for high-quality synthesis.
- Keep the pipeline deterministic, testable, and easy to extend.
- Export final audio as MP3 while maintaining a local-first workflow.

## 3. Non-goals

- Multi-user SaaS backend or remote hosting.
- Advanced voice cloning or fine-tuned custom TTS models.
- Real-time streaming audio generation.
- Browser frontend or mobile client.
- Serverless deployment or cloud orchestration.

## 4. Primary Users

- Students studying notes, summaries, or reading materials.
- Researchers or educators converting text documents into audio.
- Developers working on local TTS pipelines for experimentation.

## 5. Functional Requirements

### 5.1 Text preprocessing
- The system must accept raw text input that may include Markdown formatting.
- Markdown syntax such as headings, emphasis, links, blockquotes, and list markers must be cleaned from the final spoken output while preserving meaningful content.
- The system must return a list of TTS-ready plain-text chunks.
- Empty or whitespace-only input must return an empty result without errors.

### 5.2 Chunking
- Long text must be broken into smaller chunks according to configured limits.
- Chunks should respect sentence and paragraph boundaries when possible.
- Chunking should avoid splitting important semantic content in a way that harms listening quality.

### 5.3 Audio synthesis
- The system must render each chunk to audio using the configured default voice model.
- Voice, speed, and bitrate must be configurable through central settings.
- Audio generation must preserve the sequence of chunks in the final output.

### 5.4 Output generation
- The pipeline must merge rendered audio segments into a single WAV file.
- The merged file must be exported to MP3 format.
- The system must return metadata including output file path, processing duration, chunk count, and file size.
- Temporary files must be cleaned up after generation.

### 5.5 Health and configuration status
- The application must expose a health endpoint.
- Health responses should include runtime status, project metadata, ffmpeg availability, default voice configuration, and chunk size configuration.

## 6. System Components

### Backend app
- FastAPI application entrypoint in `backend/app/main.py`
- Central configuration in `backend/app/core/config.py`

### Text processing
- MarkdownNormalizer: strips Markdown syntax while preserving semantic text.
- TextChunker: segments normalized text into chunk-sized units.
- TextPreprocessingPipeline: orchestrates normalization and chunking.

### Audio processing
- AudioRenderer: converts chunks to temporary WAV segments.
- AudioConcatenator: merges WAV segments into a single file.
- MP3Exporter: converts the final WAV to MP3.
- AudioOrchestrator: coordinates the full synthesis pipeline.

## 7. Technical Constraints

- Python >= 3.13
- FastAPI for API layer
- Pydantic settings for configuration
- Piper TTS as the default provider
- ffmpeg required for audio conversion workflow
- Local filesystem storage for generated outputs and temporary audio

## 8. Quality Attributes

### Reliability
- Temporary files should always be cleaned on failure.
- Rendering should fail clearly if synthesis fails at any chunk.

### Testability
- Each pipeline stage should be independently injectable and unit-testable.
- The project should have automated tests for text normalization, chunking, and audio orchestration.

### Maintainability
- Settings should be centralized and environment-driven.
- Pipeline responsibilities should remain isolated by service and module.

## 9. Acceptance Criteria

1. A user can provide plain or Markdown-formatted text and receive a list of cleaned chunks.
2. Markdown formatting is not present in the spoken content returned by the preprocessing pipeline.
3. Large text input is split into multiple chunks without losing semantic meaning.
4. The system can generate an MP3 output file from a list of text chunks.
5. The result contains metadata describing the generated audio artifact.
6. A health endpoint confirms that the service is running and reports key configuration details.
7. Temporary files are cleaned after audio generation, even when errors occur.

## 10. Open Risks and Notes

- Local TTS performance depends on the installed Piper voice models and ffmpeg availability.
- The default voice and chunking thresholds are configuration-backed and may need tuning per use case.
- Further API endpoints may be added later for file upload, voice selection, and direct text submission.

## 11. Future Iterations

- Add REST endpoints for text submission and MP3 download.
- Support multiple voice models and language variants.
- Add job status tracking and asynchronous generation.
- Introduce richer validation and error reporting.
- Add UI or CLI tooling for end-to-end playback and export workflows.
