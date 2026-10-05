import { registerSW } from 'virtual:pwa-register'

export type UpdateState = 'idle' | 'available' | 'applying'

export interface UpdateNoticeController {
  getState(): UpdateState
  apply(): void
}

function supportsServiceWorker(): boolean {
  return typeof navigator !== 'undefined' && 'serviceWorker' in navigator
}

export function createUpdateNotice(container: HTMLElement): UpdateNoticeController {
  let state: UpdateState = 'idle'
  let updateSW: ((reloadPage?: boolean) => Promise<void>) | undefined

  function render(): void {
    if (state !== 'available') {
      container.innerHTML = ''
      return
    }
    container.innerHTML = `
      <div class="update-notice" role="status" aria-live="polite">
        <span class="update-notice-text">Uma nova versão está disponível.</span>
        <button class="update-notice-action" type="button" data-update-apply>Atualizar agora</button>
      </div>
    `
    container
      .querySelector<HTMLButtonElement>('[data-update-apply]')
      ?.addEventListener('click', () => apply())
  }

  function apply(): void {
    if (state !== 'available' || updateSW === undefined) return
    state = 'applying'
    render()
    void updateSW(true)
  }

  if (supportsServiceWorker()) {
    try {
      updateSW = registerSW({
        onNeedRefresh() {
          state = 'available'
          render()
        },
      })
    } catch {
      state = 'idle'
    }
  }

  render()

  return {
    getState: () => state,
    apply,
  }
}
