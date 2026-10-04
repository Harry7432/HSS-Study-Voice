// @vitest-environment node

import { describe, expect, it, vi } from 'vitest'

import { openLibraryDb } from '../../src/library/db'
import { createLibraryService } from '../../src/library/libraryService'
import { LibraryUnavailableError } from '../../src/library/types'
import { makeStudyResult } from '../setup'

describe('libraryService save and list', () => {
  it('saves metadata and assets with initial progress', async () => {
    const now = () => new Date('2026-10-03T12:00:00.000Z')
    const service = createLibraryService({ now })
    const result = makeStudyResult()

    await service.saveStudy(result, 'Revisão de citologia')

    const database = await openLibraryDb()
    const metadata = await database.get('studyMetadata', result.studyId)
    const assets = await database.get('studyAssets', result.studyId)
    expect(metadata).toEqual({
      studyId: result.studyId,
      label: 'Revisão de citologia',
      createdAt: '2026-10-03T12:00:00.000Z',
      durationSeconds: 2,
      fileSizeBytes: 8,
      voice: null,
      speed: null,
      bitrate: null,
      progress: {
        positionSeconds: 0,
        completed: false,
        updatedAt: '2026-10-03T12:00:00.000Z',
      },
    })
    expect(assets).toEqual({
      studyId: result.studyId,
      audio: result.audio,
      timeline: result.timeline,
    })
    expect(metadata).not.toHaveProperty('text')
  })

  it('returns summaries from newest to oldest without heavy assets', async () => {
    const dates = [
      new Date('2026-10-03T10:00:00.000Z'),
      new Date('2026-10-03T12:00:00.000Z'),
    ]
    const service = createLibraryService({ now: () => dates.shift()! })
    await service.saveStudy(makeStudyResult({ studyId: '1'.repeat(32) }), 'Primeiro')
    await service.saveStudy(makeStudyResult({ studyId: '2'.repeat(32) }), 'Segundo')

    const studies = await service.listStudies()

    expect(studies.map((study) => study.label)).toEqual(['Segundo', 'Primeiro'])
    expect(studies[0]).toEqual({
      studyId: '2'.repeat(32),
      label: 'Segundo',
      createdAt: '2026-10-03T12:00:00.000Z',
      durationSeconds: 2,
      progress: {
        positionSeconds: 0,
        completed: false,
        updatedAt: '2026-10-03T12:00:00.000Z',
      },
    })
    expect(studies[0]).not.toHaveProperty('audio')
    expect(studies[0]).not.toHaveProperty('timeline')
  })

  it('returns an empty list for a new library', async () => {
    await expect(createLibraryService().listStudies()).resolves.toEqual([])
  })

  it.each(['', 'a'.repeat(81)])('rejects an invalid required label', async (label) => {
    await expect(createLibraryService().saveStudy(makeStudyResult(), label)).rejects.toThrow(
      'O rótulo deve ter entre 1 e 80 caracteres.',
    )
  })

  it('translates database availability failures', async () => {
    const service = createLibraryService({
      openDb: vi.fn().mockRejectedValue(new DOMException('sem cota', 'QuotaExceededError')),
    })

    await expect(service.listStudies()).rejects.toBeInstanceOf(LibraryUnavailableError)
    await expect(service.saveStudy(makeStudyResult(), 'Estudo')).rejects.toBeInstanceOf(
      LibraryUnavailableError,
    )
  })
})
