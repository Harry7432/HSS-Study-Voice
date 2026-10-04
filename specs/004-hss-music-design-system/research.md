# Phase 0 Research: Migração do frontend para o Design System HSS Music

Todas as decisões abaixo documentam, retroativamente, escolhas já tomadas na implementação
(`3619557`, `923dd1d`), mais a investigação feita nesta sessão para o único ponto que ainda não
tinha causa raiz registrada (`UnicodeDecodeError`/`cp1252`). Nenhum item permanece como
`NEEDS CLARIFICATION`.

## 1. Vendorizar tokens e componentes do HSS Music

- **Decision**: copiar `tokens.css` e `bundle.css` do design system HSS Music para
  `frontend/src/hss/` (mais `tokens.json` e um `README.md`/`preview.html` por componente), e importar
  os dois arquivos uma única vez em `frontend/src/styles.css`. `DESIGN.md`, na raiz do repositório,
  registra as regras de uso derivadas desses tokens.
- **Rationale**: o Study Voice não tem (e não deve ter) identidade visual própria — `DESIGN.md`
  declara explicitamente que ele "consome" o HSS Music. Vendorizar os dois arquivos finais (em vez de
  depender de um pacote/build separado) mantém a fonte de verdade única e auditável sem introduzir
  uma dependência de build adicional para um projeto que já não usa framework de UI.
- **Alternatives considered**: reimplementar os estilos específicos do Study Voice (rejeitado —
  violaria diretamente `DESIGN.md` e o Princípio VII, No Overengineering, ao duplicar decisões de
  design já tomadas); referenciar o HSS Music como pacote npm externo (não avaliado nesta fase por
  não haver publicação desse pacote disponível).

## 2. `is-playing` derivado de "estudo carregado", não de evento play/pause real

- **Decision**: `frontend/src/ui/libraryView.ts` calcula `is-playing` a partir de
  `dependencies.isPlaying?.(study.studyId)`, que `frontend/src/main.ts:106` conecta a
  `player.isOpen(studyId)`. Em `frontend/src/ui/player.ts:113`,
  `isOpen = (studyId) => activeStudy?.studyId === studyId` — verdadeiro do momento em que
  `player.open(study)` é chamado até `discard()` rodar (por remoção do estudo ou abertura de outro).
  A lista de linhas só é reconstruída quando `libraryView.refresh()` roda, e isso só acontece no
  mount inicial, em `onOpen`, em `onCompleted` (dependente do evento `ended`) e após remover um
  estudo — nunca em `pause` isolado.
- **Rationale observada no código**: essa escolha é simples e correta para os dois gatilhos que
  importavam mais ao implementar (abrir um estudo diferente e remover o estudo atual), mas deixa dois
  casos sem cobertura: pausar sem trocar de estudo (nenhum `refresh()` é disparado) e concluir a
  reprodução (`refresh()` roda, mas `isOpen` continua `true` porque só `discard()` o zera, então o
  glifo de "em reprodução" permanece ao lado do rótulo "Concluído").
- **Decisão para esta fase**: registrar o comportamento observado como item de verificação/correção
  em aberto (FR-006, `tasks.md`) em vez de presumir que está correto só porque o código existe.
  Qualquer correção deve continuar usando o mesmo mecanismo de `refresh()` dirigido por eventos (sem
  introduzir observação contínua/polling do estado do `<audio>`), por exemplo adicionando um
  `onPaused`/recalculando `isOpen` em conjunto com `playing` no próprio `player.ts`.
- **Alternatives considered**: manter como está, sem registrar (rejeitado — o usuário pediu
  explicitamente para validar esses três gatilhos antes de considerar a fase fechada).

## 3. Player nativo (`<audio controls>`) mantido nesta fase

- **Decision**: `frontend/src/main.ts:72` usa `<audio controls preload="metadata"></audio>` dentro de
  um `.player-frame` (`frontend/src/styles.css:151-159`) que aplica apenas `--bg-raised`,
  `--radius-md` e espaçamento — nenhuma reconstrução do transporte de mídia com `hss-player`/
  `hss-iconbtn-play`.
- **Rationale**: confirmado com o usuário — reescrever o transporte de mídia (play/pause, barra de
  progresso, volume) com os componentes `hss-player` é um esforço à parte, com estado e testes
  próprios, que não deveria ser misturado com a migração visual do restante do produto (Princípio
  VIII, Phase-Bounded Delivery).
- **Alternatives considered**: construir o `hss-player` já nesta fase (rejeitado pelo usuário —
  registrado como User Story 4, fora de escopo, para uma fase futura dedicada).

## 4. Tema claro definido, sem alternância em tempo de execução

