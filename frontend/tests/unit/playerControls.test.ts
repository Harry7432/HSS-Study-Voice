import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  createLocalStoragePlaybackRateStorage,
  createPlayerControls,
  type PlaybackRateStorage,
} from '../../src/ui/playerControls'

function mockPlayableAudio(audio: HTMLAudioElement): { setPaused(value: boolean): void } {
  let paused = true
  vi.spyOn(audio, 'paused', 'get').mockImplementation(() => paused)
  vi.spyOn(audio, 'play').mockImplementation(() => {
    paused = false
    return Promise.resolve()
  })
  vi.spyOn(audio, 'pause').mockImplementation(() => {
    paused = true
  })
  return {
    setPaused(value: boolean) {
      paused = value
    },
  }
}

function mockDuration(audio: HTMLAudioElement, seconds: number): void {
  vi.spyOn(audio, 'duration', 'get').mockReturnValue(seconds)
}

function memoryRateStorage(): PlaybackRateStorage {
  let stored: number | undefined
  return {
    getRate: () => stored,
    setRate: (rate) => {
      stored = rate
    },
  }
}

describe('player controls', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('toggles play/pause on click and swaps the icon from the real audio events', () => {
    const container = document.createElement('div')
    const audio = document.createElement('audio')
    audio.setAttribute('src', 'blob:study')
    const playable = mockPlayableAudio(audio)
    createPlayerControls(container, audio, { rateStorage: memoryRateStorage() })

    const toggle = container.querySelector<HTMLButtonElement>('[data-player-toggle]')!
    expect(toggle.getAttribute('aria-label')).toBe('Reproduzir')

    toggle.click()
    expect(audio.play).toHaveBeenCalledOnce()
    audio.dispatchEvent(new Event('play'))
    expect(toggle.getAttribute('aria-label')).toBe('Pausar')

    toggle.click()
    expect(audio.pause).toHaveBeenCalledOnce()
    audio.dispatchEvent(new Event('pause'))
    expect(toggle.getAttribute('aria-label')).toBe('Reproduzir')

    playable.setPaused(true)
    audio.dispatchEvent(new Event('ended'))
    expect(toggle.getAttribute('aria-label')).toBe('Reproduzir')
  })

  it('seeks ±10s from the transport buttons, clamped to [0, duration]', () => {
    const container = document.createElement('div')
    const audio = document.createElement('audio')
    audio.setAttribute('src', 'blob:study')
    mockDuration(audio, 30)
    createPlayerControls(container, audio, { rateStorage: memoryRateStorage() })

    audio.currentTime = 5
    container.querySelector<HTMLButtonElement>('[data-player-back]')!.click()
    expect(audio.currentTime).toBe(0)

    audio.currentTime = 25
    container.querySelector<HTMLButtonElement>('[data-player-forward]')!.click()
    expect(audio.currentTime).toBe(30)
  })

  it('seeks the audio proportionally when the progress track is clicked', () => {
    const container = document.createElement('div')
    const audio = document.createElement('audio')
    audio.setAttribute('src', 'blob:study')
    mockDuration(audio, 200)
    createPlayerControls(container, audio, { rateStorage: memoryRateStorage() })

    const track = container.querySelector<HTMLElement>('[data-player-track]')!
    vi.spyOn(track, 'getBoundingClientRect').mockReturnValue({
      left: 0,
      top: 0,
      right: 100,
      bottom: 0,
      width: 100,
      height: 0,
      x: 0,
      y: 0,
      toJSON: () => undefined,
    })

    track.dispatchEvent(new MouseEvent('click', { clientX: 25 }))
    expect(audio.currentTime).toBe(50)
  })

  it('sets playbackRate and preservesPitch from a speed preset, and persists it', () => {
    const container = document.createElement('div')
    const audio = document.createElement('audio')
    const rateStorage = memoryRateStorage()
    createPlayerControls(container, audio, { rateStorage })

    container.querySelector<HTMLButtonElement>('[data-speed-preset="1.5"]')!.click()

    expect(audio.playbackRate).toBe(1.5)
    expect(audio.preservesPitch).toBe(true)
    expect(rateStorage.getRate()).toBe(1.5)
    expect(
      container.querySelector('[data-speed-preset="1.5"]')!.getAttribute('aria-pressed'),
    ).toBe('true')
    expect(
      container.querySelector('[data-speed-preset="1"]')!.getAttribute('aria-pressed'),
    ).toBe('false')
  })

  it('sets playbackRate from the fine-tune slider', () => {
    const container = document.createElement('div')
    const audio = document.createElement('audio')
    createPlayerControls(container, audio, { rateStorage: memoryRateStorage() })

    const slider = container.querySelector<HTMLInputElement>('[data-speed-slider]')!
    slider.value = '0.8'
    slider.dispatchEvent(new Event('input'))

    expect(audio.playbackRate).toBe(0.8)
  })

  it('reapplies the saved playback rate every time a new track loads', () => {
    const container = document.createElement('div')
    const audio = document.createElement('audio')
    const rateStorage = memoryRateStorage()
    rateStorage.setRate(1.25)
    createPlayerControls(container, audio, { rateStorage })

    audio.playbackRate = 1
    audio.dispatchEvent(new Event('loadedmetadata'))

    expect(audio.playbackRate).toBe(1.25)
  })

  describe('localStorage-backed rate storage', () => {
    it('round-trips a valid rate and ignores a corrupted stored value', () => {
      const memory = new Map<string, string>()
      const storage = {
        getItem: (key: string) => memory.get(key) ?? null,
        setItem: (key: string, value: string) => memory.set(key, value),
      } as unknown as Storage
      const rateStorage = createLocalStoragePlaybackRateStorage(storage)

      rateStorage.setRate(1.5)
      expect(rateStorage.getRate()).toBe(1.5)

      memory.set('hss-study-playback-rate', 'not-a-number')
      expect(rateStorage.getRate()).toBeUndefined()
    })
  })

  describe('keyboard shortcuts', () => {
    beforeEach(() => {
      document.body.innerHTML = ''
    })

    it('Space toggles play/pause and arrows seek ±5s, unless a text field has focus', () => {
      const container = document.createElement('div')
      document.body.append(container)
      const audio = document.createElement('audio')
      audio.setAttribute('src', 'blob:study')
      mockDuration(audio, 60)
      mockPlayableAudio(audio)
      createPlayerControls(container, audio, { rateStorage: memoryRateStorage() })

      audio.currentTime = 10
      document.dispatchEvent(new KeyboardEvent('keydown', { code: 'ArrowRight' }))
      expect(audio.currentTime).toBe(15)

      document.dispatchEvent(new KeyboardEvent('keydown', { code: 'ArrowLeft' }))
      expect(audio.currentTime).toBe(10)

      document.dispatchEvent(new KeyboardEvent('keydown', { code: 'Space' }))
      expect(audio.play).toHaveBeenCalledOnce()

      const textarea = document.createElement('textarea')
      document.body.append(textarea)
      textarea.focus()
      document.dispatchEvent(new KeyboardEvent('keydown', { code: 'ArrowRight' }))
      expect(audio.currentTime).toBe(10)
    })

    it('does nothing when no track is loaded', () => {
      const container = document.createElement('div')
      document.body.append(container)
      const audio = document.createElement('audio')
      mockDuration(audio, 60)
      mockPlayableAudio(audio)
      createPlayerControls(container, audio, { rateStorage: memoryRateStorage() })

      audio.currentTime = 10
      document.dispatchEvent(new KeyboardEvent('keydown', { code: 'ArrowRight' }))
      expect(audio.currentTime).toBe(10)
    })
  })

  describe('previous/next navigation', () => {
    it('invokes the callbacks and disables buttons per hasPrevious/hasNext', () => {
      const container = document.createElement('div')
      const audio = document.createElement('audio')
      const onPrevious = vi.fn()
      const onNext = vi.fn()
      let hasPrevious = false
      let hasNext = true
      const controls = createPlayerControls(container, audio, {
        rateStorage: memoryRateStorage(),
        onPrevious,
        onNext,
        hasPrevious: () => hasPrevious,
        hasNext: () => hasNext,
      })

      const previousButton = container.querySelector<HTMLButtonElement>('[data-player-previous]')!
      const nextButton = container.querySelector<HTMLButtonElement>('[data-player-next]')!
      expect(previousButton.disabled).toBe(true)
      expect(nextButton.disabled).toBe(false)

      nextButton.click()
      expect(onNext).toHaveBeenCalledOnce()

      hasPrevious = true
      hasNext = false
      controls.syncNavigation()
      expect(previousButton.disabled).toBe(false)
      expect(nextButton.disabled).toBe(true)

      previousButton.click()
      expect(onPrevious).toHaveBeenCalledOnce()
    })
  })
})
