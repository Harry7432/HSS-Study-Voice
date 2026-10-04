import './styles.css'

import { createAndSaveStudy } from './application/createStudy'
import { createStudiesClient } from './api/studiesClient'
import { createLibraryService } from './library/libraryService'
import type {
  CreateStudyOutcome,
  LibraryService,
  SavedStudySummary,
  StudyCreateInput,
} from './library/types'
import { createLibraryView } from './ui/libraryView'
import { createLocalPlayer } from './ui/player'

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

export async function mountApp(
  root: HTMLElement,
  dependencies: AppDependencies = defaultDependencies(),
): Promise<void> {
  root.innerHTML = `
    <main class="shell">
      <header class="masthead">
        <h1 class="brand">HSS Study Voice</h1>
        <p class="local-note">Seu áudio fica no navegador. O servidor só entra em cena para produzir uma nova faixa.</p>
      </header>
      <div class="workspace">
        <section class="production-sheet" aria-labelledby="production-title">
          <h2 class="section-heading" id="production-title">Prepare o próximo estudo</h2>
          <p class="section-intro">Cole seu material. Nós removemos a marcação, produzimos o áudio sincronizado e arquivamos a cópia neste dispositivo.</p>
          <form class="study-form">
            <div class="field">
              <label for="study-text">Texto do estudo</label>
              <textarea id="study-text" name="text" required placeholder="Cole aqui o conteúdo que você quer ouvir…"></textarea>
            </div>
            <div class="field">
              <label for="study-label">Rótulo opcional</label>
              <input id="study-label" name="label" maxlength="80" placeholder="Ex.: Revisão de biologia celular">
            </div>
            <div class="form-actions">
              <button class="primary-action" type="submit">Gerar estudo em áudio</button>
              <p class="status-line" role="status" aria-live="polite">Pronto para receber seu texto.</p>
            </div>
          </form>
          <section class="now-playing" data-now-playing aria-labelledby="now-playing-title">
            <span class="status-label">No ar agora</span>
            <h3 id="now-playing-title">Estudo gerado</h3>
            <audio controls preload="metadata"></audio>
          </section>
        </section>
        <section data-library aria-label="Biblioteca local"></section>
      </div>
    </main>
  `

  const form = root.querySelector<HTMLFormElement>('form')!
  const textField = root.querySelector<HTMLTextAreaElement>('[name="text"]')!
  const labelField = root.querySelector<HTMLInputElement>('[name="label"]')!
  const submitButton = root.querySelector<HTMLButtonElement>('button[type="submit"]')!
  const status = root.querySelector<HTMLElement>('[role="status"]')!
  const nowPlaying = root.querySelector<HTMLElement>('[data-now-playing]')!
  const nowPlayingTitle = root.querySelector<HTMLElement>('#now-playing-title')!
  const audio = root.querySelector<HTMLAudioElement>('audio')!
  let activeObjectUrl: string | undefined
  let generatedStudyId: string | undefined
  const libraryContainer = root.querySelector<HTMLElement>('[data-library]')!
  let libraryView: ReturnType<typeof createLibraryView>
  const player = createLocalPlayer(audio, {
    updateProgress: dependencies.updateProgress ?? (async () => undefined),
    createObjectUrl: dependencies.createObjectUrl,
    revokeObjectUrl: dependencies.revokeObjectUrl ?? (() => undefined),
    onCompleted: async () => libraryView.refresh(),
    onWarning: (message) => {
      status.dataset.kind = 'error'
      status.textContent = message
    },
  })
  const openStudy = dependencies.getStudy
  libraryView = createLibraryView(libraryContainer, {
    listStudies: dependencies.listStudies,
    ...(dependencies.removeStudy === undefined
      ? {}
      : { removeStudy: dependencies.removeStudy }),
    ...(dependencies.confirmRemoval === undefined
      ? {}
      : { confirmRemoval: dependencies.confirmRemoval }),
    ...(openStudy === undefined
      ? {}
      : {
          getStudy: openStudy,
          onOpen: async (studyId: string) => {
            try {
              const study = await openStudy(studyId)
              if (study === undefined) {
                status.dataset.kind = 'error'
                status.textContent = 'Este estudo não está mais disponível na biblioteca local.'
                await libraryView.refresh()
                return
              }
              if (activeObjectUrl !== undefined) {
                dependencies.revokeObjectUrl?.(activeObjectUrl)
                activeObjectUrl = undefined
                generatedStudyId = undefined
              }
              player.open(study)
              nowPlayingTitle.textContent = study.label
              nowPlaying.classList.add('is-visible')
              status.dataset.kind = 'success'
              status.textContent = 'Reproduzindo a cópia salva neste navegador.'
            } catch {
              status.dataset.kind = 'error'
              status.textContent = 'Não foi possível abrir este estudo na biblioteca local.'
            }
          },
        }),
    onRemoved: (studyId) => {
      if (player.isOpen(studyId)) player.discard()
      if (generatedStudyId === studyId && activeObjectUrl !== undefined) {
        dependencies.revokeObjectUrl?.(activeObjectUrl)
        activeObjectUrl = undefined
        generatedStudyId = undefined
        audio.removeAttribute('src')
      }
    },
  })
  await libraryView.refresh()

  form.addEventListener('submit', (event) => {
    event.preventDefault()
    void (async () => {
      submitButton.disabled = true
      submitButton.textContent = 'Produzindo áudio…'
      status.dataset.kind = 'progress'
      status.textContent = 'Processando texto, voz e timeline.'

      try {
        const label = labelField.value.trim()
        const input: StudyCreateInput = {
          text: textField.value,
          ...(label.length > 0 ? { label } : {}),
        }
        const outcome = await dependencies.createStudy(input)
        player.discard()
        if (activeObjectUrl !== undefined) {
          dependencies.revokeObjectUrl?.(activeObjectUrl)
        }
        activeObjectUrl = dependencies.createObjectUrl(outcome.result.audio)
        generatedStudyId = outcome.saved ? outcome.result.studyId : undefined
        audio.src = activeObjectUrl
        nowPlayingTitle.textContent = outcome.label
        nowPlaying.classList.add('is-visible')

        if (outcome.saved) {
          status.dataset.kind = 'success'
          status.textContent = 'Áudio pronto e arquivado neste navegador.'
          await libraryView.refresh()
        } else {
          status.dataset.kind = 'error'
          status.textContent = outcome.libraryWarning ?? 'O áudio está pronto, mas não foi arquivado.'
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
