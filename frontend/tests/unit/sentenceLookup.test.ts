import { describe, expect, it } from 'vitest'

import type { TimelineDocument, TimelineSentence } from '../../src/library/types'
import { findSentenceIndexAtSample, flattenSentences } from '../../src/reading/sentenceLookup'

function sentence(index: number, start: number, end: number): TimelineSentence {
  return { index, text: `Frase ${index}.`, start_sample: start, end_sample: end }
}

function timelineWithThreeSentences(): TimelineDocument {
  return {
    schema_version: 1,
    audio: {
      filename: `${'a'.repeat(32)}.mp3`,
      sha256: 'b'.repeat(64),
      sample_rate_hz: 22_050,
      total_samples: 300,
    },
    chunks: [
      {
        index: 0,
        start_sample: 0,
        end_sample: 200,
        sentences: [sentence(0, 0, 100), sentence(1, 100, 200)],
      },
      {
        index: 1,
        start_sample: 200,
        end_sample: 300,
        sentences: [sentence(0, 200, 300)],
      },
    ],
  }
}

function largeTimeline(sentenceCount: number): TimelineSentence[] {
  const step = 10
  return Array.from({ length: sentenceCount }, (_, index) =>
    sentence(index, index * step, index * step + step),
  )
}

describe('flattenSentences', () => {
  it('concatenates chunk.sentences in chunk order', () => {
    const flattened = flattenSentences(timelineWithThreeSentences())

    expect(flattened).toHaveLength(3)
    expect(flattened.map((item) => item.start_sample)).toEqual([0, 100, 200])
  })
})

describe('findSentenceIndexAtSample', () => {
  const sentences = flattenSentences(timelineWithThreeSentences())

  it('resolves a sample at the start of the first sentence', () => {
    expect(findSentenceIndexAtSample(sentences, 0)).toBe(0)
  })

  it('resolves a sample in the middle of the first sentence', () => {
    expect(findSentenceIndexAtSample(sentences, 50)).toBe(0)
  })

  it('resolves a sample at the end of the first sentence (exclusive) to the next sentence', () => {
    expect(findSentenceIndexAtSample(sentences, 100)).toBe(1)
  })

  it('resolves a sample in the middle of an intermediate sentence', () => {
    expect(findSentenceIndexAtSample(sentences, 150)).toBe(1)
  })

  it('resolves a sample in the middle of the last sentence', () => {
    expect(findSentenceIndexAtSample(sentences, 250)).toBe(2)
  })

  it('resolves the exact boundary between two sentences consistently to the later one', () => {
    expect(findSentenceIndexAtSample(sentences, 200)).toBe(2)
  })

  it('resolves a sample equal to total_samples to the last sentence', () => {
    expect(findSentenceIndexAtSample(sentences, 300)).toBe(2)
  })

  it('resolves a sample beyond total_samples (overshoot) to the last sentence', () => {
    expect(findSentenceIndexAtSample(sentences, 10_000)).toBe(2)
  })

  it('resolves a negative sample to the first sentence', () => {
    expect(findSentenceIndexAtSample(sentences, -1)).toBe(0)
  })

  it('resolves correctly across scattered positions in a timeline with 5,000+ sentences', () => {
    const many = largeTimeline(5_000)

    expect(findSentenceIndexAtSample(many, 0)).toBe(0)
    expect(findSentenceIndexAtSample(many, 5)).toBe(0)
    expect(findSentenceIndexAtSample(many, 25_005)).toBe(2_500)
    expect(findSentenceIndexAtSample(many, 49_995)).toBe(4_999)
    expect(findSentenceIndexAtSample(many, 49_999)).toBe(4_999)
    expect(findSentenceIndexAtSample(many, 1_234 * 10 + 7)).toBe(1_234)
  })
})
