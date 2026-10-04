import { describe, expect, it, vi } from 'vitest'

import { createStudiesClient } from '../../src/api/studiesClient'
import { makeTimeline } from '../setup'

describe('studiesClient', () => {
  it('creates a study through the relative API and maps snake_case metadata', async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      Response.json(
        {
          study_id: 'a'.repeat(32),
          chunks_count: 2,
          duration_seconds: 4.5,
          file_size_bytes: 1_024,
          processing_time_seconds: 0.4,
        },
        { status: 201 },
      ),
    )
    const client = createStudiesClient(fetcher)

    const result = await client.createStudy({
      text: 'Texto para estudo.',
      label: 'Rótulo apenas local',
      voice: 'pt_BR-cadu-medium',
      speed: 1.2,
      bitrate: '192k',
    })

    expect(result).toEqual({
      studyId: 'a'.repeat(32),
      chunksCount: 2,
      durationSeconds: 4.5,
      fileSizeBytes: 1_024,
      processingTimeSeconds: 0.4,
    })
    expect(fetcher).toHaveBeenCalledWith('/api/v1/studies', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: 'Texto para estudo.',
        voice: 'pt_BR-cadu-medium',
        speed: 1.2,
        bitrate: '192k',
      }),
    })
  })

  it('downloads and validates audio from a relative URL', async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(new Blob(['ID3audio']), {
        headers: { 'Content-Type': 'audio/mpeg' },
      }),
    )
    const client = createStudiesClient(fetcher)

    const audio = await client.getAudio('b'.repeat(32))

    expect(audio.size).toBeGreaterThan(0)
    expect(fetcher).toHaveBeenCalledWith(`/api/v1/studies/${'b'.repeat(32)}/audio`)
  })

  it('downloads and validates the timeline from a relative URL', async () => {
    const timeline = makeTimeline('c'.repeat(32))
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(Response.json(timeline))
    const client = createStudiesClient(fetcher)

    await expect(client.getTimeline('c'.repeat(32))).resolves.toEqual(timeline)
    expect(fetcher).toHaveBeenCalledWith(`/api/v1/studies/${'c'.repeat(32)}/timeline`)
  })

  it('rejects HTTP and contract errors', async () => {
    const httpFailure = createStudiesClient(
      vi.fn<typeof fetch>().mockResolvedValue(new Response('erro', { status: 500 })),
    )
    const invalidContract = createStudiesClient(
      vi.fn<typeof fetch>().mockResolvedValue(Response.json({ study_id: 'bad' })),
    )

    await expect(httpFailure.createStudy({ text: 'Texto.' })).rejects.toThrow(
      'Falha ao criar o estudo.',
    )
    await expect(invalidContract.createStudy({ text: 'Texto.' })).rejects.toThrow(
      'Resposta de criação inválida.',
    )
  })
})
