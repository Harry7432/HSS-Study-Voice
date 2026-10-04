import type { IDBPDatabase } from 'idb'

import { openLibraryDb, type StudyLibraryDb } from './db'
import {
  LibraryUnavailableError,
  type LibraryService,
  type SavedStudySummary,
  type StudyCreationResult,
} from './types'

type CurrentLibraryService = Pick<
  LibraryService,
  'saveStudy' | 'listStudies' | 'getStudy' | 'updateProgress' | 'removeStudy'
>

interface LibraryServiceDependencies {
  openDb?: () => Promise<IDBPDatabase<StudyLibraryDb>>
  now?: () => Date
}

function unavailable(error: unknown): LibraryUnavailableError {
  return error instanceof LibraryUnavailableError
    ? error
    : new LibraryUnavailableError('Não foi possível acessar a biblioteca local.', {
        cause: error,
      })
}

export function createLibraryService(
  dependencies: LibraryServiceDependencies = {},
): CurrentLibraryService {
  const openDb = dependencies.openDb ?? openLibraryDb
  const now = dependencies.now ?? (() => new Date())

  return {
    async saveStudy(result: StudyCreationResult, label: string): Promise<void> {
      if (label.length < 1 || label.length > 80) {
        throw new Error('O rótulo deve ter entre 1 e 80 caracteres.')
      }

      try {
        const timestamp = now().toISOString()
        const database = await openDb()
        const transaction = database.transaction(
          ['studyMetadata', 'studyAssets'],
          'readwrite',
        )
        await Promise.all([
          transaction.objectStore('studyMetadata').put({
            studyId: result.studyId,
            label,
            createdAt: timestamp,
            durationSeconds: result.durationSeconds,
            fileSizeBytes: result.fileSizeBytes,
            voice: result.voice,
            speed: result.speed,
            bitrate: result.bitrate,
            progress: {
              positionSeconds: 0,
              completed: false,
              updatedAt: timestamp,
            },
          }),
          transaction.objectStore('studyAssets').put({
            studyId: result.studyId,
            audio: result.audio,
            timeline: result.timeline,
          }),
          transaction.done,
        ])
      } catch (error) {
        throw unavailable(error)
      }
    },

    async listStudies(): Promise<SavedStudySummary[]> {
      try {
        const database = await openDb()
        const index = database
          .transaction('studyMetadata', 'readonly')
          .objectStore('studyMetadata')
          .index('createdAt')
        const summaries: SavedStudySummary[] = []
        let cursor = await index.openCursor(null, 'prev')
        while (cursor !== null) {
          const metadata = cursor.value
          summaries.push({
            studyId: metadata.studyId,
            label: metadata.label,
            createdAt: metadata.createdAt,
            durationSeconds: metadata.durationSeconds,
            progress: metadata.progress,
          })
          cursor = await cursor.continue()
        }
        return summaries
      } catch (error) {
        throw unavailable(error)
      }
    },

    async getStudy(studyId) {
      try {
        const database = await openDb()
        const transaction = database.transaction(
          ['studyMetadata', 'studyAssets'],
          'readonly',
        )
        const [metadata, assets] = await Promise.all([
          transaction.objectStore('studyMetadata').get(studyId),
          transaction.objectStore('studyAssets').get(studyId),
          transaction.done,
        ])
        if (metadata === undefined || assets === undefined) return undefined
        return {
          ...metadata,
          audio: assets.audio,
          timeline: assets.timeline,
        }
      } catch (error) {
        throw unavailable(error)
      }
    },

    async updateProgress(studyId, update): Promise<void> {
      if (
        update.positionSeconds !== undefined &&
        (!Number.isFinite(update.positionSeconds) || update.positionSeconds < 0)
      ) {
        throw new RangeError('A posição deve estar entre 0 e a duração do estudo.')
      }

      try {
        const database = await openDb()
        const transaction = database.transaction('studyMetadata', 'readwrite')
        const store = transaction.objectStore('studyMetadata')
        const metadata = await store.get(studyId)
        if (metadata === undefined) {
          await transaction.done
          return
        }
        if (
          update.positionSeconds !== undefined &&
          update.positionSeconds > metadata.durationSeconds
        ) {
          transaction.abort()
          await transaction.done.catch(() => undefined)
          throw new RangeError('A posição deve estar entre 0 e a duração do estudo.')
        }

        await store.put({
          ...metadata,
          progress: {
            ...metadata.progress,
            ...update,
            updatedAt: now().toISOString(),
          },
        })
        await transaction.done
      } catch (error) {
        if (error instanceof RangeError) {
          throw error
        }
        throw unavailable(error)
      }
    },

    async removeStudy(studyId): Promise<void> {
      try {
        const database = await openDb()
        const transaction = database.transaction(
          ['studyMetadata', 'studyAssets'],
          'readwrite',
        )
        await Promise.all([
          transaction.objectStore('studyMetadata').delete(studyId),
          transaction.objectStore('studyAssets').delete(studyId),
          transaction.done,
        ])
      } catch (error) {
        throw unavailable(error)
      }
    },
  }
}
