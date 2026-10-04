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

interface AppDependencies {
  createStudy(input: StudyCreateInput): Promise<CreateStudyOutcome>
  listStudies(): Promise<SavedStudySummary[]>
  createObjectUrl(blob: Blob): string
  revokeObjectUrl?(url: string): void
}

function defaultDependencies(): AppDependencies {
  const client = createStudiesClient()
  const library = createLibraryService()
  return {
    createStudy: (input) => createAndSaveStudy(input, { client, library }),
    listStudies: () => library.listStudies(),
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

  const libraryContainer = root.querySelector<HTMLElement>('[data-library]')!
  const libraryView = createLibraryView(libraryContainer, {
    listStudies: dependencies.listStudies,
  })
  await libraryView.refresh()

  const form = root.querySelector<HTMLFormElement>('form')!
  const textField = root.querySelector<HTMLTextAreaElement>('[name="text"]')!
  const labelField = root.querySelector<HTMLInputElement>('[name="label"]')!
  const submitButton = root.querySelector<HTMLButtonElement>('button[type="submit"]')!
  const status = root.querySelector<HTMLElement>('[role="status"]')!
  const nowPlaying = root.querySelector<HTMLElement>('[data-now-playing]')!
  const nowPlayingTitle = root.querySelector<HTMLElement>('#now-playing-title')!
  const audio = root.querySelector<HTMLAudioElement>('audio')!
  let activeObjectUrl: string | undefined

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
        if (activeObjectUrl !== undefined) {
          dependencies.revokeObjectUrl?.(activeObjectUrl)
        }
        activeObjectUrl = dependencies.createObjectUrl(outcome.result.audio)
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