- **Decision**: `frontend/src/hss/tokens.css` define um bloco completo `[data-theme="light"]`
  (linhas 34-63) e `bundle.css` tem regras específicas para ele (`.hss-panel` sem raio e com borda
  lateral, `.hss-player` com borda superior) — mas `frontend/index.html:2` fixa
  `data-theme="dark"` sem nenhum controle de interface para o usuário alternar.
- **Rationale**: o objetivo desta fase é garantir que o tema claro *funcione* quando ativado (ex.: via
  preferência do sistema operacional ou QA manual), não necessariamente oferecer um seletor visível
  ao usuário final — isso é uma decisão de produto separada.
- **Alternatives considered**: adicionar um botão de alternância de tema nesta fase (não solicitado
  pelo usuário; mantido fora de escopo até haver demanda explícita).

## 5. Lacunas do design system: reaproveitar, não inventar

- **Decision**: três lacunas confirmadas em `frontend/src/hss/tokens.css` e `bundle.css`:
  1. Sem token de cor de **sucesso** dedicado — `tokens.css` só define `--danger`, `--warning` e
     `--info` como cores de status. `frontend/src/styles.css:127` reaproveita `--accent-text` para
     `.status-line[data-kind='success']`.
  2. Sem variante **destrutiva** de botão — `bundle.css` só tem `.hss-menu-item.is-danger` para itens
     de menu, nenhuma classe `hss-btn-danger`/similar. O botão "Remover" em `libraryView.ts:171` usa
     `hss-btn-tertiary` comum; o aviso de falha ao remover usa `--danger` apenas no texto
     (`frontend/src/styles.css:217-221`).
  3. Sem **componente de campo de texto** — `bundle.css` só estiliza `.hss-search input`. Os campos
     de texto/rótulo do formulário de criação (`.field-input`,
     `frontend/src/styles.css:94-105`) são um input simples do próprio Study Voice sobre
     `--bg-raised`, sem equivalente em `bundle.css`.
- **Rationale**: `DESIGN.md` é explícito — "se um token ou componente que você precisa não existe,
  não invente uma cor ou estilo. Componha a partir de tokens existentes e sinalize a lacuna". As três
  soluções acima já seguem essa regra.
- **Alternatives considered**: criar classes `hss-btn-danger`/`hss-input`/um token `--success`
  específicos do Study Voice (rejeitado — isso duplicaria decisões de design system que pertencem ao
  HSS Music, não ao produto que o consome; a lacuna fica registrada aqui para uma eventual atualização
  do design system, não resolvida unilateralmente).

## 6. `UnicodeDecodeError`/`cp1252` no servidor de desenvolvimento — causa raiz

- **Decision/Finding**: reproduzido ao rodar `npm run test:e2e` nesta sessão. A stack trace aponta
  para `Thread-N (_readerthread)` dentro de `subprocess.py`, decodificando a saída de um processo
  filho com o codec `cp1252` (padrão do Windows em locale pt-BR) e falhando no byte `0x81` (não
  mapeado em cp1252). As únicas duas chamadas do backend que leem saída de subprocesso como texto são:
  - `backend/app/services/audio/concatenator.py:101-106` — `subprocess.run([ffmpeg, ...],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)`
  - `backend/app/services/audio/exporter.py:93-98` — mesmo padrão, para o export MP3.
  Nenhuma das duas chamadas passa `encoding=`; com `text=True` e sem `encoding`, o Python usa
  `locale.getpreferredencoding()`, que no Windows com locale pt-BR é `cp1252`. O FFmpeg emite seu
  banner/log em UTF-8 (incluindo símbolos fora de cp1252), o que dispara o erro na thread leitora do
  `subprocess`.
- **Impacto observado**: a exceção ocorre em uma thread de fundo do módulo `subprocess` (não no
  código de aplicação), por isso **não falha a requisição nem os testes** — os dois testes e2e
  passam. O efeito visível é apenas um traceback ruidoso no log do servidor de desenvolvimento a cada
  geração de áudio.
- **Correção mínima recomendada (não aplicada nesta sessão de documentação)**: passar
  `encoding="utf-8", errors="replace"` nas duas chamadas de `subprocess.run` acima, em vez de confiar
  na codificação padrão do sistema operacional. É uma mudança de uma linha por chamada, não toca no
  pipeline `normalization → chunking → TTS → WAV → concatenation → MP3`, e está dentro do limite de
  FR-011 desta fase.
- **Alternatives considered**: ignorar o traceback por não quebrar testes (rejeitado pelo usuário —
  pediu investigação explícita); mudar o locale do processo Python inteiro (rejeitado — mais invasivo
  que corrigir as duas chamadas específicas que leem saída de um processo externo).
