import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { defineConfig } from 'vitest/config'

const dirname = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  resolve: {
    alias: {
      // Só existe de verdade quando o plugin VitePWA processa o build (vite.config.ts); aqui
      // aponta para um stub para que a resolução do import nunca falhe (research.md, Decisão 5).
      'virtual:pwa-register': path.resolve(dirname, 'tests/stubs/pwaRegisterStub.ts'),
    },
  },
  test: {
    include: ['tests/unit/**/*.test.ts'],
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    restoreMocks: true,
    clearMocks: true,
  },
})
