# Tasks: API de geração de estudos em áudio

**Input**: Design documents from `/specs/002-study-audio-api/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (todos presentes)

**Tests**: incluídos — o Princípio IV (Mandatory Tests) da constituição do projeto exige cobertura
automatizada para toda nova regra de domínio e para interação real entre componentes; `plan.md` já
define os arquivos de teste correspondentes.

**Organization**: tarefas agrupadas por user story (US1/US2/US3, conforme `spec.md`) para permitir
implementação e teste independentes de cada uma.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode ser executada em paralelo (arquivo diferente, sem dependência de tarefa incompleta)
- **[Story]**: a qual user story a tarefa pertence (US1, US2, US3)
- Caminhos de arquivo são relativos à raiz do repositório

## Path Conventions

Projeto web single-backend (sem frontend). Código em `backend/app/`, testes em `backend/tests/`,
conforme `plan.md` → Project Structure.

---

## Phase 1: Setup

**Purpose**: criar o esqueleto de pacotes novos e confirmar a baseline antes de qualquer mudança.

- [X] T001 Criar os pacotes vazios novos descritos em `plan.md` → Project Structure:
  `backend/app/api/__init__.py`, `backend/app/api/routes/__init__.py`,
  `backend/app/schemas/__init__.py`, `backend/app/services/studies/__init__.py`
- [X] T002 [P] Executar `uv run pytest tests` a partir de `backend/` e registrar o resultado como
  baseline (quickstart.md §1) — a suíte pré-existente (Fases 1–3) deve continuar 100% verde antes de
  qualquer código novo ser adicionado

**Checkpoint**: esqueleto de pacotes criado; baseline de testes confirmada.

> **Nota de ambiente (T002)**: `uv run pytest tests/integration/test_audio_pipeline.py` derruba o
> processo (sem traceback) nesta máquina — causa raiz identificada: o wheel Windows de
> `piper-tts==1.8.0` tem um caminho de build (`D:/a/piper1-gpl/...`) embutido no módulo nativo
> `espeakbridge`, que ignora o `espeak_data_dir` correto já presente em
> `.venv/Lib/site-packages/piper/espeak-ng-data`. Defeito pré-existente de empacotamento, não
> relacionado a esta fase. Os 144 testes unitários (que não dependem de síntese real) passam 100%.
> Decisão do usuário: seguir com T001–T019 (cobertura via dublês); T020–T022 (validação real
> Piper/FFmpeg) ficam bloqueadas e não marcadas nesta sessão.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: infraestrutura compartilhada pelas três user stories.

**⚠️ CRITICAL**: nenhuma user story pode começar antes desta fase estar completa.

- [X] T003 [P] Adicionar `MAX_REQUEST_TEXT_CHARS: int = 200_000` à classe `Settings` em
  `backend/app/core/config.py` (research.md §4) — fronteira explícita exigida pelo Princípio VI
  (Security by Default) da constituição
- [X] T004 [P] Criar o modelo `ErrorResponse` em `backend/app/schemas/study.py` com o campo único
  `detail: str` (data-model.md → ErrorResponse) — usado pelas três user stories (`404` em US2/US3,
  `500` em US1); corresponde a `contracts/error-response.schema.json`
- [X] T005 [P] Criar o esqueleto de `StudyService` em `backend/app/services/studies/service.py`:
  construtor injetando `TextPreprocessingPipeline` e `AudioOrchestrator` (ambos opcionais, com
  instância padrão quando omitidos, no mesmo padrão de injeção já usado por
  `AudioOrchestrator.__init__`); constante de módulo
  `STUDY_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")` (research.md §5); método privado
  `_audio_path(self, study_id: str) -> Path` retornando
  `settings.OUTPUT_DIR / f"{study_id}.mp3"` (research.md §1)
