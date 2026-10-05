import './styles.css'

import { createAndSaveStudy } from './application/createStudy'
import { createStudiesClient } from './api/studiesClient'
import { createLibraryService } from './library/libraryService'
import type {
  CreateStudyOutcome,
  LibraryService,
  SavedStudySummary,
  StudyCreateInput,
  TimelineDocument,
} from './library/types'
import { getConnectivityStatus } from './platform/connectivity'
import { createConnectivityIndicator } from './ui/connectivityIndicator'
import { createLibraryView } from './ui/libraryView'
import { buildTimelineSrt, canShareFiles, downloadBlob, shareOrDownloadAudio, slugifyLabel } from './ui/mediaExport'
import { createLocalPlayer } from './ui/player'
import { createPlayerControls } from './ui/playerControls'
import { createReadingView } from './ui/readingView'
import { initThemeToggle } from './ui/theme'
import { createUpdateNotice } from './ui/updateNotice'

interface AppDependencies {
  createStudy(input: StudyCreateInput): Promise<CreateStudyOutcome>
  listStudies(): Promise<SavedStudySummary[]>
  getStudy?: LibraryService['getStudy']
  updateProgress?: LibraryService['updateProgress']
  removeStudy?: LibraryService['removeStudy']
  createObjectUrl(blob: Blob): string
  revokeObjectUrl?(url: string): void
  confirmRemoval?: (study: SavedStudySummary) => boolean
}

function defaultDependencies(): AppDependencies {
  const client = createStudiesClient()
  const library = createLibraryService()
  return {
    createStudy: (input) => createAndSaveStudy(input, { client, library }),
    listStudies: () => library.listStudies(),
    getStudy: (studyId) => library.getStudy(studyId),
    updateProgress: (studyId, update) => library.updateProgress(studyId, update),
    removeStudy: (studyId) => library.removeStudy(studyId),
    createObjectUrl: (blob) => URL.createObjectURL(blob),
    revokeObjectUrl: (url) => URL.revokeObjectURL(url),
  }
}

const VOICE_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
  { value: 'pt_BR-cadu-medium', label: 'Cadu' },
  { value: 'pt_BR-faber-medium', label: 'Faber' },
  { value: 'pt_BR-jeff-medium', label: 'Jeff' },
  { value: 'pt_BR-edresson-low', label: 'Edresson' },
]

const GENERATION_SPEED_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
  { value: '0.75', label: '0,75x' },
  { value: '1.25', label: '1,25x' },
  { value: '1.5', label: '1,5x' },
  { value: '2', label: '2x' },
]

function renderChipGroup(options: ReadonlyArray<{ value: string; label: string }>): string {
  return [
    '<button type="button" class="hss-chip" data-chip-value="" aria-pressed="true">Automático</button>',
    ...options.map(
      ({ value, label }) =>
        `<button type="button" class="hss-chip" data-chip-value="${value}" aria-pressed="false">${label}</button>`,
    ),
  ].join('')
}

function wireSingleSelectChips(
  group: HTMLElement,
  onSelect: (value: string | undefined) => void,
): void {
  const chips = Array.from(group.querySelectorAll<HTMLButtonElement>('[data-chip-value]'))
  chips.forEach((chip) => {
    chip.addEventListener('click', () => {
      chips.forEach((other) => other.setAttribute('aria-pressed', String(other === chip)))
      const raw = chip.dataset.chipValue
      onSelect(raw === undefined || raw === '' ? undefined : raw)
    })
  })
}

