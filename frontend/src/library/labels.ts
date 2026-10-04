const MAX_LABEL_LENGTH = 80

function normalizeSpaces(value: string): string {
  return value.trim().replace(/\s+/g, ' ')
}

export function resolveStudyLabel(sourceText: string, manualLabel?: string): string {
  const normalizedText = normalizeSpaces(sourceText)
  if (normalizedText.length === 0) {
    throw new Error('O texto não pode ser vazio.')
  }

  const normalizedManualLabel = normalizeSpaces(manualLabel ?? '')
  if (normalizedManualLabel.length > 0) {
    if (normalizedManualLabel.length > MAX_LABEL_LENGTH) {
      throw new Error('O rótulo deve ter no máximo 80 caracteres.')
    }
    return normalizedManualLabel
  }

  if (normalizedText.length <= MAX_LABEL_LENGTH) {
    return normalizedText
  }

  const availableText = normalizedText.slice(0, MAX_LABEL_LENGTH - 1)
  const wordBoundary = availableText.lastIndexOf(' ')
  const truncated = wordBoundary > 0 ? availableText.slice(0, wordBoundary) : availableText
  return `${truncated.trimEnd()}…`
}
