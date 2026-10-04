# Implementation Plan: Player com texto sincronizado

**Branch**: `005-synced-text-player` | **Date**: 2026-10-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-synced-text-player/spec.md`

## Summary

Ao abrir um estudo salvo (pela biblioteca local ou logo após gerá-lo), a aplicação hoje toca apenas
o áudio via `<audio controls>` nativo, sem mostrar o texto. Esta fase adiciona uma "Reading View"
que renderiza o texto completo a partir da `TimelineDocument` já armazenada localmente, destaca a
frase correspondente à posição atual de reprodução em tempo real, rola automaticamente até ela
(suspendendo a rolagem automática se o usuário rolar manualmente), permite clicar numa frase para
reposicionar a reprodução, restaura a frase correta ao reabrir um estudo com progresso salvo, e
degrada graciosamente (mantendo o áudio tocando) quando a timeline local está ausente ou corrompida.
A abordagem técnica é um lookup por busca binária sobre o array achatado de frases, acionado pelos
eventos nativos do próprio elemento `<audio>` (`timeupdate`, `seeked`, `play`, `ended`,
`loadedmetadata`), sem nenhuma mudança de backend, API ou esquema da timeline.

## Technical Context

**Language/Version**: TypeScript estrito (sem mudança de stack), compilado/servido via Vite, mesmo
`tsconfig.json` (ES2022/ESNext, `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`).

**Primary Dependencies**: nenhuma dependência nova de runtime ou build. Reaproveita `idb` (já usado
por `library/db.ts`, não tocado por esta fase) e o DOM nativo (`HTMLAudioElement`,
`Element.scrollIntoView`). Nenhum framework de UI é introduzido.

**Storage**: inalterado — IndexedDB (`hss-study-library`, Fase 5). Esta fase não grava nenhum dado
novo; o estado da Reading View (frase atual, suspensão de auto-scroll) é efêmero, mantido só em
memória enquanto o estudo está aberto, e descartado em `discard()`.

**Testing**: Vitest (jsdom), eventos nativos (`dispatchEvent(new Event(...))`) sobre
`document.createElement('audio')`, dependências injetadas via objetos simples com `vi.fn()`,
fixtures `makeTimeline()`/`makeStudyResult()` de `frontend/tests/setup.ts` (timelines
multi-frase/multi-chunk construídas localmente nos novos testes, sem alterar a fixture
compartilhada); Playwright para um cenário e2e adicional em `frontend/e2e/library.spec.ts`.

**Target Platform**: o mesmo navegador desktop/mobile (≤390px) já suportado, temas `dark`/`light` do
design system HSS Music.

**Project Type**: aplicação web cliente existente (`frontend/`) — nenhum workspace novo.

**Performance Goals**: destaque deve acompanhar a reprodução sem atraso perceptível (SC-001:
<300ms); resolução de frase por amostra em O(log n) via busca binária, responsiva mesmo em textos
com muitas frases (edge case explícito do spec); clique atualiza destaque e posição de forma
síncrona no próprio handler (SC-002: <1s, na prática imediato).

**Constraints**: funcionamento 100% offline (FR-012, nenhuma requisição de rede nova); nenhuma
mudança no esquema da timeline, em endpoints de API ou no esquema de armazenamento local (FR-014);
granularidade de destaque apenas por frase (sem palavra); texto somente leitura; `player.ts` não é
modificado — a nova lógica se conecta ao mesmo elemento `<audio>` via listeners próprios, sem
duplicar a persistência de progresso já existente.

**Scale/Scope**: a mesma aplicação de usuário único por navegador; estudos com potencialmente
centenas/milhares de frases devem continuar responsivos (busca binária cobre isso com folga: ~13
comparações para 10.000 frases).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Resultado | Justificativa |
|---|---|---|
| I. Spec-Driven Development | PASS | `spec.md` aprovada antes deste plano; `/speckit.clarify` não encontrou ambiguidades que exigissem registro adicional além das Assumptions já na spec |
| II. Local-First Ownership | PASS | Nenhuma mudança de armazenamento; a Reading View é derivada em memória do `timeline`/`audio` já locais, nada novo é persistido ou enviado ao servidor |
| III. Simple and Modular Backend | N/A (PASS) | Backend não é tocado (FR-014) |
| IV. Mandatory Tests | PASS | Novos módulos puros e de DOM ganham testes unitários dedicados; suíte existente (incl. `player.test.ts`, `main.test.ts`) permanece verde sem alteração de `player.ts`; um novo teste e2e cobre o fluxo real no navegador |
| V. Incremental Pipeline Compatibility | N/A (PASS) | Pipeline de áudio/timeline não é alterado, apenas consumido como já produzido |
| VI. Security by Default | PASS | Nenhuma nova entrada externa; texto exibido já passou por normalização/validação nas fases anteriores; timeline corrompida é tratada defensivamente (FR-011) sem expor stack traces ao usuário |
| VII. No Overengineering | PASS | Reaproveita `parseTimeline` existente em vez de um segundo validador; usa `timeupdate` nativo em vez de loop próprio; busca binária simples em vez de cache incremental; sem botão dedicado de "retomar rolagem" além do que as Assumptions exigem |
| VIII. Phase-Bounded Delivery | PASS | Escopo restrito aos dois fluxos de reprodução já existentes (reabrir estudo salvo e reprodução logo após gerar); nenhuma mistura com fases futuras (sincronização por palavra, edição de texto) |
| IX. Architecture Ready for Evolution | PASS | Lógica de resolução de frase (`reading/sentenceLookup.ts`) é pura e isolada da renderização (`ui/readingView.ts`), que por sua vez é isolada da persistência (`player.ts`, intocado) — cada peça é substituível/testável isoladamente |
| X. Explicit Technical Decisions | PASS | Decisões (busca binária, reaproveitar `parseTimeline`, dependência de ordem de listeners entre `player.ts` e `readingView.ts`, `floor` na conversão amostra, tratamento de fim/overshoot) documentadas em `research.md` |

Nenhuma violação. `Complexity Tracking` não é necessário.

## Project Structure

### Documentation (this feature)

```text
specs/005-synced-text-player/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

