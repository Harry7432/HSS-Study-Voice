import 'fake-indexeddb/auto'

import { afterEach } from 'vitest'

import { resetLibraryDb } from '../src/library/db'
import type { StudyCreationResult, TimelineDocument } from '../src/library/types'

export function makeTimeline(studyId = 'a'.repeat(32)): TimelineDocument {
  return {
    schema_version: 1,
    audio: {
      filename: `${studyId}.mp3`,
      sha256: 'b'.repeat(64),
      sample_rate_hz: 22_050,
      total_samples: 44_100,
    },
    chunks: [
      {
        index: 0,
        start_sample: 0,
        end_sample: 44_100,
        sentences: [
          {
            index: 0,
            text: 'Uma frase de estudo.',
            start_sample: 0,
            end_sample: 44_100,
          },
        ],
      },
    ],
  }
}

export function makeStudyResult(
  overrides: Partial<StudyCreationResult> = {},
): StudyCreationResult {
  const studyId = overrides.studyId ?? 'a'.repeat(32)
  return {
    studyId,
    chunksCount: 1,
    durationSeconds: 2,
    fileSizeBytes: 8,
    processingTimeSeconds: 0.2,
    voice: null,
    speed: null,
    bitrate: null,
    audio: new Blob(['ID3audio'], { type: 'audio/mpeg' }),
    timeline: makeTimeline(studyId),
    ...overrides,
  }
}

afterEach(async () => {
  if (typeof document !== 'undefined') {
    document.body.innerHTML = ''
  }
  await resetLibraryDb()
})
