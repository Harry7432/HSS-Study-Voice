# Phase 0 Research: API de geração de estudos em áudio

Todas as decisões abaixo resolvem os pontos técnicos abertos pelo Technical Context e pelo
Constitution Check de `plan.md`. Nenhum item permanece como `NEEDS CLARIFICATION`.

## 1. Identificador do estudo e layout de armazenamento

- **Decision**: cada estudo recebe um identificador único no formato hexadecimal de 32 caracteres
  (`uuid4().hex`, minúsculo). O áudio final é gravado em
  `settings.OUTPUT_DIR / f"{study_id}.mp3"` e a timeline correspondente é derivada por
  `timeline_path_for(audio_path)` (já existente em `app/services/audio/timeline.py`), produzindo
  `settings.OUTPUT_DIR / f"{study_id}.timeline.json"`.
- **Rationale**: reaproveita a convenção de nome-irmão já estabelecida na Fase 3
  (`AudioOrchestrator.generate_synchronized`) sem introduzir um segundo esquema de nomenclatura.
  Um UUID evita qualquer dependência do texto do usuário no nome do arquivo (sem risco de path
  traversal ou colisão) e não exige um índice/banco de dados novo — a existência do próprio arquivo
  no `OUTPUT_DIR` é a fonte de verdade para "o estudo existe".
- **Alternatives considered**: slug derivado do texto (rejeitado — risco de colisão e de path
  traversal; exigiria sanitização extra); índice incremental em arquivo/SQLite (rejeitado por
  "No Overengineering" — não há necessidade documentada de listagem ou de metadados além dos dois
  arquivos já produzidos pelo orquestrador).

## 2. Camada de API: localização do código e forma dos handlers

- **Decision**: adicionar um router FastAPI em `app/api/routes/studies.py`, montado em
  `main.py` sob o prefixo já existente `settings.API_V1_STR` (`/api/v1`, hoje declarado mas não
  usado). A lógica de orquestração (gerar, localizar áudio, localizar timeline) fica em um serviço
  fino e testável isoladamente, `app/services/studies/service.py` (`StudyService`), que injeta
  `TextPreprocessingPipeline` e `AudioOrchestrator` exatamente como já são usados internamente. Os
  handlers do router apenas validam a requisição (via Pydantic), chamam `StudyService` e traduzem o
  resultado/erro para a resposta HTTP.
- **Rationale**: mantém o princípio "Simple and Modular Backend" — nenhuma infraestrutura nova,
  apenas uma camada fina sobre componentes já existentes. Isolar `StudyService` do FastAPI permite
  testá-lo com `pytest` puro (sem `TestClient`), e mantém a porta aberta para "Architecture Ready for
  Evolution" (ex.: troca futura de armazenamento em arquivo por um índice persistente, sem alterar o
  contrato HTTP).
- **Alternatives considered**: colocar a lógica diretamente nos handlers do router (rejeitado —
  dificulta testes unitários sem subir a app e viola a separação de responsabilidades já usada no
  restante do backend).

## 3. Handlers síncronos (`def`, não `async def`)

- **Decision**: os três endpoints usam `def` (síncrono), não `async def`.
- **Rationale**: `TextPreprocessingPipeline`, `AudioOrchestrator` e o `PiperProvider` são código
  síncrono e bloqueante (incluindo chamadas de `subprocess` para o FFmpeg). O FastAPI executa
  handlers `def` automaticamente em uma threadpool, evitando bloquear o event loop assíncrono do
  Uvicorn durante a síntese. Declarar `async def` sem `await` real bloquearia o loop inteiro durante
  toda a geração.
- **Alternatives considered**: `async def` chamando os serviços síncronos diretamente (rejeitado —
  bloquearia o event loop); mover a síntese para um worker assíncrono dedicado (rejeitado — exigiria
  fila/infra nova, fora do escopo síncrono já confirmado com o usuário).

## 4. Limite explícito de tamanho de texto (gate de segurança da constituição)

- **Decision**: introduzir uma nova configuração `MAX_REQUEST_TEXT_CHARS` em `Settings`
  (`app/core/config.py`), com um valor padrão generoso (200 000 caracteres — equivalente a um livro
  de estudo extenso). O corpo da requisição de criação valida `text` com essa fronteira explícita via
  Pydantic (`Field(max_length=...)` + validador que rejeita texto vazio/apenas espaços), retornando
  `422` quando violado.