Sem pasta `contracts/`: esta fase não introduz nenhuma interface externa nova (API, CLI, schema) —
é uma feature puramente interna ao app cliente, consumindo a `TimelineDocument` já contratada pela
Fase 3.1 (`specs/001-text-audio-timeline/contracts/timeline-v1.schema.json`) sem alterá-la.

### Source Code (repository root)

```text
frontend/
├── src/
│   ├── reading/
│   │   └── sentenceLookup.ts   # NOVO — lookup puro (busca binária), sem DOM
│   ├── ui/
│   │   ├── player.ts            # intocado
│   │   ├── libraryView.ts       # intocado
│   │   ├── readingView.ts       # NOVO — renderização + sincronização com o <audio>
│   │   └── theme.ts              # intocado
│   ├── library/                  # intocado (types.ts já expõe TimelineDocument/TimelineSentence)
│   ├── api/                      # intocado (validators.ts: parseTimeline reaproveitado, não alterado)
│   ├── application/              # intocado
│   ├── main.ts                   # modificado — monta a Reading View e conecta aos dois fluxos de abertura
│   └── styles.css                # modificado — novo bloco `.reading-*`
├── tests/
│   ├── unit/
│   │   ├── sentenceLookup.test.ts  # NOVO
│   │   ├── readingView.test.ts     # NOVO
│   │   └── main.test.ts            # estendido
│   └── setup.ts                    # intocado (fixtures reaproveitadas, não alteradas)
└── e2e/
    └── library.spec.ts             # estendido com um novo `test(...)`
```

**Structure Decision**: nenhum workspace novo. Dois arquivos de produto novos —
`frontend/src/reading/sentenceLookup.ts` (lógica pura de resolução de frase, nova pasta de domínio
`reading/`) e `frontend/src/ui/readingView.ts` (renderização/sincronização, mesma convenção de
`ui/player.ts` e `ui/libraryView.ts`) — mais dois arquivos modificados, `frontend/src/main.ts`
(monta e conecta a Reading View aos dois fluxos de reprodução de um estudo) e
`frontend/src/styles.css` (bloco novo de classes `.reading-*`, tokens-only). `frontend/src/ui/player.ts`
e `frontend/src/api/validators.ts` permanecem intocados (o segundo é apenas reaproveitado).

## Complexity Tracking

> Não aplicável — nenhuma violação do Constitution Check acima.
