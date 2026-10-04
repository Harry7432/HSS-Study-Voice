# Feature Specification: Migração do frontend para o Design System HSS Music

**Feature Branch**: `master`

**Created**: 2026-10-04

**Status**: Draft

**Input**: User description: "Fase 6 — Migração do frontend para o Design System HSS Music"

**Nota de processo**: a implementação desta fase já existia no repositório (commits `3619557` e
`923dd1d`) quando esta documentação foi escrita. Por decisão explícita do usuário, o fluxo
`specify → clarify → plan → tasks` foi executado **retroativamente**, sem reimplementar nada, para
que a Fase 6 fique coberta pelo Princípio I (Spec-Driven Development) da constituição assim como as
fases anteriores. `tasks.md` reflete essa ordem: marca como concluído o que já está no código e abre
tarefas apenas para o que ainda falta.

## Clarifications

### Session 2026-10-04

- Q: Onde vive a definição visual (tokens e componentes) que o Study Voice deve consumir? → A: Em
  `frontend/src/hss/` (`tokens.css` + `bundle.css`, compilados do design system HSS Music), com
  `DESIGN.md` na raiz do repositório como regra de uso. `frontend/src/styles.css` só pode importar
  esses dois arquivos e compor layout a partir dos tokens; nunca declara cor, fonte, raio ou sombra
  própria.
- Q: Quantos pontos de destaque (cor de acento) uma tela pode ter? → A: No máximo um por tela — a
  ação principal (ex.: "Gerar estudo em áudio") ou o item em reprodução, nunca os dois com o mesmo
  peso visual.
- Q: Qual a convenção tipográfica e de idioma da interface? → A: Sentence case em todo lugar (sem
  caixa alta rastreada, nem em títulos de seção, botões ou metadados); texto em português do Brasil,
  direto, com tratamento "você".
- Q: O player de áudio deve ser reconstruído com os componentes `hss-player`/`hss-iconbtn-play`
  nesta fase? → A: Não. O elemento nativo `<audio controls>` é mantido nesta fase — recebe apenas
  uma moldura (`.player-frame`) com o tratamento visual de superfície elevada do HSS Music. Um
  player customizado com `hss-player` é trabalho de uma fase futura, fora de escopo aqui.
- Q: O que fazer quando o design system HSS Music não oferece um token ou componente que o Study
  Voice precisaria (por exemplo, uma cor de sucesso dedicada, uma variante destrutiva de botão, ou
  um componente de campo de texto)? → A: Não inventar cor, componente ou variante nova. Reaproveitar
  os tokens e componentes existentes mais próximos (`--accent-text` para sucesso, `--danger` para
  avisos de falha, `hss-btn-tertiary` para ações de remoção, um input simples sobre `--bg-raised`
  para os campos de texto) e registrar a lacuna em `research.md` para uma decisão futura do design
  system, em vez de uma solução silenciosa específica do Study Voice.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reconhecer a identidade visual HSS Music no Study Voice (Priority: P1)

Como usuário do Study Voice, quero que o aplicativo pareça parte da mesma família visual do HSS
Music (painéis escuros e planos, tipografia Figtree/DM Mono, controles em formato de pílula, um
único acento de cor por tela), para reconhecer o produto como parte da mesma marca e não como uma
interface genérica ou inconsistente.

**Why this priority**: é a mudança que entrega valor imediatamente visível em toda tela do produto;
sem ela, nenhuma das demais stories desta fase tem onde se apoiar.

**Independent Test**: abrir o aplicativo e inspecionar `frontend/src/styles.css` e o DOM renderizado
— nenhum valor de cor, fonte, raio ou sombra deve estar fora de `frontend/src/hss/tokens.css`;
`<html>` deve declarar `lang="pt-BR"` e `data-theme="dark"`; o corpo deve usar a classe
`hss-surface`; botões, chips e linhas de biblioteca devem usar as classes `hss-*` correspondentes.

**Acceptance Scenarios**:

1. **Given** o aplicativo carregado no navegador, **When** o usuário inspeciona a folha de estilos
   da aplicação, **Then** ela contém apenas dois `@import` (`./hss/tokens.css` e `./hss/bundle.css`)
   seguidos de regras de layout que usam exclusivamente `var(--...)`.
2. **Given** qualquer tela do produto, **When** o usuário a observa, **Then** existe no máximo um
   elemento com a cor de acento (`--accent`/`--accent-text`) como destaque principal.
3. **Given** qualquer rótulo, botão ou título da interface, **When** o usuário lê o texto, **Then**
   ele está em sentence case, nunca em caixa alta rastreada.

