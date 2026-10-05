// Stub para 'virtual:pwa-register', que só existe quando o plugin VitePWA processa o build
// (vite.config.ts). vitest.config.ts aponta esse specifier para este arquivo (resolve.alias) para
// que qualquer teste que importe algo de updateNotice.ts, direta ou indiretamente, resolva com
// sucesso — mesmo sem mockar o módulo explicitamente. Testes que querem controlar o
// comportamento (ex.: updateNotice.test.ts) sobrescrevem isto com seu próprio vi.mock.
export function registerSW(): (reloadPage?: boolean) => Promise<void> {
  return async () => undefined
}
