# Quickstart: Offline e PWA consolidado

Guia de validação ponta a ponta para `specs/006-offline-pwa`. Não contém código de implementação —
veja `data-model.md` e `research.md` para as decisões técnicas, e `tasks.md` (gerado por
`/speckit.tasks`) para a divisão do trabalho.

## Pré-requisitos

- `cd frontend && npm install` (workspace já inicializado nas fases anteriores; a implementação
  desta fase adiciona `vite-plugin-pwa` como devDependency — `npm install` depois de `tasks.md`
  aplicar essa mudança).
- Para os cenários de biblioteca/reprodução/leitura offline (que já funcionam desde as Fases 5 e
  7), nenhum backend é necessário.
- Para gerar um estudo novo durante a validação manual e para o backend local exigido pelos
  cenários e2e existentes, o backend deve estar rodando, como já documentado nas fases anteriores.
- Os cenários e2e que dependem do service worker real (recarregar offline, instalabilidade,
  atualização) vivem em `frontend/e2e/offline-shell.spec.ts` e precisam de um build de produção
  servido (`vite build` + `vite preview`, projeto Playwright `offline-shell`), não do servidor de
  desenvolvimento — ver `research.md`, Decisão 9, e `plan.md` → Testing. O comando exato é
  definido em `tasks.md` (T009).

## Verificação automatizada

```bash
cd frontend
npm run build         # tsc --noEmit && vite build — também gera o service worker/manifesto
npm test               # vitest run — inclui os novos testes de connectivity/guarda de criação
npm run test:e2e       # playwright test — cenários existentes + novos desta fase
```

Critério de aprovação: as três etapas terminam sem erro, com os testes novos e todos os já
existentes (incluindo `library.spec.ts` e `main.test.ts`) passando.

- [x] Resultado (2026-10-04, `tasks.md` T032): `npm run build` (tsc --noEmit + vite build) sem
  erro; `npm test` (vitest) com **121 testes, 14 arquivos, 0 falhas** (inclui os 7 testes novos de
  `main.test.ts` para a guarda offline e os 5 de `updateNotice.test.ts`, antes escondidos por uma
  falha de resolução do módulo virtual `virtual:pwa-register` sob `vitest.config.ts` — corrigida
  adicionando um `resolve.alias` para um stub em `frontend/tests/stubs/pwaRegisterStub.ts`); `npm
  run test:e2e` (playwright) com **11/11 testes passando**, confirmado de forma determinística com
  `--workers=1` (70–82s) e também com a saída não filtrada do runner. Com o paralelismo padrão (3
  workers) a suíte pode mostrar falhas intermitentes por contenção de CPU — um teste
  backend-dependente ultrapassando o timeout de 90s enquanto o novo cenário de atualização (T026)
  roda dois `npm run build` completos em paralelo — não é um defeito de produto; ver nota em T026.

## Cenários manuais

Cada cenário referencia a história de usuário e os critérios de sucesso correspondentes no
`spec.md`.

### 1. Carregar a biblioteca e reproduzir offline após visita prévia (US1 · SC-001)

1. Abra o aplicativo normalmente, online, e espere o carregamento completo (garante que o service
   worker instalou e o app shell foi precacheado).
2. Coloque o navegador ou o dispositivo em modo avião / desative a rede.
3. Recarregue o aplicativo.
4. Confirme: a interface carrega normalmente, sem tela de erro do navegador.
5. Abra a biblioteca local; confirme que todos os estudos salvos aparecem.
6. Reproduza um estudo salvo; confirme que o áudio toca, o progresso é salvo e o texto sincronizado
   (Fase 7) funciona normalmente.
7. Na aba Network das DevTools, confirme que nenhuma requisição de rede foi bem-sucedida durante
   todo o fluxo (as que aparecem, se houver, devem estar servidas do cache do service worker ou
   falhando de forma esperada).

- [x] Resultado (2026-10-04, `tasks.md` T012/T013): validado via Playwright (projeto
  `offline-shell`, `vite build` + `vite preview`), não manualmente — `recarrega offline depois de
  uma visita anterior` e `biblioteca, reprodução e texto sincronizado funcionam offline, sem
  requisição de rede bem-sucedida` em `frontend/e2e/offline-shell.spec.ts`, ambos GREEN direto na
  primeira execução, confirmando SC-001 para os passos 1–7. A verificação manual completa (modo
  avião real) permanece pendente para T033.