---

### User Story 2 - Ver o estudo em reprodução destacado na biblioteca (Priority: P2)

Como usuário navegando pela biblioteca local enquanto ouve um estudo, quero que a linha
correspondente ao estudo atualmente carregado no player seja destacada com um glifo de reprodução,
para identificar rapidamente qual item está tocando sem precisar olhar para o player.

**Why this priority**: é o único comportamento de estado (não puramente estático) introduzido pela
migração visual, e é o mais fácil de ficar incorreto silenciosamente.

**Independent Test**: abrir um estudo salvo, confirmar que sua linha (`hss-row`) ganha a classe
`is-playing` e o glifo de reprodução; em seguida pausar o áudio, deixá-lo chegar ao fim, e abrir um
outro estudo — em cada um desses três momentos, verificar se o destaque é atualizado corretamente.

**Acceptance Scenarios**:

1. **Given** um estudo recém-aberto no player, **When** a biblioteca é renderizada, **Then** a linha
   desse estudo tem a classe `is-playing` e exibe o glifo de reprodução no lugar do índice.
2. **Given** um estudo com o glifo de reprodução ativo, **When** o usuário abre um estudo diferente,
   **Then** o glifo e a classe `is-playing` passam para a nova linha e desaparecem da anterior.
3. **Given** um estudo com o glifo de reprodução ativo, **When** o usuário pausa a reprodução sem
   trocar de estudo, **Then** o comportamento esperado do destaque visual precisa ser confirmado
   contra a implementação atual (ver Edge Cases) — hoje nada força uma nova renderização da lista
   nesse momento.
4. **Given** um estudo com o glifo de reprodução ativo, **When** a reprodução chega ao fim, **Then**
   o comportamento esperado do destaque visual também precisa ser confirmado contra a implementação
   atual (ver Edge Cases).

---

### User Story 3 - Usar o produto em tema claro e em largura mobile estreita (Priority: P3)

Como usuário em um dispositivo móvel estreito ou com preferência pelo tema claro, quero que todas as
telas do Study Voice permaneçam legíveis e sem conteúdo cortado, para usar o produto normalmente
fora do desktop em tema escuro.

**Why this priority**: o design system já define os tokens para os dois temas e o layout já tem um
ponto de quebra responsivo; falta apenas a verificação manual de que nada quebra visualmente nessas
condições.

**Independent Test**: alternar `document.documentElement.dataset.theme` entre `"dark"` e `"light"` e
redimensionar a janela para uma largura ≤390px, percorrendo todas as telas (mastro, mesa de criação,
player, arquivo local e detalhes de um estudo).

**Acceptance Scenarios**:

1. **Given** o tema alternado para `"light"`, **When** o usuário percorre todas as telas, **Then**
   nenhum texto perde contraste AA e nenhum painel usa camadas cinza (o tema claro é editorial, com
   `hss-panel` separado por `--border-subtle`, não por camadas).
2. **Given** a janela redimensionada para ≤390px, **When** o usuário percorre todas as telas,
   **Then** nenhum conteúdo é cortado ou exige rolagem horizontal.

---

### User Story 4 - Ouvir estudos por um player customizado HSS Music (Priority: P4, fora de escopo)

Como usuário, no futuro quero um transporte de áudio com a aparência `hss-player` (em vez do
elemento nativo do navegador), para ter uma experiência de reprodução visualmente consistente com o
resto do produto.

**Why this priority**: é melhoria incremental sobre uma função que já funciona (reprodução via
`<audio controls>` nativo); explicitamente adiada por decisão do usuário nesta fase.

**Independent Test**: não aplicável nesta fase — nenhum critério de aceite desta story é exigido
agora; fica registrada apenas como direção futura.

**Acceptance Scenarios**: nenhum nesta fase.

---

### Edge Cases

- **`is-playing`/glifo são derivados de "qual estudo está carregado no player", não do estado real
  de play/pause.** Em `frontend/src/ui/player.ts`, `isOpen(studyId)` retorna
  `activeStudy?.studyId === studyId`, verdadeiro desde a abertura do estudo até ele ser descartado
  (`discard()`) ou até outro estudo ser aberto — `pause` e `ended` não alteram esse valor. Como
  `frontend/src/ui/libraryView.ts` só recalcula `is-playing` quando `refresh()` roda, e
  `frontend/src/main.ts` só chama `refresh()` ao montar a página, ao abrir um estudo (`onOpen`), ao
  concluir (`onCompleted`, acionado pelo evento `ended`) e após remover um estudo — **pausar sem
  trocar de estudo não aciona nenhum `refresh()`**, então o destaque permanece mesmo com o áudio
  pausado; e mesmo quando `ended` aciona o `refresh()`, `isOpen` continua `true` (só é zerado por
  `discard()`), então o glifo de reprodução permanece ativo ao lado do rótulo "Concluído" na mesma
  linha. Isso é tratado como um item de verificação/correção em aberto desta fase (ver `tasks.md`),
  não como comportamento aceito.
