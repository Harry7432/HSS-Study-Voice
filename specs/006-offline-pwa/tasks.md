---

description: "Task list for Offline e PWA consolidado"
---

# Tasks: Offline e PWA consolidado

**Input**: Design documents from `specs/006-offline-pwa/` (`spec.md`, `plan.md`, `research.md`,
`data-model.md`, `quickstart.md`) e `.specify/memory/constitution.md`.

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`. Sem pasta `contracts/`
(nenhum endpoint novo — FR-009).

**Tests**: FR-010 e o Princípio IV (Mandatory Tests) da constitution exigem verificação
automatizada para toda a lógica nova. Todas as tarefas de teste abaixo são **obrigatórias**, não
opcionais — mas a ordem esperada depende do que está sendo testado:

- **Comportamento novo** desta fase (`connectivity.ts`, a guarda de bloqueio offline, o
  indicador de conectividade, o aviso de atualização): o teste é escrito e **deve falhar (RED)**
  antes da tarefa de implementação correspondente, só passando (**GREEN**) depois dela. Vale para
  T004→T005, T017→T022, T018→T021 e T025→T027/T028.
- **Validação de comportamento pré-existente ou gerado por infraestrutura** — já produzido por
  uma tarefa anterior da própria fase (o `manifest`/service worker de T006/T007) ou por código de
  fases anteriores (biblioteca/player/texto sincronizado, Fases 5 e 7): o teste correspondente
  **pode e deve começar GREEN** já na primeira execução. Isso não é uma falha de processo — é o
  resultado esperado — e a tarefa continua obrigatória porque fixa o comportamento como regressão
  futura. Vale para T010/T011 (US1) e T014 (US2), marcadas abaixo como "(validação)" em vez de
  "(RED)".

**Fora de escopo nesta fase** (não criar tarefas para isso): backend, endpoints da API (Fase 4),
esquema do IndexedDB (Fase 5), formato da timeline (Fase 3.1), fila de criação offline, push
notifications, wrapper nativo, sincronização entre dispositivos, botão de instalação customizado
(`beforeinstallprompt`) — ver `spec.md` Scope Boundaries e `research.md` Decisão 7.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode executar em paralelo (arquivos diferentes, sem dependência entre si)
- **[Story]**: US1, US2, US3, ou `Setup`/`Foundational`/`Polish` para tarefas transversais
- Caminhos de arquivo são sempre relativos à raiz do repositório

## Path Conventions

Aplicação web existente de workspace único: `frontend/` (sem novo workspace, conforme
`plan.md` → Project Structure). `backend/` não é tocado nesta fase.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: adicionar a dependência de build e o esqueleto de pastas que toda user story
consome, sem qualquer comportamento novo ainda.

- [x] T001 [Setup] Adicionar `vite-plugin-pwa` como devDependency em `frontend/package.json` e
      rodar `npm install` em `frontend/` (`research.md`, Decisão 1).
- [x] T002 [P] [Setup] Criar `frontend/public/icons/` e produzir os três ícones do manifesto —
      `icon-192.png` (192×192, `purpose: any`), `icon-512.png` (512×512, `purpose: any`) e
      `icon-512-maskable.png` (512×512, `purpose: maskable`) — usando `--bg-canvas` (`#000000`)
      como fundo e `--accent` (`#19e3a1`) como primeiro plano, lidos de
      `frontend/src/hss/tokens.css` (`research.md`, Decisão 8; `data-model.md` → Web App
      Manifest).
- [x] T003 [P] [Setup] Criar a pasta `frontend/src/platform/` (vazia além do arquivo da Phase 2),
      paralela a `frontend/src/reading/`, conforme a Structure Decision do `plan.md`.

**Checkpoint**: dependência instalada, ícones existem, pasta de domínio criada. Nenhum
comportamento novo ainda — `npm run build` e `npm test` continuam passando exatamente como antes.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: o módulo de conectividade puro e a configuração do service worker/manifesto são
consumidos por todas as três user stories; nenhuma delas pode ser implementada nem testada de
forma independente sem esta fase.

**⚠️ CRITICAL**: nenhuma tarefa de user story começa antes desta fase estar completa.

### Testes fundacionais (RED) ⚠️

