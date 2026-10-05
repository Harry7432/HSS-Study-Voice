import type { TimelineDocument } from '../library/types'

export interface BlobUrlPort {
  createObjectUrl(blob: Blob): string
  revokeObjectUrl(url: string): void
}

export function slugifyLabel(label: string): string {
  const slug = label
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
  return slug.length > 0 ? slug : 'estudo'
}

export function canShareFiles(): boolean {
  if (typeof navigator === 'undefined') return false
  if (typeof navigator.share !== 'function' || typeof navigator.canShare !== 'function') {
    return false
  }
  try {
    const probe = new File(['probe'], 'probe.mp3', { type: 'audio/mpeg' })
    return navigator.canShare({ files: [probe] })
  } catch {
    return false
  }
}

export function downloadBlob(blob: Blob, fileName: string, urls: BlobUrlPort): void {
  const url = urls.createObjectUrl(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  link.rel = 'noopener'
  document.body.append(link)
  link.click()
  link.remove()
  urls.revokeObjectUrl(url)
}

export async function shareOrDownloadAudio(
  blob: Blob,
  fileName: string,
  label: string,
  urls: BlobUrlPort,
): Promise<void> {
  const file = new File([blob], fileName, { type: 'audio/mpeg' })
  if (typeof navigator.canShare === 'function' && navigator.canShare({ files: [file] })) {
    try {
      await navigator.share({ files: [file], title: label })
      return
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
    }
  }
  downloadBlob(blob, fileName, urls)
}

function formatSrtTimestamp(totalSeconds: number): string {
  const totalMillis = Math.max(0, Math.round(totalSeconds * 1000))
  const hours = Math.floor(totalMillis / 3_600_000)
  const minutes = Math.floor((totalMillis % 3_600_000) / 60_000)
  const seconds = Math.floor((totalMillis % 60_000) / 1000)
  const millis = totalMillis % 1000
  const pad = (value: number, length = 2) => value.toString().padStart(length, '0')
  return `${pad(hours)}:${pad(minutes)}:${pad(seconds)},${pad(millis, 3)}`
}

export function buildTimelineSrt(timeline: TimelineDocument): string | undefined {
  const sampleRateHz = timeline.audio.sample_rate_hz
  const blocks: string[] = []
  let counter = 1
  for (const chunk of timeline.chunks) {
    for (const sentence of chunk.sentences) {
      const start = formatSrtTimestamp(sentence.start_sample / sampleRateHz)
      const end = formatSrtTimestamp(sentence.end_sample / sampleRateHz)
      blocks.push(`${counter}\n${start} --> ${end}\n${sentence.text}\n`)
      counter += 1
    }
  }
  return blocks.length > 0 ? blocks.join('\n') : undefined
}