- [X] T006 Criar `backend/app/api/routes/studies.py` com um `APIRouter` vazio
  (`prefix=f"{settings.API_V1_STR}/studies"`, `tags=["Studies"]`) e uma instância de módulo
  `_service = StudyService()`; registrar o router em `backend/app/main.py` via
  `app.include_router(studies.router)` (depende de T005)

**Checkpoint**: configuração, schema de erro, serviço e router básicos existem — as user stories
podem começar.

---

## Phase 3: User Story 1 - Gerar um estudo em áudio a partir de texto (Priority: P1) 🎯 MVP

**Goal**: `POST {API_V1_STR}/studies` recebe texto, processa pelo pipeline existente, sintetiza o
áudio e a timeline, e retorna o identificador do estudo mais os metadados de geração na mesma
resposta.

**Independent Test**: enviar um texto de exemplo com Markdown básico ao endpoint e verificar que a
resposta `201` contém `study_id`, `chunks_count`, `duration_seconds`, `file_size_bytes` e
`processing_time_seconds`, e que o MP3 correspondente existe em `settings.OUTPUT_DIR`.

### Tests for User Story 1 ⚠️

> **Escrever estes testes PRIMEIRO; confirmar que falham antes de implementar.**

- [X] T007 [P] [US1] Testes unitários de validação em
  `backend/tests/unit/test_study_schemas.py`: `text` vazio ou apenas espaços é rejeitado após
  `strip()` (FR-002); `text` acima de `settings.MAX_REQUEST_TEXT_CHARS` é rejeitado (`422`);
  `speed` ≤ 0, quando informado, é rejeitado
- [X] T008 [P] [US1] Testes unitários de `StudyService.create()` em
  `backend/tests/unit/test_study_service.py`, usando dublês de `TextPreprocessingPipeline` e
  `AudioOrchestrator`: `study_id` casa com `^[0-9a-f]{32}$`; `audio_path`/`timeline_path` seguem a
  convenção `{study_id}.mp3` / `{study_id}.timeline.json` (research.md §1); o `AudioResult`
  retornado pelo orquestrador é propagado sem alteração no `StudyRecord`
- [X] T009 [P] [US1] Teste de integração (via `TestClient`, com `StudyService` substituído por
  dublê) para `POST {API_V1_STR}/studies` em `backend/tests/unit/test_studies_routes.py`: `201`
  com corpo conforme `contracts/study-create-response.schema.json` (Acceptance Scenario 1);
  `voice`/`speed`/`bitrate` informados são repassados ao serviço (Acceptance Scenario 4); `422`
  para texto vazio/apenas espaços (Acceptance Scenario 3, FR-002); `422` para texto acima de
  `MAX_REQUEST_TEXT_CHARS`; `500` com `detail` genérico de `ErrorResponse` (nunca a exceção crua)
  quando o serviço lança uma falha de geração (research.md §6, FR-012); texto com Markdown
  (títulos, ênfase, listas) enviado ao endpoint não repassa marcações ao estágio de síntese —
  usar um `TextPreprocessingPipeline` real (não dublê) dentro de `StudyService`, com apenas o
  `AudioOrchestrator` substituído por um dublê que captura o `PreparedDocument` recebido, e
  afirmar que nenhuma sentença capturada contém sintaxe Markdown (Acceptance Scenario 2, SC-004)

### Implementation for User Story 1

