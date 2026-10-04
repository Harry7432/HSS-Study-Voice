import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { TimelineDocument } from '../../src/library/types'
import { createReadingView, type ReadingViewStudy } from '../../src/ui/readingView'

const SAMPLE_RATE_HZ = 22_050

function buildTimeline(chunks: string[][]): TimelineDocument {
  let cursor = 0
  const timelineChunks = chunks.map((sentenceTexts, chunkIndex) => {
    const chunkStart = cursor
    const sentences = sentenceTexts.map((text, sentenceIndex) => {
      const start = cursor
      cursor += SAMPLE_RATE_HZ
      return { index: sentenceIndex, text, start_sample: start, end_sample: cursor }
    })
    return { index: chunkIndex, start_sample: chunkStart, end_sample: cursor, sentences }
  })
  return {
    schema_version: 1,
    audio: {
      filename: `${'a'.repeat(32)}.mp3`,
      sha256: 'b'.repeat(64),
      sample_rate_hz: SAMPLE_RATE_HZ,
      total_samples: cursor,
    },
    chunks: timelineChunks,
  }
}

function buildManySentenceTimeline(count: number): TimelineDocument {
  return buildTimeline([Array.from({ length: count }, (_, index) => `Frase ${index}.`)])
}

function study(
  timeline: TimelineDocument,
  progress: Partial<ReadingViewStudy['progress']> = {},
): ReadingViewStudy {
  return {
    timeline,
    progress: { positionSeconds: 0, completed: false, ...progress },
  }
}

