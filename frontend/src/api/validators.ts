import type { StudyCreationMetadata, TimelineDocument } from '../library/types'

const STUDY_ID_PATTERN = /^[0-9a-f]{32}$/
const SHA256_PATTERN = /^[0-9a-f]{64}$/

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function hasExactKeys(value: Record<string, unknown>, keys: string[]): boolean {
  const actualKeys = Object.keys(value).sort()
  return actualKeys.length === keys.length && keys.sort().every((key, index) => key === actualKeys[index])
}

function isSafeSample(value: unknown): value is number {
  return Number.isSafeInteger(value) && Number(value) >= 0
}

function creationError(): never {
  throw new Error('Resposta de criação inválida.')
}

export function parseStudyCreationMetadata(value: unknown): StudyCreationMetadata {
  const expectedKeys = [
    'study_id',
    'chunks_count',
    'duration_seconds',
    'file_size_bytes',
    'processing_time_seconds',
  ]
  if (!isRecord(value) || !hasExactKeys(value, expectedKeys)) creationError()

  const studyId = value.study_id
  const chunksCount = value.chunks_count
  const durationSeconds = value.duration_seconds
  const fileSizeBytes = value.file_size_bytes
  const processingTimeSeconds = value.processing_time_seconds

  if (
    typeof studyId !== 'string' ||
    !STUDY_ID_PATTERN.test(studyId) ||
    !Number.isInteger(chunksCount) ||
    Number(chunksCount) < 1 ||
    typeof durationSeconds !== 'number' ||
    !Number.isFinite(durationSeconds) ||
    durationSeconds < 0 ||
    !Number.isInteger(fileSizeBytes) ||
    Number(fileSizeBytes) < 1 ||
    typeof processingTimeSeconds !== 'number' ||
    !Number.isFinite(processingTimeSeconds) ||
    processingTimeSeconds < 0
  ) {
    creationError()
  }

  return {
    studyId,
    chunksCount: Number(chunksCount),
    durationSeconds,
    fileSizeBytes: Number(fileSizeBytes),
    processingTimeSeconds,
  }
}

export async function validateAudioResponse(response: Response): Promise<Blob> {
  const contentType = response.headers.get('content-type')?.split(';', 1)[0]?.trim().toLowerCase()
  if (!response.ok || contentType !== 'audio/mpeg') {
    throw new Error('Resposta de áudio inválida.')
  }

  const audio = await response.blob()
  if (audio.size === 0) {
    throw new Error('Resposta de áudio inválida.')
  }
  return audio
}

function timelineError(): never {
  throw new Error('Timeline inválida.')
}

function validateSentence(
  value: unknown,
  expectedIndex: number,
  expectedStart: number,
): { end: number } {
  if (
    !isRecord(value) ||
    !hasExactKeys(value, ['index', 'text', 'start_sample', 'end_sample']) ||
    value.index !== expectedIndex ||
    typeof value.text !== 'string' ||
    value.text.length === 0 ||
    !isSafeSample(value.start_sample) ||
    !isSafeSample(value.end_sample) ||
    value.start_sample !== expectedStart ||
    value.end_sample <= value.start_sample
  ) {
    timelineError()
  }
  return { end: value.end_sample }
}

export function parseTimeline(value: unknown): TimelineDocument {
  if (
    !isRecord(value) ||
    !hasExactKeys(value, ['schema_version', 'audio', 'chunks']) ||
    value.schema_version !== 1 ||
    !isRecord(value.audio) ||
    !hasExactKeys(value.audio, ['filename', 'sha256', 'sample_rate_hz', 'total_samples']) ||
    typeof value.audio.filename !== 'string' ||
    !/^[^/\\]+\.mp3$/.test(value.audio.filename) ||
    typeof value.audio.sha256 !== 'string' ||
    !SHA256_PATTERN.test(value.audio.sha256) ||
    value.audio.sample_rate_hz !== 22_050 ||
    !Number.isSafeInteger(value.audio.total_samples) ||
    Number(value.audio.total_samples) < 1 ||
    !Array.isArray(value.chunks) ||
    value.chunks.length === 0
  ) {
    timelineError()
  }

  let expectedChunkStart = 0
  value.chunks.forEach((chunk, chunkIndex) => {
    if (
      !isRecord(chunk) ||
      !hasExactKeys(chunk, ['index', 'start_sample', 'end_sample', 'sentences']) ||
      chunk.index !== chunkIndex ||
      !isSafeSample(chunk.start_sample) ||
      !isSafeSample(chunk.end_sample) ||
      chunk.start_sample !== expectedChunkStart ||
      chunk.end_sample <= chunk.start_sample ||
      !Array.isArray(chunk.sentences) ||
      chunk.sentences.length === 0
    ) {
      timelineError()
    }

    let expectedSentenceStart = chunk.start_sample
    chunk.sentences.forEach((sentence, sentenceIndex) => {
      expectedSentenceStart = validateSentence(
        sentence,
        sentenceIndex,
        expectedSentenceStart,
      ).end
    })
    if (expectedSentenceStart !== chunk.end_sample) timelineError()
    expectedChunkStart = chunk.end_sample
  })

  if (expectedChunkStart !== value.audio.total_samples) timelineError()
  return value as unknown as TimelineDocument
}
