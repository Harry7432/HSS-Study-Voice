import { expect, test } from '@playwright/test'

test('bloqueia a criação de estudo offline, sem disparar requisição para /api/v1/studies (US3, SC-003)', async ({
  page,
  context,
}) => {
  await page.goto('/')

  const studyRequests: string[] = []
  page.on('request', (request) => {
    if (new URL(request.url()).pathname.startsWith('/api/v1/studies')) studyRequests.push(request.url())
  })

  await context.setOffline(true)

  await page.getByLabel('Texto do estudo').fill('Texto que não deveria ser enviado enquanto offline.')
  await page.getByRole('button', { name: 'Gerar estudo em áudio' }).click()

  await expect(page.locator('.status-line')).toContainText('offline')
  expect(studyRequests).toEqual([])

  await context.setOffline(false)
})

test('o indicador de conectividade reflete online/offline automaticamente, sem recarregar a página, e a criação volta a ficar disponível (US3, FR-004)', async ({
  page,
  context,
}) => {
  test.setTimeout(120_000)
  await page.goto('/')

  const indicator = page.locator('.connectivity-indicator')
  await expect(indicator).toHaveText(/Online/)
  await expect(indicator).toHaveAttribute('data-online', 'true')

  await context.setOffline(true)
  await expect(indicator).toHaveText(/Offline/)
  await expect(indicator).toHaveAttribute('data-online', 'false')

  await context.setOffline(false)
  await expect(indicator).toHaveText(/Online/)
  await expect(indicator).toHaveAttribute('data-online', 'true')

  await page.getByLabel('Texto do estudo').fill('Texto de verificação após reconexão.')
  await page.getByRole('button', { name: 'Gerar estudo em áudio' }).click()
  await expect(page.locator('.status-line')).toHaveText('Áudio pronto e arquivado neste navegador.', {
    timeout: 90_000,
  })
})