describe('reading view', () => {
  beforeEach(() => {
    // jsdom does not implement Element.prototype.scrollIntoView at all (not even as a no-op), so
    // it must be assigned directly before it can be stubbed/spied on; every open()/highlight
    // change can then call it without throwing, regardless of whether a given test cares about
    // tracking its calls.
    Element.prototype.scrollIntoView = vi.fn()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it('renders chunks and sentences in the same order as the timeline (FR-001)', () => {
    const container = document.createElement('div')
    const audio = document.createElement('audio')
    const timeline = buildTimeline([
      ['Primeira frase.', 'Segunda frase.'],
      ['Terceira frase.'],
    ])
    const view = createReadingView(container, audio)

    view.open(study(timeline))

    const texts = Array.from(container.querySelectorAll('.reading-sentence')).map(
      (element) => element.textContent,
    )
    expect(texts).toEqual(['Primeira frase.', 'Segunda frase.', 'Terceira frase.'])
    expect(container.querySelectorAll('.reading-chunk')).toHaveLength(2)
  })

  it('highlights exactly one sentence at a time as timeupdate fires, moving the highlight (FR-002/FR-004)', () => {
    const container = document.createElement('div')
    const audio = document.createElement('audio')
    const timeline = buildTimeline([['Primeira frase.', 'Segunda frase.', 'Terceira frase.']])
    const view = createReadingView(container, audio)
    view.open(study(timeline))

    audio.currentTime = 1.5
    audio.dispatchEvent(new Event('timeupdate'))
    let current = container.querySelectorAll('[aria-current="true"]')
    expect(current).toHaveLength(1)
    expect(current[0]?.textContent).toBe('Segunda frase.')

    audio.currentTime = 2.5
    audio.dispatchEvent(new Event('timeupdate'))
    current = container.querySelectorAll('[aria-current="true"]')
    expect(current).toHaveLength(1)
    expect(current[0]?.textContent).toBe('Terceira frase.')
  })

  it('marks the current sentence with aria-current and a non-color signal (FR-015)', () => {
    const container = document.createElement('div')
    const audio = document.createElement('audio')
    const timeline = buildTimeline([['Primeira frase.', 'Segunda frase.']])
    const view = createReadingView(container, audio)
    view.open(study(timeline))

    audio.currentTime = 1
    audio.dispatchEvent(new Event('timeupdate'))

    const current = container.querySelector('[aria-current="true"]')
    expect(current).not.toBeNull()
    expect(current?.getAttribute('aria-current')).toBe('true')
    expect(current?.classList.contains('is-current')).toBe(true)
  })

  it('scrolls to the current sentence on change, suspends after a manual scroll, and resumes on seeked/play (FR-005/FR-006)', () => {
    vi.useFakeTimers()
    const container = document.createElement('div')
    const audio = document.createElement('audio')
    const timeline = buildTimeline([['Primeira frase.', 'Segunda frase.', 'Terceira frase.']])
    const scrollIntoView = vi.fn()
    Element.prototype.scrollIntoView = scrollIntoView
    const view = createReadingView(container, audio)
    view.open(study(timeline))
    scrollIntoView.mockClear()

    audio.currentTime = 1
    audio.dispatchEvent(new Event('timeupdate'))
    expect(scrollIntoView).toHaveBeenCalledTimes(1)

    vi.advanceTimersByTime(1_000)
    container.dispatchEvent(new Event('scroll'))

    audio.currentTime = 2
    audio.dispatchEvent(new Event('timeupdate'))
    expect(scrollIntoView).toHaveBeenCalledTimes(1)

    audio.dispatchEvent(new Event('seeked'))
    audio.currentTime = 0
    audio.dispatchEvent(new Event('timeupdate'))
    expect(scrollIntoView).toHaveBeenCalledTimes(2)
  })

  it('falls back to an unavailability message without throwing on a corrupted timeline, and keeps working afterwards (FR-011)', () => {
    const container = document.createElement('div')
    const audio = document.createElement('audio')
    const valid = buildTimeline([['Primeira frase.']])
    const corrupted = { ...valid, audio: { ...valid.audio, sha256: 'bad' } }
    const view = createReadingView(container, audio)

    expect(() => view.open(study(corrupted))).not.toThrow()
    expect(container.querySelector('.reading-sentence')).toBeNull()
    expect(container.textContent).toBeTruthy()

    expect(() => {
      audio.currentTime = 1
      audio.dispatchEvent(new Event('timeupdate'))
    }).not.toThrow()

    view.open(study(valid))
    expect(container.querySelectorAll('.reading-sentence')).toHaveLength(1)
  })

  it('renders in a single batch insertion on the container regardless of sentence count', () => {
    const smallContainer = document.createElement('div')
    const audio = document.createElement('audio')
    const smallReplaceChildren = vi.spyOn(smallContainer, 'replaceChildren')
    const smallAppendChild = vi.spyOn(smallContainer, 'appendChild')
    createReadingView(smallContainer, audio).open(study(buildTimeline([['Única frase.']])))
    const smallCalls = smallReplaceChildren.mock.calls.length + smallAppendChild.mock.calls.length
    expect(smallCalls).toBe(1)

    const largeContainer = document.createElement('div')
    const largeAudio = document.createElement('audio')
    const largeReplaceChildren = vi.spyOn(largeContainer, 'replaceChildren')
    const largeAppendChild = vi.spyOn(largeContainer, 'appendChild')
    createReadingView(largeContainer, largeAudio).open(study(buildManySentenceTimeline(5_000)))
    const largeCalls = largeReplaceChildren.mock.calls.length + largeAppendChild.mock.calls.length
    expect(largeCalls).toBe(1)
    expect(largeCalls).toBe(smallCalls)
    expect(largeContainer.querySelectorAll('.reading-sentence')).toHaveLength(5_000)
  })

  it('clicking a sentence seeks to its start and highlights it immediately, playing or paused, without calling play/pause (FR-007/FR-008)', () => {
    const container = document.createElement('div')
    const audio = document.createElement('audio')
    const play = vi.spyOn(audio, 'play').mockImplementation(() => Promise.resolve())
    const pause = vi.spyOn(audio, 'pause').mockImplementation(() => undefined)
    const timeline = buildTimeline([['Primeira frase.', 'Segunda frase.', 'Terceira frase.']])
    const view = createReadingView(container, audio)
    view.open(study(timeline))
    const buttons = container.querySelectorAll<HTMLButtonElement>('.reading-sentence')

    buttons[1]!.click()
    expect(audio.currentTime).toBe(1)
    expect(container.querySelectorAll('[aria-current="true"]')).toHaveLength(1)
    expect(container.querySelector('[aria-current="true"]')?.textContent).toBe('Segunda frase.')

    audio.dispatchEvent(new Event('play'))
    buttons[2]!.click()
    expect(audio.currentTime).toBe(2)
    expect(container.querySelector('[aria-current="true"]')?.textContent).toBe('Terceira frase.')

    expect(play).not.toHaveBeenCalled()
    expect(pause).not.toHaveBeenCalled()
  })

  it('resolves a click/native-seek race in favor of whichever is processed last, in either order (FR-007 edge case)', () => {
    const container = document.createElement('div')
    const audio = document.createElement('audio')
    const timeline = buildTimeline([['Frase X.', 'Frase Y.', 'Frase Z.']])
    const view = createReadingView(container, audio)
    view.open(study(timeline))
    const buttons = container.querySelectorAll<HTMLButtonElement>('.reading-sentence')

    audio.currentTime = 0
    audio.dispatchEvent(new Event('timeupdate'))
    expect(container.querySelector('[aria-current="true"]')?.textContent).toBe('Frase X.')

    buttons[1]!.click()
    audio.currentTime = 2
    audio.dispatchEvent(new Event('seeked'))
    expect(container.querySelectorAll('[aria-current="true"]')).toHaveLength(1)
    expect(container.querySelector('[aria-current="true"]')?.textContent).toBe('Frase Z.')

    audio.currentTime = 2
    audio.dispatchEvent(new Event('seeked'))
    buttons[1]!.click()
    expect(container.querySelectorAll('[aria-current="true"]')).toHaveLength(1)
    expect(container.querySelector('[aria-current="true"]')?.textContent).toBe('Frase Y.')
  })

  it('highlights the sentence matching saved progress on open, before any playback event (FR-009)', () => {
    const container = document.createElement('div')
    const audio = document.createElement('audio')
    const timeline = buildTimeline([['Primeira frase.', 'Segunda frase.', 'Terceira frase.']])
    const view = createReadingView(container, audio)

    view.open(study(timeline, { positionSeconds: 1.5 }))

    expect(container.querySelector('[aria-current="true"]')?.textContent).toBe('Segunda frase.')
  })

  it('highlights the last sentence on open when progress is marked completed (FR-009)', () => {
    const container = document.createElement('div')
    const audio = document.createElement('audio')
    const timeline = buildTimeline([['Primeira frase.', 'Segunda frase.', 'Terceira frase.']])
    const view = createReadingView(container, audio)

    view.open(study(timeline, { completed: true, positionSeconds: 0 }))

    expect(container.querySelector('[aria-current="true"]')?.textContent).toBe('Terceira frase.')
  })

  it('highlights the first sentence on open when there is no prior progress (FR-009)', () => {
    const container = document.createElement('div')
    const audio = document.createElement('audio')
    const timeline = buildTimeline([['Primeira frase.', 'Segunda frase.', 'Terceira frase.']])
    const view = createReadingView(container, audio)

    view.open(study(timeline, { positionSeconds: 0, completed: false }))

    expect(container.querySelector('[aria-current="true"]')?.textContent).toBe('Primeira frase.')
  })

  it('keeps the last sentence highlighted when the audio ends, instead of clearing it (FR-010)', () => {
    const container = document.createElement('div')
    const audio = document.createElement('audio')
    const timeline = buildTimeline([['Primeira frase.', 'Segunda frase.', 'Terceira frase.']])
    const view = createReadingView(container, audio)
    view.open(study(timeline))
    audio.currentTime = 0
    audio.dispatchEvent(new Event('timeupdate'))

    audio.dispatchEvent(new Event('ended'))

    expect(container.querySelectorAll('[aria-current="true"]')).toHaveLength(1)
    expect(container.querySelector('[aria-current="true"]')?.textContent).toBe('Terceira frase.')
  })
})