export async function mountApp(
  root: HTMLElement,
  dependencies: AppDependencies = defaultDependencies(),
): Promise<void> {
  root.innerHTML = `
    <main class="shell">
      <header class="masthead">
        <div class="masthead-heading">
          <button class="hss-iconbtn hss-iconbtn-ghost" type="button" data-theme-toggle></button>
          <h1 class="masthead-title">HSS Study Voice</h1>
          <div data-connectivity-indicator></div>
        </div>
        <p class="masthead-note">Seu áudio fica no navegador. O servidor só entra em cena para produzir uma nova faixa.</p>
      </header>
      <div data-update-notice></div>
      <div class="workspace">
        <section class="desk hss-panel" aria-labelledby="production-title">
          <h2 class="desk-title" id="production-title">Prepare o próximo estudo</h2>
          <p class="desk-intro">Cole seu material. Nós removemos a marcação, produzimos o áudio sincronizado e arquivamos a cópia neste dispositivo.</p>
          <form class="study-form">
            <div class="field">
              <label class="field-label" for="study-text">Texto do estudo</label>
              <textarea class="field-input" id="study-text" name="text" required placeholder="Cole aqui o conteúdo que você quer ouvir…"></textarea>
            </div>
            <div class="field">
              <label class="field-label" for="study-label">Rótulo opcional</label>
              <input class="field-input" id="study-label" name="label" maxlength="80" placeholder="Ex.: Revisão de biologia celular">
            </div>
            <div class="field">
              <span class="field-label" id="voice-field-label">Voz</span>
              <div class="chip-group" role="group" aria-labelledby="voice-field-label" data-voice-group>${renderChipGroup(VOICE_OPTIONS)}</div>
            </div>
            <div class="field">
              <span class="field-label" id="generation-speed-field-label">Velocidade da narração</span>
              <div class="chip-group" role="group" aria-labelledby="generation-speed-field-label" data-generation-speed-group>${renderChipGroup(GENERATION_SPEED_OPTIONS)}</div>
            </div>
            <div class="form-actions">
              <button class="hss-btn hss-btn-primary" type="submit">Gerar estudo em áudio</button>
              <p class="status-line" role="status" aria-live="polite">Pronto para receber seu texto.</p>
            </div>
          </form>
          <section class="now-playing" data-now-playing aria-labelledby="now-playing-title">
            <span class="now-playing-label">No ar agora</span>
            <h3 class="now-playing-title" id="now-playing-title">Estudo gerado</h3>
            <audio preload="metadata" hidden></audio>
            <div class="player-frame" data-player-controls></div>
            <div class="now-playing-actions">
              <button class="hss-btn hss-btn-tertiary hss-btn-sm" type="button" data-download-audio>Baixar MP3</button>
              <button class="hss-btn hss-btn-tertiary hss-btn-sm" type="button" data-share-audio hidden>Salvar no celular</button>
              <button class="hss-btn hss-btn-tertiary hss-btn-sm" type="button" data-download-text>Baixar texto</button>
            </div>
            <section class="reading-frame" data-reading-view aria-label="Texto sincronizado"></section>
          </section>
        </section>
        <section data-library aria-label="Biblioteca local"></section>
      </div>
    </main>
  `

  const themeToggleButton = root.querySelector<HTMLButtonElement>('[data-theme-toggle]')!
  initThemeToggle(themeToggleButton)
  createConnectivityIndicator(root.querySelector<HTMLElement>('[data-connectivity-indicator]')!)
  createUpdateNotice(root.querySelector<HTMLElement>('[data-update-notice]')!)

  const form = root.querySelector<HTMLFormElement>('form')!
  const textField = root.querySelector<HTMLTextAreaElement>('[name="text"]')!
  const labelField = root.querySelector<HTMLInputElement>('[name="label"]')!
  const submitButton = root.querySelector<HTMLButtonElement>('button[type="submit"]')!
  const status = root.querySelector<HTMLElement>('.status-line')!
  const nowPlaying = root.querySelector<HTMLElement>('[data-now-playing]')!
  const nowPlayingTitle = root.querySelector<HTMLElement>('#now-playing-title')!
  const audio = root.querySelector<HTMLAudioElement>('audio')!
  const playerControlsContainer = root.querySelector<HTMLElement>('[data-player-controls]')!
  const downloadAudioButton = root.querySelector<HTMLButtonElement>('[data-download-audio]')!
  const shareAudioButton = root.querySelector<HTMLButtonElement>('[data-share-audio]')!
  const downloadTextButton = root.querySelector<HTMLButtonElement>('[data-download-text]')!
  shareAudioButton.hidden = !canShareFiles()

  let selectedVoice: string | undefined
  let selectedGenerationSpeed: string | undefined
  wireSingleSelectChips(root.querySelector<HTMLElement>('[data-voice-group]')!, (value) => {
    selectedVoice = value
  })
  wireSingleSelectChips(
    root.querySelector<HTMLElement>('[data-generation-speed-group]')!,
    (value) => {
      selectedGenerationSpeed = value
    },
  )

  const blobUrls = {
    createObjectUrl: dependencies.createObjectUrl,
    revokeObjectUrl: dependencies.revokeObjectUrl ?? (() => undefined),
  }
  let currentAudio: { blob: Blob; label: string; timeline: TimelineDocument } | undefined
  downloadAudioButton.addEventListener('click', () => {
    if (currentAudio === undefined) return
    downloadBlob(currentAudio.blob, `${slugifyLabel(currentAudio.label)}.mp3`, blobUrls)
  })
  shareAudioButton.addEventListener('click', () => {
    if (currentAudio === undefined) return
    void shareOrDownloadAudio(
      currentAudio.blob,
      `${slugifyLabel(currentAudio.label)}.mp3`,
      currentAudio.label,
      blobUrls,
    )
  })
  downloadTextButton.addEventListener('click', () => {
    if (currentAudio === undefined) return
    const srt = buildTimelineSrt(currentAudio.timeline)
    if (srt === undefined) {
      status.dataset.kind = 'error'
      status.textContent = 'Este estudo não tem texto sincronizado disponível.'
      return
    }
    downloadBlob(new Blob([srt], { type: 'text/plain' }), `${slugifyLabel(currentAudio.label)}.srt`, blobUrls)
  })

  let activeObjectUrl: string | undefined
  let generatedStudyId: string | undefined
  let activeStudyId: string | undefined
  let libraryOrder: SavedStudySummary[] = []
  const libraryContainer = root.querySelector<HTMLElement>('[data-library]')!
  let libraryView: ReturnType<typeof createLibraryView>
  let playerControls: ReturnType<typeof createPlayerControls>

  const refreshLibrary = async (): Promise<SavedStudySummary[]> => {
    libraryOrder = await libraryView.refresh()
    playerControls.syncNavigation()
    return libraryOrder
  }

  // "Próxima" walks forward through the archive's newest-first order (ui/libraryView.ts
  // displays the same order listStudies() returns), "Anterior" walks backward.
  const neighborStudyId = (direction: 1 | -1): string | undefined => {
    if (activeStudyId === undefined) return undefined
    const index = libraryOrder.findIndex((study) => study.studyId === activeStudyId)
    if (index === -1) return undefined
    return libraryOrder[index + direction]?.studyId
  }

  const openStudy = dependencies.getStudy

  const player = createLocalPlayer(audio, {
    updateProgress: dependencies.updateProgress ?? (async () => undefined),
    createObjectUrl: dependencies.createObjectUrl,
    revokeObjectUrl: dependencies.revokeObjectUrl ?? (() => undefined),
    onPlaying: async () => {
      await refreshLibrary()
    },
    onPaused: async () => {
      await refreshLibrary()
    },
    onCompleted: async () => {
      await refreshLibrary()
    },
    onWarning: (message) => {
      status.dataset.kind = 'error'
      status.textContent = message
    },
  })
  // readingView must be created *after* player above: player's own loadedmetadata handler
  // corrects audio.currentTime to the saved position, and readingView's loadedmetadata
  // re-sync relies on that already-corrected value (research.md, Decisão 7). addEventListener
  // fires in registration order for the same event/target, so this ordering is load-bearing.
  const readingView = createReadingView(
    root.querySelector<HTMLElement>('[data-reading-view]')!,
    audio,
  )

  const openStudyById = async (studyId: string): Promise<void> => {
    if (openStudy === undefined) return
    try {
      const study = await openStudy(studyId)
      if (study === undefined) {
        status.dataset.kind = 'error'
        status.textContent = 'Este estudo não está mais disponível na biblioteca local.'
        activeStudyId = undefined
        await refreshLibrary()
        return
      }
      if (activeObjectUrl !== undefined) {
        dependencies.revokeObjectUrl?.(activeObjectUrl)
        activeObjectUrl = undefined
        generatedStudyId = undefined
      }
      player.open(study)
      readingView.open(study)
      currentAudio = { blob: study.audio, label: study.label, timeline: study.timeline }
      activeStudyId = studyId
      nowPlayingTitle.textContent = study.label
      nowPlaying.classList.add('is-visible')
      status.dataset.kind = 'success'
      status.textContent = 'Reproduzindo a cópia salva neste navegador.'
      await refreshLibrary()
    } catch {
      status.dataset.kind = 'error'
      status.textContent = 'Não foi possível abrir este estudo na biblioteca local.'
    }
  }

  playerControls = createPlayerControls(playerControlsContainer, audio, {
    onPrevious: () => {
      const previousId = neighborStudyId(-1)
      if (previousId !== undefined) void openStudyById(previousId)
    },
    onNext: () => {
      const nextId = neighborStudyId(1)
      if (nextId !== undefined) void openStudyById(nextId)
    },
    hasPrevious: () => neighborStudyId(-1) !== undefined,
    hasNext: () => neighborStudyId(1) !== undefined,
  })

  libraryView = createLibraryView(libraryContainer, {
    listStudies: dependencies.listStudies,
    isPlaying: (studyId) => player.isOpen(studyId) && player.isPlaying(),
    createObjectUrl: dependencies.createObjectUrl,
    ...(dependencies.revokeObjectUrl === undefined
      ? {}
      : { revokeObjectUrl: dependencies.revokeObjectUrl }),
    ...(dependencies.removeStudy === undefined
      ? {}
      : { removeStudy: dependencies.removeStudy }),
    ...(dependencies.confirmRemoval === undefined
      ? {}
      : { confirmRemoval: dependencies.confirmRemoval }),
    ...(openStudy === undefined ? {} : { getStudy: openStudy, onOpen: openStudyById }),
    onRemoved: (studyId) => {
      libraryOrder = libraryOrder.filter((study) => study.studyId !== studyId)
      if (player.isOpen(studyId)) {
        player.discard()
        readingView.discard()
        currentAudio = undefined
        activeStudyId = undefined
      }
      if (generatedStudyId === studyId && activeObjectUrl !== undefined) {
        dependencies.revokeObjectUrl?.(activeObjectUrl)
        activeObjectUrl = undefined
        generatedStudyId = undefined
        audio.removeAttribute('src')
      }
      playerControls.syncNavigation()
    },
  })
  await refreshLibrary()

  form.addEventListener('submit', (event) => {
    event.preventDefault()
    void (async () => {
      if (!getConnectivityStatus().online) {
        status.dataset.kind = 'error'
        status.textContent = 'Você está offline. Conecte-se à internet para gerar um novo estudo.'
        return
      }
      submitButton.disabled = true
      submitButton.textContent = 'Produzindo áudio…'
      status.dataset.kind = 'progress'
      status.textContent = 'Processando texto, voz e timeline.'

      try {
        const label = labelField.value.trim()
        const input: StudyCreateInput = {
          text: textField.value,
          ...(label.length > 0 ? { label } : {}),
          ...(selectedVoice === undefined ? {} : { voice: selectedVoice }),
          ...(selectedGenerationSpeed === undefined
            ? {}
            : { speed: Number(selectedGenerationSpeed) }),
        }
        const outcome = await dependencies.createStudy(input)
        player.discard()
        if (activeObjectUrl !== undefined) {
          dependencies.revokeObjectUrl?.(activeObjectUrl)
        }
        activeObjectUrl = dependencies.createObjectUrl(outcome.result.audio)
        generatedStudyId = outcome.saved ? outcome.result.studyId : undefined
        activeStudyId = generatedStudyId
        audio.src = activeObjectUrl
        currentAudio = {
          blob: outcome.result.audio,
          label: outcome.label,
          timeline: outcome.result.timeline,
        }
        readingView.open({
          timeline: outcome.result.timeline,
          progress: { positionSeconds: 0, completed: false },
        })
        nowPlayingTitle.textContent = outcome.label
        nowPlaying.classList.add('is-visible')

        if (outcome.saved) {
          status.dataset.kind = 'success'
          status.textContent = 'Áudio pronto e arquivado neste navegador.'
          await refreshLibrary()
        } else {
          status.dataset.kind = 'error'
          status.textContent = outcome.libraryWarning ?? 'O áudio está pronto, mas não foi arquivado.'
          playerControls.syncNavigation()
        }
      } catch {
        status.dataset.kind = 'error'
        status.textContent = 'Não foi possível gerar o estudo. Verifique o texto e tente novamente.'
      } finally {
        submitButton.disabled = false
        submitButton.textContent = 'Gerar estudo em áudio'
      }
    })()
  })
}

const root = document.querySelector<HTMLElement>('#app')
if (root !== null) {
  void mountApp(root)
}
