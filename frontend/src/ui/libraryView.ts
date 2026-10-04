import type { LibraryService, SavedStudySummary } from '../library/types'

type LibraryReader = Pick<LibraryService, 'listStudies'>

export interface LibraryView {
  refresh(): Promise<void>
}

function formatDuration(totalSeconds: number): string {
  const rounded = Math.round(totalSeconds)
  const minutes = Math.floor(rounded / 60)
  const seconds = rounded % 60
  return `${minutes} min ${seconds.toString().padStart(2, '0')} s`
}

function createStudyRow(study: SavedStudySummary): HTMLLIElement {
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
  date.textContent = new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(study.createdAt))

  const duration = document.createElement('span')
  duration.textContent = formatDuration(study.durationSeconds)

  metadata.append(id, date, duration)
  if (study.progress.completed) {
    const completed = document.createElement('strong')
    completed.textContent = 'Concluído'
    metadata.append(completed)
  }
  item.append(label, metadata)
  return item
}

export function createLibraryView(
  container: HTMLElement,
  library: LibraryReader,
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

  return {
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
        studies.forEach((study) => list.append(createStudyRow(study)))
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
}
