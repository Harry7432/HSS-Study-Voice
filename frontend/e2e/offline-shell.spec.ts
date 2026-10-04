import { expect, test } from '@playwright/test'

const STUDY_TEXT = 'Primeira frase do estudo offline. Segunda frase para o texto sincronizado.'
const STUDY_LABEL = 'Estudo offline'

test('recarrega offline depois de uma visita anterior, sem tela de erro do navegador (US1, SC-001)', async ({
  page,
  context,
}) => {
  test.setTimeout(150_000)

  await page.goto('/')
  await page.evaluate(() => navigator.serviceWorker.ready)

  await context.setOffline(true)
  await page.reload()

  await expect(page.getByRole('heading', { name: 'HSS Study Voice' })).toBeVisible()
})

test('biblioteca, reprodução e texto sincronizado funcionam offline, sem requisição de rede bem-sucedida (US1, SC-001)', async ({
  page,
  context,
}) => {
  test.setTimeout(150_000)

  await page.goto('/')
  await page.evaluate(() => navigator.serviceWorker.ready)

  await page.getByLabel('Texto do estudo').fill(STUDY_TEXT)
  await page.getByLabel('Rótulo opcional').fill(STUDY_LABEL)
  await page.getByRole('button', { name: 'Gerar estudo em áudio' }).click()
  await expect(page.getByRole('status')).toHaveText('Áudio pronto e arquivado neste navegador.', {
    timeout: 90_000,
  })

  const networkResponses: string[] = []
  page.on('response', (response) => {
    const url = response.url()
    if (url.startsWith('blob:') || url.startsWith('data:')) return
    if (response.ok() && !response.fromServiceWorker()) networkResponses.push(url)
  })

  await context.setOffline(true)
  await page.reload()

  await expect(page.getByRole('heading', { name: 'HSS Study Voice' })).toBeVisible()

  const library = page.getByRole('region', { name: 'Biblioteca local' })
  await expect(library.getByRole('heading', { name: STUDY_LABEL })).toBeVisible()

  await page.getByRole('button', { name: 'Ouvir' }).click()
  const audio = page.locator('audio')
  await expect(audio).toHaveAttribute('src', /^blob:/)

  const readingView = page.locator('[data-reading-view]')
  await expect(readingView).toContainText('Primeira frase do estudo offline.')

  await audio.evaluate((element: HTMLAudioElement) => {
    if (element.readyState >= HTMLMediaElement.HAVE_METADATA) return undefined
    return new Promise<void>((resolve) => {
      element.addEventListener('loadedmetadata', () => resolve(), { once: true })
    })
  })
  await audio.evaluate((element: HTMLAudioElement) => element.play())
  await expect
    .poll(() => audio.evaluate((element: HTMLAudioElement) => element.currentTime))
    .toBeGreaterThan(0)

  expect(networkResponses).toEqual([])
})
