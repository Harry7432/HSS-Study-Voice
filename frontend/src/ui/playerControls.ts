export interface PlaybackRateStorage {
  getRate(): number | undefined
  setRate(rate: number): void
}

const RATE_STORAGE_KEY = 'hss-study-playback-rate'
const MIN_RATE = 0.5
const MAX_RATE = 2
const SEEK_STEP_SECONDS = 10
const KEYBOARD_SEEK_STEP_SECONDS = 5
const SPEED_PRESETS = [0.75, 1, 1.25, 1.5, 2] as const

function isValidRate(value: number): boolean {
  return Number.isFinite(value) && value >= MIN_RATE && value <= MAX_RATE
}

export function createLocalStoragePlaybackRateStorage(storage: Storage): PlaybackRateStorage {
  return {
    getRate(): number | undefined {
      try {
        const value = Number(storage.getItem(RATE_STORAGE_KEY))
        return isValidRate(value) ? value : undefined
      } catch {
        return undefined
      }
    },
    setRate(rate: number): void {
      try {
        storage.setItem(RATE_STORAGE_KEY, String(rate))
      } catch {
        // localStorage indisponível (modo privado, cota excedida): a velocidade
        // ainda se aplica nesta sessão, só não é lembrada na próxima visita.
      }
    },
  }
}

interface WebkitPitchControl {
  webkitPreservesPitch?: boolean
}

function applyPreservesPitch(audio: HTMLAudioElement): void {
  audio.preservesPitch = true
  ;(audio as HTMLAudioElement & WebkitPitchControl).webkitPreservesPitch = true
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max)
}

