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
> Nesta sessão, a verificação dos três gatilhos foi feita via teste de integração determinístico em
> `frontend/tests/unit/main.test.ts` (disparando os eventos reais `play`/`pause`/`ended` no elemento
> `<audio>` e inspecionando a classe `is-playing` renderizada), já que o Chrome conectado a esta
> sessão não tem acesso de rede ao `localhost` do ambiente onde os servidores de desenvolvimento
> rodam — verificação visual manual em navegador real fica para quem tiver acesso direto ao app.

- [X] T009 [US2] Executar o roteiro equivalente ao de `quickstart.md` §4 (pausar / concluir / trocar
  de estudo), via `frontend/tests/unit/main.test.ts` (`highlights is-playing only while actually
  playing...`) e `frontend/tests/unit/player.test.ts` (`tracks the playing state across play, pause
  and ended...`): confirmado que, antes da correção de T011, (a) pausar sem trocar de estudo **não**
  limpava `is-playing` (nenhum `refresh()` era disparado) e (b) concluir a reprodução **não** limpava
  `is-playing` (glifo permanecia ao lado de "Concluído", pois `isOpen` só é zerado por `discard()`);
  (c) trocar de estudo já funcionava corretamente

### Implementation for User Story 2

- [X] T010 [US2] Implementar `is-playing` + glifo de reprodução em
  `frontend/src/ui/libraryView.ts:81-90`, calculado a partir de `isPlaying?.(studyId)`
- [X] T011 [US2] Corrigidos os dois casos confirmados por T009: `frontend/src/ui/player.ts` agora
  expõe `isPlaying(): boolean` (refletindo o estado real de play/pause do `<audio>`) e dispara
  `onPlaying`/`onPaused` nos eventos `play`/`pause`, além do `onCompleted` já existente em `ended`;
  `frontend/src/main.ts` passa a calcular `isPlaying: (studyId) => player.isOpen(studyId) &&
  player.isPlaying()` e aciona `libraryView.refresh()` nos três eventos. Suíte unitária passou de 71
  para 73 testes (2 novos cobrindo os gatilhos de pausa/retomada/conclusão), todos verdes; `npm run
  build` e `npm run test:e2e` (2 testes) seguem verdes sem regressão

**Checkpoint**: US2 concluída — T009 confirmou os três gatilhos e T011 corrigiu os dois que
precisavam de ajuste (pausar e concluir); trocar de estudo já funcionava.

---

## Phase 5: User Story 3 - Usar o produto em tema claro e em largura mobile estreita (Priority: P3)

**Goal**: nenhuma tela perde conteúdo ou legibilidade em tema claro ou em largura ≤390px.

**Independent Test**: roteiro de `quickstart.md` §2–3.

### Tests for User Story 3

> O roteiro de `quickstart.md` §2–3 pede uma inspeção visual em navegador real (DevTools, redimensionar
> janela). O Chrome conectado a esta sessão não tem acesso de rede ao `localhost` deste ambiente — a
> mesma limitação já registrada na nota de T009. Por isso, nesta sessão, T012/T013 foram tratadas com
> **validação estática** (leitura de tokens, matemática de box model, cálculo de contraste), não com a
> inspeção visual pedida pelo roteiro. Essa validação estática não substitui a conferência visual real:
> os itens abaixo permanecem **não marcados como concluídos** até alguém com acesso direto ao app
> confirmar visualmente.

