# Tasks: Migração do frontend para o Design System HSS Music

**Input**: Design documents from `/specs/004-hss-music-design-system/`

**Prerequisites**: plan.md, spec.md, research.md, quickstart.md

**Nota de processo**: esta feature documenta retroativamente um trabalho já commitado (`3619557`,
`923dd1d`). As tarefas de implementação visual (T001–T006) estão marcadas `[X]` porque já existem no
código, verificadas nesta sessão de documentação. As tarefas abertas (T007–T012) são o que de fato
falta: verificação manual e, onde necessário, correção.

**Organization**: tarefas agrupadas por user story, como nas fases anteriores. Todo código novo fica
em `frontend/`, exceto a eventual correção de codificação em `backend/app/services/audio/` prevista
por FR-011.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: arquivo diferente e nenhuma dependência incompleta
- **[Story]**: `US1`, `US2`, `US3` ou `US4`
- Caminhos são relativos à raiz do repositório

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: nenhuma ferramenta nova — reaproveita o workspace `frontend/` da Fase 5.

- [X] T001 Confirmar que `frontend/package.json`, `vite.config.ts`, `vitest.config.ts` e
  `playwright.config.ts` da Fase 5 não precisam de nenhuma dependência nova para consumir o design
  system (CSS puro, sem pré-processador) — confirmado nesta sessão.

**Checkpoint**: nenhuma mudança de ferramentas necessária.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: vendorizar o design system antes de qualquer tela consumi-lo.

- [X] T002 [P] Vendorizar `frontend/src/hss/tokens.css`, `tokens.json` e `bundle.css` (tokens
  dark/light, tipografia, espaçamento, raio, e classes `hss-btn`/`hss-chip`/`hss-search`/`hss-card`/
  `hss-row`/`hss-libitem`/`hss-player`/`hss-menu`/`hss-shelf`/`hss-mood`/`hss-panel`)
- [X] T003 [P] Documentar as regras de uso em `DESIGN.md` (raiz do repositório): cores só por token,
  um acento por tela, sentence case, componentes por necessidade, do/don't
- [X] T004 [P] Adicionar `README.md` + `preview.html` por componente em
  `frontend/src/hss/components/` (Button, Chip, LibraryItem, MediaCard, Menu, MoodShortcut,
  PlayerBar, SearchField, Shelf, TrackRow; `Cover/` tem apenas `preview.html`)

**Checkpoint**: design system disponível para consumo pelas telas do produto.

---

## Phase 3: User Story 1 - Reconhecer a identidade visual HSS Music (Priority: P1) MVP

**Goal**: toda tela do Study Voice usa exclusivamente tokens/classes do HSS Music.

**Independent Test**: inspecionar `styles.css` (só dois `@import` + layout em `var(--...)`),
`index.html` (`lang`/`data-theme`/`hss-surface`/fontes) e o DOM renderizado (classes `hss-*`).

### Implementation for User Story 1

- [X] T005 [US1] Migrar `frontend/index.html`: `lang="pt-BR"`, `data-theme="dark"`, `hss-surface` no
  `<body>`, fontes Figtree 400/700/800 e DM Mono 400 via Google Fonts
- [X] T006 [US1] Reduzir `frontend/src/styles.css` a dois `@import` (`hss/tokens.css`,
  `hss/bundle.css`) seguidos de regras de layout próprias do Study Voice (`.shell`, `.masthead`,
  `.workspace`, `.desk`, `.field`/`.field-input`, `.status-line`, `.now-playing`/`.player-frame`,
  `.archive`, `.library-list`/`.study-row`, `.row-actions`, `.study-details`), todas usando apenas
  `var(--...)`
- [X] T007 [US1] Migrar `frontend/src/main.ts` para usar `hss-panel` (mesa de criação) e
  `hss-btn hss-btn-primary` (ação "Gerar estudo em áudio", único acento de tela)
- [X] T008 [US1] Migrar `frontend/src/ui/libraryView.ts` para usar `hss-panel` (arquivo local),
  `hss-row`/`hss-row-index`/`hss-row-main`/`hss-row-title`/`hss-row-artist`/`hss-row-album`/
  `hss-row-time` (linhas da biblioteca) e `hss-btn hss-btn-tertiary hss-btn-sm` (ações
  Detalhes/Ouvir/Remover)

**Checkpoint**: US1 entrega a identidade visual completa; verificado nesta sessão via build/inspeção
de código, sem regressão nos 71 testes unitários.

---

## Phase 4: User Story 2 - Ver o estudo em reprodução destacado na biblioteca (Priority: P2)

**Goal**: a linha do estudo carregado no player é destacada de forma confiável nos três gatilhos
(abrir, pausar, concluir).

**Independent Test**: abrir um estudo, pausar, deixar concluir, abrir outro — conferir o destaque em
cada momento (ver `quickstart.md` §4).

### Tests for User Story 2

> T009 é verificação manual, não teste automatizado — não há asserção de CSS computado nesta stack.

- [ ] T009 [US2] Executar o roteiro de `quickstart.md` §4 (pausar / concluir / trocar de estudo) e
  registrar o resultado observado para cada um dos três gatilhos

### Implementation for User Story 2

- [X] T010 [US2] Implementar `is-playing` + glifo de reprodução em
  `frontend/src/ui/libraryView.ts:81-90`, calculado a partir de `isPlaying?.(studyId)`
