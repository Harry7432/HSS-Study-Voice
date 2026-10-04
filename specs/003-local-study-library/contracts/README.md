# Contratos: Biblioteca local-first de estudos

Esta fase não expõe API HTTP nova. O frontend consome os três endpoints da Fase 4 por URLs relativas
`/api/v1/...`, encaminhadas pelo proxy Vite no desenvolvimento e servidas sob a mesma origem em
produção.

## Validação runtime da API

Tipos TypeScript não são considerados validação. Antes de retornar dados ao fluxo de aplicação,
`frontend/src/api/validators.ts` valida:

- criação: objeto fechado, `study_id` em `^[0-9a-f]{32}$`, `chunks_count` inteiro `>= 1`,
  `duration_seconds >= 0`, `file_size_bytes` inteiro `>= 1` e `processing_time_seconds >= 0`;
- áudio: resposta HTTP bem-sucedida, `Content-Type: audio/mpeg` e Blob não vazio;
- timeline: forma completa de `001-text-audio-timeline/contracts/timeline-v1.schema.json`, incluindo
  versão 1, SHA-256 hexadecimal, sample rate/total de amostras positivos e intervalos ordenados.

Falha em qualquer validação encerra o fluxo antes de qualquer escrita IndexedDB.

## `libraryService`

[`library-service.interface.ts`](./library-service.interface.ts) é a interface pública consumida pela
UI/aplicação. `saveStudy(result, label)` exige rótulo de 1–80 caracteres já normalizado; o serviço não
recebe o texto original. Todos os métodos podem lançar `LibraryUnavailableError`.

## Formatos persistidos

- [`study-metadata.schema.json`](./study-metadata.schema.json): registro leve em `studyMetadata`,
  incluindo progresso e índice `createdAt`.
- [`study-assets.schema.json`](./study-assets.schema.json): Blob MP3 e timeline em `studyAssets`.

Salvar e remover usam uma única transação `readwrite` abrangendo os dois stores. `listStudies()` lê
somente `studyMetadata`; `getStudy()` compõe as duas entradas em memória.

## Backend consumido

- `POST /api/v1/studies`
- `GET /api/v1/studies/{study_id}/audio`
- `GET /api/v1/studies/{study_id}/timeline`

Os contratos HTTP originais permanecem em `../../002-study-audio-api/contracts/` e o backend não é
alterado por esta feature.
