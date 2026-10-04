import type {
  StudiesClient,
  StudyCreateInput,
  StudyCreationMetadata,
  TimelineDocument,
} from '../library/types'
import {
  parseStudyCreationMetadata,
  parseTimeline,
  validateAudioResponse,
} from './validators'

async function parseJson(response: Response, failureMessage: string): Promise<unknown> {
  if (!response.ok) throw new Error(failureMessage)
  try {
    return await response.json()
  } catch {
    throw new Error(failureMessage)
  }
}

export function createStudiesClient(fetcher: typeof fetch = globalThis.fetch): StudiesClient {
  return {
    async createStudy(input: StudyCreateInput): Promise<StudyCreationMetadata> {
      const response = await fetcher('/api/v1/studies', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: input.text,
          voice: input.voice,
          speed: input.speed,
          bitrate: input.bitrate,
        }),
      })
      return parseStudyCreationMetadata(
        await parseJson(response, 'Falha ao criar o estudo.'),
      )
    },

    async getAudio(studyId: string): Promise<Blob> {
      return validateAudioResponse(
        await fetcher(`/api/v1/studies/${studyId}/audio`),
      )
    },

    async getTimeline(studyId: string): Promise<TimelineDocument> {
      const response = await fetcher(`/api/v1/studies/${studyId}/timeline`)
      return parseTimeline(await parseJson(response, 'Falha ao baixar a timeline.'))
    },
  }
}
