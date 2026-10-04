import { describe, expect, it, vi } from 'vitest'

import {
  createLocalStorageThemeStorage,
  createThemeController,
  initThemeToggle,
  type ThemeStorage,
} from '../../src/ui/theme'

function makeStorage(initial?: 'dark' | 'light'): ThemeStorage & { setTheme: ReturnType<typeof vi.fn> } {
  let current = initial
  return {
    getTheme: () => current,
    setTheme: vi.fn((theme: 'dark' | 'light') => {
      current = theme
    }),
  }
}

describe('theme controller', () => {
  it('starts dark when nothing is saved and the system has no light preference', () => {
    const root = document.createElement('html')
    const controller = createThemeController({
      root,
      storage: makeStorage(),
      prefersLight: () => false,
    })

    expect(controller.getTheme()).toBe('dark')
    expect(root.dataset.theme).toBe('dark')
  })

  it('starts light when nothing is saved but the system prefers light', () => {
    const root = document.createElement('html')
    const controller = createThemeController({
      root,
      storage: makeStorage(),
      prefersLight: () => true,
    })

    expect(controller.getTheme()).toBe('light')
    expect(root.dataset.theme).toBe('light')
  })

  it('prefers the saved choice over the system preference', () => {
    const root = document.createElement('html')
    const controller = createThemeController({
      root,
      storage: makeStorage('light'),
      prefersLight: () => false,
    })

    expect(controller.getTheme()).toBe('light')
  })

  it('respects a theme already applied to root (set by the anti-flash bootstrap script)', () => {
    const root = document.createElement('html')
    root.dataset.theme = 'light'
    const controller = createThemeController({
      root,
      storage: makeStorage(),
      prefersLight: () => false,
    })

    expect(controller.getTheme()).toBe('light')
  })

  it('toggles between dark and light, applying and persisting each change', () => {
    const root = document.createElement('html')
    const storage = makeStorage('dark')
    const controller = createThemeController({ root, storage, prefersLight: () => false })

    expect(controller.toggle()).toBe('light')
    expect(root.dataset.theme).toBe('light')
    expect(storage.setTheme).toHaveBeenLastCalledWith('light')

    expect(controller.toggle()).toBe('dark')
    expect(root.dataset.theme).toBe('dark')
    expect(storage.setTheme).toHaveBeenLastCalledWith('dark')
  })
})

describe('localStorage-backed theme storage', () => {
  it('reads back a previously saved theme', () => {
    const memory = new Map<string, string>()
    const fakeStorage = {
      getItem: (key: string) => memory.get(key) ?? null,
      setItem: (key: string, value: string) => memory.set(key, value),
    } as unknown as Storage
    const storage = createLocalStorageThemeStorage(fakeStorage)

    expect(storage.getTheme()).toBeUndefined()
    storage.setTheme('light')
    expect(storage.getTheme()).toBe('light')
  })

  it('ignores a corrupted stored value', () => {
    const fakeStorage = {
      getItem: () => 'sepia',
      setItem: vi.fn(),
    } as unknown as Storage
    const storage = createLocalStorageThemeStorage(fakeStorage)

    expect(storage.getTheme()).toBeUndefined()
  })

  it('does not throw when storage access fails (private mode, quota)', () => {
    const fakeStorage = {
      getItem: () => {
        throw new Error('SecurityError')
      },
      setItem: () => {
        throw new Error('QuotaExceededError')
      },
    } as unknown as Storage
    const storage = createLocalStorageThemeStorage(fakeStorage)

    expect(storage.getTheme()).toBeUndefined()
    expect(() => storage.setTheme('dark')).not.toThrow()
  })
})

describe('theme toggle button', () => {
  it('reflects the initial theme and flips on click', () => {
    const root = document.createElement('html')
    const storage = makeStorage('dark')
    const button = document.createElement('button')

    initThemeToggle(button, { root, storage, prefersLight: () => false })

    expect(button.getAttribute('aria-pressed')).toBe('false')
    expect(button.getAttribute('aria-label')).toBe('Ativar tema claro')
    expect(button.querySelector('svg')).not.toBeNull()

    button.click()

    expect(root.dataset.theme).toBe('light')
    expect(button.getAttribute('aria-pressed')).toBe('true')
    expect(button.getAttribute('aria-label')).toBe('Ativar tema escuro')
    expect(storage.setTheme).toHaveBeenLastCalledWith('light')

    button.click()

    expect(root.dataset.theme).toBe('dark')
    expect(button.getAttribute('aria-pressed')).toBe('false')
    expect(button.getAttribute('aria-label')).toBe('Ativar tema claro')
  })
})