- [x] T004 [P] [Foundational] Escrever `frontend/tests/unit/connectivity.test.ts`: estado inicial
      reflete `navigator.onLine`; disparar `window.dispatchEvent(new Event('offline'))` atualiza o
      estado para `false` e notifica assinantes; disparar `new Event('online')` atualiza para
      `true`; múltiplos assinantes recebem a mesma notificação (`data-model.md` → Connectivity
      Status; `research.md`, Decisão 3). Rodar `npm test` em `frontend/` e confirmar que falha
      (módulo ainda não existe).

### Implementação fundacional (GREEN)

- [x] T005 [Foundational] Implementar `frontend/src/platform/connectivity.ts`: expõe o estado
      atual (`navigator.onLine` na leitura inicial) e uma função de inscrição nos eventos nativos
      `online`/`offline` da `window`; módulo puro, sem DOM de apresentação, sem sondagem ativa de
      rede (`research.md`, Decisão 3). Rodar T004 novamente e confirmar que passa.
- [x] T006 [Foundational] Configurar o plugin `VitePWA` em `frontend/vite.config.ts`: estratégia
      `generateSW`, `registerType: 'prompt'`, `manifest` com os campos de
      `data-model.md` → Web App Manifest (`name`, `short_name`, `description`, `start_url: '/'`,
      `scope: '/'`, `display: 'standalone'`, `background_color: '#000000'`,
      `theme_color: '#000000'`, `icons` apontando para `frontend/public/icons/` de T002), e
      `workbox.runtimeCaching` com estratégia `CacheFirst` apenas para `fonts.googleapis.com` e
      `fonts.gstatic.com` — **sem** entrada para `/api/*` (`research.md`, Decisões 1 e 2).
- [x] T007 [Foundational] Adicionar `<link rel="apple-touch-icon" href="/icons/icon-192.png">` em
      `frontend/index.html` para instalação no iOS (`plan.md` → Project Structure); não alterar
      manualmente nenhuma outra tag — manifesto e registro do service worker são injetados
      automaticamente pelo plugin.
- [x] T008 [Foundational] Rodar `npm run build` em `frontend/` e confirmar que
      `dist/manifest.webmanifest` e `dist/sw.js` são gerados sem erro, e que `npm test` continua
      100% verde (nenhuma regressão nos testes existentes).

**Checkpoint**: `connectivity.ts` testado e funcional; build de produção já gera service worker e
manifesto. As três user stories podem agora ser implementadas.

---

## Phase 3: User Story 1 - Continuar usando a biblioteca e os estudos salvos sem rede (Priority: P1) 🎯 MVP

**Goal**: depois de uma visita online, o app shell carrega e a biblioteca/player/texto
sincronizado funcionam 100% offline, sem nenhuma requisição de rede bem-sucedida (SC-001).

**Independent Test**: visitar o app uma vez online, ativar modo avião, reabrir o app e confirmar
que a biblioteca carrega, um estudo salvo reproduz e o texto sincronizado funciona, sem requisição
de rede bem-sucedida (`spec.md` → US1 Independent Test; `quickstart.md`, Cenário 1).

### Testes para User Story 1 (validação de comportamento já implementado) ⚠️

> Estes testes fixam como regressão um comportamento que a Foundational (T006/T007) e as Fases
> 5/7 já implementam — pela regra de RED→GREEN no topo deste arquivo, o resultado esperado na
> primeira execução (T012) é **GREEN direto**, não RED. Escrevê-los continua obrigatório (FR-010);
> só não há necessidade de forçar nem esperar uma falha artificial.

- [x] T009 [P] [US1] Em `frontend/playwright.config.ts`: adicionar um terceiro `webServer` que
      roda `vite build && vite preview --port 4173` (porta dedicada, distinta dos 5173 do dev
      server), e substituir a configuração atual (implícita, um único projeto) por dois projetos
      Playwright explícitos com `testMatch` que particionam todos os arquivos **sem sobreposição**
      — `default` (`baseURL: 'http://127.0.0.1:5173'`, `testMatch: ['library.spec.ts',
      'offline-connectivity.spec.ts']`) e `offline-shell` (`baseURL: 'http://127.0.0.1:4173'`,
      `testMatch: 'offline-shell.spec.ts'`). A sobreposição é o risco real aqui: se o projeto
      `default` não excluir `offline-shell.spec.ts` explicitamente, o Playwright roda esse arquivo
      nos dois projetos — uma vez contra a baseURL errada (dev server, sem service worker). Isso é
      necessário porque Playwright atribui arquivos inteiros a projetos, não testes individuais
      dentro de um arquivo (`research.md`, Decisão 9). Configurar também `preview: { proxy: {
      '/api': 'http://127.0.0.1:8000' } }` em `frontend/vite.config.ts`, espelhando o
      `server.proxy` existente — sem isso, o passo de "visita online" de T010/T011 não alcança o
      backend quando servido por `vite preview`. Pré-requisito de infraestrutura para T010 e T011;
      sem asserção própria nesta tarefa.
