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

describe('libraryService details', () => {
  it('composes metadata and assets from one local readonly lookup', async () => {
    const service = createLibraryService({
      now: () => new Date('2026-10-03T12:00:00.000Z'),
    })
    const result = makeStudyResult()
    await service.saveStudy(result, 'Citologia')

    await expect(service.getStudy(result.studyId)).resolves.toEqual({
      studyId: result.studyId,
      label: 'Citologia',
      createdAt: '2026-10-03T12:00:00.000Z',
      durationSeconds: result.durationSeconds,
      fileSizeBytes: result.fileSizeBytes,
      voice: result.voice,
      speed: result.speed,
      bitrate: result.bitrate,
      progress: {
        positionSeconds: 0,
        completed: false,
        updatedAt: '2026-10-03T12:00:00.000Z',
      },
      audio: result.audio,
      timeline: result.timeline,
    })
  })

  it('returns undefined for an absent study', async () => {
    await expect(createLibraryService().getStudy('a'.repeat(32))).resolves.toBeUndefined()
  })

  it.each(['studyMetadata', 'studyAssets'] as const)(
    'returns undefined when the %s half is missing',
    async (storeName) => {
      const service = createLibraryService()
      const result = makeStudyResult()
      await service.saveStudy(result, 'Citologia')
      const database = await openLibraryDb()
      await database.delete(storeName, result.studyId)

      await expect(service.getStudy(result.studyId)).resolves.toBeUndefined()
    },
  )

  it('translates detail storage failures', async () => {
    const service = createLibraryService({
      openDb: vi.fn().mockRejectedValue(new DOMException('indisponível', 'UnknownError')),
    })

    await expect(service.getStudy('a'.repeat(32))).rejects.toBeInstanceOf(
      LibraryUnavailableError,
    )
  })
})

describe('libraryService progress', () => {
  it('loads the complete local study for playback', async () => {
    const service = createLibraryService()
    const result = makeStudyResult()
    await service.saveStudy(result, 'Citologia')

    await expect(service.getStudy(result.studyId)).resolves.toMatchObject({
      studyId: result.studyId,
      label: 'Citologia',
      audio: result.audio,
      timeline: result.timeline,
    })
  })

  it('updates only the requested progress fields and timestamp', async () => {
    const service = createLibraryService({
      now: () => new Date('2026-10-03T13:00:00.000Z'),
    })
    const result = makeStudyResult()
    await service.saveStudy(result, 'Citologia')
    const database = await openLibraryDb()
    const assetsBefore = await database.get('studyAssets', result.studyId)

    await service.updateProgress(result.studyId, { positionSeconds: 1.25 })

    const metadata = await database.get('studyMetadata', result.studyId)
    expect(metadata).toMatchObject({
      label: 'Citologia',
      durationSeconds: 2,
      progress: {
        positionSeconds: 1.25,
        completed: false,
        updatedAt: '2026-10-03T13:00:00.000Z',
      },
    })
    expect(await database.get('studyAssets', result.studyId)).toEqual(assetsBefore)
  })

  it.each([-0.01, 2.01, Number.NaN])('rejects an invalid position of %s seconds', async (positionSeconds) => {
    const service = createLibraryService()
    const result = makeStudyResult()
    await service.saveStudy(result, 'Citologia')

    await expect(service.updateProgress(result.studyId, { positionSeconds })).rejects.toThrow(
      'A posição deve estar entre 0 e a duração do estudo.',
    )
  })

  it('updates the position of a completed study without clearing completion', async () => {
    const service = createLibraryService()
    const result = makeStudyResult()
    await service.saveStudy(result, 'Citologia')
    await service.updateProgress(result.studyId, { completed: true, positionSeconds: 2 })

    await service.updateProgress(result.studyId, { positionSeconds: 0.5 })

    const database = await openLibraryDb()
    expect((await database.get('studyMetadata', result.studyId))?.progress).toMatchObject({
      positionSeconds: 0.5,
      completed: true,
    })
  })

  it('translates progress storage failures', async () => {
    const service = createLibraryService({
      openDb: vi.fn().mockRejectedValue(new DOMException('sem cota', 'QuotaExceededError')),
    })

    await expect(
      service.updateProgress('a'.repeat(32), { positionSeconds: 1 }),
    ).rejects.toBeInstanceOf(LibraryUnavailableError)
  })
})

describe('libraryService removal', () => {
  it('atomically removes metadata and assets while preserving other studies', async () => {
    const service = createLibraryService()
    const removed = makeStudyResult({ studyId: 'a'.repeat(32) })
    const preserved = makeStudyResult({ studyId: 'b'.repeat(32) })
    await service.saveStudy(removed, 'Remover')
    await service.saveStudy(preserved, 'Preservar')

    await service.removeStudy(removed.studyId)

    const database = await openLibraryDb()
    expect(await database.get('studyMetadata', removed.studyId)).toBeUndefined()
    expect(await database.get('studyAssets', removed.studyId)).toBeUndefined()
    expect(await database.get('studyMetadata', preserved.studyId)).toBeDefined()
    expect(await database.get('studyAssets', preserved.studyId)).toBeDefined()
  })

  it('is idempotent for an absent study', async () => {
    const service = createLibraryService()

    await expect(service.removeStudy('a'.repeat(32))).resolves.toBeUndefined()
    await expect(service.removeStudy('a'.repeat(32))).resolves.toBeUndefined()
  })

  it('rolls back both deletes when the transaction aborts', async () => {
    const baseService = createLibraryService()
    const result = makeStudyResult()
    await baseService.saveStudy(result, 'Citologia')
    const database = await openLibraryDb()
    const service = createLibraryService({
      openDb: async () => ({
        transaction(...args: Parameters<typeof database.transaction>) {
          const transaction = database.transaction(...args)
          queueMicrotask(() => transaction.abort())
          return transaction
        },
      }) as typeof database,
    })

    await expect(service.removeStudy(result.studyId)).rejects.toBeInstanceOf(
      LibraryUnavailableError,
    )
    expect(await database.get('studyMetadata', result.studyId)).toBeDefined()
    expect(await database.get('studyAssets', result.studyId)).toBeDefined()
  })

  it('translates removal storage failures', async () => {
    const service = createLibraryService({
      openDb: vi.fn().mockRejectedValue(new DOMException('indisponível', 'UnknownError')),
    })

    await expect(service.removeStudy('a'.repeat(32))).rejects.toBeInstanceOf(
      LibraryUnavailableError,
    )
  })
})