- **Servidor de desenvolvimento Python falha com `UnicodeDecodeError`/`cp1252` durante geração de
  áudio.** Reproduzido ao rodar `npm run test:e2e`: uma thread leitora de `subprocess.run(...,
  text=True)` em `backend/app/services/audio/concatenator.py:101-106` e
  `backend/app/services/audio/exporter.py:93-98` decodifica a saída do FFmpeg com a codificação
  padrão do Windows (`cp1252`) em vez de UTF-8, e falha ao encontrar um byte fora desse mapa
  (`byte 0x81`). A exceção ocorre em uma thread de fundo do `subprocess`, não interrompe a geração
  nem os testes (que continuam verdes), mas polui o log do servidor. Root cause e correção mínima
  sugerida (`encoding="utf-8"` nas duas chamadas) ficam registrados em `research.md` como item de
  investigação desta fase.
- **Lacunas do design system HSS Music**: não existe um token de cor de sucesso dedicado (o produto
  reaproveita `--accent-text`), nem uma variante destrutiva de botão (o botão "Remover" usa
  `hss-btn-tertiary` comum; o aviso de falha ao remover usa `--danger` apenas no texto), nem um
  componente de campo de texto (`.field-input` é um input simples do próprio Study Voice sobre
  `--bg-raised`, sem equivalente em `bundle.css`). Nenhuma dessas lacunas deve ser resolvida
  inventando uma cor, variante ou componente específico do Study Voice.
- **Tema claro sem alternância em tempo de execução**: `tokens.css` define um conjunto completo de
  tokens para `[data-theme="light"]`, mas nenhuma tela do produto oferece hoje um controle visível
  para o usuário alternar entre os temas — a troca só é possível manualmente via
  `document.documentElement.dataset.theme`. Um seletor de tema para o usuário final está fora do
  escopo desta fase.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O frontend DEVE importar `frontend/src/hss/tokens.css` e `frontend/src/hss/bundle.css`
  exatamente uma vez, a partir de `frontend/src/styles.css`, e NÃO DEVE declarar cor, fonte, raio de
  borda ou sombra fora desses dois arquivos.
- **FR-002**: O documento raiz (`frontend/index.html`) DEVE definir `lang="pt-BR"` e
  `data-theme="dark"` no elemento `<html>`, carregar as fontes Figtree (400/700/800) e DM Mono
  (400), e envolver o conteúdo em um elemento com a classe `hss-surface`.
- **FR-003**: Cada tela DEVE ter no máximo um ponto de destaque com a cor de acento (`--accent`,
  `--accent-text` ou `--on-accent` sobre um fundo de acento) — a ação principal da tela ou o item em
  reprodução, nunca os dois com o mesmo peso.
- **FR-004**: Todo texto da interface DEVE usar sentence case; nenhum rótulo, título de seção,
  botão ou metadado PODE usar caixa alta rastreada.
- **FR-005**: Linhas da biblioteca local DEVEM usar a classe `hss-row` (com `hss-row-index`,
  `hss-row-main`, `hss-row-title`, `hss-row-artist`, `hss-row-album`, `hss-row-time`); a linha do
  estudo atualmente carregado no player DEVE receber a classe `is-playing` e exibir um glifo de
  reprodução em `hss-row-index` no lugar do índice.
- **FR-006**: `is-playing` e o glifo de reprodução DEVEM ser removidos da linha de um estudo quando
  (a) sua reprodução é pausada sem abrir outro estudo, (b) sua reprodução chega ao fim, ou (c) outro
  estudo é aberto. *(Pendente — ver Edge Cases e `tasks.md`; hoje apenas o caso (c), e a remoção do
  próprio estudo, atualizam o destaque corretamente.)*
- **FR-007**: Botões de ação DEVEM usar as classes `hss-btn-primary` (no máximo um por tela),
  `hss-btn-secondary` ou `hss-btn-tertiary` (com `hss-btn-sm` para variantes compactas), em vez de
  estilos próprios do Study Voice.
