import { expect, test, type Page } from '@playwright/test'

const DB_NAME = 'hss-study-library'
const STUDY_TEXT = 'Primeira frase para o estudo. Segunda frase para validar a retomada.'
const STUDY_LABEL = 'Fluxo local completo'

interface StoredStudyState {
  metadataCount: number
  assetsCount: number
  studyId: string | undefined
  positionSeconds: number | undefined
  completed: boolean | undefined
}

async function readStoredStudy(page: Page): Promise<StoredStudyState> {
  return page.evaluate(async ({ databaseName }) => {
    const database = await new Promise<IDBDatabase>((resolve, reject) => {
      const request = indexedDB.open(databaseName)
      request.onerror = () => reject(request.error)
      request.onsuccess = () => resolve(request.result)
    })
    const transaction = database.transaction(['studyMetadata', 'studyAssets'], 'readonly')
    const metadataStore = transaction.objectStore('studyMetadata')
    const assetsStore = transaction.objectStore('studyAssets')
    const metadata = await new Promise<Record<string, unknown>[]>((resolve, reject) => {
      const request = metadataStore.getAll()
      request.onerror = () => reject(request.error)
      request.onsuccess = () => resolve(request.result)
    })
    const assetsCount = await new Promise<number>((resolve, reject) => {
      const request = assetsStore.count()
      request.onerror = () => reject(request.error)
      request.onsuccess = () => resolve(request.result)
    })
    database.close()
    const study = metadata[0]
    const progress = study?.progress as Record<string, unknown> | undefined
    return {
      metadataCount: metadata.length,
      assetsCount,
      studyId: study?.studyId as string | undefined,
      positionSeconds: progress?.positionSeconds as number | undefined,
      completed: progress?.completed as boolean | undefined,
    }
  }, { databaseName: DB_NAME })
}

test('gera, salva, retoma, conclui offline e remove o estudo local', async ({ page }) => {
  test.setTimeout(120_000)
  await page.goto('/')

  await page.getByLabel('Texto do estudo').fill(STUDY_TEXT)
  await page.getByLabel('Rótulo opcional').fill(STUDY_LABEL)
  await page.getByRole('button', { name: 'Gerar estudo em áudio' }).click()

  await expect(page.getByRole('status')).toHaveText('Áudio pronto e arquivado neste navegador.', {
    timeout: 90_000,
  })
  const library = page.getByRole('region', { name: 'Biblioteca local' })
  await expect(library.getByRole('heading', { name: STUDY_LABEL })).toBeVisible()
  await expect.poll(() => readStoredStudy(page)).toMatchObject({
    metadataCount: 1,
    assetsCount: 1,
    positionSeconds: 0,
    completed: false,
  })

  await page.getByRole('button', { name: 'Ouvir' }).click()
  const audio = page.locator('audio')
  await expect(audio).toHaveAttribute('src', /^blob:/)
  const checkpoint = await page.locator('audio').evaluate((element: HTMLAudioElement) => {
    const position = Math.min(1.25, element.duration / 2)
    element.currentTime = position
    element.dispatchEvent(new Event('pause'))
    return position
  })
  await expect.poll(async () => (await readStoredStudy(page)).positionSeconds).toBeCloseTo(checkpoint, 2)

  await page.reload()
  await page.getByRole('button', { name: 'Ouvir' }).click()
  await page.locator('audio').evaluate((element: HTMLAudioElement) => {
    if (element.readyState >= HTMLMediaElement.HAVE_METADATA) return
    return new Promise<void>((resolve) => {
      element.addEventListener('loadedmetadata', () => resolve(), { once: true })
    })
  })
  const resumedAt = await page.locator('audio').evaluate((element: HTMLAudioElement) => element.currentTime)
  expect(Math.abs(resumedAt - checkpoint)).toBeLessThanOrEqual(1)

  await page.route(/\/api\/v1\//, (route) => route.abort())
  await page.reload()
  await expect(library.getByRole('heading', { name: STUDY_LABEL })).toBeVisible()
  await page.getByRole('button', { name: 'Ouvir' }).click()
  await expect(page.locator('audio')).toHaveAttribute('src', /^blob:/)
  await page.locator('audio').evaluate((element: HTMLAudioElement) => {
    element.dispatchEvent(new Event('ended'))
  })
  await expect(page.getByText('Concluído')).toBeVisible()
  await expect.poll(async () => (await readStoredStudy(page)).completed).toBe(true)

  page.once('dialog', (dialog) => dialog.accept())
  await page.getByRole('button', { name: 'Remover' }).click()
  await expect(page.getByText('Nenhum estudo arquivado ainda.')).toBeVisible()
  await expect.poll(() => readStoredStudy(page)).toMatchObject({
    metadataCount: 0,
    assetsCount: 0,
  })
})

test('mantém o áudio reproduzível quando o armazenamento local está indisponível', async ({
  page,
}) => {
  test.setTimeout(120_000)
  await page.addInitScript(() => {
    Object.defineProperty(window, 'indexedDB', {
      configurable: true,
      value: {
        open: () => {
          throw new DOMException('Armazenamento indisponível', 'QuotaExceededError')
        },
      },
    })
  })
  const apiRequests: string[] = []
  page.on('request', (request) => {
    if (new URL(request.url()).pathname.startsWith('/api/')) apiRequests.push(request.url())
  })
  await page.goto('/')

  await page.getByLabel('Texto do estudo').fill(STUDY_TEXT)
  await page.getByLabel('Rótulo opcional').fill('Sem armazenamento')
  await page.getByRole('button', { name: 'Gerar estudo em áudio' }).click()

  await expect(page.getByRole('status')).toContainText(
    'O áudio foi gerado, mas não pôde ser salvo na biblioteca local.',
    { timeout: 90_000 },
  )
  await expect(page.locator('audio')).toHaveAttribute('src', /^blob:/)
  expect(apiRequests).toHaveLength(3)
  expect(apiRequests.every((url) => new URL(url).origin === 'http://127.0.0.1:5173')).toBe(true)
})