- [x] T010 [P] [US1] Escrever o cenário e2e "recarregar offline após visita prévia" em
      `frontend/e2e/offline-shell.spec.ts`, rodando contra o projeto `offline-shell` (T009):
      visitar a URL online, esperar o service worker instalar (`navigator.serviceWorker.ready`),
      simular offline (`context.setOffline(true)` do Playwright), recarregar, e confirmar que a
      interface carrega sem erro de navegador (`quickstart.md`, Cenário 1, passos 1–4).
- [x] T011 [P] [US1] Estender o cenário de T010 (ou um novo teste no mesmo arquivo
      `frontend/e2e/offline-shell.spec.ts`) para, ainda offline e com um estudo já salvo na
      biblioteca, confirmar que a biblioteca lista o estudo, a reprodução toca e o texto
      sincronizado acompanha o áudio, e que nenhuma requisição de rede bem-sucedida ocorre durante
      o fluxo (monitorar eventos `request`/`response` do Playwright) (SC-001; `quickstart.md`,
      Cenário 1, passos 5–7).

### Implementação para User Story 1

- [x] T012 [US1] Rodar T010 e T011 pela primeira vez: resultado esperado é **GREEN direto**
      (validação, não RED) — a biblioteca/player/texto sincronizado já funcionam offline desde as
      Fases 5 e 7, e o app shell já foi configurado em T006/T007 (`plan.md` → Summary; regra de
      RED→GREEN no topo deste arquivo). Nenhuma mudança de produção é esperada nesta user story
      além da configuração já feita em T006/T007. Se T010/T011 falharem, investigar antes de
      prosseguir — a causa esperada seria um problema na infraestrutura nova de T009 (projeto
      `offline-shell`/proxy do preview), não ausência de funcionalidade.
- [x] T013 [US1] Rodar `npm run build && npm run test:e2e` (ou o comando equivalente que exercita
      o projeto `offline-shell` de T009) em `frontend/` e confirmar que T010 e T011 passam
      (GREEN).

**Checkpoint**: User Story 1 (MVP) funcional e testável de forma independente — app shell,
biblioteca, player e texto sincronizado funcionam 100% offline após visita prévia.

---

## Phase 4: User Story 2 - Instalar o aplicativo como um app (Priority: P2)

**Goal**: o navegador reconhece o app como instalável, com nome/ícone corretos, abrindo em janela
própria sem controles de aba (SC-002); navegadores sem suporte continuam funcionando normalmente
(FR-008).

**Independent Test**: abrir o app em navegador compatível, usar a ação de instalação nativa do
navegador/SO, e confirmar que o app passa a abrir em janela própria com nome/ícone corretos
(`spec.md` → US2 Independent Test; `quickstart.md`, Cenário 3).

### Testes para User Story 2 (validação de comportamento já implementado) ⚠️

> Mesmo caso de T010/T011: o `manifest` já foi configurado em T006/T002 (Foundational), então o
> resultado esperado na primeira execução de T014 é **GREEN direto** (regra de RED→GREEN no topo
> deste arquivo).

- [ ] T014 [P] [US2] Escrever o cenário e2e "manifesto de instalabilidade" em
      `frontend/e2e/offline-shell.spec.ts`, rodando contra o projeto `offline-shell` (T009):
      navegar até o app e buscar o `<link rel="manifest">` resolvido, buscar
      `manifest.webmanifest` via `request`, e validar que o JSON contém `name: "HSS Study
      Voice"`, `short_name`, `display: "standalone"`, `background_color: "#000000"`,
      `theme_color: "#000000"` e os três ícones (192, 512, 512 maskable) com URLs resolvíveis
      (`data-model.md` → Web App Manifest; SC-002). Resultado esperado é **GREEN direto**; se
      falhar, o motivo é um campo incorreto em T006/T002, a corrigir antes de T015.

