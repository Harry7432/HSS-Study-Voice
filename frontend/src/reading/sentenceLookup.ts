import type { TimelineDocument, TimelineSentence } from '../library/types'

export function flattenSentences(timeline: TimelineDocument): TimelineSentence[] {
  return timeline.chunks.flatMap((chunk) => chunk.sentences)
}

export function findSentenceIndexAtSample(
  sentences: readonly TimelineSentence[],
  samplePosition: number,
): number {
  const lastIndex = sentences.length - 1
  if (samplePosition <= 0) return 0
  const last = sentences[lastIndex]
  if (last === undefined || samplePosition >= last.end_sample) return lastIndex

  let low = 0
  let high = lastIndex
  while (low < high) {
    const mid = Math.floor((low + high + 1) / 2)
    const candidate = sentences[mid]
    if (candidate !== undefined && candidate.start_sample <= samplePosition) {
      low = mid
    } else {
      high = mid - 1
    }
  }
  return low
}
