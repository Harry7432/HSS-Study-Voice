# Quickstart: Validar a API de geração de estudos em áudio

## Prerequisites

- Python 3.13 ou mais recente
- Dependências do projeto instaladas via `uv`
- FFmpeg disponível via `FFMPEG_PATH` ou `PATH` para validação ponta a ponta
- Arquivos de voz Piper para `DEFAULT_VOICE` baixados (ou acesso de rede na primeira execução, via
  `PiperProvider.ensure_voice_downloaded`)

Execute os comandos a partir de `backend/`, salvo indicação contrária.

## 1. Validar que o comportamento existente não foi afetado

```powershell
uv run pytest tests
```

Resultado esperado: toda a suíte pré-existente (Fases 1–3) continua verde — esta fase é puramente
aditiva, sem alterar `TextPreprocessingPipeline` nem `AudioOrchestrator`.

## 2. Validar a camada de API com `TestClient` (sem FFmpeg/Piper reais)

```powershell
uv run pytest tests/unit/test_study_service.py tests/unit/test_studies_routes.py -v
```

Resultado esperado: os testes unitários do `StudyService` e dos handlers do router passam usando
dublês (`AudioOrchestrator`/`TextPreprocessingPipeline` injetados), cobrindo:

- criação com sucesso → `201` com os campos de `study-create-response.schema.json`;
- texto vazio/apenas espaços → `422`;
- texto acima de `MAX_REQUEST_TEXT_CHARS` → `422`;
- `study_id` com formato inválido em `/audio` e `/timeline` → `422`;
- `study_id` bem formado mas inexistente em `/audio` e `/timeline` → `404`;
- falha simulada de geração (exceção do orquestrador) → `500` com `detail` genérico, sem stack
  trace no corpo da resposta.

## 3. Validação de integração real (end-to-end)

Requer FFmpeg e o modelo de voz padrão disponíveis localmente.

```powershell
uv run uvicorn app.main:app --reload
```

Em outro terminal:

```powershell
curl.exe -s -X POST http://127.0.0.1:8000/api/v1/studies `
  -H "Content-Type: application/json" `
  -d '{"text": "## Ola\n\nEste e um texto de **teste** com duas frases. A segunda frase confirma a timeline."}'
```

Resultado esperado: resposta `201` com um `study_id` de 32 caracteres hexadecimais e os metadados de
geração (`chunks_count`, `duration_seconds`, `file_size_bytes`, `processing_time_seconds`).

Anote o `study_id` retornado e valide a recuperação:

```powershell
curl.exe -s -o estudo.mp3 http://127.0.0.1:8000/api/v1/studies/<study_id>/audio
curl.exe -s http://127.0.0.1:8000/api/v1/studies/<study_id>/timeline
```

Resultado esperado:

- `estudo.mp3` é um MP3 válido e reproduzível, sem nenhuma marcação Markdown lida em voz alta;
- a resposta de `/timeline` valida contra
  `../001-text-audio-timeline/contracts/timeline-v1.schema.json`, com uma entrada por frase.

Teste também os casos de erro:

```powershell
curl.exe -s -X POST http://127.0.0.1:8000/api/v1/studies -H "Content-Type: application/json" -d '{"text": "   "}'
curl.exe -s http://127.0.0.1:8000/api/v1/studies/00000000000000000000000000000000/audio
curl.exe -s http://127.0.0.1:8000/api/v1/studies/not-a-valid-id/audio
```

Resultado esperado, respectivamente: `422` (texto vazio), `404` (bem formado, inexistente), `422`
(formato inválido).

## 4. Verificação de limpeza de temporários

Após qualquer execução acima (sucesso ou falha simulada), confirme que nenhum diretório temporário
de processamento (`tts_phase3_*`, criado por `AudioOrchestrator`) permanece em `backend/temp` ou no
diretório temporário do sistema — comportamento já garantido pelo orquestrador existente e apenas
reexercitado aqui através da API.
