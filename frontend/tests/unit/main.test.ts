import { expect, it, vi } from 'vitest'

import { mountApp } from '../../src/main'
import { makeStudyResult } from '../setup'

it('keeps generated audio playable and warns when only local storage fails', async () => {
  const root = document.createElement('div')
  const result = makeStudyResult()
  const createStudy = vi.fn().mockResolvedValue({
    result,
    label: 'Citologia aplicada',
    saved: false,
    libraryWarning: 'O áudio foi gerado, mas não pôde ser salvo na biblioteca local.',
  })
  const listStudies = vi.fn().mockResolvedValue([])
  await mountApp(root, {
    createStudy,
    listStudies,
    createObjectUrl: vi.fn().mockReturnValue('blob:estudo-gerado'),
  })
  const text = root.querySelector<HTMLTextAreaElement>('[name="text"]')!
  const label = root.querySelector<HTMLInputElement>('[name="label"]')!
  text.value = 'Texto para o estudo.'
  label.value = 'Citologia aplicada'

  root.querySelector('form')!.dispatchEvent(new SubmitEvent('submit', { cancelable: true }))

  await vi.waitFor(() => {
    expect(createStudy).toHaveBeenCalledWith({
      text: 'Texto para o estudo.',
      label: 'Citologia aplicada',
    })
  })
  expect(root.querySelector('audio')?.getAttribute('src')).toBe('blob:estudo-gerado')
  expect(root.querySelector('[role="status"]')?.textContent).toContain(
    'O áudio foi gerado, mas não pôde ser salvo',
  )
  expect(root.querySelector('[data-now-playing]')?.classList).toContain('is-visible')
})
