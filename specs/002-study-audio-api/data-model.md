# Data Model: API de geração de estudos em áudio

Modelos novos introduzidos por esta fase. Não altera os modelos existentes de texto/áudio/timeline
(`app/services/text/models.py`, `app/services/audio/timeline.py`) — apenas os envolve em uma camada
HTTP.

## StudyCreateRequest

Corpo da requisição de criação (`POST {API_V1_STR}/studies`).

| Campo    | Tipo            | Obrigatório | Regras de validação |
|----------|-----------------|-------------|----------------------|
| `text`   | `str`           | Sim         | Após `strip()`, não pode ser vazio (FR-002). Tamanho máximo `settings.MAX_REQUEST_TEXT_CHARS` (ver `research.md` §4); acima disso, `422`. |
| `voice`  | `str \| None`   | Não         | Quando omitido, usa `settings.DEFAULT_VOICE`. Voz desconhecida é detectada pelo provider na geração, não na validação do request (ver `research.md` §7). |
| `speed`  | `float \| None` | Não         | Quando omitido, usa `settings.DEFAULT_SPEED`. Deve ser `> 0` quando informado. |
| `bitrate`| `str \| None`   | Não         | Quando omitido, usa `settings.MP3_BITRATE`. |

## StudyCreateResponse

Corpo de resposta de sucesso (`201 Created`) da criação.

| Campo                     | Tipo    | Descrição |
|---------------------------|---------|-----------|
| `study_id`                | `str`   | Identificador hexadecimal de 32 caracteres (ver `research.md` §1). |
| `chunks_count`             | `int`   | Quantidade de chunks processados (de `AudioResult.chunks_count`). |
| `duration_seconds`        | `float` | Duração do áudio final (de `AudioResult.duration_seconds`). |
| `file_size_bytes`         | `int`   | Tamanho do MP3 final em bytes (de `AudioResult.file_size_bytes`). |
| `processing_time_seconds` | `float` | Tempo total de processamento (de `AudioResult.processing_time_seconds`). |

Mapeamento 1:1 a partir do `AudioResult` já retornado por
`AudioOrchestrator.generate_synchronized` — nenhum campo novo é calculado pela camada de API.

## ErrorResponse

Corpo de erro para `404` e `500` (requisições `422` usam o formato padrão de validação do
FastAPI/Pydantic).

| Campo    | Tipo  | Descrição |
|----------|-------|-----------|
| `detail` | `str` | Mensagem curta e não técnica. Nunca contém stack trace, caminho de arquivo interno ou o texto submetido (FR-011, FR-012). |

Valores possíveis de `detail`:

- `404` (busca de áudio/timeline): `"Estudo não encontrado."`
- `500` (falha de geração, ver `research.md` §6): `"Falha ao gerar o estudo em áudio."`

## StudyRecord (interno, não serializado na API)

Estrutura de retorno interna de `StudyService.create(...)`, usada apenas entre o serviço e o
router — não é um modelo Pydantic exposto.

| Campo          | Tipo   | Origem |
|----------------|--------|--------|
| `study_id`     | `str`  | Gerado pelo `StudyService` (uuid4 hex). |
| `audio_path`   | `Path` | `settings.OUTPUT_DIR / f"{study_id}.mp3"`. |
| `timeline_path`| `Path` | `timeline_path_for(audio_path)`. |
| `result`       | `AudioResult` | Retorno de `AudioOrchestrator.generate_synchronized`. |

## Relações e ciclo de vida

```text
StudyCreateRequest
   │  StudyService.create()
   │    1. TextPreprocessingPipeline.prepare(text) → PreparedDocument
   │    2. AudioOrchestrator.generate_synchronized(document, audio_path, ...) → AudioResult
   ▼
StudyRecord (study_id, audio_path, timeline_path, result)
   │
   ├─▶ GET /studies/{study_id}/audio      → FileResponse(audio_path)          [404 se ausente]
   └─▶ GET /studies/{study_id}/timeline   → TimelineDocument.to_dict()        [404 se ausente]
```

Não há transição de estado além de "criado" → "existe no `OUTPUT_DIR`"; não há exclusão,
atualização ou listagem nesta fase (ver Assumptions em `spec.md`). A existência simultânea dos
dois arquivos (`.mp3` e `.timeline.json`) já é garantida pela publicação atômica existente em
`AudioOrchestrator.generate_synchronized` (Fase 3) — a camada de API não precisa reimplementar essa
garantia.

## Validações cruzadas com o spec

- FR-002 (texto vazio) → `StudyCreateRequest.text`.
- FR-004 (voz/velocidade/bitrate opcionais) → `StudyCreateRequest.voice/speed/bitrate`.
- FR-007 (identificador único) → `StudyRecord.study_id`.
- FR-008 (metadados na resposta) → `StudyCreateResponse`.
- FR-011 (erro claro e não técnico para id inexistente) → `ErrorResponse` com `404`.
- FR-012 (erro claro sem vazar detalhes internos em falha de geração) → `ErrorResponse` com `500`.