### Implementação para User Story 2

- [ ] T015 [US2] Rodar T014 e, se necessário, ajustar os campos do `manifest` em
      `frontend/vite.config.ts` (T006) até o teste passar (GREEN) — nenhum código de aplicação
      novo é esperado para US2 além do manifesto e dos ícones já produzidos em T002/T006
      (`research.md`, Decisão 7: sem botão de instalação customizado).
- [ ] T016 [US2] Validar manualmente o Cenário 3 do `quickstart.md` em pelo menos um navegador
      desktop e um navegador/dispositivo mobile compatíveis com instalação de PWA (instalar,
      confirmar janela própria sem barra de endereço e nome/ícone corretos — SC-002) e em um
      navegador sem suporte à instalação (confirmar que a oferta de instalação simplesmente não
      aparece, sem erro — FR-008; a ausência de travamento/erro não tratado quando
      `navigator.serviceWorker` não existe já é coberta automaticamente por T025/T027, então esta
      tarefa cobre só a parte que exige navegador real: a oferta de instalação em si). Registrar o
      resultado no placeholder já preparado no `quickstart.md` (Cenário 3) e marcar esta tarefa em
      `tasks.md`, seguindo o mesmo padrão usado na Fase 6 (`specs/004-hss-music-design-system/quickstart.md`,
      commit `b3eb647`) — não existe pasta `docs/validation/` neste repositório.

**Checkpoint**: User Stories 1 e 2 funcionam de forma independente. App instalável com
manifesto correto; US1 continua intacta.

---

## Phase 5: User Story 3 - Saber quando uma ação exige conexão (Priority: P3)

**Goal**: o usuário vê um indicador visível de conectividade (mais de um sinal, não só cor) e a
criação de novo estudo é bloqueada com mensagem clara quando offline, antes de qualquer chamada de
rede (SC-003, FR-004, FR-005, FR-011).

**Independent Test**: colocar o app offline, tentar criar um novo estudo, e confirmar que o
sistema impede a tentativa com mensagem clara em vez de tentar a chamada de rede (`spec.md` → US3
Independent Test; `quickstart.md`, Cenário 4).

### Testes para User Story 3 (RED) ⚠️

- [ ] T017 [P] [US3] Estender `frontend/tests/unit/main.test.ts`: com `connectivity.ts` (T005)
      mockado/forçado para `online: false`, submeter o formulário de criação de estudo e
      confirmar que `dependencies.createStudy` **não é chamado**, que a mensagem de bloqueio
      aparece no elemento `role="status"` existente (`frontend/src/main.ts`, linha do
      `status-line`), e que nenhum erro não tratado é lançado (`research.md`, Decisão 4; FR-005).
      Confirmar que o teste falha (guarda ainda não existe).
- [ ] T018 [P] [US3] Criar `frontend/tests/unit/connectivityIndicator.test.ts`: renderizar o
      indicador com estado inicial `online: true` e confirmar texto "Online" + um segundo sinal
      não-cor (ex.: ícone/glifo) dentro de elemento com `role="status"`/`aria-live="polite"`;
      disparar o evento `offline` via `connectivity.ts` (T005) e confirmar que o texto muda para
      "Offline" com o sinal correspondente, sem exigir recarregamento (`data-model.md` →
      Connectivity Status; FR-004, FR-011). Confirmar que o teste falha (módulo ainda não
      existe).
- [ ] T019 [P] [US3] Criar `frontend/e2e/offline-connectivity.spec.ts` (arquivo novo, separado de
      `offline-shell.spec.ts` — ver T009 sobre por que os dois cenários de servidor não podem
      compartilhar um arquivo) e escrever o cenário e2e "bloquear criação de estudo offline",
      rodando contra o projeto padrão/servidor de desenvolvimento existente (não precisa do
      projeto `offline-shell` — `research.md`, Decisão 9): com o app online, simular offline via
      `context.setOffline(true)`, preencher e submeter o formulário de criação, confirmar que
      nenhuma requisição para `/api/v1/studies` é disparada e que a mensagem de bloqueio aparece
      (`quickstart.md`, Cenário 4; SC-003). Confirmar que falha.
