import { parseTimeline } from '../api/validators'
import type { Progress, TimelineDocument, TimelineSentence } from '../library/types'
import { findSentenceIndexAtSample, flattenSentences } from '../reading/sentenceLookup'

export interface ReadingViewStudy {
  timeline: TimelineDocument
  progress: Pick<Progress, 'positionSeconds' | 'completed'>
}

export interface ReadingView {
  open(study: ReadingViewStudy): void
  discard(): void
}

const AUTO_SCROLL_WINDOW_MS = 400
// Compensates for real browsers not returning a bit-exact currentTime after a programmatic
// seek (observed ~0.01 sample of quantization noise in Chromium's media pipeline) — without
// this, seeking to a sentence's own start_sample can floor to one sample *before* it, landing
// back in the previous sentence. One sample (~45µs at 22.05kHz) is far below any perceptible
// threshold and stays well short of any real sentence boundary.
const SAMPLE_POSITION_EPSILON = 1
const UNAVAILABLE_MESSAGE =
  'Texto sincronizado não está disponível para este estudo. O áudio continua tocando normalmente.'

export function createReadingView(container: HTMLElement, audio: HTMLAudioElement): ReadingView {
  let sentences: readonly TimelineSentence[] = []
  let elements: HTMLButtonElement[] = []
  let sampleRateHz = 0
  let totalSamples = 0
  let currentIndex: number | undefined
  let available = false
  let autoScrollSuspended = false
  let programmaticScroll = false
  let programmaticScrollTimer: ReturnType<typeof setTimeout> | undefined

  const clearProgrammaticScrollTimer = (): void => {
    if (programmaticScrollTimer !== undefined) {
      clearTimeout(programmaticScrollTimer)
      programmaticScrollTimer = undefined
    }
  }

  const highlight = (index: number): HTMLButtonElement | undefined => {
    if (currentIndex !== undefined) {
      const previous = elements[currentIndex]
      previous?.removeAttribute('aria-current')
      previous?.classList.remove('is-current')
    }
    currentIndex = index
    const next = elements[index]
    next?.setAttribute('aria-current', 'true')
    next?.classList.add('is-current')
    return next
  }

  const scrollToCurrent = (element: HTMLButtonElement | undefined): void => {
    if (element === undefined || autoScrollSuspended) return
    clearProgrammaticScrollTimer()
    programmaticScroll = true
    // Optional call: jsdom (unlike every real browser) does not implement scrollIntoView at
    // all, and frontend/tests/setup.ts is shared by suites that never stub it.
    element.scrollIntoView?.({ block: 'nearest', behavior: 'smooth' })
    programmaticScrollTimer = setTimeout(() => {
      programmaticScroll = false
    }, AUTO_SCROLL_WINDOW_MS)
  }

  const resolveAndHighlight = (samplePosition: number): void => {
    if (!available || sentences.length === 0) return
    const index = findSentenceIndexAtSample(sentences, samplePosition)
    if (index === currentIndex) return
    scrollToCurrent(highlight(index))
  }

  const sampleFromSeconds = (seconds: number): number =>
    Math.max(
      0,
      Math.min(Math.floor(seconds * sampleRateHz + SAMPLE_POSITION_EPSILON), totalSamples),
    )

  const onTimeUpdate = (): void => {
    if (!available) return
    resolveAndHighlight(sampleFromSeconds(audio.currentTime))
  }

  const onSeekedOrPlay = (): void => {
    autoScrollSuspended = false
    onTimeUpdate()
  }

  const onEnded = (): void => {
    if (!available) return
    resolveAndHighlight(totalSamples)
  }

  const onScroll = (): void => {
    if (programmaticScroll) return
    autoScrollSuspended = true
  }

  // `readingView` listeners are registered once here, at creation time, and reused across every
  // open()/discard() cycle — not re-attached per open() — mirroring player.ts's own lifecycle.
  audio.addEventListener('timeupdate', onTimeUpdate)
  audio.addEventListener('seeked', onSeekedOrPlay)
  audio.addEventListener('play', onSeekedOrPlay)
  audio.addEventListener('ended', onEnded)
  // Safety re-sync only (research.md, Decisão 7): open() already computes the initial highlight
  // from study.progress directly, so this just re-reads audio.currentTime in case the browser
  // adjusts it asynchronously between open() and this event.
  audio.addEventListener('loadedmetadata', onTimeUpdate)
  container.addEventListener('scroll', onScroll)

  const renderUnavailable = (): void => {
    const message = document.createElement('p')
    message.className = 'reading-unavailable'
    message.textContent = UNAVAILABLE_MESSAGE
    container.replaceChildren(message)
  }

  const resetState = (): void => {
    clearProgrammaticScrollTimer()
    sentences = []
    elements = []
    sampleRateHz = 0
    totalSamples = 0
    currentIndex = undefined
    available = false
    autoScrollSuspended = false
    programmaticScroll = false
  }

  const discard = (): void => {
    resetState()
    container.replaceChildren()
  }

  return {
    open(study): void {
      // Reset internal state only — the DOM clear is folded into the single replaceChildren()
      // call below (success or failure path), so open() never performs two container mutations.
      resetState()

      let timeline: TimelineDocument
      try {
        timeline = parseTimeline(study.timeline)
      } catch {
        renderUnavailable()
        return
      }

      available = true
      sampleRateHz = timeline.audio.sample_rate_hz
      totalSamples = timeline.audio.total_samples
      sentences = flattenSentences(timeline)

      const fragment = document.createDocumentFragment()
      const nextElements: HTMLButtonElement[] = []
      let sentenceIndex = 0
      timeline.chunks.forEach((chunk) => {
        const chunkElement = document.createElement('div')
        chunkElement.className = 'reading-chunk'
        chunk.sentences.forEach((sentence) => {
          const button = document.createElement('button')
          button.type = 'button'
          button.className = 'reading-sentence'
          button.textContent = sentence.text
          const clickedIndex = sentenceIndex
          // Click always highlights the clicked sentence directly (not derived from
          // audio.currentTime), so it wins deterministically over a concurrent native
          // seek/timeupdate only when processed after it (T009 concurrency case).
          button.addEventListener('click', () => {
            highlight(clickedIndex)
            audio.currentTime = sentence.start_sample / sampleRateHz
          })
          chunkElement.appendChild(button)
          nextElements.push(button)
          sentenceIndex += 1
        })
        fragment.appendChild(chunkElement)
      })
      elements = nextElements
      container.replaceChildren(fragment)

      const initialSamplePosition = study.progress.completed
        ? totalSamples
        : sampleFromSeconds(study.progress.positionSeconds)
      scrollToCurrent(highlight(findSentenceIndexAtSample(sentences, initialSamplePosition)))
    },
    discard,
  }
}
