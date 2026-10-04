import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { getConnectivityStatus, subscribeToConnectivity } from '../../src/platform/connectivity'

function setNavigatorOnLine(value: boolean): void {
  Object.defineProperty(navigator, 'onLine', { configurable: true, value })
}

describe('connectivity', () => {
  let originalOnLine: boolean

  beforeEach(() => {
    originalOnLine = navigator.onLine
  })

  afterEach(() => {
    setNavigatorOnLine(originalOnLine)
  })

  it('reflects navigator.onLine as the initial state at module load, for both values', async () => {
    setNavigatorOnLine(true)
    vi.resetModules()
    const online = await import('../../src/platform/connectivity')
    expect(online.getConnectivityStatus().online).toBe(true)

    setNavigatorOnLine(false)
    vi.resetModules()
    const offline = await import('../../src/platform/connectivity')
    expect(offline.getConnectivityStatus().online).toBe(false)
  })

  it('updates to false and notifies subscribers when the offline event fires', () => {
    setNavigatorOnLine(true)
    const listener = vi.fn()
    const unsubscribe = subscribeToConnectivity(listener)

    window.dispatchEvent(new Event('offline'))

    expect(getConnectivityStatus().online).toBe(false)
    expect(listener).toHaveBeenCalledWith({ online: false })
    unsubscribe()
  })

  it('updates to true and notifies subscribers when the online event fires', () => {
    setNavigatorOnLine(false)
    const listener = vi.fn()
    const unsubscribe = subscribeToConnectivity(listener)

    window.dispatchEvent(new Event('online'))

    expect(getConnectivityStatus().online).toBe(true)
    expect(listener).toHaveBeenCalledWith({ online: true })
    unsubscribe()
  })

  it('notifies every subscriber with the same state', () => {
    setNavigatorOnLine(true)
    const first = vi.fn()
    const second = vi.fn()
    const unsubscribeFirst = subscribeToConnectivity(first)
    const unsubscribeSecond = subscribeToConnectivity(second)

    window.dispatchEvent(new Event('offline'))

    expect(first).toHaveBeenCalledWith({ online: false })
    expect(second).toHaveBeenCalledWith({ online: false })
    unsubscribeFirst()
    unsubscribeSecond()
  })

  it('stops notifying a subscriber after it unsubscribes', () => {
    setNavigatorOnLine(true)
    const listener = vi.fn()
    const unsubscribe = subscribeToConnectivity(listener)
    unsubscribe()

    window.dispatchEvent(new Event('offline'))

    expect(listener).not.toHaveBeenCalled()
  })
})