### 2. Primeira visita já offline (edge case)

1. Usando um perfil/navegador que nunca visitou o aplicativo online, desative a rede.
2. Tente abrir a URL do aplicativo.
3. Confirme que o comportamento é o mesmo de qualquer site inacessível offline sem visita prévia
   (erro padrão do navegador) — o aplicativo não finge oferecer uma cópia que não existe.

- [x] Resultado (2026-10-04, `tasks.md` T029): validado via uma verificação Playwright pontual
  (não um teste commitado — contexto novo, `context.setOffline(true)` antes de qualquer
  `page.goto`): a navegação falha com `net::ERR_INTERNET_DISCONNECTED` e a página permanece em
  `about:blank`, exatamente o erro padrão do navegador para um site nunca visitado — nenhuma cópia
  parcial ou quebrada é oferecida.

### 3. Instalar o aplicativo (US2 · SC-002)

1. Abra o aplicativo em um navegador desktop ou mobile com suporte a instalação de PWA (ex.:
   Chrome/Edge).
2. Acione a instalação pela própria UI do navegador/SO (ícone na barra de endereço, menu do
   navegador, ou "Adicionar à tela inicial" no mobile).
3. Confirme que o navegador reconhece o app como instalável e completa a instalação com o nome e
   ícone definidos (`data-model.md`, Web App Manifest).
4. Abra o app pelo ícone instalado; confirme que ele abre em janela própria, sem barra de endereço
   nem controles padrão de aba.
5. Repita em um navegador sem suporte a instalação (ou desative a flag correspondente); confirme
   que o app continua funcionando normalmente em aba comum, sem erro e sem oferta de instalação
   quebrada (FR-008 — a ausência de erro não tratado quando `navigator.serviceWorker` não existe
   também tem cobertura automatizada, ver `tasks.md` T025/T027).

- [ ] Resultado parcial (2026-10-04, `tasks.md` T016): os critérios de instalabilidade
  automatizáveis estão confirmados por teste e2e (`frontend/e2e/offline-shell.spec.ts`,
  "manifesto expõe nome, exibição e os três ícones exigidos" — `name`, `short_name`, `display:
  standalone`, `background_color`/`theme_color`, os três ícones com URLs resolvíveis). A oferta de
  instalação nativa em si (ícone na barra de endereço, fluxo de instalação do navegador/SO, janela
  própria sem controles de aba) **não foi verificada neste ambiente**: a tentativa de abrir a
  build de produção num Chrome real via automação de navegador falhou por uma restrição de rede
  do próprio ambiente de automação (não alcançou `127.0.0.1`, enquanto `curl` no mesmo host
  alcançava normalmente), e não há dispositivo mobile disponível aqui. Esta parte continua
  pendente de verificação manual num navegador desktop e num navegador/dispositivo mobile reais,
  além do navegador sem suporte (FR-008).

### 4. Bloquear criação de estudo offline (US3 · SC-003)

1. Com o app aberto e online, coloque o navegador em modo offline (DevTools → Network → Offline é
   suficiente; não precisa ser e2e com service worker, já que este fluxo não depende dele).
2. Tente criar um novo estudo (preencha o texto e envie o formulário).
3. Confirme: a tentativa é bloqueada imediatamente, com uma mensagem clara informando que a ação
   exige conexão — sem travar a interface, sem erro genérico de rede no console.
4. Confirme que nenhuma requisição para `/api/v1/studies` foi disparada (aba Network).

- [x] Resultado (2026-10-04, `tasks.md` T024): validado via e2e
  (`frontend/e2e/offline-connectivity.spec.ts`, "bloqueia a criação de estudo offline") — a
  mensagem de bloqueio aparece na `.status-line` e nenhuma requisição para `/api/v1/studies` é
  disparada.

### 5. Indicador de conectividade (US3 · FR-004/FR-011)

1. Com o app aberto online, confirme que o indicador de conectividade mostra o estado "Online" com
   mais de um sinal visual (não só cor — ver `research.md`, Decisão 6).
2. Desative a rede (sem recarregar a página); confirme que o indicador muda para "Offline"
   automaticamente, sem recarregamento manual.
3. Reative a rede; confirme que o indicador volta para "Online" automaticamente e que a criação de
   estudo volta a ficar disponível, sem recarregar a página.
