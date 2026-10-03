# Contratos: API de geração de estudos em áudio

Três endpoints HTTP, montados sob `settings.API_V1_STR` (`/api/v1`). Todas as respostas de sucesso
e erro usam JSON, exceto o download do áudio.

## `POST /api/v1/studies`

Cria um estudo em áudio de forma síncrona (bloqueia até o resultado estar pronto).

- **Request body**: [`study-create-request.schema.json`](./study-create-request.schema.json)
- **201 Created**: [`study-create-response.schema.json`](./study-create-response.schema.json)
- **422 Unprocessable Entity**: texto vazio/apenas espaços, texto acima de
  `settings.MAX_REQUEST_TEXT_CHARS`, ou `speed` ≤ 0 — formato padrão de validação do
  FastAPI/Pydantic.
- **500 Internal Server Error**: falha de geração (voz desconhecida, FFmpeg indisponível, falha de
  síntese ou de publicação) → [`error-response.schema.json`](./error-response.schema.json).

## `GET /api/v1/studies/{study_id}/audio`

Recupera o arquivo MP3 de um estudo já gerado.

- **Path param**: `study_id` — string, deve casar com `^[0-9a-f]{32}$`.
- **200 OK**: corpo binário, `Content-Type: audio/mpeg` (o próprio arquivo gravado por
  `AudioOrchestrator.generate_synchronized`).
- **404 Not Found**: nenhum estudo com esse `study_id` →
  [`error-response.schema.json`](./error-response.schema.json).
- **422 Unprocessable Entity**: `study_id` não casa com o formato esperado (ver
  `research.md` §5).

## `GET /api/v1/studies/{study_id}/timeline`

Recupera a timeline sincronizada por frase de um estudo já gerado.

- **Path param**: `study_id` — mesma validação acima.
- **200 OK**: JSON conforme o contrato já existente
  [`../../001-text-audio-timeline/contracts/timeline-v1.schema.json`](../../001-text-audio-timeline/contracts/timeline-v1.schema.json)
  — esta fase apenas expõe o arquivo já produzido pela Fase 3, sem alterar seu schema.
- **404 Not Found**: nenhum estudo com esse `study_id` →
  [`error-response.schema.json`](./error-response.schema.json).
- **422 Unprocessable Entity**: `study_id` não casa com o formato esperado.
