# Tasks: Player com texto sincronizado

**Input**: Design documents from `/specs/005-synced-text-player/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: obrigatórios pelo spec (FR-016) e pelo Princípio IV da constituição. Em cada fase, escrever
e executar os testes RED antes da implementação GREEN correspondente.

**Organization**: tarefas agrupadas por user story, como nas fases anteriores. Todo código novo fica
em `frontend/`; nenhuma mudança em `backend/`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: arquivo diferente e nenhuma dependência incompleta
- **[Story]**: `US1`, `US2` ou `US3`
- Caminhos são relativos à raiz do repositório

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: nenhuma ferramenta nova — reaproveita o workspace `frontend/` já existente.

- [X] T001 Confirmar que `frontend/package.json`, `vitest.config.ts` e `playwright.config.ts`
  atuais não precisam de nenhuma dependência nova para esta feature (sem framework de UI, sem
  biblioteca de scroll/observers — ver `plan.md` Technical Context)

**Checkpoint**: nenhuma mudança de ferramentas necessária.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: a lógica de resolução de frase por posição de amostra é usada por todas as user
stories (destaque contínuo em US1, recálculo após clique em US2, posição inicial e fim de áudio em
US3) — nenhuma delas pode ser implementada antes dela existir.

**CRITICAL**: nenhuma user story começa antes desta fase.

- [X] T002 Criar `frontend/tests/unit/sentenceLookup.test.ts` cobrindo `findSentenceIndexAtSample`:
  amostra no início/meio/fim da primeira, de uma frase intermediária e da última frase; amostra
  exatamente no limite entre duas frases (`end_sample` de A == `start_sample` de B) resolve
  consistentemente para B (intervalo semiaberto `[start_sample, end_sample)`); amostra igual a
  `total_samples` e amostra além de `total_samples` (overshoot) resolvem para a última frase;
  amostra negativa resolve para a primeira frase; timeline sintética com 5.000+ frases resolve
  corretamente em posições espalhadas. Usar timelines construídas localmente no arquivo (não alterar
  `frontend/tests/setup.ts`)
- [X] T003 Implementar `frontend/src/reading/sentenceLookup.ts`: `flattenSentences(timeline:
  TimelineDocument): TimelineSentence[]` (concatena `chunk.sentences` na ordem dos chunks) e
  `findSentenceIndexAtSample(sentences: readonly TimelineSentence[], samplePosition: number):
  number` por busca binária sobre `start_sample`, clampando `samplePosition < 0` para `0` e
  `samplePosition >= sentences[last].end_sample` para o último índice (data-model.md, invariante de
  Current Sentence Resolution) — até T002 passar

**Checkpoint**: lookup de frase por amostra disponível e testado; nenhuma user story depende de mais
nada além disto para começar.

---

## Phase 3: User Story 1 - Acompanhar o texto enquanto o áudio toca (Priority: P1) 🎯 MVP

**Goal**: ao abrir um estudo (salvo pela biblioteca, ou logo após gerá-lo), o texto completo aparece
agrupado por chunk/frase, a frase correspondente à posição de reprodução fica destacada em tempo
real, a visualização rola automaticamente até ela sem brigar com rolagem manual, e uma timeline
ausente/corrompida degrada para "áudio toca, texto indisponível" em vez de quebrar a tela.

**Independent Test**: abrir um estudo salvo com timeline conhecida, iniciar a reprodução e verificar
que a frase destacada muda continuamente acompanhando o áudio, com rolagem automática e suspensão ao
rolar manualmente; simular uma timeline corrompida e confirmar que o áudio continua tocando com um
aviso claro no lugar do texto.

### Tests for User Story 1

> Executar T004–T005 e confirmar RED antes de T006–T008.

- [X] T004 [P] [US1] Criar `frontend/tests/unit/readingView.test.ts` (eventos nativos sobre
  `document.createElement('audio')`, como em `player.test.ts`): FR-001 `open()` renderiza
  chunks/frases na mesma ordem da timeline; FR-002/FR-004 definir `audio.currentTime` e disparar
  `timeupdate` destaca exatamente uma frase (`aria-current="true"`) por vez, removendo o destaque da
  anterior, sem lag perceptível entre ticks; FR-005/FR-006 mudar de frase chama `scrollIntoView`
  (stubado via `vi.fn()` em `Element.prototype.scrollIntoView`); um `scroll` manual no contêiner
  suspende chamadas seguintes até um `seeked` ou `play` no áudio; FR-011 `open()` com uma timeline
  deliberadamente inválida (derivada de `makeTimeline()` com um campo alterado) renderiza uma
  mensagem de indisponibilidade, não lança exceção, e não impede futuras chamadas a `open()`/eventos
  do áudio; FR-015 a frase destacada tem `aria-current="true"` **e** um sinal não dependente de cor
  (ex.: `font-weight` diferente), nunca só cor; **renderização em lote** (cobre o requisito de T006):
  instalar um spy (`vi.spyOn`) diretamente na instância do `container` —
  `vi.spyOn(container, 'replaceChildren')` e `vi.spyOn(container, 'appendChild')` — nunca em
  `Element.prototype`, para não capturar os `appendChild` usados ao montar cada frase/chunk fora do
  DOM (dentro do `DocumentFragment`, ainda não anexado); antes de chamar `open()`; para uma timeline
  pequena (poucas frases) e para uma timeline sintética com milhares de frases (mesma ordem de
  grandeza de T002), confirmar que exatamente uma dessas duas chamadas (`replaceChildren` ou
  `appendChild` recebendo o `DocumentFragment` já montado) ocorre sobre o `container`, e nenhuma
  chamada adicional por frase — a contagem total de chamadas sobre o `container` deve ser idêntica
  independentemente da quantidade de frases. Apenas o teste (RED); não implementar `readingView.ts`
  nesta tarefa
- [X] T005 [P] [US1] Estender `frontend/tests/unit/main.test.ts`: reabrir um estudo salvo pela
  biblioteca monta a Reading View com o texto daquele estudo; gerar um estudo novo pelo formulário
  também monta a Reading View com o texto recém-gerado (decisão confirmada: texto sincronizado vale
  tanto para reabertura quanto para reprodução imediata); os testes já existentes de
  reproduzir/pausar/retomar/erro continuam passando sem nenhuma alteração em `frontend/src/ui/player.ts`

### Implementation for User Story 1

- [X] T006 [US1] Implementar `frontend/src/ui/readingView.ts`: `createReadingView(container:
  HTMLElement, audio: HTMLAudioElement): ReadingView` com `open(study)`/`discard()`. `open()` chama
  `discard()`, tenta `parseTimeline(study.timeline)` (reaproveitado de
  `frontend/src/api/validators.ts`, não alterado) dentro de `try/catch`; em falha, renderiza a
  mensagem de indisponibilidade (FR-011) sem lançar; em sucesso, achata as frases
  (`flattenSentences`), renderiza cada chunk/frase como um `<button>` clicável (clique ainda sem
  comportamento — ver T010) guardando um array paralelo de elementos. **Renderização em lote
  obrigatória**: construir todos os elementos de chunk/frase num `DocumentFragment` isolado e anexá-lo
  ao container com um único `appendChild`/`replaceChildren` ao final, em vez de inserir nó a nó
  diretamente no DOM ativo — evita reflow por frase em estudos longos (timelines com milhares de
  frases, mesma ordem de grandeza do cenário de T002). Listener de `timeupdate`
  calcula `samplePosition = Math.floor(audio.currentTime * sample_rate_hz)` (floor, não round —
  research.md Decisão 5), resolve via `findSentenceIndexAtSample` (T003) e só atualiza o DOM se o
  índice mudou (FR-002/003/004). Rolagem automática via
  `element.scrollIntoView({ block: 'nearest', behavior: 'smooth' })` a cada mudança de frase, com uma
  janela transitória para distinguir rolagem própria de um `scroll` manual do usuário no contêiner,
  que suspende o auto-scroll até o próximo `seeked`/`play` do áudio (FR-005/006, research.md Decisão
  4). Depende de T002/T003
- [X] T007 [P] [US1] Adicionar bloco `.reading-*` em `frontend/src/styles.css` (após o bloco
  `.player-frame` existente, tokens-only, seguindo a convenção flat do arquivo): frase atual com
  `[aria-current="true"]` combinando `font-weight: 700` (sinal não-cor) e fundo `var(--bg-hover)`
  (FR-015, research.md Decisão 3); contêiner com `max-height`/`overflow-y: auto`; incluir os ajustes
  de largura estreita no `@media (max-width: 820px)` já existente, sem criar uma nova media query
- [X] T008 [US1] Em `frontend/src/main.ts`: adicionar `<section class="reading-frame"
  data-reading-view aria-label="Texto sincronizado"></section>` dentro de `.now-playing`, depois de
  `.player-frame`; criar `const readingView = createReadingView(root.querySelector('[data-reading-view]')!, audio)`
  **depois** de `const player = createLocalPlayer(...)` (dependência de ordem explícita: o
  `loadedmetadata` de `readingView` precisa ver a posição já corrigida pelo `loadedmetadata` de
  `player` — research.md Decisão 7; deixar um comentário no código apontando essa dependência); no
  handler `onOpen` (reabrir estudo salvo), chamar `readingView.open(study)` logo após
  `player.open(study)`; no handler de submit do formulário (estudo recém-gerado), chamar
  `readingView.open({ timeline: outcome.result.timeline, progress: { positionSeconds: 0, completed:
  false } })` logo após `audio.src = activeObjectUrl`, independentemente de `outcome.saved`; em
  `onRemoved`, chamar `readingView.discard()` junto com `player.discard()`. Depende de T006

**Checkpoint**: US1 entrega o MVP — texto sincronizado visível e destacado em tempo real, com
degradação graciosa, em ambos os fluxos de reprodução.

---

## Phase 4: User Story 2 - Pular para um trecho clicando no texto (Priority: P2)

**Goal**: clicar em qualquer frase do texto reposiciona a reprodução para o início exato dela, sem
alterar se o áudio está tocando ou pausado.

**Independent Test**: com um estudo aberto (US1 já funcionando), clicar numa frase diferente da
atual enquanto o áudio toca e enquanto está pausado; confirmar que a posição salta para o início
exato da frase clicada e o destaque é atualizado imediatamente nos dois casos, sem o clique iniciar
ou pausar a reprodução.

### Tests for User Story 2

> Executar T009 e confirmar RED antes de T010.

- [X] T009 [US2] Estender `frontend/tests/unit/readingView.test.ts`: clicar no botão de uma frase
  define `audio.currentTime = sentence.start_sample / sample_rate_hz` e destaca essa frase
  imediatamente, tanto com o áudio tocando quanto pausado (FR-007/FR-008); o clique nunca chama
  `audio.play()` nem `audio.pause()` (preserva o estado de reprodução, conforme as Assumptions do
  spec); **caso de concorrência (seek nativo vs. clique)**: com o destaque já estabelecido numa frase
  X por um `timeupdate` anterior, clicar numa frase Y e, em seguida (ainda de forma síncrona no
  teste, simulando um evento de seek nativo da barra de progresso do `<audio>` que estava em
  andamento) disparar um `timeupdate`/`seeked` referente a uma posição de uma frase Z diferente de Y
  — o destaque final MUST refletir Z (o evento processado por último), nunca reverter para Y nem para
  X; repetir na ordem inversa (seek para Z primeiro, clique em Y depois) e confirmar que Y prevalece.
  Isso garante que nenhuma lógica de supressão introduzida para o auto-scroll (FR-005/006) também
  suprima o próprio cálculo de destaque — apenas a chamada a `scrollIntoView` pode ser suspensa, nunca
  a resolução de `findSentenceIndexAtSample`

### Implementation for User Story 2

- [X] T010 [US2] Em `frontend/src/ui/readingView.ts`, adicionar um listener de `click` em cada
  elemento de frase criado em T006: ao clicar, destacar a frase sincronamente e então definir
  `audio.currentTime = sentences[i].start_sample / sampleRateHz` — isso já dispara o `seeked` nativo
  que `player.ts` usa para persistir progresso, sem duplicar lógica. Nunca chamar `play`/`pause`.
  **Garantia de concorrência (cobre T009)**: o cálculo de destaque (`findSentenceIndexAtSample` sobre
  o `timeupdate`/`seeked` mais recente) MUST permanecer incondicional — a janela de supressão de
  auto-scroll (T006, FR-005/006) só pode pular a chamada a `scrollIntoView`, nunca pular a atualização
  do índice destacado; como cada handler já lê `audio.currentTime` no momento em que é chamado, o
  último evento processado (clique ou `timeupdate`/`seeked` nativo) naturalmente determina a frase
  final, sem necessidade de um contador de geração adicional. Depende de T006

**Checkpoint**: US1 + US2 funcionam juntas — destaque em tempo real e navegação por clique.

---

## Phase 5: User Story 3 - Retomar um estudo já iniciado com o texto certo (Priority: P3)

**Goal**: reabrir um estudo com progresso salvo já mostra, antes de qualquer reprodução, a frase
correspondente destacada e visível; ao final da reprodução, a última frase permanece destacada.

**Independent Test**: abrir um estudo com posição salva no meio do áudio e confirmar que a frase
correspondente aparece destacada e visível antes de iniciar a reprodução; repetir para um estudo
concluído (última frase) e um sem progresso (primeira frase); deixar um áudio curto terminar e
confirmar que a última frase permanece destacada após o fim.

### Tests for User Story 3

> Executar T011 e confirmar RED antes de T012.

- [X] T011 [US3] Estender `frontend/tests/unit/readingView.test.ts`: `open()` com
  `progress.positionSeconds` correspondente a uma frase intermediária destaca essa frase antes de
  qualquer evento de reprodução (FR-009); `progress.completed === true` destaca a última frase;
  `positionSeconds` zero ou sem progresso anterior destaca a primeira frase; disparar `ended` no
  áudio mantém a última frase destacada em vez de remover o destaque (FR-010)

### Implementation for User Story 3

- [X] T012 [US3] Em `frontend/src/ui/readingView.ts`, dentro de `open()`, calcular o destaque
  inicial a partir de `study.progress` antes de depender de qualquer evento do áudio: `completed ===
  true` resolve com `samplePosition = totalSamples` (mesmo clamp de T003 → última frase); caso
  contrário, `samplePosition = Math.floor(positionSeconds * sampleRateHz)` via
  `findSentenceIndexAtSample` (cobre posição zero → primeira frase, e overshoot por arredondamento →
  última frase, sem caso especial). Adicionar um listener de `ended` que força
  `samplePosition = totalSamples`, garantindo a última frase destacada de forma determinística
  (research.md Decisão 6). Depende de T006

**Checkpoint**: todas as três user stories funcionam juntas — a feature completa da spec.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T013 Adicionar um novo `test(...)` em `frontend/e2e/library.spec.ts` (não um arquivo
  novo): gerar e salvar um estudo, reabri-lo pela biblioteca, confirmar que o texto sincronizado
  aparece com o conteúdo esperado, e que clicar numa frase posterior avança `audio.currentTime` de
  verdade no navegador real (cobertura de SC-002, que exige um `<audio>` real fora do alcance
  confiável do jsdom). Não cobre SC-006 — ver T014
- [X] T014 Adicionar um novo `test(...)` em `frontend/e2e/library.spec.ts` dedicado a FR-012/SC-006:
  com a aplicação já carregada e um estudo salvo já aberto (áudio e timeline já residentes no
  armazenamento local/memória da página, sem depender de reload), chamar
  `page.context().setOffline(true)` e então, com a rede desligada, confirmar que (a) o texto
  sincronizado completo continua visível, (b) clicar numa frase ainda reposiciona `audio.currentTime`
  e atualiza o destaque corretamente, e (c) nenhuma requisição de rede é disparada durante essas
  interações (monitorar via `page.on('request', ...)` registrado antes de `setOffline(true)` e
  asserir lista vazia) — prova direta de que a exibição/destaque funcionam inteiramente a partir de
  dados locais, sem exigir conexão
- [X] T015 Adicionar uma medição leve de latência de destaque no mesmo `frontend/e2e/library.spec.ts`,
  cobrindo parcialmente SC-001: durante a reprodução real, capturar via `page.evaluate` o timestamp
  (`performance.now()`) em que `audio.currentTime` cruza o `start_sample` de uma frase conhecida e o
  timestamp em que o elemento correspondente recebe `aria-current="true"`, para uma amostra pequena de
  3–5 transições de frase; asserir que a diferença fica abaixo de 300ms em cada uma. **Limitação
  documentada**: isto cobre apenas o componente de atraso perceptível (<300ms) de SC-001; a outra
  metade do critério — "a frase destacada corresponde à frase realmente falada em pelo menos 95% das
  verificações amostradas" — exigiria comparação com transcrição/áudio real (ground truth de fala) e
  não tem cobertura automatizada viável sem um pipeline de ASR, o que seria overengineering para esta
  feature; essa parte permanece validação manual documentada no `quickstart.md` (ver T017)
- [X] T016 Executar `npm run build`, `npm test` e `npm run test:e2e` em `frontend/` e confirmar que
  tudo passa, incluindo a suíte pré-existente sem regressão (em especial `player.test.ts`, intocado)
- [X] T017 Executar os cenários manuais de `specs/005-synced-text-player/quickstart.md` (§1–§7) e
  registrar o resultado de cada um de volta nesse arquivo, incluindo uma verificação explícita e
  registrada de SC-001 (frase destacada corresponde à fala real, amostrada ao longo de um estudo de
  teste) como validação manual — não automatizada, pelo motivo descrito em T015. Cobertura
  automatizada equivalente por cenário registrada em `quickstart.md` nesta sessão; a parte
  irredutivelmente humana (ouvir o áudio e confirmar a correspondência frase/fala — segunda metade
  de SC-001 — e os demais cenários §1–§6) foi concluída e confirmada pelo usuário em sessão separada,
  rodando a aplicação real localmente

**Checkpoint**: feature completa, testada automaticamente (incluindo independência de rede e latência
de destaque) e validada manualmente conforme o `quickstart.md`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001)**: sem dependências — pode começar imediatamente.
- **Foundational (T002–T003)**: depende do Setup — bloqueia todas as user stories.
- **US1 (T004–T008)**: depende do Foundational. É o MVP; não depende de US2/US3.
- **US2 (T009–T010)**: depende de US1 (reaproveita `readingView.ts`/elementos criados em T006).
- **US3 (T011–T012)**: depende de US1 (idem). Independente de US2 — podem avançar em paralelo depois
  de US1.
- **Polish (T013–T017)**: depende de US1, US2 e US3 completas.

### User Story Graph

```text
Setup → Foundational (sentenceLookup) → US1 (MVP: render + destaque + auto-scroll + degradação)
                                           ├──→ US2 (clique para pular)
                                           └──→ US3 (retomar + fim de áudio)
