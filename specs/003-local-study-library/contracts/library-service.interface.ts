/**
 * Contrato público do libraryService (Fase 5 — Biblioteca local-first).
 *
 * O chamador só constrói StudyCreationResult depois de validar em runtime criação, áudio e
 * timeline. O rótulo também chega pronto e obrigatório; o serviço nunca recebe o texto original.
 */

export interface TimelineDocument {
  schema_version: 1;
  audio: {
    filename: string;
    sha256: string;
    sample_rate_hz: number;
    total_samples: number;
  };
  chunks: Array<{
    index: number;
    start_sample: number;
    end_sample: number;
    sentences: Array<{
      index: number;
      text: string;
      start_sample: number;
      end_sample: number;
    }>;
  }>;
}

export interface StudyCreationResult {
  studyId: string;
  durationSeconds: number;
  fileSizeBytes: number;
  voice: string | null;
  speed: number | null;
  bitrate: string | null;
  audio: Blob;
  timeline: TimelineDocument;
}

export interface Progress {
  positionSeconds: number;
  completed: boolean;
  updatedAt: string;
}

export interface StudyMetadata {
  studyId: string;
  label: string;
  createdAt: string;
  durationSeconds: number;
  fileSizeBytes: number;
  voice: string | null;
  speed: number | null;
  bitrate: string | null;
  progress: Progress;
}

export interface StudyAssets {
  studyId: string;
  audio: Blob;
  timeline: TimelineDocument;
}

export type SavedStudySummary = Pick<
  StudyMetadata,
  "studyId" | "label" | "createdAt" | "durationSeconds" | "progress"
>;

export interface SavedStudyDetail extends StudyMetadata, Omit<StudyAssets, "studyId"> {}

/** Lançado por qualquer método quando o IndexedDB está indisponível ou sem cota. */
export declare class LibraryUnavailableError extends Error {}

export interface LibraryService {
  /** Grava metadata e assets em uma única transação multi-store. */
  saveStudy(result: StudyCreationResult, label: string): Promise<void>;

  /** Lista somente metadados, do mais recente para o mais antigo. */
  listStudies(): Promise<SavedStudySummary[]>;

  /** Compõe metadata + assets, ou retorna undefined se qualquer parte não existir. */
  getStudy(studyId: string): Promise<SavedStudyDetail | undefined>;

  updateProgress(
    studyId: string,
    update: Partial<Pick<Progress, "positionSeconds" | "completed">>,
  ): Promise<void>;

  /** Apaga metadata e assets em uma única transação multi-store; é idempotente. */
  removeStudy(studyId: string): Promise<void>;
}
