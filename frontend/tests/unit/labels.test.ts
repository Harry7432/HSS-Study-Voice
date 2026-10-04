import { describe, expect, it } from 'vitest'

import { resolveStudyLabel } from '../../src/library/labels'

describe('resolveStudyLabel', () => {
  it('normalizes a manual label', () => {
    expect(resolveStudyLabel('Texto original.', '  Revisão   de   biologia  ')).toBe(
      'Revisão de biologia',
    )
  })

  it('rejects a manual label longer than 80 normalized characters', () => {
    expect(() => resolveStudyLabel('Texto original.', 'a'.repeat(81))).toThrow(
      'O rótulo deve ter no máximo 80 caracteres.',
    )
  })

  it('derives a label when the manual value is absent or blank', () => {
    expect(resolveStudyLabel('  Introdução   à genética molecular.  ')).toBe(
      'Introdução à genética molecular.',
    )
    expect(resolveStudyLabel('Citologia aplicada.', '   ')).toBe('Citologia aplicada.')
  })

  it('cuts an automatic label on a word boundary within 80 characters including ellipsis', () => {
    const text =
      'Este material apresenta fundamentos detalhados de biologia celular para uma revisão completa.'

    const label = resolveStudyLabel(text)

    expect(label).toBe(
      'Este material apresenta fundamentos detalhados de biologia celular para uma…',
    )
    expect(label.length).toBeLessThanOrEqual(80)
  })

  it('rejects source text without visible characters', () => {
    expect(() => resolveStudyLabel('   \n  ')).toThrow('O texto não pode ser vazio.')
  })
})
