# Implementation Plan: Offline e PWA consolidado

**Branch**: `master` | **Date**: 2026-10-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/006-offline-pwa/spec.md`

## Summary

Hoje o Study Voice (`frontend/`) só carrega a partir de uma requisição de rede normal — a
biblioteca local (Fase 5) e o player com texto sincronizado (Fase 7) já funcionam sem rede para os
próprios dados, mas a casca da aplicação (HTML/CSS/JS) em si não. Esta fase adiciona um app shell
instalável e funcional offline após a primeira visita online, usando `vite-plugin-pwa`
(Workbox `generateSW`) para gerar e manter um service worker que precacheia os arquivos estáticos
do build e as duas origens de fonte já carregadas hoje, mais um Web App Manifest com nome/ícones/
cores do Design System HSS Music (Fase 6) para instalabilidade. Um módulo de conectividade baseado
em `navigator.onLine` alimenta um indicador visível (texto + sinal não-cor) e bloqueia a tentativa
de criação de um novo estudo quando offline, com mensagem clara em vez de um erro genérico de rede.
Atualizações de versão usam o modo `prompt` do plugin — nunca recarregamento automático — para não
interromper uma reprodução em andamento. Nenhuma mudança em backend, API, esquema do IndexedDB ou
formato da timeline.

## Technical Context

**Language/Version**: TypeScript estrito (sem mudança de stack), compilado/servido via Vite 7,
mesmo `tsconfig.json` (ES2022/ESNext, `strict`, `noUncheckedIndexedAccess`,
`exactOptionalPropertyTypes`).

**Primary Dependencies**: uma dependência nova de build (devDependency): `vite-plugin-pwa`
(gera o service worker via Workbox `generateSW` e o `manifest.webmanifest` a partir da config do
Vite). Nenhum framework de UI novo; o módulo virtual `virtual:pwa-register` fornecido pelo plugin é
consumido só para registrar o service worker e observar seu ciclo de vida (`research.md`, Decisões
1 e 5).

**Storage**: inalterado — IndexedDB (`hss-study-library`, Fase 5) não recebe nenhum campo novo
(FR-009). O novo armazenamento introduzido por esta fase é o Cache Storage do navegador, gerenciado
inteiramente pelo service worker gerado (Workbox), nunca lido/escrito diretamente pelo código da
aplicação (`data-model.md`, App Shell Cache).

**Testing**: Vitest (jsdom) para o módulo de conectividade (eventos nativos `dispatchEvent(new
Event('online'/'offline'))` sobre `window`) e para a guarda de criação offline em `main.ts`, nos
mesmos moldes de `frontend/tests/setup.ts` — inclui também um caso de FR-008 (ausência de
`navigator.serviceWorker`) no teste de `updateNotice.ts`, cobrindo automaticamente a parte de "não
lançar erro" da degradação graciosa. Playwright para os cenários e2e novos, divididos em dois
arquivos por dependência de servidor (Playwright atribui um arquivo inteiro a um projeto, não
testes individuais dentro dele): `frontend/e2e/offline-shell.spec.ts` para os cenários que dependem
do service worker real (recarregar offline, instalabilidade, atualização), rodando contra um
projeto Playwright dedicado (`offline-shell`) que serve `vite build` + `vite preview` numa porta
própria — porque a estratégia `generateSW` só gera o service worker em build de produção
(`research.md`, Decisão 9) — e `frontend/e2e/offline-connectivity.spec.ts` para o indicador de
conectividade e o bloqueio de criação offline, que não dependem do service worker e continuam
contra o servidor de desenvolvimento usado por `frontend/e2e/library.spec.ts`. O servidor de `vite
preview` precisa de `preview.proxy` configurado para `/api` (espelhando `server.proxy` de
`vite.config.ts`, que hoje só se aplica a `vite dev`); sem isso, o passo de "visita online" de
`offline-shell.spec.ts` não alcançaria o backend ao ser servido pelo preview.

**Target Platform**: os mesmos navegadores desktop/mobile já suportados, com e sem suporte a
Service Worker/Cache Storage/Web App Manifest — a degradação graciosa sem esse suporte é FR-008.

**Project Type**: aplicação web cliente existente (`frontend/`) — nenhum workspace novo.

**Performance Goals**: nenhum alvo de latência novo; os critérios são qualitativos e binários
(SC-001 a SC-006: carrega offline, reconhecido como instalável, bloqueia criação offline, sem
regressão, sem interrupção de reprodução na atualização, sem funcionalidade quebrada em navegadores
sem suporte).

**Constraints**: zero requisições de rede bem-sucedidas exigidas no carregamento/uso offline do
app shell e dos dados já locais (FR-001, FR-006); nenhum runtime caching para `/api/*`
(`research.md`, Decisão 2) — a criação de estudo continua exigindo rede no momento da ação, e
quando offline a tentativa é bloqueada antes de qualquer `fetch` (Decisão 4); atualização de versão
nunca força recarregamento com reprodução em andamento (FR-007); indicador de conectividade e
mensagem de bloqueio precisam de mais de um sinal visual e identificação por tecnologia assistiva
(FR-011); nenhuma mudança no esquema do IndexedDB, nos contratos de API ou no formato da timeline
(FR-009).

**Scale/Scope**: a mesma aplicação de usuário único por navegador/dispositivo das fases anteriores;
nenhuma sincronização entre dispositivos (fora do escopo, Scope Boundaries); tamanho do precache do
app shell limitado à saída atual do build (SPA pequena, poucos chunks JS/CSS + CSS vendorizado do
design system + dois domínios de fonte).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Resultado | Justificativa |
|---|---|---|
| I. Spec-Driven Development | PASS | `spec.md` já aprovada, com Assumptions cobrindo as ambiguidades relevantes antes deste plano; nenhuma clarificação adicional pendente |
| II. Local-First Ownership | PASS | Nenhum armazenamento novo no servidor; o App Shell Cache vive no navegador (Cache Storage), gerenciado pelo service worker; IndexedDB da biblioteca (Fase 5) não é tocado |
| III. Simple and Modular Backend | N/A (PASS) | Backend não é tocado (FR-009) |
| IV. Mandatory Tests | PASS | Novos testes unitários para `connectivity.ts`, para a guarda de criação offline em `main.ts` e para o fallback sem Service Worker em `updateNotice.ts` (FR-008); suíte existente permanece verde; novos cenários e2e cobrem recarregar offline, instalabilidade e bloqueio de criação |
| V. Incremental Pipeline Compatibility | N/A (PASS) | Pipeline de síntese/áudio não é alterado |
| VI. Security by Default | PASS | Nenhuma nova entrada externa; o service worker só precacheia arquivos estáticos do próprio build e dois domínios de fonte já carregados hoje; nenhum runtime caching de `/api/*`; nenhum conteúdo do usuário é executado |
| VII. No Overengineering | PASS | `vite-plugin-pwa`/Workbox reaproveitado em vez de service worker próprio; sem botão de instalação customizado (US2 já é satisfeita pela ação nativa do navegador); sem sondagem ativa de conectividade; sem fila de criação offline (fora do escopo) |
| VIII. Phase-Bounded Delivery | PASS | Escopo restrito às três user stories e FRs desta fase; Scope Boundaries excluem explicitamente fila offline, push, wrapper nativo e sincronização entre dispositivos |
| IX. Architecture Ready for Evolution | PASS | `platform/connectivity.ts` é um módulo pequeno e isolado, sem acoplamento à UI; a configuração do service worker/manifesto fica isolada em `vite.config.ts`, substituível sem tocar o código da aplicação |
| X. Explicit Technical Decisions | PASS | Nove decisões documentadas em `research.md`: ferramenta de service worker, runtime caching de fontes, detecção de conectividade (e sua limitação aceita), ordem de verificação do bloqueio offline, modo de atualização, sinalização dupla de acessibilidade, ausência de botão de instalação, origem dos ícones, e estratégia de teste e2e para o service worker |

Nenhuma violação. `Complexity Tracking` não é necessário.

## Project Structure

### Documentation (this feature)

```text
specs/006-offline-pwa/
├── spec.md               # Spec já aprovada
├── plan.md                # Este arquivo
├── research.md            # Fase 0: nove decisões técnicas
├── data-model.md          # Fase 1: App Shell Cache, Web App Manifest, Connectivity Status, Update Availability
├── quickstart.md           # Fase 1: guia de validação (build/testes + roteiro manual)
└── tasks.md                # Será criado por /speckit.tasks
```

Sem pasta `contracts/`: esta fase não introduz nenhuma interface nova entre serviços — o Web App
Manifest e o service worker são consumidos pelo próprio navegador do usuário, não por outro
sistema, e nenhum endpoint de API novo é criado (FR-009). As formas exatas do manifesto e dos
estados de runtime estão documentadas em `data-model.md`.

### Source Code (repository root)

```text
backend/                               # Inalterado por esta fase (FR-009)

frontend/
├── index.html                         # modificado — <link rel="apple-touch-icon"> para instalação
                                        # no iOS; manifesto/registro do service worker injetados
                                        # automaticamente pelo plugin, sem outras mudanças manuais
├── vite.config.ts                     # modificado — plugin VitePWA: manifest, generateSW,
                                        # registerType: 'prompt', runtimeCaching das duas origens
                                        # de fonte (research.md, Decisões 1, 2 e 5); preview.proxy
                                        # para `/api` espelhando server.proxy, exigido pelos
                                        # cenários de offline-shell.spec.ts servidos por
                                        # `vite preview` (ver Testing acima)
├── package.json                       # modificado — nova devDependency vite-plugin-pwa
├── playwright.config.ts               # modificado — terceiro `webServer` (vite build + vite
                                        # preview, porta dedicada) e projeto Playwright
                                        # `offline-shell` com baseURL própria, restrito a
                                        # `e2e/offline-shell.spec.ts` (research.md, Decisão 9;
                                        # ver Testing acima sobre por que o arquivo é separado)
├── public/
│   └── icons/                         # NOVO — ícones do manifesto (192, 512, 512 maskable),
                                        # cores derivadas de hss/tokens.css (research.md, Decisão 8)
├── src/
│   ├── platform/
│   │   └── connectivity.ts            # NOVO — navigator.onLine + eventos online/offline, puro,
                                        # sem DOM de apresentação
│   ├── ui/
│   │   ├── connectivityIndicator.ts    # NOVO — indicador online/offline (texto + sinal não-cor)
│   │   ├── updateNotice.ts             # NOVO — aviso de atualização disponível (virtual:pwa-register)
│   │   ├── player.ts                   # intocado
│   │   ├── libraryView.ts              # intocado
│   │   ├── readingView.ts              # intocado
│   │   └── theme.ts                    # intocado
│   ├── library/                        # intocado (FR-009)
│   ├── api/                            # intocado (FR-009)
│   ├── application/                    # intocado (a guarda de offline fica em main.ts, não aqui —
                                        # ver research.md, Decisão 4)
│   ├── main.ts                         # modificado — monta indicador + aviso de atualização;
                                        # guarda o submit de criação de estudo com o estado de
                                        # conectividade antes de chamar createStudy
│   └── styles.css                      # modificado — novos blocos `.connectivity-*`/`.update-notice-*`,
                                        # tokens-only
├── tests/
│   ├── unit/
│   │   ├── connectivity.test.ts        # NOVO
│   │   └── main.test.ts                # estendido (guarda offline + indicador)
│   └── setup.ts                        # intocado
└── e2e/
    ├── library.spec.ts                 # intocado (continua contra o servidor de desenvolvimento)
    ├── offline-shell.spec.ts           # NOVO — recarregar offline, instalabilidade e atualização
                                        # (contra o projeto `offline-shell`: vite build + preview)
    └── offline-connectivity.spec.ts    # NOVO — indicador online/offline e bloqueio de criação
                                        # offline (contra o servidor de desenvolvimento existente)
```

**Structure Decision**: nenhum workspace novo. A conectividade é isolada em `platform/` (nova
pasta de domínio, paralela a `reading/` da Fase 7 — lógica pura, sem DOM) para poder ser testada e
reaproveitada independentemente da apresentação; a apresentação (`connectivityIndicator.ts`,
`updateNotice.ts`) segue a mesma convenção de `ui/player.ts`/`ui/libraryView.ts`/`ui/readingView.ts`.
A guarda de bloqueio offline (FR-005) fica em `main.ts`, junto do handler de submit existente, em
vez de em `application/createStudy.ts` — `createStudy` já teria que receber e repassar o estado de
conectividade sem usá-lo para nada além de decidir "nem chamar", então a verificação mais simples é
no próprio ponto de chamada (`research.md`, Decisão 4; Princípio VII). `library/`, `api/`,
`application/` e `backend/` permanecem intocados.

## Complexity Tracking

> Não aplicável — nenhuma violação do Constitution Check acima.