- [ ] T020 [P] [US3] Estender o mesmo arquivo `frontend/e2e/offline-connectivity.spec.ts` com o
      cenário "indicador de conectividade reflete online/offline automaticamente": alternar
      `context.setOffline(true)`/`false` sem recarregar a página e confirmar que o indicador
      muda de estado automaticamente nas duas direções, e que a criação de estudo volta a ficar
      disponível ao voltar online (`quickstart.md`, Cenário 5; FR-004). Confirmar que falha.

### Implementação para User Story 3

- [ ] T021 [P] [US3] Implementar `frontend/src/ui/connectivityIndicator.ts`: consome
      `connectivity.ts` (T005), renderiza texto (`"Online"`/`"Offline"`) + glifo/ícone dentro de
      um elemento com `role="status"` e `aria-live="polite"`, atualizando em resposta aos eventos
      de conectividade (`research.md`, Decisão 6). Rodar T018 e confirmar GREEN.
- [ ] T022 [US3] Em `frontend/src/main.ts`: importar e montar `connectivityIndicator.ts` (T021)
      no `mountApp`; adicionar a guarda de conectividade no handler de submit do formulário de
      criação — consultar `connectivity.ts` (T005) **antes** de chamar
      `dependencies.createStudy`, e se offline, interromper imediatamente exibindo mensagem clara
      no elemento `role="status"` existente, sem disparar nenhum `fetch` (`research.md`, Decisão
      4; FR-005). Rodar T017 e confirmar GREEN.
- [ ] T023 [US3] Em `frontend/src/styles.css`: adicionar os blocos `.connectivity-*` (apenas
      tokens já existentes em `frontend/src/hss/tokens.css`, sem cor nova) para o indicador de
      T021, incluindo estado visual do glifo online/offline (`research.md`, Decisão 6).
- [ ] T024 [US3] Rodar `npm run test:e2e` em `frontend/` e confirmar que T019 e T020 passam
      (GREEN).

**Checkpoint**: todas as três user stories funcionam de forma independente. Indicador de
conectividade visível e acessível; criação de estudo bloqueada offline com mensagem clara.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: cobrir o fluxo de atualização (FR-007), os edge cases restantes do `spec.md` e a
validação final de ponta a ponta via `quickstart.md`. Depende de todas as três user stories
estarem completas.

### Testes de atualização (RED) ⚠️

- [ ] T025 [P] [Polish] Criar `frontend/tests/unit/updateNotice.test.ts`: mockar os callbacks do
      módulo virtual `virtual:pwa-register` (`onNeedRefresh`, `onOfflineReady`); confirmar que o
      estado inicial é `"idle"`, que `onNeedRefresh()` transiciona para `"available"` e exibe um
      aviso não bloqueante, e que só uma ação explícita do usuário chama `updateSW(true)`
      (transição para `"applying"`) — nenhuma chamada automática (`data-model.md` → Update
      Availability; `research.md`, Decisão 5; FR-007). Adicionar um caso cobrindo FR-008: com
      `navigator.serviceWorker` ausente/indisponível (mock), confirmar que o módulo não lança
      erro não tratado e permanece em `"idle"` sem exibir aviso de atualização — esta é a parte de
      FR-008 que pode ser verificada automaticamente, sem depender de um navegador real sem
      suporte. Confirmar que falha.
- [ ] T026 [P] [Polish] Escrever o cenário e2e "atualização não interrompe reprodução em
      andamento" em `frontend/e2e/offline-shell.spec.ts`, rodando contra o projeto `offline-shell`
      (T009): com áudio tocando, simular uma nova versão do service worker disponível (ex.:
      reconstruir o build com um comentário trivial alterado e servir a nova versão), confirmar
      que a reprodução não é interrompida, que o aviso de atualização aparece, e que a atualização
      só é aplicada após ação explícita (`quickstart.md`, Cenário 6; SC-005). Confirmar que falha.

### Implementação de atualização (GREEN)

- [ ] T027 [Polish] Implementar `frontend/src/ui/updateNotice.ts`: consome
      `virtual:pwa-register`, registra `onNeedRefresh`/`onOfflineReady`, mantém o estado
      `"idle" | "available" | "applying"` de `data-model.md`, e expõe um aviso não bloqueante que
      só chama `updateSW(true)` mediante ação explícita do usuário — nenhum timer, nenhum
      recarregamento automático (`research.md`, Decisão 5). Tratar a ausência de suporte a Service
      Worker como um no-op seguro (sem lançar erro, sem exibir aviso) em vez de presumir que o
      módulo virtual sempre resolve — FR-008. Rodar T025 e confirmar GREEN.
