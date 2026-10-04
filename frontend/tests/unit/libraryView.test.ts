import { describe, expect, it, vi } from 'vitest'

import { createLibraryView } from '../../src/ui/libraryView'
import {
  LibraryUnavailableError,
  type SavedStudyDetail,
  type SavedStudySummary,
} from '../../src/library/types'

function makeDetail(): SavedStudyDetail {
  return {
    studyId: 'a'.repeat(32),
    label: 'Citologia',
    createdAt: '2026-10-03T12:00:00.000Z',
    durationSeconds: 125,
    fileSizeBytes: 2048,
    voice: null,
    speed: null,
    bitrate: null,
    progress: {
      positionSeconds: 61,
      completed: true,
      updatedAt: '2026-10-03T12:01:00.000Z',
    },
    audio: new Blob(['audio'], { type: 'audio/mpeg' }),
    timeline: {
      schema_version: 1,
      audio: {
        filename: 'study.mp3',
        sha256: 'a'.repeat(64),
        sample_rate_hz: 22_050,
        total_samples: 44_100,
      },
      chunks: [],
    },
  }
}

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

  it('confirms removal and refreshes the list after success', async () => {
    const study: SavedStudySummary = {
      studyId: 'a'.repeat(32),
      label: 'Citologia',
      createdAt: '2026-10-03T12:00:00.000Z',
      durationSeconds: 60,
      progress: { positionSeconds: 0, completed: false, updatedAt: '2026-10-03T12:00:00.000Z' },
    }
    const listStudies = vi.fn().mockResolvedValueOnce([study]).mockResolvedValueOnce([])
    const removeStudy = vi.fn().mockResolvedValue(undefined)
    const onRemoved = vi.fn()
    const container = document.createElement('section')
    const view = createLibraryView(container, {
      listStudies,
      removeStudy,
      confirmRemoval: vi.fn().mockReturnValue(true),
      onRemoved,
    })
    await view.refresh()

    container.querySelector<HTMLButtonElement>('[data-remove-study]')!.click()

    await vi.waitFor(() => expect(removeStudy).toHaveBeenCalledWith(study.studyId))
    expect(onRemoved).toHaveBeenCalledWith(study.studyId)
    await vi.waitFor(() => {
      expect(container.textContent).toContain('Nenhum estudo arquivado ainda')
    })
  })

  it('keeps the study visible and warns clearly when removal fails', async () => {
    const study: SavedStudySummary = {
      studyId: 'a'.repeat(32),
      label: 'Citologia',
      createdAt: '2026-10-03T12:00:00.000Z',
      durationSeconds: 60,
      progress: { positionSeconds: 0, completed: false, updatedAt: '2026-10-03T12:00:00.000Z' },
    }
    const container = document.createElement('section')
    const view = createLibraryView(container, {
      listStudies: vi.fn().mockResolvedValue([study]),
      removeStudy: vi.fn().mockRejectedValue(new LibraryUnavailableError('erro interno')),
      confirmRemoval: vi.fn().mockReturnValue(true),
    })
    await view.refresh()

    container.querySelector<HTMLButtonElement>('[data-remove-study]')!.click()

    await vi.waitFor(() => {
      expect(container.querySelector('[role="alert"]')?.textContent).toContain(
        'Não foi possível remover este estudo',
      )
    })
    expect(container.textContent).toContain('Citologia')
    expect(container.textContent).not.toContain('erro interno')
  })

  it('shows complete local details without starting playback', async () => {
    const detail = makeDetail()
    const getStudy = vi.fn().mockResolvedValue(detail)
    const onOpen = vi.fn()
    const container = document.createElement('section')
    const view = createLibraryView(container, {
      listStudies: vi.fn().mockResolvedValue([detail]),
      getStudy,
      onOpen,
    })
    await view.refresh()

    container.querySelector<HTMLButtonElement>('[data-show-study-details]')!.click()

    await vi.waitFor(() => expect(getStudy).toHaveBeenCalledWith(detail.studyId))
    const details = container.querySelector('[data-study-details]')
    expect(details?.textContent).toContain('Citologia')
    expect(details?.textContent).toContain('2 min 05 s')
    expect(details?.textContent).toContain('2 KB')
    expect(details?.textContent).toContain('1 min 01 s')
    expect(details?.textContent).toContain('Concluído')
    expect(onOpen).not.toHaveBeenCalled()
  })

  it('shows a consistent absence when local details no longer exist', async () => {
    const detail = makeDetail()
    const container = document.createElement('section')
    const view = createLibraryView(container, {
      listStudies: vi.fn().mockResolvedValue([detail]),
      getStudy: vi.fn().mockResolvedValue(undefined),
    })
    await view.refresh()

    container.querySelector<HTMLButtonElement>('[data-show-study-details]')!.click()

    await vi.waitFor(() => {
      expect(container.querySelector('[data-study-details]')?.textContent).toContain(
        'não está mais disponível',
      )
    })
  })

  it('warns clearly when details are unavailable without exposing the technical error', async () => {
    const detail = makeDetail()
    const container = document.createElement('section')
    const view = createLibraryView(container, {
      listStudies: vi.fn().mockResolvedValue([detail]),
      getStudy: vi
        .fn()
        .mockRejectedValue(new LibraryUnavailableError('QuotaExceededError interno')),
    })
    await view.refresh()

    container.querySelector<HTMLButtonElement>('[data-show-study-details]')!.click()

    await vi.waitFor(() => {
      const alert = container.querySelector('[data-study-details][role="alert"]')
      expect(alert?.textContent).toContain('Não foi possível consultar os detalhes')
      expect(alert?.textContent).not.toContain('QuotaExceededError')
    })
  })
})
