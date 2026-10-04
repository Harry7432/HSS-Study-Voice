export interface TimelineSentence {
  index: number
  text: string
  start_sample: number
  end_sample: number
}

export interface TimelineChunk {
  index: number
  start_sample: number
  end_sample: number
  sentences: TimelineSentence[]
}

export interface TimelineDocument {
  schema_version: 1
  audio: {
    filename: string
    sha256: string
    sample_rate_hz: number
    total_samples: number
  }
  chunks: TimelineChunk[]
}

export interface StudyCreateInput {
  text: string
  label?: string
  voice?: string
  speed?: number
  bitrate?: string
}

export interface StudyCreationMetadata {
  studyId: string
  chunksCount: number
  durationSeconds: number
  fileSizeBytes: number
  processingTimeSeconds: number
}

export interface StudyCreationResult extends StudyCreationMetadata {
  voice: string | null
  speed: number | null
  bitrate: string | null
  audio: Blob
  timeline: TimelineDocument
}

export interface Progress {
  positionSeconds: number
  completed: boolean
  updatedAt: string
}

export interface StudyMetadata {
  studyId: string
  label: string
  createdAt: string
  durationSeconds: number
  fileSizeBytes: number
  voice: string | null
  speed: number | null
  bitrate: string | null
  progress: Progress
}

export interface StudyAssets {
  studyId: string
  audio: Blob
  timeline: TimelineDocument
}

export type SavedStudySummary = Pick<
  StudyMetadata,
  'studyId' | 'label' | 'createdAt' | 'durationSeconds' | 'progress'
>

export interface SavedStudyDetail extends StudyMetadata {
  audio: Blob
  timeline: TimelineDocument
}

export class LibraryUnavailableError extends Error {
  constructor(message = 'A biblioteca local não está disponível.', options?: ErrorOptions) {
    super(message, options)
    this.name = 'LibraryUnavailableError'
  }
}

export interface LibraryService {
  saveStudy(result: StudyCreationResult, label: string): Promise<void>
  listStudies(): Promise<SavedStudySummary[]>
  getStudy(studyId: string): Promise<SavedStudyDetail | undefined>
  updateProgress(
    studyId: string,
    update: Partial<Pick<Progress, 'positionSeconds' | 'completed'>>,
  ): Promise<void>
  removeStudy(studyId: string): Promise<void>
}

export interface StudiesClient {
  createStudy(input: StudyCreateInput): Promise<StudyCreationMetadata>
  getAudio(studyId: string): Promise<Blob>
  getTimeline(studyId: string): Promise<TimelineDocument>
}

export interface CreateStudyOutcome {
  result: StudyCreationResult
  label: string
  saved: boolean
  libraryWarning?: string
}