- [ ] T012 [US3] Executar o roteiro de `quickstart.md` §2 (tema claro) em todas as telas e registrar
  o resultado. **Validação estática feita nesta sessão** (não substitui a inspeção visual real):
  - `frontend/src/hss/tokens.css:34-63` define uma paleta `[data-theme="light"]` completa e independente
    (nenhum valor herda do tema escuro por acidente).
  - `frontend/src/hss/bundle.css:102-106` confirma que o tema claro usa divisórias
    (`border-inline-end`/`border-top` com `--border-subtle`), não camadas cinza — consistente com o
    roteiro.
  - Contraste calculado (luminância relativa WCAG) de texto sobre fundo claro: `--text-secondary`
    (#4f5753) sobre `--bg-panel` (#ffffff) ≈ 7.45:1; `--accent-text` (#006b49) sobre `--bg-panel`/
    `--bg-raised` ≈ 6.5:1; `--danger` (#b3202a) sobre `--bg-panel` ≈ 6.65:1 — todos acima do mínimo AA
    (4.5:1) para texto normal.
  - Nenhum valor hardcoded encontrado em `frontend/src/styles.css` que pudesse quebrar no tema claro
    (todas as regras usam `var(--...)`, confirmando SC-001 também sob este ângulo).
  - **Pendente**: a conferência visual real (abrir o app, alternar `data-theme` no DevTools, percorrer
    mastro/mesa/arquivo) descrita no roteiro, que só pode ser feita por quem tem acesso direto ao
    `npm run dev` deste ambiente.
- [ ] T013 [US3] Executar o roteiro de `quickstart.md` §3 (largura ≤390px) em todas as telas e
  registrar o resultado. **Validação estática feita nesta sessão** (não substitui a inspeção visual
  real):
  - `frontend/index.html:5` tem a meta viewport correta; `frontend/src/styles.css:6,10` fixam
    `min-width: 320px` em `html`/`body.hss-surface`, abaixo do pior caso de 390px.
  - O único breakpoint (`frontend/src/styles.css:246`, `max-width: 820px`) já reorganiza `.workspace`
    em coluna única bem acima de 390px, antes de qualquer risco de aperto.
  - Cálculo de largura disponível a 390px (`.shell` → `.desk`/`.archive` → `.study-row`) não encontra
    nenhum elemento com largura mínima fixa maior que o espaço sobrando: as colunas de `.hss-row`
    (`frontend/src/hss/bundle.css:53`) usam `minmax(0, …)` com `overflow: hidden`/`text-overflow:
    ellipsis` em título/artista/álbum (truncam, não cortam a caixa); `.row-actions` tem
    `flex-wrap: wrap`; `.form-actions` não força nowrap no texto de status.
  - `.study-details dl div` (`frontend/src/styles.css:237`) sobra ~150px para o valor após a coluna de
    rótulo (`minmax(5rem, 0.4fr)`) a 390px — sem necessidade de rolagem horizontal.
  - **Pendente**: a conferência visual real (redimensionar a janela/DevTools para ≤390px e observar o
    app rodando) descrita no roteiro, que só pode ser feita por quem tem acesso direto ao `npm run dev`
    deste ambiente.

### Implementation for User Story 3

- [ ] T014 [US3] Caso T012 ou T013 encontrem conteúdo cortado, sobreposto ou ilegível, corrigir com
  regras adicionais em `frontend/src/styles.css` (sempre via tokens existentes, nunca valores
  hardcoded) ou ajustar o breakpoint de `frontend/src/styles.css:246`. **Nesta sessão**: a validação
  estática de T012/T013 não encontrou nenhum indício de corte, sobreposição ou rolagem horizontal
  forçada — por isso nenhuma correção foi aplicada. Esta tarefa permanece aberta: ela só pode ser
  fechada (como "sem correção necessária" ou com uma correção de fato) depois que a conferência visual
  real pendente em T012/T013 for feita.

**Checkpoint**: US3 ainda não concluída — falta a conferência visual real de T012/T013 (ver notas
acima). A validação estática desta sessão não encontrou problemas, mas não é o critério de aceite do
roteiro (`quickstart.md` §2–3), que exige inspeção visual em navegador real.

---

## Phase 6: Investigação — `UnicodeDecodeError`/`cp1252` no servidor de desenvolvimento

> Não é uma user story do produto — é o item de investigação técnica pedido pelo usuário (FR-011,
> SC-005), análogo em espírito à nota de "Phase 6 interna ≠ fase do produto" já usada em
> `003-local-study-library/tasks.md`.

- [X] T015 Reproduzir o erro via `npm run test:e2e` e localizar a causa raiz: `subprocess.run(...,
  text=True)` sem `encoding` em `backend/app/services/audio/concatenator.py:101-106` e
  `backend/app/services/audio/exporter.py:93-98`, decodificando a saída UTF-8 do FFmpeg como
  `cp1252` — documentado em `research.md` §6
- [X] T016 Decidir e, se aprovado, aplicar a correção mínima (`encoding="utf-8", errors="replace"`
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
- [X] T018 [P] Executar `npm test` em `frontend/` e confirmar os testes unitários verdes — eram 71
  (8 arquivos); após a correção de T011 (com 2 testes novos em `player.test.ts`/`main.test.ts`), 73
  testes (8 arquivos), sem regressão
- [X] T019 [P] Executar `npm run test:e2e` em `frontend/` com backend real e proxy Vite e confirmar
  os 2 testes Playwright verdes — confirmado nesta sessão; após a correção de T016 (`encoding="utf-8"`
  no ffmpeg), o traceback de `cp1252` já não aparece mais no log do backend
- [ ] T020 Atualizar a tabela de rastreabilidade de `quickstart.md` com os resultados reais de
  T009/T012/T013/T016 após essas tarefas serem concluídas. **Feito nesta sessão, com uma ressalva**: a
  tabela foi atualizada com base nas evidências já existentes em código/testes/`quickstart.md` — T009 e
  T016 estão concluídas (PASS) e a tabela reflete isso; T012/T013 só têm validação estática nesta
  sessão (ver notas acima), então as linhas correspondentes (FR-009, SC-002) ficam marcadas como
  parcialmente verificadas, não como PASS. Esta tarefa continua sem o `[X]` porque a tabela ainda não
  está "fechada" — ela precisa de uma nova atualização quando a conferência visual real de T012/T013
  acontecer.

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup/Foundational (T001–T004): já concluídas, sem dependências pendentes.
- US1 (T005–T008): já concluída, entrega o MVP visual; US2/US3 dependem dela.
- US2 (T009–T011): concluída nesta sessão. US3 (T012–T014): ainda pendente.
- Investigação `cp1252` (T015–T016): concluída (sessão anterior).
- US4: backlog, sem dependência de execução nesta fase.
- Polish (T017–T020): T017–T019 já concluídas; T020 depende de T012/T013 (únicas verificações ainda
  em aberto).

### User Story Graph

```text
Setup → Foundational → US1 (MVP, concluída)
                           ├──→ US2 (concluída: T009–T011)
                           ├──→ US3 (verificação pendente: T012–T014)
                           └──→ Investigação cp1252 (concluída: T015–T016)
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
