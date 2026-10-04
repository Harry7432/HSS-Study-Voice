import type { LibraryService, SavedStudyDetail } from '../library/types'

interface LocalPlayerDependencies {
  updateProgress: LibraryService['updateProgress']
  createObjectUrl(blob: Blob): string
  revokeObjectUrl(url: string): void
  isVisible?: () => boolean
  onCompleted?: (studyId: string) => void | Promise<void>
  onWarning?: (message: string) => void
}

export interface LocalPlayer {
  open(study: SavedStudyDetail): void
  discard(): void
  isOpen(studyId: string): boolean
}

export function createLocalPlayer(
  audio: HTMLAudioElement,
  dependencies: LocalPlayerDependencies,
): LocalPlayer {
  const isVisible = dependencies.isVisible ?? (() => document.visibilityState === 'visible')
  let activeStudy: SavedStudyDetail | undefined
  let objectUrl: string | undefined
  let playing = false
  let checkpointTimer: ReturnType<typeof setInterval> | undefined

  const warn = () => {
    dependencies.onWarning?.(
      'Não foi possível salvar seu progresso. O áudio continua disponível para reprodução.',
    )
  }

  const persist = async (completed = false): Promise<void> => {
    if (activeStudy === undefined) return
    const study = activeStudy
    const positionSeconds = completed
      ? study.durationSeconds
      : Math.min(Math.max(audio.currentTime, 0), study.durationSeconds)
    try {
      await dependencies.updateProgress(study.studyId, {
        positionSeconds,
        ...(completed ? { completed: true } : {}),
      })
      if (completed) {
        await dependencies.onCompleted?.(study.studyId)
      }
    } catch {
      warn()
    }
  }

  const stopTimer = () => {
    if (checkpointTimer !== undefined) {
      clearInterval(checkpointTimer)
      checkpointTimer = undefined
    }
  }

  const startTimer = () => {
    stopTimer()
    checkpointTimer = setInterval(() => {
      if (playing && isVisible()) void persist()
    }, 5_000)
  }

  audio.addEventListener('loadedmetadata', () => {
    if (activeStudy !== undefined) {
      audio.currentTime = Math.min(
        activeStudy.progress.positionSeconds,
        activeStudy.durationSeconds,
      )
    }
  })
  audio.addEventListener('play', () => {
    playing = true
    startTimer()
  })
  audio.addEventListener('pause', () => {
    playing = false
    stopTimer()
    void persist()
  })
  audio.addEventListener('seeked', () => void persist())
  audio.addEventListener('ended', () => {
    playing = false
    stopTimer()
    void persist(true)
  })
  document.addEventListener('visibilitychange', () => {
    if (!isVisible()) void persist()
  })

  const discard = () => {
    stopTimer()
    playing = false
    activeStudy = undefined
    if (objectUrl !== undefined) {
      dependencies.revokeObjectUrl(objectUrl)
      objectUrl = undefined
    }
    audio.removeAttribute('src')
  }

  return {
    open(study): void {
      discard()
      activeStudy = study
      objectUrl = dependencies.createObjectUrl(study.audio)
      audio.src = objectUrl
    },
    discard,
    isOpen: (studyId) => activeStudy?.studyId === studyId,
  }
}
