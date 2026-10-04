import { describe, expect, it, vi } from 'vitest'

import { createLibraryView } from '../../src/ui/libraryView'
import { LibraryUnavailableError, type SavedStudySummary } from '../../src/library/types'

describe('libraryView', () => {
  it('renders an empty library as a useful state', async () => {
    const container = document.createElement('section')
    const view = createLibraryView(container, {
      listStudies: vi.fn().mockResolvedValue([]),
    })

    await view.refresh()

    expect(container.textContent).toContain('Nenhum estudo arquivado ainda')
    expect(container.querySelector('[data-library-count]')?.textContent).toBe('0 estudos')
  })

  it('renders local summaries newest-first as returned by the service', async () => {
    const studies: SavedStudySummary[] = [
      {
        studyId: '2'.repeat(32),
        label: 'Genética molecular',
        createdAt: '2026-10-03T12:00:00.000Z',
        durationSeconds: 125,
        progress: {
          positionSeconds: 0,
          completed: false,
          updatedAt: '2026-10-03T12:00:00.000Z',
        },
      },
      {
        studyId: '1'.repeat(32),
        label: 'Citologia',
        createdAt: '2026-10-03T10:00:00.000Z',
        durationSeconds: 60,
        progress: {
          positionSeconds: 60,
          completed: true,
          updatedAt: '2026-10-03T11:00:00.000Z',
        },
      },
    ]
    const container = document.createElement('section')
    const view = createLibraryView(container, {
      listStudies: vi.fn().mockResolvedValue(studies),
    })

    await view.refresh()

    const labels = [...container.querySelectorAll('[data-study-label]')].map(
      (element) => element.textContent,
    )
    expect(labels).toEqual(['Genética molecular', 'Citologia'])
    expect(container.textContent).toContain('Concluído')
  })

  it('shows a clear recovery message without exposing the technical error', async () => {
    const container = document.createElement('section')
    const view = createLibraryView(container, {
      listStudies: vi
        .fn()
        .mockRejectedValue(new LibraryUnavailableError('QuotaExceededError interno')),
    })

    await view.refresh()

    const alert = container.querySelector('[role="alert"]')
    expect(alert?.textContent).toContain('Não foi possível abrir sua biblioteca local')
    expect(alert?.textContent).not.toContain('QuotaExceededError')
  })
})
