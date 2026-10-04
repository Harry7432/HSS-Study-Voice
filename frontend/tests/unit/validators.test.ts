import { describe, expect, it } from 'vitest'

import {
  parseStudyCreationMetadata,
  parseTimeline,
  validateAudioResponse,
} from '../../src/api/validators'
import { makeTimeline } from '../setup'

describe('parseStudyCreationMetadata', () => {
  const validResponse = {
    study_id: 'a'.repeat(32),
    chunks_count: 1,
    duration_seconds: 0,
    file_size_bytes: 1,
    processing_time_seconds: 0,
  }

  it('maps a contract-valid response at its lower numeric bounds', () => {
    expect(parseStudyCreationMetadata(validResponse)).toEqual({
      studyId: 'a'.repeat(32),
      chunksCount: 1,
      durationSeconds: 0,
      fileSizeBytes: 1,
      processingTimeSeconds: 0,
    })
  })

  it.each([
    [{ ...validResponse, study_id: 'invalid' }],
    [{ ...validResponse, chunks_count: 0 }],
    [{ ...validResponse, duration_seconds: -1 }],
    [{ ...validResponse, file_size_bytes: 1.5 }],
    [{ ...validResponse, processing_time_seconds: -0.1 }],
    [{ ...validResponse, unexpected: true }],
  ])('rejects a response outside the Phase 4 contract', (value) => {
    expect(() => parseStudyCreationMetadata(value)).toThrow('Resposta de criação inválida.')
  })
})

describe('validateAudioResponse', () => {
  it('returns a non-empty MP3 blob', async () => {
    const response = new Response(new Blob(['ID3audio'], { type: 'audio/mpeg' }), {
      status: 200,
      headers: { 'Content-Type': 'audio/mpeg' },
    })

    const audio = await validateAudioResponse(response)

    expect(audio.type).toBe('audio/mpeg')
    expect(audio.size).toBeGreaterThan(0)
  })

  it.each([
    new Response('erro', { status: 500, headers: { 'Content-Type': 'audio/mpeg' } }),
    new Response('texto', { status: 200, headers: { 'Content-Type': 'text/plain' } }),
    new Response('', { status: 200, headers: { 'Content-Type': 'audio/mpeg' } }),
  ])('rejects invalid audio responses', async (response) => {
    await expect(validateAudioResponse(response)).rejects.toThrow('Resposta de áudio inválida.')
  })
})

describe('parseTimeline', () => {
  it('accepts a valid timeline-v1 document', () => {
    const timeline = makeTimeline()

    expect(parseTimeline(timeline)).toEqual(timeline)
  })

  it.each([
    (timeline: ReturnType<typeof makeTimeline>) => ({ ...timeline, schema_version: 2 }),
    (timeline: ReturnType<typeof makeTimeline>) => ({
      ...timeline,
      audio: { ...timeline.audio, sha256: 'bad' },
    }),
    (timeline: ReturnType<typeof makeTimeline>) => ({
      ...timeline,
      audio: { ...timeline.audio, sample_rate_hz: 44_100 },
    }),
    (timeline: ReturnType<typeof makeTimeline>) => ({
      ...timeline,
      audio: { ...timeline.audio, total_samples: 0 },
    }),
    (timeline: ReturnType<typeof makeTimeline>) => ({
      ...timeline,
      chunks: [{ ...timeline.chunks[0]!, start_sample: 10, end_sample: 5 }],
    }),
    (timeline: ReturnType<typeof makeTimeline>) => ({ ...timeline, extra: true }),
  ])('rejects an invalid timeline', (mutate) => {
    expect(() => parseTimeline(mutate(makeTimeline()))).toThrow('Timeline inválida.')
  })
})
