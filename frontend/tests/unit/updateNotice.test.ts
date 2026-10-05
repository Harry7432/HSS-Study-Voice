import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

interface CapturedRegisterSWOptions {
  onNeedRefresh?: () => void
  onOfflineReady?: () => void
}

let capturedOptions: CapturedRegisterSWOptions = {}
const updateSW = vi.fn().mockResolvedValue(undefined)
const registerSW = vi.fn((options?: CapturedRegisterSWOptions) => {
  capturedOptions = options ?? {}
  return updateSW
})

vi.mock('virtual:pwa-register', () => ({ registerSW }))

const { createUpdateNotice } = await import('../../src/ui/updateNotice')

function setServiceWorkerSupport(supported: boolean): void {
  if (supported) {
    Object.defineProperty(navigator, 'serviceWorker', { configurable: true, value: {} })
  } else {
    delete (navigator as unknown as Record<string, unknown>).serviceWorker
  }
}

describe('updateNotice', () => {
  beforeEach(() => {
    capturedOptions = {}
    setServiceWorkerSupport(true)
  })

  afterEach(() => {
    delete (navigator as unknown as Record<string, unknown>).serviceWorker
  })

  it('starts idle with no visible notice', () => {
    const container = document.createElement('div')

    const controller = createUpdateNotice(container)

    expect(controller.getState()).toBe('idle')
    expect(container.querySelector('[role="status"]')).toBeNull()
  })

  it('transitions to "available" and shows a non-blocking notice when onNeedRefresh fires', () => {
    const container = document.createElement('div')
    const controller = createUpdateNotice(container)

    capturedOptions.onNeedRefresh?.()

    expect(controller.getState()).toBe('available')
    expect(container.querySelector('[role="status"]')).not.toBeNull()
    expect(updateSW).not.toHaveBeenCalled()
  })

  it('only calls updateSW(true) after an explicit user action, transitioning to "applying"', () => {
    const container = document.createElement('div')
    const controller = createUpdateNotice(container)
    capturedOptions.onNeedRefresh?.()

    controller.apply()

    expect(controller.getState()).toBe('applying')
    expect(updateSW).toHaveBeenCalledWith(true)
  })

  it('never calls updateSW automatically, only onNeedRefresh firing is not enough', () => {
    const container = document.createElement('div')
    createUpdateNotice(container)

    capturedOptions.onNeedRefresh?.()

    expect(updateSW).not.toHaveBeenCalled()
  })

  it('stays idle without throwing or registering when navigator.serviceWorker is unavailable (FR-008)', () => {
    setServiceWorkerSupport(false)
    const container = document.createElement('div')

    const controller = createUpdateNotice(container)

    expect(controller.getState()).toBe('idle')
    expect(container.querySelector('[role="status"]')).toBeNull()
    expect(registerSW).not.toHaveBeenCalled()
  })
})