- [ ] T011 [US2] Com base no resultado de T009: se pausar e/ou concluir não limparem `is-playing`
  corretamente (comportamento hoje esperado por `research.md` §2), ajustar o gatilho de
  `refresh()`/o cálculo de `isOpen` em `frontend/src/ui/player.ts` e/ou `frontend/src/main.ts` para
  cobrir os três casos de FR-006, preservando a suíte de 71 testes unitários

**Checkpoint**: US2 fica concluída quando T009 confirma os três gatilhos corretos (com ou sem a
correção de T011).

---

## Phase 5: User Story 3 - Usar o produto em tema claro e em largura mobile estreita (Priority: P3)

**Goal**: nenhuma tela perde conteúdo ou legibilidade em tema claro ou em largura ≤390px.

**Independent Test**: roteiro de `quickstart.md` §2–3.

### Tests for User Story 3

- [ ] T012 [US3] Executar o roteiro de `quickstart.md` §2 (tema claro) em todas as telas e registrar
  o resultado
- [ ] T013 [US3] Executar o roteiro de `quickstart.md` §3 (largura ≤390px) em todas as telas e
  registrar o resultado

### Implementation for User Story 3

- [ ] T014 [US3] Caso T012 ou T013 encontrem conteúdo cortado, sobreposto ou ilegível, corrigir com
  regras adicionais em `frontend/src/styles.css` (sempre via tokens existentes, nunca valores
  hardcoded) ou ajustar o breakpoint de `frontend/src/styles.css:246`

**Checkpoint**: US3 concluída quando T012/T013 não encontram nenhum problema (ou T014 os corrige).

---

## Phase 6: Investigação — `UnicodeDecodeError`/`cp1252` no servidor de desenvolvimento

> Não é uma user story do produto — é o item de investigação técnica pedido pelo usuário (FR-011,
> SC-005), análogo em espírito à nota de "Phase 6 interna ≠ fase do produto" já usada em
> `003-local-study-library/tasks.md`.

- [X] T015 Reproduzir o erro via `npm run test:e2e` e localizar a causa raiz: `subprocess.run(...,
  text=True)` sem `encoding` em `backend/app/services/audio/concatenator.py:101-106` e
  `backend/app/services/audio/exporter.py:93-98`, decodificando a saída UTF-8 do FFmpeg como
  `cp1252` — documentado em `research.md` §6
- [ ] T016 Decidir e, se aprovado, aplicar a correção mínima (`encoding="utf-8", errors="replace"`
  nas duas chamadas) e confirmar via `npm run test:e2e` que o traceback não aparece mais e que a
  suíte `uv run pytest tests` do backend continua verde

---

## Phase 7: User Story 4 - Player customizado HSS Music (Priority: P4, futuro — fora de escopo)

**Goal**: não é trabalho desta fase. Registrado apenas como backlog.

- [ ] (backlog, não iniciado) Implementar transporte de áudio com `hss-player`/`hss-iconbtn-play` em
  substituição ao `<audio controls>` nativo, com testes unitários e e2e próprios — **não faz parte do
  escopo aprovado da Fase 6**; abrir como feature própria quando priorizado.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T017 [P] Executar `npm run build` em `frontend/` e confirmar sucesso sem relaxar TypeScript
  estrito — confirmado nesta sessão
- [X] T018 [P] Executar `npm test` em `frontend/` e confirmar os 71 testes unitários (8 arquivos)
  verdes — confirmado nesta sessão, sem regressão da Fase 5
- [X] T019 [P] Executar `npm run test:e2e` em `frontend/` com backend real e proxy Vite e confirmar
  os 2 testes Playwright verdes — confirmado nesta sessão (com o traceback de `cp1252` registrado em
  T015, que não derruba os testes)
- [ ] T020 Atualizar a tabela de rastreabilidade de `quickstart.md` com os resultados reais de
  T009/T012/T013/T016 após essas tarefas serem concluídas

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup/Foundational (T001–T004): já concluídas, sem dependências pendentes.
- US1 (T005–T008): já concluída, entrega o MVP visual; US2/US3 dependem dela.
- US2 (T009–T011) e US3 (T012–T014): independentes entre si, ambas podem avançar em paralelo.
- Investigação `cp1252` (T015–T016): independente de US2/US3, pode avançar em paralelo.
- US4: backlog, sem dependência de execução nesta fase.
- Polish (T017–T020): T017–T019 já concluídas; T020 depende de T009/T012/T013/T016.

### User Story Graph

```text
Setup → Foundational → US1 (MVP, concluída)
                           ├──→ US2 (verificação pendente: T009–T011)
                           ├──→ US3 (verificação pendente: T012–T014)
                           └──→ Investigação cp1252 (T015 concluída; T016 pendente)
US2 + US3 + Investigação → Polish (T020)
US4 → backlog, fora desta fase
```

### Parallel Opportunities

- T009 (US2) e T012/T013 (US3) podem ser executadas em paralelo — áreas de verificação distintas.
- T015/T016 (investigação `cp1252`) são independentes de US2/US3 e podem avançar em paralelo.

## Notes

- Nenhuma tarefa desta fase deveria reimplementar o que já está em `3619557`/`923dd1d` — T005–T008 e
  T010 estão marcadas `[X]` porque já existem no código, não porque foram refeitas nesta sessão.
- T011, T014 e T016 só devem ser executadas se as respectivas verificações (T009, T012/T013, T015)
  confirmarem um problema — do contrário, basta registrar o resultado "sem correção necessária" em
  `quickstart.md`.
- Nenhuma tarefa desta fase altera o esquema de armazenamento local, o pipeline de síntese além da
  correção pontual de T016, ou introduz o player customizado de US4.