function formatTime(totalSeconds: number): string {
  if (!Number.isFinite(totalSeconds) || totalSeconds < 0) return '0:00'
  const rounded = Math.floor(totalSeconds)
  const minutes = Math.floor(rounded / 60)
  const seconds = rounded % 60
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

function formatSpeedLabel(rate: number): string {
  return `${rate.toFixed(2).replace(/\.?0+$/, '')}x`
}

function isTypingInFocusedField(): boolean {
  const active = document.activeElement
  if (!(active instanceof HTMLElement)) return false
  if (active.isContentEditable) return true
  const tag = active.tagName
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT'
}

const PLAY_GLYPH =
  '<svg class="hss-icon hss-icon-24" aria-hidden="true" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>'
const PAUSE_GLYPH =
  '<svg class="hss-icon hss-icon-24" aria-hidden="true" viewBox="0 0 24 24"><path d="M7 5h4v14H7zM13 5h4v14h-4z"/></svg>'
const PREVIOUS_GLYPH =
  '<svg class="hss-icon" aria-hidden="true" viewBox="0 0 24 24"><path d="M18 5v14l-9-7zM8 5H6v14h2z"/></svg>'
const NEXT_GLYPH =
  '<svg class="hss-icon" aria-hidden="true" viewBox="0 0 24 24"><path d="M6 5v14l9-7zM16 5h2v14h-2z"/></svg>'
const BACK_10_GLYPH =
  '<svg class="hss-icon" aria-hidden="true" viewBox="0 0 24 24"><path d="M12 5V1L6 6l6 5V7a6 6 0 1 1-6 6H4a8 8 0 1 0 8-8z"/><text x="12" y="16.5" font-size="7" font-family="var(--font-sans)" text-anchor="middle">10</text></svg>'
const FORWARD_10_GLYPH =
  '<svg class="hss-icon" aria-hidden="true" viewBox="0 0 24 24"><path d="M12 5V1l6 5-6 5V7a6 6 0 1 0 6 6h2a8 8 0 1 1-8-8z"/><text x="12" y="16.5" font-size="7" font-family="var(--font-sans)" text-anchor="middle">10</text></svg>'

export interface PlayerControlsDependencies {
  rateStorage?: PlaybackRateStorage
  onPrevious?: () => void | Promise<void>
  onNext?: () => void | Promise<void>
  hasPrevious?: () => boolean
  hasNext?: () => boolean
}

export interface PlayerControls {
  syncNavigation(): void
}

export function createPlayerControls(
  container: HTMLElement,
  audio: HTMLAudioElement,
  dependencies: PlayerControlsDependencies = {},
): PlayerControls {
  const rateStorage =
    dependencies.rateStorage ?? createLocalStoragePlaybackRateStorage(window.localStorage)
  const hasPrevious = dependencies.hasPrevious ?? (() => false)
  const hasNext = dependencies.hasNext ?? (() => false)

  container.className = 'hss-player player-controls'
  container.innerHTML = `
    <div class="player-controls-transport hss-player-controls">
      <button type="button" class="hss-iconbtn hss-iconbtn-ghost" data-player-previous aria-label="Estudo anterior">${PREVIOUS_GLYPH}</button>
      <button type="button" class="hss-iconbtn hss-iconbtn-ghost" data-player-back aria-label="Voltar 10 segundos">${BACK_10_GLYPH}</button>
      <button type="button" class="hss-iconbtn hss-iconbtn-play" data-player-toggle aria-label="Reproduzir">${PLAY_GLYPH}</button>
      <button type="button" class="hss-iconbtn hss-iconbtn-ghost" data-player-forward aria-label="Avançar 10 segundos">${FORWARD_10_GLYPH}</button>
      <button type="button" class="hss-iconbtn hss-iconbtn-ghost" data-player-next aria-label="Próximo estudo">${NEXT_GLYPH}</button>
    </div>
    <div class="hss-player-scrub player-controls-scrub">
      <span data-player-current-time>0:00</span>
      <div class="hss-bar" data-player-track role="progressbar" aria-label="Progresso do áudio" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0" tabindex="0"><span data-player-fill></span></div>
      <span data-player-duration>0:00</span>
    </div>
    <div class="player-controls-speed">
      <span class="player-controls-speed-label" id="player-speed-label">Velocidade</span>
      <div class="player-controls-speed-chips" role="group" aria-labelledby="player-speed-label">
        ${SPEED_PRESETS.map(
          (preset) =>
            `<button type="button" class="hss-chip" data-speed-preset="${preset}" aria-pressed="false">${formatSpeedLabel(preset)}</button>`,
        ).join('')}
      </div>
      <input type="range" class="player-controls-speed-slider" data-speed-slider min="${MIN_RATE}" max="${MAX_RATE}" step="0.05" value="1" aria-label="Ajuste fino da velocidade de reprodução">
      <span class="player-controls-speed-value" data-speed-value>1x</span>
    </div>
  `

  const toggleButton = container.querySelector<HTMLButtonElement>('[data-player-toggle]')!
  const previousButton = container.querySelector<HTMLButtonElement>('[data-player-previous]')!
  const nextButton = container.querySelector<HTMLButtonElement>('[data-player-next]')!
  const backButton = container.querySelector<HTMLButtonElement>('[data-player-back]')!
  const forwardButton = container.querySelector<HTMLButtonElement>('[data-player-forward]')!
  const track = container.querySelector<HTMLElement>('[data-player-track]')!
  const fill = container.querySelector<HTMLElement>('[data-player-fill]')!
  const currentTimeLabel = container.querySelector<HTMLElement>('[data-player-current-time]')!
  const durationLabel = container.querySelector<HTMLElement>('[data-player-duration]')!
  const speedChips = Array.from(
    container.querySelectorAll<HTMLButtonElement>('[data-speed-preset]'),
  )
  const speedSlider = container.querySelector<HTMLInputElement>('[data-speed-slider]')!
  const speedValueLabel = container.querySelector<HTMLElement>('[data-speed-value]')!

  const seekBy = (deltaSeconds: number): void => {
    const duration = Number.isFinite(audio.duration) ? audio.duration : 0
    audio.currentTime = clamp(audio.currentTime + deltaSeconds, 0, duration)
  }

  const togglePlay = (): void => {
    if (audio.paused) {
      void audio.play()
    } else {
      audio.pause()
    }
  }

  const renderToggleButton = (): void => {
    const playing = !audio.paused
    toggleButton.innerHTML = playing ? PAUSE_GLYPH : PLAY_GLYPH
    toggleButton.setAttribute('aria-label', playing ? 'Pausar' : 'Reproduzir')
  }

  const renderProgress = (): void => {
    const duration = Number.isFinite(audio.duration) ? audio.duration : 0
    const ratio = duration > 0 ? clamp(audio.currentTime / duration, 0, 1) : 0
    fill.style.width = `${ratio * 100}%`
    track.setAttribute('aria-valuenow', String(Math.round(ratio * 100)))
    currentTimeLabel.textContent = formatTime(audio.currentTime)
    durationLabel.textContent = formatTime(duration)
  }

  const applyRate = (rate: number): void => {
    audio.playbackRate = rate
    applyPreservesPitch(audio)
    speedChips.forEach((chip) => {
      chip.setAttribute('aria-pressed', String(Number(chip.dataset.speedPreset) === rate))
    })
    speedSlider.value = String(rate)
    speedValueLabel.textContent = formatSpeedLabel(rate)
  }

  const setRate = (rawRate: number): void => {
    const rate = clamp(rawRate, MIN_RATE, MAX_RATE)
    applyRate(rate)
    rateStorage.setRate(rate)
  }

  toggleButton.addEventListener('click', togglePlay)
  backButton.addEventListener('click', () => seekBy(-SEEK_STEP_SECONDS))
  forwardButton.addEventListener('click', () => seekBy(SEEK_STEP_SECONDS))
  previousButton.addEventListener('click', () => void dependencies.onPrevious?.())
  nextButton.addEventListener('click', () => void dependencies.onNext?.())

  const seekFromPointer = (clientX: number): void => {
    const duration = Number.isFinite(audio.duration) ? audio.duration : 0
    if (duration <= 0) return
    const rect = track.getBoundingClientRect()
    const ratio = rect.width > 0 ? clamp((clientX - rect.left) / rect.width, 0, 1) : 0
    audio.currentTime = ratio * duration
  }

  track.addEventListener('click', (event) => seekFromPointer(event.clientX))

  speedChips.forEach((chip) => {
    chip.addEventListener('click', () => setRate(Number(chip.dataset.speedPreset)))
  })
  speedSlider.addEventListener('input', () => setRate(Number(speedSlider.value)))

  audio.addEventListener('play', renderToggleButton)
  audio.addEventListener('pause', renderToggleButton)
  audio.addEventListener('timeupdate', renderProgress)
  audio.addEventListener('ended', renderToggleButton)
  audio.addEventListener('loadedmetadata', () => {
    renderProgress()
    applyRate(rateStorage.getRate() ?? audio.playbackRate ?? 1)
  })

  document.addEventListener('keydown', (event) => {
    // Guards against a stale listener outliving an unmounted/replaced player: production
    // only ever mounts one player per app lifetime, but tests create many in isolation.
    if (!container.isConnected) return
    if (isTypingInFocusedField()) return
    if (audio.getAttribute('src') === null) return
    if (event.code === 'Space') {
      event.preventDefault()
      togglePlay()
    } else if (event.code === 'ArrowRight') {
      event.preventDefault()
      seekBy(KEYBOARD_SEEK_STEP_SECONDS)
    } else if (event.code === 'ArrowLeft') {
      event.preventDefault()
      seekBy(-KEYBOARD_SEEK_STEP_SECONDS)
    }
  })

  applyRate(rateStorage.getRate() ?? 1)
  renderToggleButton()
  renderProgress()

  const syncNavigation = (): void => {
    previousButton.disabled = !hasPrevious()
    nextButton.disabled = !hasNext()
  }
  syncNavigation()

  return { syncNavigation }
}
