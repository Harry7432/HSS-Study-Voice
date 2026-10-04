import { expect, it, vi } from 'vitest'

import { mountApp } from '../../src/main'
import type { SavedStudyDetail, SavedStudySummary } from '../../src/library/types'
import { makeStudyResult } from '../setup'

function makeSavedStudy(): SavedStudyDetail {
  const result = makeStudyResult()
  return {
    studyId: result.studyId,
    label: 'Citologia aplicada',
    createdAt: '2026-10-03T12:00:00.000Z',
    durationSeconds: result.durationSeconds,
    fileSizeBytes: result.fileSizeBytes,
    voice: result.voice,
    speed: result.speed,
    bitrate: result.bitrate,
    progress: {
      positionSeconds: 1,
      completed: false,
      updatedAt: '2026-10-03T12:00:00.000Z',
    },
    audio: result.audio,
    timeline: result.timeline,
  }
}

function summary(detail: SavedStudyDetail): SavedStudySummary {
  const { studyId, label, createdAt, durationSeconds, progress } = detail
  return { studyId, label, createdAt, durationSeconds, progress }
}

it('keeps generated audio playable and warns when only local storage fails', async () => {
  const root = document.createElement('div')
  const result = makeStudyResult()
  const createStudy = vi.fn().mockResolvedValue({
    result,
    label: 'Citologia aplicada',
    saved: false,
    libraryWarning: 'O áudio foi gerado, mas não pôde ser salvo na biblioteca local.',
  })
  const listStudies = vi.fn().mockResolvedValue([])
  await mountApp(root, {
    createStudy,
    listStudies,
    createObjectUrl: vi.fn().mockReturnValue('blob:estudo-gerado'),
  })
  const text = root.querySelector<HTMLTextAreaElement>('[name="text"]')!
  const label = root.querySelector<HTMLInputElement>('[name="label"]')!
  text.value = 'Texto para o estudo.'
  label.value = 'Citologia aplicada'

  root.querySelector('form')!.dispatchEvent(new SubmitEvent('submit', { cancelable: true }))

  await vi.waitFor(() => {
    expect(createStudy).toHaveBeenCalledWith({
      text: 'Texto para o estudo.',
      label: 'Citologia aplicada',
    })
  })
  expect(root.querySelector('audio')?.getAttribute('src')).toBe('blob:estudo-gerado')
  expect(root.querySelector('[role="status"]')?.textContent).toContain(
    'O áudio foi gerado, mas não pôde ser salvo',
  )
  expect(root.querySelector('[data-now-playing]')?.classList).toContain('is-visible')
})

it('opens a saved study locally and refreshes its visible completion', async () => {
  const root = document.createElement('div')
  const detail = makeSavedStudy()
  const completed = {
    ...summary(detail),
    progress: { ...detail.progress, positionSeconds: 2, completed: true },
  }
  const listStudies = vi
    .fn()
    .mockResolvedValueOnce([summary(detail)])
    .mockResolvedValueOnce([summary(detail)])
    .mockResolvedValueOnce([completed])
  const updateProgress = vi.fn().mockResolvedValue(undefined)
  await mountApp(root, {
    createStudy: vi.fn(),
    listStudies,
    getStudy: vi.fn().mockResolvedValue(detail),
    updateProgress,
    removeStudy: vi.fn(),
    createObjectUrl: vi.fn().mockReturnValue('blob:saved-study'),
    revokeObjectUrl: vi.fn(),
    confirmRemoval: vi.fn().mockReturnValue(true),
  })

  root.querySelector<HTMLButtonElement>('[data-open-study]')!.click()

  await vi.waitFor(() => {
    expect(root.querySelector('audio')?.getAttribute('src')).toBe('blob:saved-study')
  })
  root.querySelector('audio')!.dispatchEvent(new Event('ended'))
  await vi.waitFor(() => expect(updateProgress).toHaveBeenCalledWith(detail.studyId, {
    positionSeconds: detail.durationSeconds,
    completed: true,
  }))
  await vi.waitFor(() => expect(root.textContent).toContain('Concluído'))
})

it('highlights is-playing only while actually playing, clearing it on pause and on completion', async () => {
  const root = document.createElement('div')
  const detail = makeSavedStudy()
  const listStudies = vi.fn().mockResolvedValue([summary(detail)])
  await mountApp(root, {
    createStudy: vi.fn(),
    listStudies,
    getStudy: vi.fn().mockResolvedValue(detail),
    updateProgress: vi.fn().mockResolvedValue(undefined),
    removeStudy: vi.fn(),
    createObjectUrl: vi.fn().mockReturnValue('blob:saved-study'),
    revokeObjectUrl: vi.fn(),
    confirmRemoval: vi.fn().mockReturnValue(true),
  })

  root.querySelector<HTMLButtonElement>('[data-open-study]')!.click()
  await vi.waitFor(() => {
    expect(root.querySelector('audio')?.getAttribute('src')).toBe('blob:saved-study')
  })
  expect(root.querySelector('.hss-row')?.classList).not.toContain('is-playing')

  root.querySelector('audio')!.dispatchEvent(new Event('play'))
  await vi.waitFor(() => {
    expect(root.querySelector('.hss-row')?.classList).toContain('is-playing')
  })

  root.querySelector('audio')!.dispatchEvent(new Event('pause'))
  await vi.waitFor(() => {
    expect(root.querySelector('.hss-row')?.classList).not.toContain('is-playing')
  })

  root.querySelector('audio')!.dispatchEvent(new Event('play'))
  await vi.waitFor(() => {
    expect(root.querySelector('.hss-row')?.classList).toContain('is-playing')
  })

  root.querySelector('audio')!.dispatchEvent(new Event('ended'))
  await vi.waitFor(() => {
    expect(root.querySelector('.hss-row')?.classList).not.toContain('is-playing')
  })
})

it('removes a saved study and discards its active player', async () => {
  const root = document.createElement('div')
  const detail = makeSavedStudy()
  const revokeObjectUrl = vi.fn()
  const listStudies = vi
    .fn()
    .mockResolvedValueOnce([summary(detail)])
    .mockResolvedValueOnce([summary(detail)])
    .mockResolvedValueOnce([])
  const removeStudy = vi.fn().mockResolvedValue(undefined)
  await mountApp(root, {
    createStudy: vi.fn(),
    listStudies,
    getStudy: vi.fn().mockResolvedValue(detail),
    updateProgress: vi.fn(),
    removeStudy,
    createObjectUrl: vi.fn().mockReturnValue('blob:saved-study'),
    revokeObjectUrl,
    confirmRemoval: vi.fn().mockReturnValue(true),
  })
  root.querySelector<HTMLButtonElement>('[data-open-study]')!.click()
  await vi.waitFor(() => expect(root.querySelector('audio')?.getAttribute('src')).toBe('blob:saved-study'))

  root.querySelector<HTMLButtonElement>('[data-remove-study]')!.click()

  await vi.waitFor(() => expect(removeStudy).toHaveBeenCalledWith(detail.studyId))
  expect(revokeObjectUrl).toHaveBeenCalledWith('blob:saved-study')
  expect(root.querySelector('audio')?.getAttribute('src')).toBeNull()
  await vi.waitFor(() => expect(root.textContent).toContain('Nenhum estudo arquivado ainda'))
})