4. Usando as ferramentas de acessibilidade do navegador (ou um leitor de tela), confirme que a
   mudança de estado é anunciada (texto dentro de um `role="status"`/`aria-live`).

- [x] Resultado (2026-10-04, `tasks.md` T024): validado via e2e
  (`frontend/e2e/offline-connectivity.spec.ts`, "o indicador de conectividade reflete
  online/offline automaticamente") — o indicador (`role="status"`, `aria-live="polite"`, texto +
  glifo) alterna Online/Offline nas duas direções sem recarregar a página, e a criação de estudo
  volta a funcionar ao reconectar. Verificação de leitor de tela real não foi feita; o padrão
  reaproveita `role="status"`/`aria-live="polite"` já em uso por `main.ts`.

### 6. Atualização não interrompe reprodução em andamento (US1 edge case · SC-005)

1. Com um estudo tocando, publique/sirva uma nova versão do build (ex.: rode `npm run build` de
   novo com uma mudança trivial e sirva o novo `dist/`).
2. Confirme que a reprodução em andamento não é interrompida nem recarregada automaticamente.
3. Confirme que um aviso não bloqueante aparece oferecendo a atualização (`data-model.md`, Update
   Availability).
4. Acione o aviso explicitamente; confirme que a atualização é aplicada só então (recarregamento
   controlado), sem afetar negativamente a biblioteca local já salva.

- [x] Resultado (2026-10-04, `tasks.md` T026): validado via e2e
  (`frontend/e2e/offline-shell.spec.ts`, "uma atualização publicada não interrompe a reprodução em
  andamento") — publica uma nova versão real (`npm run build` com uma mudança trivial em
  `index.html`) enquanto o áudio toca, confirma que a reprodução continua e o aviso aparece, e só
  recarrega após o clique explícito em "Atualizar agora". Nota de implementação: o
  `workbox-window` usado pelo `vite-plugin-pwa` só recarrega automaticamente após `updateSW(true)`
  quando já havia um service worker no controle *antes* da navegação atual (sinal `isUpdate`) — o
  teste faz um reload único logo após a primeira instalação para reproduzir isso, que é o que
  acontece numa visita real após uma instalação anterior.

### 7. Múltiplas abas durante uma atualização (edge case)

1. Abra o aplicativo em duas abas/janelas.
2. Publique uma nova versão e aceite a atualização em uma das abas.
3. Confirme que a outra aba continua operando de forma consistente, sem perda do progresso de
   reprodução em andamento nela.

- [ ] Resultado (2026-10-04, `tasks.md` T030): **não verificado empiricamente** — apenas análise
  de arquitetura, sem teste real com duas abas. `self.skipWaiting()` ativa o novo service worker
  globalmente para todos os clientes da origem/escopo quando qualquer aba chama `updateSW(true)`,
  mas uma aba que não acionou o aviso não recarrega sozinha (nenhum código nosso ou do
  `workbox-window` força isso) — ela continua executando o JS já carregado em memória, com o
  áudio e o progresso de reprodução intactos, até sua própria próxima navegação/reload. Recomenda-
  se confirmar isso manualmente com duas abas reais antes de considerar este edge case encerrado.

### 8. Falha ao atualizar o cache (edge case)

1. Simule esgotamento de armazenamento do navegador para o Cache Storage (ex.: DevTools → Storage →
   limitar quota, ou um perfil de teste já próximo do limite).
2. Force uma tentativa de atualização do app shell.
3. Confirme que os estudos já salvos na biblioteca (IndexedDB, Fase 5) não são perdidos, e que o
   aplicativo continua funcional em modo online mesmo que a atualização do cache falhe.

- [ ] Resultado (2026-10-04, `tasks.md` T031): **não verificado empiricamente** — simular
  esgotamento de quota do Cache Storage de forma confiável não foi possível neste ambiente.
  Análise de arquitetura: Cache Storage (service worker/Workbox) e IndexedDB (biblioteca local,
  `frontend/src/library/db.ts`) são buckets de armazenamento completamente separados no
  navegador; uma falha ao popular o precache não grava nem apaga nada em IndexedDB, e o Workbox
  trata uma falha de `cache.put` durante a instalação deixando o service worker atual (e seu
  cache já funcional) no controle — o app continua servindo a versão já instalada. Recomenda-se
  confirmar isso manualmente (DevTools → Storage, cota reduzida) antes de considerar este edge
  case encerrado.
