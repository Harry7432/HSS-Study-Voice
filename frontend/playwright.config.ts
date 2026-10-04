import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  projects: [
    {
      name: 'default',
      use: { baseURL: 'http://127.0.0.1:5173' },
      testMatch: ['library.spec.ts', 'offline-connectivity.spec.ts']
    },
    {
      name: 'offline-shell',
      use: { baseURL: 'http://127.0.0.1:4173' },
      testMatch: 'offline-shell.spec.ts'
    }
  ],
  webServer: [
    {
      command: 'uv run uvicorn app.main:app --host 127.0.0.1 --port 8000',
      cwd: '../backend',
      url: 'http://127.0.0.1:8000/health',
      reuseExistingServer: true
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 5173',
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: true
    },
    {
      command: 'npm run build && npx vite preview --host 127.0.0.1 --port 4173',
      url: 'http://127.0.0.1:4173',
      reuseExistingServer: true,
      timeout: 120_000
    }
  ]
})
