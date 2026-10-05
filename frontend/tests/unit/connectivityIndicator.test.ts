import { describe, expect, it } from 'vitest'

import { createConnectivityIndicator } from '../../src/ui/connectivityIndicator'

describe('connectivityIndicator', () => {
  it('renders "Online" inside role=status/aria-live=polite, with a non-color glyph, when online', () => {
    window.dispatchEvent(new Event('online'))
    const container = document.createElement('div')

    createConnectivityIndicator(container)

    const status = container.querySelector('[role="status"]')
    expect(status).not.toBeNull()
    expect(status?.getAttribute('aria-live')).toBe('polite')
    expect(status?.textContent).toContain('Online')
    expect(status?.getAttribute('data-online')).toBe('true')
    expect(container.querySelector('[data-connectivity-glyph]')?.innerHTML).not.toBe('')
  })

  it('updates to "Offline" with a different glyph when the offline event fires, without a reload', () => {
    window.dispatchEvent(new Event('online'))
    const container = document.createElement('div')
    createConnectivityIndicator(container)
    const onlineGlyph = container.querySelector('[data-connectivity-glyph]')?.innerHTML

    window.dispatchEvent(new Event('offline'))

    const status = container.querySelector('[role="status"]')
    expect(status?.textContent).toContain('Offline')
    expect(status?.getAttribute('data-online')).toBe('false')
    expect(container.querySelector('[data-connectivity-glyph]')?.innerHTML).not.toBe(onlineGlyph)

    window.dispatchEvent(new Event('online'))
  })

  it('stops updating once destroyed', () => {
    window.dispatchEvent(new Event('online'))
    const container = document.createElement('div')
    const indicator = createConnectivityIndicator(container)

    indicator.destroy()
    window.dispatchEvent(new Event('offline'))

    const status = container.querySelector('[role="status"]')
    expect(status?.textContent).toContain('Online')

    window.dispatchEvent(new Event('online'))
  })
})