US1 + US2 + US3 → Polish (e2e, build/test, quickstart)
```

### Within Each User Story

- Testes (RED) antes da implementação (GREEN) correspondente.
- `sentenceLookup.ts` (Foundational) antes de `readingView.ts` (US1).
- `readingView.ts` base (US1/T006) antes de qualquer extensão de US2/US3, que modificam o mesmo
  arquivo em pontos distintos (listeners de clique e de retomada/fim), portanto não são [P] entre si.

### Parallel Opportunities

- T004 e T005 (testes de US1, arquivos diferentes) podem ser escritos em paralelo.
- T007 (CSS) pode ser feito em paralelo a T006 (lógica), já que são arquivos diferentes; T008
  depende de T006 estar pronto.
- Depois de US1 completa, US2 (T009–T010) e US3 (T011–T012) podem avançar em paralelo por
  desenvolvedores diferentes, desde que coordenem edições no mesmo arquivo
  `frontend/src/ui/readingView.ts` (pontos de inserção distintos: listener de `click` vs. cálculo
  inicial de `open()` + listener de `ended`).
- T013, T014 e T015 cobrem, respectivamente, SC-002, SC-006 e a latência de SC-001, mas os três
  adicionam blocos `test(...)` ao mesmo arquivo `frontend/e2e/library.spec.ts` — por isso nenhum deles
  é `[P]` entre si (convenção deste documento: `[P]` exige arquivo diferente); devem ser implementados
  em sequência (ou numa única sessão de edição) para evitar conflito de merge no mesmo arquivo. Todos
  só fazem sentido passar depois que T006–T012 estiverem implementadas; T016/T017 dependem de
  T013–T015 estarem concluídas.

---

## Parallel Example: User Story 1

```bash
# Testes de US1 em paralelo:
Task: "Criar frontend/tests/unit/readingView.test.ts (FR-001/002/004/005/006/011/015)"
Task: "Estender frontend/tests/unit/main.test.ts (integração dos dois fluxos de abertura)"

