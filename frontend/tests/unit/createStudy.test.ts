import { describe, expect, it, vi } from 'vitest'

import { createAndSaveStudy } from '../../src/application/createStudy'
import {
  LibraryUnavailableError,
  type LibraryService,
  type StudiesClient,
} from '../../src/library/types'
import { makeStudyResult } from '../setup'

describe('createAndSaveStudy', () => {
  it('derives the label and saves only a complete generated bundle', async () => {
    const bundle = makeStudyResult()
    const client: StudiesClient = {
      createStudy: vi.fn().mockResolvedValue({
        studyId: bundle.studyId,
        chunksCount: bundle.chunksCount,
        durationSeconds: bundle.durationSeconds,
        fileSizeBytes: bundle.fileSizeBytes,
        processingTimeSeconds: bundle.processingTimeSeconds,
      }),
      getAudio: vi.fn().mockResolvedValue(bundle.audio),
      getTimeline: vi.fn().mockResolvedValue(bundle.timeline),
    }
    const library = {
      saveStudy: vi.fn().mockResolvedValue(undefined),
    } as Pick<LibraryService, 'saveStudy'>

    const outcome = await createAndSaveStudy(
      { text: '  Fundamentos   de citologia.  ' },
      { client, library },
    )

    expect(library.saveStudy).toHaveBeenCalledOnce()
    expect(library.saveStudy).toHaveBeenCalledWith(bundle, 'Fundamentos de citologia.')
    expect(outcome).toEqual({
      result: bundle,
      label: 'Fundamentos de citologia.',
      saved: true,
    })
  })

  it('keeps the generated bundle playable when only local persistence fails', async () => {
    const bundle = makeStudyResult()
    const client: StudiesClient = {
      createStudy: vi.fn().mockResolvedValue(bundle),
      getAudio: vi.fn().mockResolvedValue(bundle.audio),
      getTimeline: vi.fn().mockResolvedValue(bundle.timeline),
    }
    const library = {
      saveStudy: vi
        .fn()
        .mockRejectedValue(new LibraryUnavailableError('sem espaço local')),
    } as Pick<LibraryService, 'saveStudy'>

    const outcome = await createAndSaveStudy(
      { text: 'Estudo que ainda pode ser ouvido.' },
      { client, library },
    )

    expect(outcome.saved).toBe(false)
    expect(outcome.result.audio).toBe(bundle.audio)
    expect(outcome.libraryWarning).toBe(
      'O áudio foi gerado, mas não pôde ser salvo na biblioteca local.',
    )
  })

  it.each(['audio', 'timeline'] as const)(
    'never persists when the %s download fails after generation',
    async (failedAsset) => {
      const bundle = makeStudyResult()
      const client: StudiesClient = {
        createStudy: vi.fn().mockResolvedValue(bundle),
        getAudio:
          failedAsset === 'audio'
            ? vi.fn().mockRejectedValue(new Error('áudio indisponível'))
            : vi.fn().mockResolvedValue(bundle.audio),
        getTimeline:
          failedAsset === 'timeline'
            ? vi.fn().mockRejectedValue(new Error('timeline indisponível'))
            : vi.fn().mockResolvedValue(bundle.timeline),
      }
      const library = {
        saveStudy: vi.fn(),
      } as Pick<LibraryService, 'saveStudy'>

      await expect(
        createAndSaveStudy({ text: 'Estudo incompleto.' }, { client, library }),
      ).rejects.toThrow()
      expect(client.getAudio).toHaveBeenCalledOnce()
      expect(client.getTimeline).toHaveBeenCalledOnce()
      expect(library.saveStudy).not.toHaveBeenCalled()
    },
  )
})
