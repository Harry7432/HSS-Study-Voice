import { deleteDB, openDB, type DBSchema, type IDBPDatabase } from 'idb'

import type { StudyAssets, StudyMetadata } from './types'

export const LIBRARY_DB_NAME = 'hss-study-library'
export const LIBRARY_DB_VERSION = 1

export interface StudyLibraryDb extends DBSchema {
  studyMetadata: {
    key: string
    value: StudyMetadata
    indexes: { createdAt: string }
  }
  studyAssets: {
    key: string
    value: StudyAssets
  }
}

let databasePromise: Promise<IDBPDatabase<StudyLibraryDb>> | undefined

export function openLibraryDb(): Promise<IDBPDatabase<StudyLibraryDb>> {
  databasePromise ??= openDB<StudyLibraryDb>(LIBRARY_DB_NAME, LIBRARY_DB_VERSION, {
    upgrade(database) {
      const metadataStore = database.createObjectStore('studyMetadata', {
        keyPath: 'studyId',
      })
      metadataStore.createIndex('createdAt', 'createdAt', { unique: false })
      database.createObjectStore('studyAssets', { keyPath: 'studyId' })
    },
  })
  return databasePromise
}

export async function resetLibraryDb(): Promise<void> {
  if (databasePromise !== undefined) {
    const database = await databasePromise
    database.close()
    databasePromise = undefined
  }
  await deleteDB(LIBRARY_DB_NAME)
}