# CSS em paralelo à lógica:
Task: "Adicionar bloco .reading-* em frontend/src/styles.css"
Task: "Implementar frontend/src/ui/readingView.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Phase 1: Setup
2. Completar Phase 2: Foundational (`sentenceLookup.ts`) — bloqueia tudo
3. Completar Phase 3: User Story 1
4. **Parar e validar**: rodar `quickstart.md` §1, §2, §5, §7 (cenários cobertos por US1) e os testes
   automatizados correspondentes
5. Esse é o MVP entregável: texto sincronizado em tempo real, com degradação graciosa

### Incremental Delivery

1. Setup + Foundational → base pronta
2. US1 → testar independentemente → MVP
3. US2 → testar independentemente (clique para pular) → incremento
4. US3 → testar independentemente (retomada + fim de áudio) → incremento
5. Polish → e2e real, build/test completos, `quickstart.md` atualizado com resultados

## Notes

- `frontend/src/ui/player.ts` e `frontend/src/api/validators.ts` não são modificados em nenhuma
  tarefa — apenas reaproveitados (ver plan.md, Structure Decision).
- Nenhuma tarefa altera o schema da timeline, endpoints de API ou o esquema de armazenamento local
  (FR-014).
- Commitar após cada tarefa ou grupo lógico (ex.: T002+T003 juntas, cada story completa).
