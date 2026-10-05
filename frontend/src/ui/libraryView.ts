import type { LibraryService, SavedStudyDetail, SavedStudySummary } from '../library/types'
import {
  buildTimelineSrt,
  canShareFiles,
  downloadBlob,
  shareOrDownloadAudio,
  slugifyLabel,
  type BlobUrlPort,
} from './mediaExport'

type LibraryReader = Pick<LibraryService, 'listStudies'>

interface LibraryViewDependencies extends LibraryReader {
  getStudy?: LibraryService['getStudy']
  removeStudy?: LibraryService['removeStudy']
  confirmRemoval?: (study: SavedStudySummary) => boolean
  onOpen?: (studyId: string) => void | Promise<void>
  onRemoved?: (studyId: string) => void
  isPlaying?: (studyId: string) => boolean
  createObjectUrl?: BlobUrlPort['createObjectUrl']
  revokeObjectUrl?: BlobUrlPort['revokeObjectUrl']
}

const PLAY_GLYPH =
  '<svg class="hss-icon" role="img" aria-label="Em reprodução" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>'

export interface LibraryView {
  refresh(): Promise<SavedStudySummary[]>
}

function formatDuration(totalSeconds: number): string {
  const rounded = Math.round(totalSeconds)
  const minutes = Math.floor(rounded / 60)
  const seconds = rounded % 60
  return `${minutes} min ${seconds.toString().padStart(2, '0')} s`
}

function formatDate(timestamp: string): string {
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(timestamp))
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function renderDetails(container: HTMLElement, study: SavedStudyDetail): void {
  container.className = 'study-details'
  container.removeAttribute('role')
  container.replaceChildren()
  const title = document.createElement('h4')
  title.textContent = `Detalhes de ${study.label}`
  const list = document.createElement('dl')
  const fields: Array<readonly [string, string]> = [
    ['Data', formatDate(study.createdAt)],
    ['Duração', formatDuration(study.durationSeconds)],
    ['Tamanho', formatFileSize(study.fileSizeBytes)],
    ['Posição', formatDuration(study.progress.positionSeconds)],
    ['Conclusão', study.progress.completed ? 'Concluído' : 'Em andamento'],
  ]
  for (const [term, value] of fields) {
    const row = document.createElement('div')
    const name = document.createElement('dt')
    const description = document.createElement('dd')
    name.textContent = term
    description.textContent = value
    row.append(name, description)
    list.append(row)
  }
  container.append(title, list)
}

function showRowWarning(item: HTMLLIElement, message: string): void {
  let alert = item.querySelector<HTMLElement>('[data-remove-warning]')
  if (alert === null) {
    alert = document.createElement('p')
    alert.dataset.removeWarning = ''
    alert.role = 'alert'
    item.append(alert)
  }
  alert.textContent = message
}

