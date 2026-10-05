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

interface StoredTimelineSentence {
  text: string
  start_sample: number
  end_sample: number
}

interface StoredTimeline {
  sample_rate_hz: number
  sentences: StoredTimelineSentence[]
}

async function readStoredTimeline(page: Page): Promise<StoredTimeline | undefined> {
  return page.evaluate(async ({ databaseName }) => {
    const database = await new Promise<IDBDatabase>((resolve, reject) => {
      const request = indexedDB.open(databaseName)
      request.onerror = () => reject(request.error)
      request.onsuccess = () => resolve(request.result)
    })
    const assets = await new Promise<Record<string, unknown>[]>((resolve, reject) => {
      const request = database.transaction('studyAssets', 'readonly').objectStore('studyAssets').getAll()
      request.onerror = () => reject(request.error)
      request.onsuccess = () => resolve(request.result)
    })
    database.close()
    const timeline = assets[0]?.timeline as
      | { audio: { sample_rate_hz: number }; chunks: { sentences: StoredTimelineSentence[] }[] }
      | undefined
    if (timeline === undefined) return undefined
    return {
      sample_rate_hz: timeline.audio.sample_rate_hz,
      sentences: timeline.chunks.flatMap((chunk) => chunk.sentences),
    }
  }, { databaseName: DB_NAME })
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

  await expect(page.locator('.status-line')).toHaveText('Áudio pronto e arquivado neste navegador.', {
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

  await expect(page.locator('.status-line')).toContainText(
    'O áudio foi gerado, mas não pôde ser salvo na biblioteca local.',
    { timeout: 90_000 },
  )
  await expect(page.locator('audio')).toHaveAttribute('src', /^blob:/)
  expect(apiRequests).toHaveLength(3)
  expect(apiRequests.every((url) => new URL(url).origin === 'http://127.0.0.1:5173')).toBe(true)
})

test('exibe o texto sincronizado ao reabrir um estudo salvo e avança a reprodução ao clicar numa frase (SC-002)', async ({
  page,
}) => {
  test.setTimeout(120_000)
  await page.goto('/')

  await page.getByLabel('Texto do estudo').fill(STUDY_TEXT)
  await page.getByLabel('Rótulo opcional').fill('Texto sincronizado')
  await page.getByRole('button', { name: 'Gerar estudo em áudio' }).click()
  await expect(page.locator('.status-line')).toHaveText('Áudio pronto e arquivado neste navegador.', {
    timeout: 90_000,
  })

  await page.reload()
  await page.getByRole('button', { name: 'Ouvir' }).click()
  const readingView = page.locator('[data-reading-view]')
  await expect(readingView).toContainText('Primeira frase para o estudo.')
  await expect(readingView).toContainText('Segunda frase para validar a retomada.')

  const audio = page.locator('audio')
  await audio.evaluate((element: HTMLAudioElement) => {
    if (element.readyState >= HTMLMediaElement.HAVE_METADATA) return undefined
    return new Promise<void>((resolve) => {
      element.addEventListener('loadedmetadata', () => resolve(), { once: true })
    })
  })

  const secondSentence = readingView.getByText('Segunda frase para validar a retomada.')
  await secondSentence.click()

  await expect.poll(() => audio.evaluate((element: HTMLAudioElement) => element.currentTime)).toBeGreaterThan(0.1)
  await expect(secondSentence).toHaveAttribute('aria-current', 'true')
})

test('mantém o texto sincronizado e a navegação por clique funcionando totalmente offline (FR-012/SC-006)', async ({
  page,
}) => {
  test.setTimeout(120_000)
  await page.goto('/')

  await page.getByLabel('Texto do estudo').fill(STUDY_TEXT)
  await page.getByLabel('Rótulo opcional').fill('Texto offline')
  await page.getByRole('button', { name: 'Gerar estudo em áudio' }).click()
  await expect(page.locator('.status-line')).toHaveText('Áudio pronto e arquivado neste navegador.', {
    timeout: 90_000,
  })

  const readingView = page.locator('[data-reading-view]')
  await expect(readingView).toContainText('Primeira frase para o estudo.')
  await expect(readingView).toContainText('Segunda frase para validar a retomada.')

  const networkRequests: string[] = []
  page.on('request', (request) => {
    // blob: reads (the already-loaded <audio> re-touching its own object URL) surface as
    // "request" events too, even though no network is involved; only http(s) calls count here.
    if (request.url().startsWith('http')) networkRequests.push(request.url())
  })
  await page.context().setOffline(true)

  const audio = page.locator('audio')
  const secondSentence = readingView.getByText('Segunda frase para validar a retomada.')
  await secondSentence.click()
  await expect.poll(() => audio.evaluate((element: HTMLAudioElement) => element.currentTime)).toBeGreaterThan(0.1)
  await expect(secondSentence).toHaveAttribute('aria-current', 'true')
  await expect(readingView).toContainText('Primeira frase para o estudo.')

  await page.context().setOffline(false)
  expect(networkRequests).toHaveLength(0)
})

test('atualiza o destaque em até 300ms da transição real de frase durante a reprodução (SC-001, componente de latência)', async ({
  page,
}) => {
  test.setTimeout(120_000)
  await page.goto('/')

  const text = 'Primeira frase curta. Segunda frase curta. Terceira frase curta. Quarta frase curta.'
  await page.getByLabel('Texto do estudo').fill(text)
  await page.getByLabel('Rótulo opcional').fill('Texto latência')
  await page.getByRole('button', { name: 'Gerar estudo em áudio' }).click()
  await expect(page.locator('.status-line')).toHaveText('Áudio pronto e arquivado neste navegador.', {
    timeout: 90_000,
  })

  const timeline = await readStoredTimeline(page)
  expect(timeline).toBeDefined()
  const boundarySeconds = timeline!.sentences
    .slice(1)
    .map((sentence) => sentence.start_sample / timeline!.sample_rate_hz)
  expect(boundarySeconds.length).toBeGreaterThanOrEqual(3)

  const delaysMs = await page.evaluate(async (boundaries: number[]) => {
    const audio = document.querySelector('audio') as HTMLAudioElement
    const sentenceElements = Array.from(document.querySelectorAll<HTMLElement>('.reading-sentence'))
    const crossedAt = new Array<number | undefined>(boundaries.length).fill(undefined)
    const highlightedAt = new Array<number | undefined>(boundaries.length).fill(undefined)

    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        const target = mutation.target as HTMLElement
        if (target.getAttribute('aria-current') !== 'true') continue
        const elementIndex = sentenceElements.indexOf(target)
        const boundaryIndex = elementIndex - 1
        if (boundaryIndex >= 0 && highlightedAt[boundaryIndex] === undefined) {
          highlightedAt[boundaryIndex] = performance.now()
        }
      }
    })
    sentenceElements.forEach((element) =>
      observer.observe(element, { attributes: true, attributeFilter: ['aria-current'] }),
    )

    const onTimeUpdate = () => {
      boundaries.forEach((boundary, index) => {
        if (crossedAt[index] === undefined && audio.currentTime >= boundary) {
          crossedAt[index] = performance.now()
        }
      })
    }
    audio.addEventListener('timeupdate', onTimeUpdate)

    await audio.play()
    const lastBoundary = boundaries[boundaries.length - 1]!
    await new Promise<void>((resolve) => {
      const checkDone = () => {
        if (audio.currentTime >= lastBoundary + 0.5 || audio.ended) {
          resolve()
        } else {
          requestAnimationFrame(checkDone)
        }
      }
      requestAnimationFrame(checkDone)
    })
    audio.removeEventListener('timeupdate', onTimeUpdate)
    observer.disconnect()
    audio.pause()

    return boundaries.map((_, index) => {
      const crossed = crossedAt[index]
      const highlighted = highlightedAt[index]
      if (crossed === undefined || highlighted === undefined) return Number.POSITIVE_INFINITY
      return highlighted - crossed
    })
  }, boundarySeconds)

  for (const delayMs of delaysMs) {
    expect(delayMs).toBeLessThan(300)
  }
})
