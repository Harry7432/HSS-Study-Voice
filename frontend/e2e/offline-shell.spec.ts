import { execSync } from 'node:child_process'
import { readFileSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { expect, test } from '@playwright/test'

const STUDY_TEXT = 'Primeira frase do estudo offline. Segunda frase para o texto sincronizado.'
const STUDY_LABEL = 'Estudo offline'

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const indexHtmlPath = path.join(frontendRoot, 'index.html')

function rebuild(): void {
  execSync('npm run build', { cwd: frontendRoot, stdio: 'ignore' })
}

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
  await expect(page.locator('.status-line')).toHaveText('Áudio pronto e arquivado neste navegador.', {
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

test('manifesto expõe nome, exibição e os três ícones exigidos para instalabilidade (US2, SC-002)', async ({
  page,
}) => {
  await page.goto('/')

  const manifestHref = await page.locator('link[rel="manifest"]').getAttribute('href')
  expect(manifestHref).not.toBeNull()
  const manifestUrl = new URL(manifestHref!, page.url()).toString()

  const manifestResponse = await page.request.get(manifestUrl)
  expect(manifestResponse.ok()).toBe(true)
  const manifest = await manifestResponse.json()

  expect(manifest.name).toBe('HSS Study Voice')
  expect(typeof manifest.short_name).toBe('string')
  expect(manifest.short_name.length).toBeGreaterThan(0)
  expect(manifest.display).toBe('standalone')
  expect(manifest.background_color).toBe('#000000')
  expect(manifest.theme_color).toBe('#000000')

  const icons = manifest.icons as { src: string; sizes: string; purpose?: string }[]
  const signatures = icons.map((icon) => `${icon.sizes}:${icon.purpose ?? 'any'}`)
  expect(signatures).toContain('192x192:any')
  expect(signatures).toContain('512x512:any')
  expect(signatures).toContain('512x512:maskable')

  for (const icon of icons) {
    const iconUrl = new URL(icon.src, page.url()).toString()
    const iconResponse = await page.request.get(iconUrl)
    expect(iconResponse.ok()).toBe(true)
  }
})

test('uma atualização publicada não interrompe a reprodução em andamento, e só é aplicada mediante ação explícita (US1 edge case, SC-005)', async ({
  page,
}) => {
  test.setTimeout(240_000)
  const originalIndexHtml = readFileSync(indexHtmlPath, 'utf-8')

  try {
    await page.goto('/')
    await page.evaluate(() => navigator.serviceWorker.ready)

    await page.getByLabel('Texto do estudo').fill(STUDY_TEXT)
    await page.getByLabel('Rótulo opcional').fill(`${STUDY_LABEL} atualização`)
    await page.getByRole('button', { name: 'Gerar estudo em áudio' }).click()
    await expect(page.locator('.status-line')).toHaveText('Áudio pronto e arquivado neste navegador.', {
      timeout: 90_000,
    })

    // O workbox-window (usado internamente pelo vite-plugin-pwa) só recarrega sozinho após a
    // ação do usuário quando já havia um service worker no controle *antes* desta navegação
    // (sinal isUpdate). Isso é o que acontece numa sessão real (visita de hoje depois de uma
    // instalação anterior); replicamos isso aqui com um reload único logo após a primeira
    // instalação, antes de simular a nova versão.
    await page.reload()
    await page.evaluate(() => navigator.serviceWorker.ready)
    await page.getByRole('button', { name: 'Ouvir' }).click()

    const audio = page.locator('audio')
    // O estudo gerado para este teste dura só alguns segundos; o rebuild + a verificação de
    // atualização abaixo levam bem mais tempo que isso. loop=true garante que "em andamento"
    // continue verdadeiro durante todo o teste, em vez de testar só a sorte do timing.
    await audio.evaluate((element: HTMLAudioElement) => {
      element.loop = true
      return element.play()
    })
    await expect
      .poll(() => audio.evaluate((element: HTMLAudioElement) => element.currentTime))
      .toBeGreaterThan(0)

    // Publica uma nova versão do app shell (comentário trivial) enquanto esta aba continua aberta.
    writeFileSync(
      indexHtmlPath,
      originalIndexHtml.replace('</head>', `<!-- build:${Date.now()} --></head>`),
    )
    rebuild()

    await page.evaluate(async () => {
      const registration = await navigator.serviceWorker.getRegistration()
      await registration?.update()
    })

    await expect(page.locator('.update-notice')).toBeVisible({ timeout: 30_000 })

    const positionBeforeApply = await audio.evaluate((element: HTMLAudioElement) => element.currentTime)
    expect(positionBeforeApply).toBeGreaterThan(0)
    await expect(audio).not.toHaveJSProperty('paused', true)

    await Promise.all([
      page.waitForEvent('load'),
      page.getByRole('button', { name: 'Atualizar agora' }).click(),
    ])

    await expect(page.getByRole('heading', { name: 'HSS Study Voice' })).toBeVisible()
  } finally {
    writeFileSync(indexHtmlPath, originalIndexHtml)
    rebuild()
  }
})
