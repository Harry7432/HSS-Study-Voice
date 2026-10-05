import { describe, expect, it, vi } from 'vitest'

import {
  buildTimelineSrt,
  canShareFiles,
  downloadBlob,
  shareOrDownloadAudio,
  slugifyLabel,
} from '../../src/ui/mediaExport'
import { makeTimeline } from '../setup'

describe('slugifyLabel', () => {
  it('lowercases, strips accents and collapses punctuation into dashes', () => {
    expect(slugifyLabel('Revisão de Biologia Celular!')).toBe('revisao-de-biologia-celular')
  })

  it('falls back to a generic name when nothing survives slugification', () => {
    expect(slugifyLabel('***')).toBe('estudo')
  })
})

describe('canShareFiles', () => {
  it('is false when the Web Share API is unavailable', () => {
    expect(canShareFiles()).toBe(false)
  })

  it('is true when canShare reports support for files', () => {
    vi.stubGlobal('navigator', {
      ...navigator,
      share: vi.fn(),
      canShare: vi.fn().mockReturnValue(true),
    })

    expect(canShareFiles()).toBe(true)

    vi.unstubAllGlobals()
  })
})

describe('downloadBlob', () => {
  it('drives a temporary anchor through the given blob URL and revokes it afterwards', () => {
    const blob = new Blob(['conteudo'], { type: 'audio/mpeg' })
    const createObjectUrl = vi.fn().mockReturnValue('blob:estudo')
    const revokeObjectUrl = vi.fn()
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})

    downloadBlob(blob, 'estudo.mp3', { createObjectUrl, revokeObjectUrl })

    expect(createObjectUrl).toHaveBeenCalledWith(blob)
    expect(clickSpy).toHaveBeenCalledOnce()
    expect(revokeObjectUrl).toHaveBeenCalledWith('blob:estudo')

    clickSpy.mockRestore()
  })
})

describe('shareOrDownloadAudio', () => {
  it('shares the file when the platform supports it, without falling back to download', async () => {
    const share = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { ...navigator, share, canShare: vi.fn().mockReturnValue(true) })
    const createObjectUrl = vi.fn()
    const revokeObjectUrl = vi.fn()
    const blob = new Blob(['conteudo'], { type: 'audio/mpeg' })

    await shareOrDownloadAudio(blob, 'estudo.mp3', 'Estudo', { createObjectUrl, revokeObjectUrl })

    expect(share).toHaveBeenCalledOnce()
    expect(createObjectUrl).not.toHaveBeenCalled()
    vi.unstubAllGlobals()
  })

  it('does not fall back to download when the user cancels the share sheet', async () => {
    const abortError = new DOMException('cancelled', 'AbortError')
    const share = vi.fn().mockRejectedValue(abortError)
    vi.stubGlobal('navigator', { ...navigator, share, canShare: vi.fn().mockReturnValue(true) })
    const createObjectUrl = vi.fn()
    const revokeObjectUrl = vi.fn()
    const blob = new Blob(['conteudo'], { type: 'audio/mpeg' })

    await shareOrDownloadAudio(blob, 'estudo.mp3', 'Estudo', { createObjectUrl, revokeObjectUrl })

    expect(createObjectUrl).not.toHaveBeenCalled()
    vi.unstubAllGlobals()
  })

  it('falls back to downloading the file when sharing is unsupported', async () => {
    vi.stubGlobal('navigator', { ...navigator, share: undefined, canShare: undefined })
    const createObjectUrl = vi.fn().mockReturnValue('blob:estudo')
    const revokeObjectUrl = vi.fn()
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    const blob = new Blob(['conteudo'], { type: 'audio/mpeg' })

    await shareOrDownloadAudio(blob, 'estudo.mp3', 'Estudo', { createObjectUrl, revokeObjectUrl })

    expect(createObjectUrl).toHaveBeenCalled()
    clickSpy.mockRestore()
    vi.unstubAllGlobals()
  })
})

describe('buildTimelineSrt', () => {
  it('converts sentence sample ranges into SRT timestamps', () => {
    const srt = buildTimelineSrt(makeTimeline())

    expect(srt).toBe('1\n00:00:00,000 --> 00:00:02,000\nUma frase de estudo.\n')
  })

  it('returns undefined when the timeline has no sentences', () => {
    const empty = buildTimelineSrt({
      schema_version: 1,
      audio: { filename: 'a.mp3', sha256: 'a'.repeat(64), sample_rate_hz: 22_050, total_samples: 0 },
      chunks: [],
    })

    expect(empty).toBeUndefined()
  })
})