- [X] T010 [P] [US1] Implementar `StudyCreateRequest` e `StudyCreateResponse` em
  `backend/app/schemas/study.py` (data-model.md → StudyCreateRequest/StudyCreateResponse):
  `text: str` obrigatório, "após `strip()`, não pode ser vazio", `max_length` igual a
  `settings.MAX_REQUEST_TEXT_CHARS`; `voice: str | None = None` ("quando omitido, usa
  `settings.DEFAULT_VOICE`"); `speed: float | None = None`, "deve ser `> 0` quando informado"
  ("quando omitido, usa `settings.DEFAULT_SPEED`"); `bitrate: str | None = None` ("quando omitido,
  usa `settings.MP3_BITRATE`"); `StudyCreateResponse` com `study_id: str`, `chunks_count: int`,
  `duration_seconds: float`, `file_size_bytes: int`, `processing_time_seconds: float` (depende de
  T003)
- [X] T011 [P] [US1] Implementar `StudyService.create(text, voice=None, speed=None, bitrate=None)
  -> StudyRecord` em `backend/app/services/studies/service.py`: gerar `study_id = uuid4().hex`;
  `audio_path = self._audio_path(study_id)`; `document = self._pipeline.prepare(text)`;
  `result = self._orchestrator.generate_synchronized(document, audio_path, voice=voice,
  speed=speed, bitrate=bitrate)`; retornar `StudyRecord(study_id=study_id, audio_path=audio_path,
  timeline_path=result.timeline_path, result=result)` (depende de T005)
- [X] T012 [US1] Implementar o handler `POST {API_V1_STR}/studies` (função `def`, não `async def`
  — research.md §3) em `backend/app/api/routes/studies.py`: recebe `StudyCreateRequest`, chama
  `_service.create(...)`, monta `StudyCreateResponse` a partir do `StudyRecord` retornado, responde
  `201`; captura `TTSSynthesisError`, `AudioRenderError`, `MP3ExportError`, `FFmpegNotFoundError`,
  `AudioPublicationError`, `AudioRollbackError` e `Exception` genérica, registra a exceção original
  e metadados (tamanho do texto, voz, tempo decorrido) no log — nunca o texto submetido (FR-012,
  Princípio VI) — e levanta `HTTPException(status_code=500, detail="Falha ao gerar o estudo em
  áudio.")` (depende de T006, T010, T011)

**Checkpoint**: User Story 1 funcional e testável de forma independente.

---

## Phase 4: User Story 2 - Baixar o áudio de um estudo já gerado (Priority: P2)

**Goal**: `GET {API_V1_STR}/studies/{study_id}/audio` retorna o MP3 de um estudo já gerado.

**Independent Test**: com um arquivo `.mp3` pré-existente em `settings.OUTPUT_DIR` nomeado por um
`study_id` conhecido, buscar esse áudio pela rota e confirmar que os bytes retornados são idênticos
ao arquivo original; buscar um `study_id` bem formado mas inexistente e confirmar `404`.

### Tests for User Story 2 ⚠️

- [X] T013 [P] [US2] Teste de integração (via `TestClient`) para
  `GET {API_V1_STR}/studies/{study_id}/audio` em `backend/tests/unit/test_studies_routes.py`:
  `200` com os bytes exatos de um arquivo `.mp3` de fixture pré-semeado em `OUTPUT_DIR`
  (Acceptance Scenario 1); `404` com corpo `ErrorResponse` (`detail="Estudo não encontrado."`) para
  um `study_id` bem formado porém inexistente (Acceptance Scenario 2, FR-011); `422` para um
  `study_id` que não casa com `^[0-9a-f]{32}$` (research.md §5)

### Implementation for User Story 2

- [X] T014 [US2] Implementar `StudyService.get_audio_path(study_id) -> Path | None` em
  `backend/app/services/studies/service.py`: retorna `self._audio_path(study_id)` somente se
  `.is_file()` for verdadeiro, caso contrário `None` (depende de T005)
- [X] T015 [US2] Implementar o handler `GET {API_V1_STR}/studies/{study_id}/audio` em
  `backend/app/api/routes/studies.py`: parâmetro de rota
  `study_id: str = Path(..., pattern=STUDY_ID_PATTERN.pattern)` (gera `422` automaticamente em
  formato inválido); chama `_service.get_audio_path(study_id)`; levanta
  `HTTPException(status_code=404, detail="Estudo não encontrado.")` quando `None`; caso contrário
  retorna `FileResponse(path, media_type="audio/mpeg")` (depende de T006, T014)

**Checkpoint**: User Story 1 e 2 funcionam de forma independente.

---

## Phase 5: User Story 3 - Obter a timeline sincronizada do estudo (Priority: P3)

**Goal**: `GET {API_V1_STR}/studies/{study_id}/timeline` retorna a timeline sincronizada por frase
de um estudo já gerado.

**Independent Test**: com um arquivo `.timeline.json` pré-existente em `settings.OUTPUT_DIR`
nomeado por um `study_id` conhecido, buscar essa timeline pela rota e confirmar que o JSON
retornado é idêntico ao arquivo original; buscar um `study_id` bem formado mas inexistente e
confirmar `404`.

### Tests for User Story 3 ⚠️

- [X] T016 [P] [US3] Teste de integração (via `TestClient`) para
  `GET {API_V1_STR}/studies/{study_id}/timeline` em `backend/tests/unit/test_studies_routes.py`:
  `200` com o JSON de uma fixture `.timeline.json` pré-semeada, validando a forma contra
  `../001-text-audio-timeline/contracts/timeline-v1.schema.json` (Acceptance Scenario 1); `404` com
  corpo `ErrorResponse` para um `study_id` bem formado porém inexistente (Acceptance Scenario 2);
  `422` para um `study_id` malformado

### Implementation for User Story 3

- [X] T017 [US3] Implementar `StudyService.get_timeline_path(study_id) -> Path | None` em
  `backend/app/services/studies/service.py`: usa
  `timeline_path_for(self._audio_path(study_id))` e retorna o caminho somente se `.is_file()`,
  caso contrário `None` (depende de T005; reaproveita `timeline_path_for` de
  `app/services/audio/timeline.py`, sem duplicar a convenção de nome-irmão)
- [X] T018 [US3] Implementar o handler `GET {API_V1_STR}/studies/{study_id}/timeline` em
  `backend/app/api/routes/studies.py`: mesma validação de `study_id` de T015; chama
  `_service.get_timeline_path(study_id)`; levanta `HTTPException(status_code=404,
  detail="Estudo não encontrado.")` quando `None`; caso contrário lê e retorna o JSON
  (`json.loads(path.read_text(encoding="utf-8"))`) como corpo da resposta (depende de T006, T017)

**Checkpoint**: as três user stories funcionam de forma independente.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T019 [P] Executar `uv run pytest tests` a partir de `backend/` e confirmar que toda a suíte
  (pré-existente + nova) passa (quickstart.md §1–2)
  > Resultado: os 173 testes unitários (144 pré-existentes + 29 novos de US1–US3) passam 100%. A
  > suíte completa (`tests` sem `--ignore`) ainda derruba o processo no mesmo ponto pré-existente
  > (`tests/integration/test_audio_pipeline.py`, ver nota em T002) — comportamento idêntico ao da
  > baseline, confirmando que nenhuma regressão foi introduzida pelo código novo desta fase.
- [X] T020 Executar a validação ponta a ponta real do quickstart.md §3 (subir `uvicorn`, criar um
  estudo via `curl`, buscar o áudio e a timeline pelo `study_id` retornado, e confirmar os três
  casos de erro — `422` texto vazio, `404` id inexistente, `422` id malformado)
  > Validada com Uvicorn e `curl`: criação `201`, áudio `200`, timeline schema v1 `200` e erros
  > `422`/`404`/`422`. O provider agora usa um cache ASCII para os dados do eSpeak no Windows
  > quando o projeto está instalado em um caminho Unicode, contornando o defeito descrito em T002.
- [X] T021 [P] Adicionar o teste de integração real (FFmpeg/Piper), seguindo o mesmo padrão de
  guarda de disponibilidade já usado em `backend/tests/integration/test_audio_pipeline.py`, para o
  fluxo completo criar → buscar áudio → buscar timeline via API, em
  `backend/tests/integration/test_studies_api.py`
  > O teste real cobre criação, download do MP3 publicado e recuperação da timeline.
- [X] T022 Verificar o quickstart.md §4 — confirmar que nenhum diretório temporário `tts_phase3_*`
  permanece após exercitar os caminhos de sucesso e de falha através da API
  > Os caminhos real de sucesso e controlado de falha são cobertos pela integração; nenhum resíduo
  > foi encontrado em `backend/temp` nem no diretório temporário do sistema.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — pode começar imediatamente
- **Foundational (Phase 2)**: depende da conclusão do Setup — bloqueia todas as user stories
- **User Stories (Phase 3+)**: todas dependem da conclusão da fase Foundational
  - US1, US2 e US3 podem prosseguir em paralelo (se houver equipe) ou em ordem de prioridade
    (P1 → P2 → P3)
- **Polish (Phase 6)**: depende da conclusão das user stories desejadas

### User Story Dependencies

- **User Story 1 (P1)**: pode começar após a Phase 2 — sem dependência de outras stories
- **User Story 2 (P2)**: pode começar após a Phase 2 — não depende de US1 em tempo de execução
  (lê um arquivo que pode ter sido criado por qualquer caminho, inclusive uma fixture de teste),
  mas reaproveita `STUDY_ID_PATTERN`/`_audio_path` criados na Phase 2
- **User Story 3 (P3)**: mesma observação de US2, reaproveitando `timeline_path_for`

### Within Each User Story

- Testes escritos e falhando antes da implementação
- Schemas/modelos antes do serviço; serviço antes do handler HTTP
- Story completa e testável antes de prosseguir para a próxima prioridade

### Parallel Opportunities

- T002 pode rodar em paralelo a T001 (nenhuma dependência de arquivo)
- T003, T004 e T005 podem rodar em paralelo entre si (arquivos diferentes); T006 depende de T005
- Dentro de cada user story, as tarefas de teste marcadas `[P]` (arquivos diferentes) podem rodar
  em paralelo entre si
- T010 e T011 podem rodar em paralelo entre si (arquivos diferentes); T012 depende de ambas
- Uma vez concluída a Phase 2, US1, US2 e US3 podem ser trabalhadas em paralelo por desenvolvedores
  diferentes

---

## Parallel Example: User Story 1

```bash
# Testes de US1 em paralelo (arquivos diferentes):
Task: "Testes de validação em backend/tests/unit/test_study_schemas.py"
Task: "Testes de StudyService.create() em backend/tests/unit/test_study_service.py"
Task: "Teste de integração de POST /studies em backend/tests/unit/test_studies_routes.py"

# Implementação de US1 em paralelo (arquivos diferentes, antes do handler):
Task: "StudyCreateRequest/StudyCreateResponse em backend/app/schemas/study.py"
Task: "StudyService.create() em backend/app/services/studies/service.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 apenas)

1. Completar Phase 1: Setup
2. Completar Phase 2: Foundational (bloqueia todas as stories)
3. Completar Phase 3: User Story 1
4. **PARAR e VALIDAR**: testar User Story 1 de forma independente (quickstart.md §2–3, apenas o
   endpoint de criação)
5. Esse já é um MVP utilizável: criar um estudo e confirmar os arquivos em `OUTPUT_DIR`

### Incremental Delivery

1. Setup + Foundational → base pronta
2. US1 → testar de forma independente → MVP (criar estudo)
3. US2 → testar de forma independente → baixar áudio pelo id
4. US3 → testar de forma independente → obter timeline pelo id
5. Cada story agrega valor sem quebrar as anteriores

---

## Notes

- `[P]` = arquivos diferentes, sem dependência entre as tarefas
- `[Story]` mapeia a tarefa à user story correspondente, para rastreabilidade com `spec.md`
- Nenhuma tarefa desta lista altera `app/services/text/` ou `app/services/audio/` — são
  reaproveitados exatamente como estão (Princípio V, Incremental Pipeline Compatibility)
- Confirmar que os testes falham antes de implementar (TDD); fazer commit após cada tarefa ou
  grupo lógico
- Parar em qualquer checkpoint para validar a story de forma independente antes de avançar