- [ ] T028 [Polish] Em `frontend/src/main.ts`: importar e montar `updateNotice.ts` (T027) no
      `mountApp`. Em `frontend/src/styles.css`: adicionar os blocos `.update-notice-*`
      (tokens-only). Rodar T026 e confirmar GREEN.

### Validação manual dos edge cases restantes

> Registrar cada resultado (T029–T031, T033) no placeholder já preparado no `quickstart.md` sob o
> respectivo Cenário, e marcar a tarefa aqui em `tasks.md` — mesmo padrão usado na Fase 6
> (`specs/004-hss-music-design-system/quickstart.md`, commit `b3eb647`). Não existe pasta
> `docs/validation/` neste repositório.

- [ ] T029 [P] [Polish] Validar manualmente o Cenário 2 do `quickstart.md` (primeira visita já
      offline, sem visita prévia — comportamento padrão de site inacessível, sem oferta de cópia
      inexistente); registrar o resultado (ver nota acima).
- [ ] T030 [P] [Polish] Validar manualmente o Cenário 7 do `quickstart.md` (múltiplas abas durante
      uma atualização — a aba que não aceitou a atualização continua operando de forma consistente,
      sem perda de progresso de reprodução); registrar o resultado (ver nota acima).
- [ ] T031 [P] [Polish] Validar manualmente o Cenário 8 do `quickstart.md` (falha ao atualizar o
      cache por esgotamento de armazenamento — os estudos já salvos no IndexedDB não são
      perdidos, e o app continua funcional online); registrar o resultado (ver nota acima).

### Regressão final

- [ ] T032 [Polish] Rodar a suíte completa em `frontend/`: `npm run build && npm test && npm run
      test:e2e`, confirmando que todos os testes novos (T004, T010, T011, T014, T017–T020, T025,
      T026) e todos os testes já existentes (incluindo `frontend/e2e/library.spec.ts` e
      `frontend/tests/unit/main.test.ts` já existentes antes desta fase) passam sem regressão
      (FR-010, SC-004; `quickstart.md` → Verificação automatizada).
- [ ] T033 [Polish] Executar o roteiro completo de validação manual do `quickstart.md`
      (Cenários 1, 3, 4, 5 e 6, além de 2, 7 e 8 já cobertos em T029–T031) e registrar a evidência
      final da fase nos placeholders do próprio `quickstart.md` (um por Cenário) e em `tasks.md`
      (ver nota acima da seção "Validação manual dos edge cases restantes") — a evidência de
      validação manual da Fase 6 foi registrada assim, dentro do `quickstart.md`/`tasks.md` da
      fase (commit `b3eb647`), não em uma pasta `docs/validation/` separada, que não existe neste
      repositório.

**Checkpoint**: as três user stories, o fluxo de atualização e todos os edge cases do `spec.md`
estão implementados, testados (unit + e2e) e validados manualmente, sem regressão em nenhum teste
preexistente.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — pode começar imediatamente.
- **Foundational (Phase 2)**: depende da conclusão do Setup — bloqueia todas as user stories.
- **User Story 1 (Phase 3)**: depende só do Foundational. Não depende de US2/US3.
- **User Story 2 (Phase 4)**: depende só do Foundational (reaproveita o projeto Playwright
  `offline-shell` criado em T009, dentro de US1 — se US1 ainda não foi feita, mover T009 para
  antes de T014).
- **User Story 3 (Phase 5)**: depende só do Foundational. Não depende de US1/US2.
- **Polish (Phase 6)**: depende das três user stories completas (o aviso de atualização, em
  particular, é montado em `main.ts` junto do indicador de conectividade de US3 — T028 toca o
  mesmo arquivo que T022).

### User Story Dependencies

- **US1 (P1)**: nenhuma dependência de outra user story; é a independent test mínima do MVP.
- **US2 (P2)**: nenhuma dependência funcional de US1, mas reaproveita a infraestrutura de teste
  e2e do projeto `offline-shell` (T009) introduzida durante US1 — se as equipes trabalharem em
  paralelo, T009 deve ser promovida para a Phase 2 (Foundational) antes de iniciar US1/US2
  simultaneamente.
