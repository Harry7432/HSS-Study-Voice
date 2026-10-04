export type Theme = 'dark' | 'light'

export interface ThemeStorage {
  getTheme(): Theme | undefined
  setTheme(theme: Theme): void
}

interface ThemeControllerDependencies {
  root?: HTMLElement
  storage?: ThemeStorage
  prefersLight?: () => boolean
}

export interface ThemeController {
  getTheme(): Theme
  toggle(): Theme
}

const STORAGE_KEY = 'hss-study-theme'

function isTheme(value: unknown): value is Theme {
  return value === 'dark' || value === 'light'
}

export function createLocalStorageThemeStorage(storage: Storage): ThemeStorage {
  return {
    getTheme(): Theme | undefined {
      try {
        const value = storage.getItem(STORAGE_KEY)
        return isTheme(value) ? value : undefined
      } catch {
        return undefined
      }
    },
    setTheme(theme: Theme): void {
      try {
        storage.setItem(STORAGE_KEY, theme)
      } catch {
        // localStorage indisponível (modo privado, cota excedida): o tema
        // ainda se aplica nesta sessão, só não é lembrado na próxima visita.
      }
    },
  }
}

function systemPrefersLight(): boolean {
  return typeof window.matchMedia === 'function'
    && window.matchMedia('(prefers-color-scheme: light)').matches
}

export function createThemeController(
  dependencies: ThemeControllerDependencies = {},
): ThemeController {
  const root = dependencies.root ?? document.documentElement
  const storage = dependencies.storage ?? createLocalStorageThemeStorage(window.localStorage)
  const prefersLight = dependencies.prefersLight ?? systemPrefersLight

  const apply = (theme: Theme): Theme => {
    root.dataset.theme = theme
    return theme
  }

  const initial = isTheme(root.dataset.theme)
    ? root.dataset.theme
    : storage.getTheme() ?? (prefersLight() ? 'light' : 'dark')
  let theme = apply(initial)

  return {
    getTheme: () => theme,
    toggle(): Theme {
      theme = apply(theme === 'dark' ? 'light' : 'dark')
      storage.setTheme(theme)
      return theme
    },
  }
}

const SUN_ICON_MARKUP = `<svg class="hss-icon hss-icon-24" viewBox="0 0 24 24" aria-hidden="true">
  <circle cx="12" cy="12" r="5"/>
  <rect x="11" y="1" width="2" height="4" rx="1"/>
  <rect x="11" y="1" width="2" height="4" rx="1" transform="rotate(45 12 12)"/>
  <rect x="11" y="1" width="2" height="4" rx="1" transform="rotate(90 12 12)"/>
  <rect x="11" y="1" width="2" height="4" rx="1" transform="rotate(135 12 12)"/>
  <rect x="11" y="1" width="2" height="4" rx="1" transform="rotate(180 12 12)"/>
  <rect x="11" y="1" width="2" height="4" rx="1" transform="rotate(225 12 12)"/>
  <rect x="11" y="1" width="2" height="4" rx="1" transform="rotate(270 12 12)"/>
  <rect x="11" y="1" width="2" height="4" rx="1" transform="rotate(315 12 12)"/>
</svg>`

const MOON_ICON_MARKUP = `<svg class="hss-icon hss-icon-24" viewBox="0 0 24 24" aria-hidden="true">
  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z"/>
</svg>`

function renderToggleButton(button: HTMLButtonElement, theme: Theme): void {
  const isLight = theme === 'light'
  button.setAttribute('aria-pressed', String(isLight))
  button.setAttribute('aria-label', isLight ? 'Ativar tema escuro' : 'Ativar tema claro')
  button.innerHTML = isLight ? MOON_ICON_MARKUP : SUN_ICON_MARKUP
}

export function initThemeToggle(
  button: HTMLButtonElement,
  dependencies: ThemeControllerDependencies = {},
): ThemeController {
  const controller = createThemeController(dependencies)
  renderToggleButton(button, controller.getTheme())
  button.addEventListener('click', () => {
    renderToggleButton(button, controller.toggle())
  })
  return controller
}