- **Rationale**: a Constituição (Princípio VI, Security by Default) exige que "text size MUST be
  limited by an explicit configured boundary" — a spec (Assumptions) dizia apenas que não haveria um
  "teto artificial" para textos de estudo típicos. Um limite generoso e configurável satisfaz as duas
  exigências: continua sem impedir o uso normal (vários capítulos de um livro cabem confortavelmente
  dentro de 200 000 caracteres), mas estabelece a fronteira explícita exigida pela constituição como
  proteção de recurso (evita que uma requisição acidental ou abusiva trave o processo por horas).
  Fica documentado aqui como a resolução desse gate, sem necessidade de reabrir `/speckit.specify`.
- **Alternatives considered**: nenhum limite (rejeitado — viola a constituição diretamente); limite
  baixo alinhado ao `MAX_CHUNK_CHARS` atual de 500 (rejeitado — isso é o tamanho de um *chunk*, não
  do documento inteiro, e tornaria a API inutilizável para textos de estudo reais).

## 5. Validação do identificador de estudo nas rotas de busca

- **Decision**: o parâmetro de rota `study_id` é restrito por regex (`^[0-9a-f]{32}$`) diretamente
  na assinatura do endpoint FastAPI. Um valor fora desse formato retorna `422` automaticamente, antes
  de qualquer acesso ao sistema de arquivos; um valor no formato correto, mas sem arquivo
  correspondente, retorna `404`.
- **Rationale**: cobre o edge case "identificador malformado" do spec distinguindo-o do caso "não
  encontrado", e evita qualquer tentativa de leitura de caminho fora do padrão esperado (defesa em
  profundidade, já que o nome do arquivo é sempre `{study_id}.mp3` / `.timeline.json`).
- **Alternatives considered**: tratar todo `study_id` invälido como `404` genérico (rejeitado — o
  spec já distingue os dois casos como edge cases separados).

## 6. Mapeamento de erros de geração para respostas HTTP

- **Decision**: qualquer falha durante a geração (`TTSSynthesisError`, `AudioRenderError`,
  `MP3ExportError`, `FFmpegNotFoundError`, `AudioPublicationError`, `AudioRollbackError`, ou qualquer
  exceção inesperada) é capturada em um único ponto no handler de criação e traduzida para `500` com
  um corpo de erro genérico e estável (`{"detail": "Falha ao gerar o estudo em áudio."}`), sem
  stack trace nem mensagem interna. O erro completo é registrado apenas no log do servidor, e o log
  nunca inclui o texto submetido (apenas metadados: tamanho do texto, voz, duração do processamento).
- **Rationale**: atende FR-012 e o Princípio VI (logs não podem conter o texto completo submetido).
  Um único ponto de tradução de erro evita duplicar lógica de mapeamento em cada handler e evita a
  complexidade de diferenciar causas de falha (voz inválida vs. FFmpeg ausente vs. falha de
  publicação) em códigos HTTP distintos — distinção que a spec não exige e que o Princípio
  "No Overengineering" recomenda não introduzir sem necessidade concreta.
- **Alternatives considered**: mapear cada tipo de exceção para um código HTTP específico (ex.: `503`
  para FFmpeg ausente) — descartado por agora como refinamento possível de uma iteração futura, não
  exigido pelos requisitos funcionais atuais.

## 7. Parâmetros opcionais de voz/velocidade/bitrate

- **Decision**: `voice`, `speed` e `bitrate` seguem exatamente os tipos e padrões já usados por
  `AudioOrchestrator.generate_mp3`/`generate_synchronized` (`str | None`, `float | None`,
  `str | None`), sem validação adicional de catálogo na camada de API — a validação de voz
  desconhecida já é feita pelo `PiperProvider` (`TTSSynthesisError`) e cai no mapeamento de erro do
  item 6.
- **Rationale**: evita duplicar a lista de vozes válidas (`PIPER_PT_BR_CATALOG`) na camada de API;
  a fonte de verdade continua sendo o provider.
- **Alternatives considered**: validar a voz contra o catálogo na camada Pydantic (rejeitado —
  duplicaria uma lista que já existe e pode mudar no provider sem sincronização).

## Resumo

Nenhum `NEEDS CLARIFICATION` permanece. Todas as decisões reaproveitam componentes já existentes
nas Fases 1–3; a única peça nova de configuração é `MAX_REQUEST_TEXT_CHARS`.
