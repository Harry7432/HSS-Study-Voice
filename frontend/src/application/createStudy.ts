import { resolveStudyLabel } from '../library/labels'
import { LibraryUnavailableError } from '../library/types'
import type {
  CreateStudyOutcome,
  LibraryService,
  StudiesClient,
  StudyCreateInput,
  StudyCreationResult,
} from '../library/types'

interface CreateStudyDependencies {
  client: StudiesClient
  library: Pick<LibraryService, 'saveStudy'>
}

export async function createAndSaveStudy(
  input: StudyCreateInput,
  dependencies: CreateStudyDependencies,
): Promise<CreateStudyOutcome> {
  const label = resolveStudyLabel(input.text, input.label)
  const metadata = await dependencies.client.createStudy(input)
  const [audio, timeline] = await Promise.all([
    dependencies.client.getAudio(metadata.studyId),
    dependencies.client.getTimeline(metadata.studyId),
  ])
  const result: StudyCreationResult = {
    ...metadata,
    voice: input.voice ?? null,
    speed: input.speed ?? null,
    bitrate: input.bitrate ?? null,
    audio,
    timeline,
  }
  try {
    await dependencies.library.saveStudy(result, label)
    return { result, label, saved: true }
  } catch (error) {
    if (!(error instanceof LibraryUnavailableError)) throw error
    return {
      result,
      label,
      saved: false,
      libraryWarning: 'O áudio foi gerado, mas não pôde ser salvo na biblioteca local.',
    }
  }
}
