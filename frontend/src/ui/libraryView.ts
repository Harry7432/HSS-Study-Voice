import type { LibraryService, SavedStudyDetail, SavedStudySummary } from '../library/types'

type LibraryReader = Pick<LibraryService, 'listStudies'>

interface LibraryViewDependencies extends LibraryReader {
  getStudy?: LibraryService['getStudy']
  removeStudy?: LibraryService['removeStudy']
  confirmRemoval?: (study: SavedStudySummary) => boolean
  onOpen?: (studyId: string) => void | Promise<void>
  onRemoved?: (studyId: string) => void
}

export interface LibraryView {
  refresh(): Promise<void>
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

function createStudyRow(
  study: SavedStudySummary,
  dependencies: LibraryViewDependencies,
  refresh: () => Promise<void>,
): HTMLLIElement {
  const item = document.createElement('li')
  item.className = 'study-row'

  const label = document.createElement('h3')
  label.className = 'study-label'
  label.dataset.studyLabel = ''
  label.textContent = study.label

  const metadata = document.createElement('div')
  metadata.className = 'study-meta'

  const id = document.createElement('span')
  id.className = 'study-id'
  id.textContent = `ID ${study.studyId.slice(0, 8)}`
  id.title = study.studyId

  const date = document.createElement('time')
  date.dateTime = study.createdAt
  date.textContent = formatDate(study.createdAt)

  const duration = document.createElement('span')
  duration.textContent = formatDuration(study.durationSeconds)

  metadata.append(id, date, duration)
  if (study.progress.completed) {
    const completed = document.createElement('strong')
    completed.textContent = 'Concluído'
    metadata.append(completed)
  }
  const actions = document.createElement('div')
  actions.className = 'study-actions'
  if (dependencies.getStudy !== undefined) {
    const details = document.createElement('button')
    details.type = 'button'
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
    open.dataset.openStudy = study.studyId
    open.textContent = 'Ouvir'
    open.addEventListener('click', () => void dependencies.onOpen?.(study.studyId))
    actions.append(open)
  }
  if (dependencies.removeStudy !== undefined) {
    const remove = document.createElement('button')
    remove.type = 'button'
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
          let alert = item.querySelector<HTMLElement>('[data-remove-warning]')
          if (alert === null) {
            alert = document.createElement('p')
            alert.dataset.removeWarning = ''
            alert.role = 'alert'
            item.append(alert)
          }
          alert.textContent =
            'Não foi possível remover este estudo. Verifique o armazenamento local e tente novamente.'
        }
      })()
    })
    actions.append(remove)
  }
  item.append(label, metadata)
  if (actions.childElementCount > 0) item.append(actions)
  return item
}

export function createLibraryView(
  container: HTMLElement,
  library: LibraryViewDependencies,
): LibraryView {
  container.classList.add('archive')
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
    async refresh(): Promise<void> {
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
          return
        }

        const list = document.createElement('ol')
        list.className = 'library-list'
        studies.forEach((study) => list.append(createStudyRow(study, library, view.refresh)))
        content.append(list)
      } catch {
        count.textContent = 'indisponível'
        content.replaceChildren()
        const alert = document.createElement('p')
        alert.className = 'library-state'
        alert.role = 'alert'
        alert.textContent =
          'Não foi possível abrir sua biblioteca local. Verifique o armazenamento do navegador e tente novamente.'
        content.append(alert)
      }
    },
  }
  return view
}
