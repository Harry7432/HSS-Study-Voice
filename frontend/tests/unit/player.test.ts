import { describe, expect, it, vi } from 'vitest'

import type { SavedStudyDetail } from '../../src/library/types'
import { createLocalPlayer } from '../../src/ui/player'
import { makeStudyResult } from '../setup'

function makeDetail(overrides: Partial<SavedStudyDetail> = {}): SavedStudyDetail {
  const result = makeStudyResult()
  return {
    studyId: result.studyId,
    label: 'Citologia',
    createdAt: '2026-10-03T12:00:00.000Z',
    durationSeconds: result.durationSeconds,
    fileSizeBytes: result.fileSizeBytes,
    voice: result.voice,
    speed: result.speed,
    bitrate: result.bitrate,
    progress: {
      positionSeconds: 1.25,
      completed: false,
      updatedAt: '2026-10-03T12:00:00.000Z',
    },
    audio: result.audio,
    timeline: result.timeline,
    ...overrides,
  }
}

describe('local player', () => {
  it('plays a local Blob and resumes within one second of saved progress', () => {
    const audio = document.createElement('audio')
    const createObjectUrl = vi.fn().mockReturnValue('blob:local-study')
    const player = createLocalPlayer(audio, {
      updateProgress: vi.fn(),
      createObjectUrl,
      revokeObjectUrl: vi.fn(),
    })

    player.open(makeDetail())
    audio.dispatchEvent(new Event('loadedmetadata'))

    expect(createObjectUrl).toHaveBeenCalledOnce()
    expect(audio.getAttribute('src')).toBe('blob:local-study')
    expect(Math.abs(audio.currentTime - 1.25)).toBeLessThanOrEqual(1)
  })

  it.each(['pause', 'seeked'])('persists progress on %s', async (eventName) => {
    const audio = document.createElement('audio')
    const updateProgress = vi.fn().mockResolvedValue(undefined)
    const player = createLocalPlayer(audio, {
      updateProgress,
      createObjectUrl: vi.fn().mockReturnValue('blob:study'),
      revokeObjectUrl: vi.fn(),
    })
    const detail = makeDetail()
    player.open(detail)
    audio.currentTime = 1.5

    audio.dispatchEvent(new Event(eventName))

    await vi.waitFor(() => {
      expect(updateProgress).toHaveBeenCalledWith(detail.studyId, { positionSeconds: 1.5 })
    })
  })

  it('persists every five seconds only while playing and visible', async () => {
    vi.useFakeTimers()
    const audio = document.createElement('audio')
    let visible = true
    const updateProgress = vi.fn().mockResolvedValue(undefined)
    const player = createLocalPlayer(audio, {
      updateProgress,
      createObjectUrl: vi.fn().mockReturnValue('blob:study'),
      revokeObjectUrl: vi.fn(),
      isVisible: () => visible,
    })
    player.open(makeDetail())
    audio.currentTime = 1
    audio.dispatchEvent(new Event('play'))

    await vi.advanceTimersByTimeAsync(5_000)
    expect(updateProgress).toHaveBeenCalledTimes(1)
    visible = false
    await vi.advanceTimersByTimeAsync(5_000)
    expect(updateProgress).toHaveBeenCalledTimes(1)
    player.discard()
    vi.useRealTimers()
  })

  it('persists when the page becomes hidden and marks completion on ended', async () => {
    const audio = document.createElement('audio')
    let visible = true
    const updateProgress = vi.fn().mockResolvedValue(undefined)
    const onCompleted = vi.fn()
    const detail = makeDetail()
    const player = createLocalPlayer(audio, {
      updateProgress,
      createObjectUrl: vi.fn().mockReturnValue('blob:study'),
      revokeObjectUrl: vi.fn(),
      isVisible: () => visible,
      onCompleted,
    })
    player.open(detail)
    audio.currentTime = 1.75
    visible = false
    document.dispatchEvent(new Event('visibilitychange'))
    audio.dispatchEvent(new Event('ended'))

    await vi.waitFor(() => expect(updateProgress).toHaveBeenCalledTimes(2))
    expect(updateProgress).toHaveBeenNthCalledWith(1, detail.studyId, { positionSeconds: 1.75 })
    expect(updateProgress).toHaveBeenNthCalledWith(2, detail.studyId, {
      positionSeconds: detail.durationSeconds,
      completed: true,
    })
    expect(onCompleted).toHaveBeenCalledWith(detail.studyId)
  })

  it('tracks the playing state across play, pause and ended, and notifies each transition', async () => {
    const audio = document.createElement('audio')
    const onPlaying = vi.fn()
    const onPaused = vi.fn()
    const onCompleted = vi.fn()
    const detail = makeDetail()
    const player = createLocalPlayer(audio, {
      updateProgress: vi.fn().mockResolvedValue(undefined),
      createObjectUrl: vi.fn().mockReturnValue('blob:study'),
      revokeObjectUrl: vi.fn(),
      onPlaying,
      onPaused,
      onCompleted,
    })
    player.open(detail)
    expect(player.isPlaying()).toBe(false)

    audio.dispatchEvent(new Event('play'))
    expect(player.isPlaying()).toBe(true)
    expect(onPlaying).toHaveBeenCalledWith(detail.studyId)

    audio.dispatchEvent(new Event('pause'))
    expect(player.isPlaying()).toBe(false)
    expect(onPaused).toHaveBeenCalledWith(detail.studyId)

    audio.dispatchEvent(new Event('play'))
    expect(player.isPlaying()).toBe(true)

    audio.dispatchEvent(new Event('ended'))
    expect(player.isPlaying()).toBe(false)
    await vi.waitFor(() => expect(onCompleted).toHaveBeenCalledWith(detail.studyId))
  })

  it('revokes the Object URL when discarded', () => {
    const audio = document.createElement('audio')
    const revokeObjectUrl = vi.fn()
    const player = createLocalPlayer(audio, {
      updateProgress: vi.fn(),
      createObjectUrl: vi.fn().mockReturnValue('blob:study'),
      revokeObjectUrl,
    })
    player.open(makeDetail())

    player.discard()

    expect(revokeObjectUrl).toHaveBeenCalledWith('blob:study')
    expect(audio.getAttribute('src')).toBeNull()
  })

  it('warns without interrupting playback when progress cannot be saved', async () => {
    const audio = document.createElement('audio')
    const onWarning = vi.fn()
    const player = createLocalPlayer(audio, {
      updateProgress: vi.fn().mockRejectedValue(new Error('QuotaExceededError interno')),
      createObjectUrl: vi.fn().mockReturnValue('blob:study'),
      revokeObjectUrl: vi.fn(),
      onWarning,
    })
    player.open(makeDetail())
    audio.currentTime = 1

    audio.dispatchEvent(new Event('pause'))

    await vi.waitFor(() => expect(onWarning).toHaveBeenCalledOnce())
    const warning = onWarning.mock.calls[0]?.[0]
    expect(warning).toContain('Não foi possível salvar seu progresso')
    expect(warning).not.toContain('QuotaExceededError')
    expect(audio.getAttribute('src')).toBe('blob:study')
  })
})
