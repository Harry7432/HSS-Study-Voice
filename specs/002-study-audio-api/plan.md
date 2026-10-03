# Implementation Plan: API de geração de estudos em áudio

**Branch**: `002-study-audio-api` | **Date**: 2026-10-03 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-study-audio-api/spec.md`

## Summary

Expor como API HTTP o pipeline de texto-para-áudio já construído nas Fases 1–3
(`TextPreprocessingPipeline` + `AudioOrchestrator.generate_synchronized`), permitindo criar um
estudo em áudio a partir de texto (síncrono), e recuperar depois o MP3 e a timeline sincronizada
pelo identificador retornado na criação. Nenhum componente interno existente é alterado — a fase
adiciona apenas uma camada fina de router + schemas + um serviço de orquestração de requisições
(`StudyService`) sobre o que já existe.

## Technical Context

**Language/Version**: Python >= 3.13

**Primary Dependencies**: FastAPI (já presente, `>=0.142.2`), Pydantic/`pydantic-settings` (já
presentes), Piper TTS e FFmpeg via os serviços já existentes; nenhuma dependência nova.

**Storage**: Arquivos locais em `settings.OUTPUT_DIR` (`.mp3` + `.timeline.json` por estudo,
nomeados pelo `study_id`); sem banco de dados.

**Testing**: pytest com `fastapi.testclient.TestClient` para os handlers do router (com
`AudioOrchestrator`/`TextPreprocessingPipeline` substituídos por dublês) e testes unitários puros
para `StudyService`; suíte de integração real (FFmpeg/Piper) opcional, seguindo o padrão já usado
em `tests/integration/test_audio_pipeline.py`.

**Target Platform**: Backend local (Windows ou Linux) com Piper e FFmpeg disponíveis, servido via
Uvicorn.

**Project Type**: Serviço web backend (API REST local, sem frontend).

**Performance Goals**: Nenhum requisito de taxa de requisições (uso local, síncrono, um usuário por
vez); o tempo de resposta de criação é dominado pela síntese de voz e conversão FFmpeg já medidas
nas Fases 1–3.

**Constraints**: processamento síncrono (sem fila/job); sem autenticação (uso local); sem
listagem/histórico de estudos nesta fase (decisões confirmadas com o usuário — ver Assumptions em
`spec.md`); handlers devem ser `def` (não `async def`) para não bloquear o event loop durante
síntese/conversão bloqueante (ver `research.md` §3).

**Scale/Scope**: Três endpoints (`POST /studies`, `GET /studies/{id}/audio`,
`GET /studies/{id}/timeline`); um estudo por requisição de criação.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Result |
|-----------|------|--------|
| I. Spec-Driven Development | Spec aprovado, sem `[NEEDS CLARIFICATION]`; duas decisões de escopo confirmadas com o usuário antes do spec | PASS |
| II. Local-First Ownership | Áudio e timeline permanecem em `settings.OUTPUT_DIR`, local; nenhum armazenamento remoto introduzido | PASS |
| III. Simple and Modular Backend | Router + `StudyService` finos sobre `TextPreprocessingPipeline`/`AudioOrchestrator` já existentes; nenhuma fila, Redis ou infraestrutura nova | PASS |
| IV. Mandatory Tests | Plano exige testes unitários de `StudyService` e de validação dos handlers, mais testes de integração reaproveitando o padrão existente; suíte atual preservada (nenhuma alteração em `services/`) | PASS (a confirmar na execução) |
| V. Incremental Pipeline Compatibility | `generate_mp3`/`generate_synchronized`/`TextPreprocessingPipeline` não são modificados; API é puramente aditiva | PASS |
| VI. Security by Default | **Inicialmente em risco**: a spec assumia "sem teto artificial" de tamanho de texto, mas a constituição exige um limite explícito configurado. **Resolvido no Phase 0** (`research.md` §4) com a nova configuração `MAX_REQUEST_TEXT_CHARS` (generosa, não restringe uso típico). `study_id` validado por regex evita acesso fora do padrão de arquivo esperado; logs nunca incluem o texto submetido (`research.md` §6) | PASS (pós-resolução) |
| VII. No Overengineering | Sem fila, autenticação, listagem ou mapeamento fino de códigos de erro por tipo de exceção — tudo deliberadamente fora de escopo (`research.md` §6, Assumptions do spec) | PASS |
| VIII. Phase-Bounded Delivery | Escopo restrito a criar + buscar por id, síncrono; exclusões explícitas no spec e neste plano | PASS |
| IX. Architecture Ready for Evolution | `StudyService` isola a camada HTTP do orquestrador; o esquema de armazenamento por arquivo pode evoluir para um índice persistente sem mudar o contrato HTTP | PASS |
| X. Explicit Technical Decisions | Todas as decisões arquiteturalmente relevantes (identificador, layout de armazenamento, handlers síncronos, limite de tamanho, mapeamento de erros) documentadas em `research.md` | PASS |

Nenhuma violação não justificada. `Complexity Tracking` não é necessário.

## Project Structure

### Documentation (this feature)

```text
specs/002-study-audio-api/
├── plan.md              # Este arquivo
├── research.md          # Fase 0: decisões técnicas
├── data-model.md         # Fase 1: modelos de request/response
├── quickstart.md         # Fase 1: guia de validação
├── contracts/            # Fase 1: contratos da API
│   ├── README.md
│   ├── study-create-request.schema.json
│   ├── study-create-response.schema.json
│   └── error-response.schema.json
└── tasks.md              # Será criado por /speckit.tasks
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── main.py                        # Registra o router novo sob settings.API_V1_STR
│   ├── core/
│   │   └── config.py                  # + MAX_REQUEST_TEXT_CHARS
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── studies.py             # 3 endpoints; valida, chama StudyService, traduz erros
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── study.py                   # StudyCreateRequest, StudyCreateResponse, ErrorResponse
│   └── services/
│       ├── studies/
│       │   ├── __init__.py
│       │   └── service.py             # StudyService: cria/localiza áudio e timeline por study_id
│       ├── text/                      # Inalterado (Fases 1-2)
│       └── audio/                     # Inalterado (Fase 3)
└── tests/
    ├── unit/
    │   ├── test_study_schemas.py      # Novo (validação de StudyCreateRequest/Response)
    │   ├── test_study_service.py      # Novo
    │   └── test_studies_routes.py     # Novo (TestClient + dublês)
    └── integration/
        └── test_studies_api.py        # Novo (FFmpeg/Piper reais, mesmo padrão de skip já usado)