- **FR-008**: O elemento `<audio controls>` nativo DEVE permanecer o controle de reprodução nesta
  fase, podendo apenas receber uma moldura visual (`hss-panel`/superfície elevada) sem recriar o
  transporte de mídia; a construção de um player customizado com `hss-player` fica fora do escopo
  desta fase (ver User Story 4).
- **FR-009**: O produto DEVE permanecer utilizável, sem conteúdo cortado ou rolagem horizontal
  forçada, tanto no tema `"light"` quanto em larguras de janela ≤390px, em todas as telas (mastro,
  mesa de criação, player, arquivo local, detalhes de um estudo). *(Pendente de verificação manual —
  ver `tasks.md`.)*
- **FR-010**: Quando um token ou componente necessário não existir no design system HSS Music (por
  exemplo, cor de sucesso dedicada, variante destrutiva de botão, componente de campo de texto), o
  frontend NÃO DEVE inventar uma solução visual própria — DEVE reaproveitar o token/componente
  existente mais próximo e registrar a lacuna como decisão explícita em `research.md`.
- **FR-011**: Esta fase NÃO DEVE alterar o backend, o pipeline de síntese de áudio, nem o esquema de
  armazenamento local (IndexedDB) definidos pelas Fases 3–5; qualquer correção de causa raiz do
  `UnicodeDecodeError`/`cp1252` encontrado durante a investigação DEVE se limitar à codificação
  explícita da leitura de subprocessos do FFmpeg, sem tocar no pipeline
  `normalization → chunking → TTS → WAV → concatenation → MP3`.

### Key Entities

- **Design System HSS Music**: a fonte visual de verdade consumida pelo Study Voice — tokens
  (`frontend/src/hss/tokens.css`) e componentes (`frontend/src/hss/bundle.css`), documentados por
  `DESIGN.md` na raiz do repositório e pelos `README.md`/`preview.html` de cada componente em
  `frontend/src/hss/components/`. O Study Voice consome essa fonte sem modificá-la.
- **Estado de reprodução visível (`is-playing`)**: indicador visual, derivado de "qual estudo está
  carregado no player" (`LocalPlayer.isOpen`), associado à linha de um estudo na biblioteca local;
  não é, hoje, equivalente ao estado real de play/pause do elemento `<audio>`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Uma auditoria de `frontend/src/styles.css` não encontra nenhum valor de cor
  hardcoded (hex, `white`, `black`, `transparent` fora dos tokens) ou declaração própria de fonte,
  raio ou sombra.
- **SC-002**: Em tema claro e em largura de janela ≤390px, nenhuma tela do produto apresenta
  conteúdo cortado, sobreposto ou que exija rolagem horizontal.
- **SC-003**: Após pausar, concluir ou trocar o estudo em reprodução, o destaque `is-playing`/glifo
  reflete corretamente qual (se algum) estudo está tocando, sem exigir reload manual da página.
- **SC-004**: `npm run build`, `npm test` (suíte unitária) e `npm run test:e2e` (Playwright) passam
  sem regressão após o encerramento desta fase.
- **SC-005**: O servidor de desenvolvimento Python não produz mais o traceback de
  `UnicodeDecodeError`/`cp1252` durante a geração de áudio, ou — se a correção não for aplicada nesta
  fase — a causa raiz e o workaround ficam documentados em `research.md` e `tasks.md`.

## Assumptions

- **Nenhuma mudança de dados ou de API**: esta fase é inteiramente visual/CSS/markup no workspace
  `frontend/`; o backend (Fases 3–4) e o esquema de armazenamento local (Fase 5) permanecem exatamente
  como estão, exceto pela eventual correção mínima de codificação descrita em FR-011.
  Por isso, esta feature não define `data-model.md` nem `contracts/` — `DESIGN.md` já cumpre o papel
  de contrato visual.
- **`DESIGN.md` é a fonte de verdade já aprovada**: as regras de uso (cores por token, um acento por
  tela, sentence case, componentes `hss-*`) já estavam definidas em `DESIGN.md` antes desta
  documentação; este spec não as redefine, apenas as referencia e verifica contra o código
  implementado.
- **Correção de bugs de UI identificados nesta fase é trabalho de implementação, não apenas de
  documentação**: os itens pendentes (FR-006, FR-009, SC-005) exigem, além de verificação manual,
  possivelmente pequenos ajustes de código (`libraryView.ts`, `player.ts`, `concatenator.py`,
  `exporter.py`); `tasks.md` os lista como tarefas abertas separadas da documentação retroativa.
- **Sem seletor de tema para o usuário final nesta fase**: validar que o tema claro funciona não
  implica adicionar um controle de interface para alterná-lo; isso fica para uma fase futura, se
  houver demanda.
