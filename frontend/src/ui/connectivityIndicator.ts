import { getConnectivityStatus, subscribeToConnectivity } from '../platform/connectivity'
import type { ConnectivityStatus } from '../platform/connectivity'

export interface ConnectivityIndicatorController {
  destroy(): void
}

const ONLINE_GLYPH = `<svg class="connectivity-glyph-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
  <circle cx="12" cy="12" r="2.6" fill="currentColor" stroke="none"/>
  <path d="M6.5 14.5a7.8 7.8 0 0 1 11 0" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
  <path d="M3 10.8a12.3 12.3 0 0 1 18 0" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
</svg>`

const OFFLINE_GLYPH = `<svg class="connectivity-glyph-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
  <circle cx="12" cy="12" r="2.6" fill="currentColor" stroke="none"/>
  <path d="M6.5 14.5a7.8 7.8 0 0 1 11 0" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
  <path d="M3 10.8a12.3 12.3 0 0 1 18 0" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
  <path d="M3 3l18 18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
</svg>`

function render(
  status: HTMLElement,
  glyph: HTMLElement,
  text: HTMLElement,
  state: ConnectivityStatus,
): void {
  status.dataset.online = String(state.online)
  glyph.innerHTML = state.online ? ONLINE_GLYPH : OFFLINE_GLYPH
  text.textContent = state.online ? 'Online' : 'Offline'
}

export function createConnectivityIndicator(container: HTMLElement): ConnectivityIndicatorController {
  container.innerHTML = `
    <div class="connectivity-indicator" role="status" aria-live="polite">
      <span class="connectivity-glyph" data-connectivity-glyph aria-hidden="true"></span>
      <span class="connectivity-text" data-connectivity-text></span>
    </div>
  `

  const status = container.querySelector<HTMLElement>('.connectivity-indicator')!
  const glyph = container.querySelector<HTMLElement>('[data-connectivity-glyph]')!
  const text = container.querySelector<HTMLElement>('[data-connectivity-text]')!

  render(status, glyph, text, getConnectivityStatus())
  const unsubscribe = subscribeToConnectivity((state) => render(status, glyph, text, state))

  return {
    destroy: unsubscribe,
  }
}