function createStudyRow(
  study: SavedStudySummary,
  dependencies: LibraryViewDependencies,
  refresh: () => Promise<SavedStudySummary[]>,
): HTMLLIElement {
  const item = document.createElement('li')
  item.className = 'study-row'

  const row = document.createElement('div')
  row.className = 'hss-row'

  const playing = dependencies.isPlaying?.(study.studyId) ?? false
  if (playing) row.classList.add('is-playing')

  const index = document.createElement('span')
  index.className = 'hss-row-index'
  if (playing) {
    index.innerHTML = PLAY_GLYPH
  } else {
    index.setAttribute('aria-hidden', 'true')
  }

  const main = document.createElement('div')
  main.className = 'hss-row-main'

  const text = document.createElement('div')

  const label = document.createElement('h3')
  label.className = 'hss-row-title'
  label.dataset.studyLabel = ''
  label.title = `ID ${study.studyId}`
  label.textContent = study.label

  const date = document.createElement('time')
  date.className = 'hss-row-artist'
  date.dateTime = study.createdAt
  date.textContent = formatDate(study.createdAt)

  text.append(label, date)
  main.append(text)

  const status = document.createElement('span')
  status.className = 'hss-row-album'
  if (study.progress.completed) status.textContent = 'Concluído'

  const duration = document.createElement('span')
  duration.className = 'hss-row-time'
  duration.textContent = formatDuration(study.durationSeconds)

  row.append(index, main, status, duration)

  const actions = document.createElement('div')
  actions.className = 'row-actions'
  if (dependencies.getStudy !== undefined) {
    const details = document.createElement('button')
    details.type = 'button'
    details.className = 'hss-btn hss-btn-tertiary hss-btn-sm'
    details.dataset.showStudyDetails = study.studyId
    details.textContent = 'Detalhes'
    details.addEventListener('click', () => {
      let panel = item.querySelector<HTMLElement>('[data-study-details]')
      if (panel === null) {
        panel = document.createElement('section')
        panel.dataset.studyDetails = study.studyId
        item.append(panel)
      }
      panel.className = 'study-details'
      panel.removeAttribute('role')
      panel.textContent = 'Consultando detalhes…'
      details.disabled = true
      void (async () => {
        try {
          const detail = await dependencies.getStudy?.(study.studyId)
          if (detail === undefined) {
            panel!.textContent = 'Este estudo não está mais disponível na biblioteca local.'
            return
          }
          renderDetails(panel!, detail)
        } catch {
          panel!.role = 'alert'
          panel!.textContent =
            'Não foi possível consultar os detalhes. Verifique o armazenamento local e tente novamente.'
        } finally {
          details.disabled = false
        }
      })()
    })
    actions.append(details)
  }
  if (dependencies.onOpen !== undefined) {
    const open = document.createElement('button')
    open.type = 'button'
    open.className = 'hss-btn hss-btn-tertiary hss-btn-sm'
    open.dataset.openStudy = study.studyId
    open.textContent = 'Ouvir'
    open.addEventListener('click', () => void dependencies.onOpen?.(study.studyId))
    actions.append(open)
  }
  if (dependencies.getStudy !== undefined) {
    const urls: BlobUrlPort = {
      createObjectUrl: dependencies.createObjectUrl ?? ((blob) => URL.createObjectURL(blob)),
      revokeObjectUrl: dependencies.revokeObjectUrl ?? ((url) => URL.revokeObjectURL(url)),
    }

    const withDetail = async (
      button: HTMLButtonElement,
      action: (detail: SavedStudyDetail) => void | Promise<void>,
    ): Promise<void> => {
      button.disabled = true
      try {
        const detail = await dependencies.getStudy?.(study.studyId)
        if (detail === undefined) {
          showRowWarning(item, 'Este estudo não está mais disponível na biblioteca local.')
          return
        }
        await action(detail)
      } catch {
        showRowWarning(
          item,
          'Não foi possível preparar este arquivo. Verifique o armazenamento local e tente novamente.',
        )
      } finally {
        button.disabled = false
      }
    }

    const download = document.createElement('button')
    download.type = 'button'
    download.className = 'hss-btn hss-btn-tertiary hss-btn-sm'
    download.dataset.downloadStudy = study.studyId
    download.textContent = 'Baixar MP3'
    download.addEventListener('click', () => {
      void withDetail(download, (detail) => {
        downloadBlob(detail.audio, `${slugifyLabel(detail.label)}.mp3`, urls)
      })
    })
    actions.append(download)

    if (canShareFiles()) {
      const share = document.createElement('button')
      share.type = 'button'
      share.className = 'hss-btn hss-btn-tertiary hss-btn-sm'
      share.dataset.shareStudy = study.studyId
      share.textContent = 'Salvar no celular'
      share.addEventListener('click', () => {
        void withDetail(share, (detail) =>
          shareOrDownloadAudio(detail.audio, `${slugifyLabel(detail.label)}.mp3`, detail.label, urls),
        )
      })
      actions.append(share)
    }

    const downloadText = document.createElement('button')
    downloadText.type = 'button'
    downloadText.className = 'hss-btn hss-btn-tertiary hss-btn-sm'
    downloadText.dataset.downloadStudyText = study.studyId
    downloadText.textContent = 'Baixar texto'
    downloadText.addEventListener('click', () => {
      void withDetail(downloadText, (detail) => {
        const srt = buildTimelineSrt(detail.timeline)
        if (srt === undefined) {
          showRowWarning(item, 'Este estudo não tem texto sincronizado disponível.')
          return
        }
        downloadBlob(
          new Blob([srt], { type: 'text/plain' }),
          `${slugifyLabel(detail.label)}.srt`,
          urls,
        )
      })
    })
    actions.append(downloadText)
  }
  if (dependencies.removeStudy !== undefined) {
    const remove = document.createElement('button')
    remove.type = 'button'
    remove.className = 'hss-btn hss-btn-tertiary hss-btn-sm'
    remove.dataset.removeStudy = study.studyId
    remove.textContent = 'Remover'
    remove.addEventListener('click', () => {
      const confirmed =
        dependencies.confirmRemoval?.(study) ??
        window.confirm(`Remover “${study.label}” deste navegador?`)
      if (!confirmed) return
      void (async () => {
        remove.disabled = true
        try {
          await dependencies.removeStudy?.(study.studyId)
          dependencies.onRemoved?.(study.studyId)
          await refresh()
        } catch {
          remove.disabled = false
          showRowWarning(
            item,
            'Não foi possível remover este estudo. Verifique o armazenamento local e tente novamente.',
          )
        }
      })()
    })
    actions.append(remove)
  }
  item.append(row)
  if (actions.childElementCount > 0) item.append(actions)
  return item
}

export function createLibraryView(
  container: HTMLElement,
  library: LibraryViewDependencies,
): LibraryView {
  container.classList.add('archive', 'hss-panel')
  container.innerHTML = `
    <header class="archive-header">
      <h2 class="archive-title">Arquivo local</h2>
      <span class="archive-count" data-library-count>—</span>
    </header>
    <div data-library-content></div>
  `
  const count = container.querySelector<HTMLElement>('[data-library-count]')!
  const content = container.querySelector<HTMLElement>('[data-library-content]')!

  const view: LibraryView = {
    async refresh(): Promise<SavedStudySummary[]> {
      content.replaceChildren()
      const loading = document.createElement('p')
      loading.className = 'library-state'
      loading.textContent = 'Consultando o arquivo local…'
      content.append(loading)

      try {
        const studies = await library.listStudies()
        count.textContent = `${studies.length} ${studies.length === 1 ? 'estudo' : 'estudos'}`
        content.replaceChildren()
        if (studies.length === 0) {
          const empty = document.createElement('p')
          empty.className = 'library-state'
          empty.textContent =
            'Nenhum estudo arquivado ainda. O próximo áudio gerado aparece aqui automaticamente.'
          content.append(empty)
          return studies
        }

        const list = document.createElement('ol')
        list.className = 'library-list'
        studies.forEach((study) => list.append(createStudyRow(study, library, view.refresh)))
        content.append(list)
        return studies
      } catch {
        count.textContent = 'indisponível'
        content.replaceChildren()
        const alert = document.createElement('p')
        alert.className = 'library-state'
        alert.role = 'alert'
        alert.textContent =
          'Não foi possível abrir sua biblioteca local. Verifique o armazenamento do navegador e tente novamente.'
        content.append(alert)
        return []
      }
    },
  }
  return view
}