- **US3 (P3)**: nenhuma dependência de US1/US2; pode ser implementada e testada de forma
  totalmente independente (não usa o service worker, só `connectivity.ts` da Phase 2).

### Within Each User Story

- Testes de comportamento novo (T017–T020, T025–T026) escritos e **falhando** antes da tarefa de
  implementação correspondente (RED → GREEN). Testes de validação (T009–T011, T014) escritos e
  esperados **GREEN** já na primeira execução, pois validam comportamento que a Foundational já
  implementa (ver regra no topo deste arquivo).
- Dentro de US3: `connectivityIndicator.ts` (T021) antes de integrá-lo em `main.ts` (T022).
- Dentro de Polish: `updateNotice.ts` (T027) antes de integrá-lo em `main.ts` (T028).

### Parallel Opportunities

- T002 e T003 (Setup) em paralelo.
- T009, T010, T011 (US1) em paralelo entre si (arquivos/análises diferentes, mesmo arquivo de
  teste para T010/T011 — tratar como sequencial se um único desenvolvedor editar o mesmo arquivo).
- T017, T018, T019, T020 (US3, testes) em paralelo entre si — arquivos diferentes.
- T021 (US3, implementação) pode começar em paralelo com a escrita de T019/T020, desde que T018
  já esteja RED.
- T025 e T026 (Polish, testes) em paralelo.
- T029, T030, T031 (Polish, validação manual) em paralelo.
- US1, US2 e US3 podem ser trabalhadas em paralelo por desenvolvedores diferentes depois da Phase
  2 (Foundational), respeitando a nota sobre T009 acima.

---

## Parallel Example: User Story 3

```bash
# Testes de US3 em paralelo (arquivos diferentes):
Task: "Estender frontend/tests/unit/main.test.ts com guarda de bloqueio offline (T017)"
Task: "Criar frontend/tests/unit/connectivityIndicator.test.ts (T018)"
Task: "Cenário e2e de bloqueio de criação offline em frontend/e2e/offline-connectivity.spec.ts (T019)"
Task: "Cenário e2e de indicador online/offline em frontend/e2e/offline-connectivity.spec.ts (T020)"
```

---

## Implementation Strategy

### MVP First (User Story 1 apenas)

1. Completar Phase 1: Setup.
2. Completar Phase 2: Foundational (CRÍTICO — bloqueia todas as user stories).
3. Completar Phase 3: User Story 1.
4. **PARAR e VALIDAR**: rodar `quickstart.md` Cenário 1 e confirmar SC-001 manualmente.
5. Este é o MVP sugerido — ver seção "Resumo" abaixo.

### Entrega incremental

1. Setup + Foundational → base pronta.
2. US1 → validar independentemente (MVP).
3. US2 → validar independentemente (instalabilidade).
4. US3 → validar independentemente (indicador + bloqueio offline).
5. Polish → atualização de versão + edge cases + regressão final.

---

## Resumo

- **Total de tarefas**: 33 (T001–T033).
- **Divisão por fase**:
  - Setup: 3 tarefas (T001–T003).
  - Foundational: 5 tarefas (T004–T008).
  - User Story 1 (P1): 5 tarefas (T009–T013).
  - User Story 2 (P2): 3 tarefas (T014–T016).
  - User Story 3 (P3): 8 tarefas (T017–T024).
  - Polish: 9 tarefas (T025–T033).
- **Divisão por tipo**: 10 tarefas de teste unitário/e2e explícitas — 7 em RED→GREEN estrito para
  comportamento novo (T004, T017–T020, T025, T026) e 3 em modo validação, GREEN esperado já na
  primeira execução, para comportamento pré-existente/gerado por infraestrutura (T010, T011, T014;
  ver regra no topo deste arquivo); 4 tarefas de validação manual (T016, T029–T031, mais o roteiro
  consolidado em T033); as demais são implementação ou verificação de regressão.
- **MVP sugerido**: Setup (T001–T003) + Foundational (T004–T008) + User Story 1 (T009–T013) — 13
  tarefas, entregando o valor central do spec (SC-001: biblioteca, player e texto sincronizado
  100% offline após visita prévia) sem instalabilidade nem indicador de conectividade, que podem
  ser entregues em incrementos seguintes (US2 e US3) sem retrabalho.