```

**Structure Decision**: manter o backend único existente; adicionar apenas `app/api/` (camada HTTP),
`app/schemas/` (contratos Pydantic) e `app/services/studies/` (orquestração fina da requisição).
`services/text/` e `services/audio/` permanecem exatamente como estão — reaproveitados, não
modificados.

## Phase 0: Research Summary

As decisões consolidadas em [research.md](research.md) resolvem todos os pontos técnicos:

- `study_id` é um UUID4 hex de 32 caracteres; áudio e timeline usam o layout de nome-irmão já
  existente em `timeline_path_for`.
- A camada HTTP fica em `app/api/routes/studies.py`; a orquestração de requisição fica isolada em
  `StudyService`, testável sem FastAPI.
- Handlers são síncronos (`def`) para não bloquear o event loop durante síntese/FFmpeg.
- Um novo `MAX_REQUEST_TEXT_CHARS` resolve o gate de segurança da constituição sem reabrir o spec.
- `study_id` malformado → `422`; bem formado mas inexistente → `404`.
- Qualquer falha de geração → `500` genérico, sem detalhes internos; log nunca inclui o texto
  submetido.
- Voz/velocidade/bitrate passam direto para o orquestrador existente, sem duplicar validação de
  catálogo de vozes.

## Phase 1: Design Summary

- [data-model.md](data-model.md) define `StudyCreateRequest`, `StudyCreateResponse`,
  `ErrorResponse` e o `StudyRecord` interno, com rastreabilidade para cada FR do spec.
- [contracts/](contracts/) define o contrato HTTP dos três endpoints, reaproveitando o schema de
  timeline já publicado em `001-text-audio-timeline` em vez de duplicá-lo.
- [quickstart.md](quickstart.md) define validação unitária, de integração com dublês, e ponta a
  ponta real via `curl`, incluindo os casos de erro (`422`, `404`, `500`) e a verificação de
  limpeza de temporários.
- Nenhuma mudança de schema de banco de dados, UI ou contrato de timeline existente.

## Post-Design Constitution Check

Todos os gates continuam PASS. O design não introduz dependência, serviço remoto ou infraestrutura
nova; o único ponto antes em risco (limite explícito de tamanho de texto) foi resolvido com uma
configuração nova e documentada, sem contradizer o uso típico já descrito no spec. A complexidade
adicional está limitada a uma camada HTTP fina sobre componentes já existentes.
