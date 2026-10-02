# Implementation Plan: Timeline de sincronizacao texto-audio

**Branch**: `001-text-audio-timeline` | **Date**: 2026-10-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-text-audio-timeline/spec.md`

## Summary

Estender o pipeline local para preservar frases canonicas antes do agrupamento em chunks, renderizar
fragmentos de sintese rastreaveis, calcular limites por frames WAV reais e publicar um MP3 com sua
timeline JSON versionada. O fluxo atual baseado em `list[str]` permanece disponivel; o fluxo
sincronizado usa uma representacao textual estruturada, concatena PCM uma vez, codifica MP3 uma vez
e publica o par somente depois de validar frames, contrato e SHA-256.

## Technical Context

**Language/Version**: Python >= 3.13

**Primary Dependencies**: FastAPI, Piper TTS, FFmpeg e biblioteca padrao (`wave`, `hashlib`, `json`,
`tempfile`, `os`, `shutil`); nenhuma dependencia nova

**Storage**: Arquivos locais temporarios e artefatos finais MP3/JSON lado a lado

**Testing**: pytest com testes unitarios isolados e integracao real opcional com Piper/FFmpeg

**Target Platform**: Backend local em Windows ou Linux com Piper e FFmpeg disponiveis

**Project Type**: Backend service com pipeline local de texto e audio

**Performance Goals**: Preparacao da timeline acrescenta no maximo 5% ao tempo total em um audio
representativo de 60 minutos

**Constraints**: 22050 Hz; limites inteiros no dominio PCM; uma codificacao MP3; SHA-256 do MP3
final; publicacao transacional no limite da operacao; sem API, frontend, filas ou armazenamento
remoto permanente

**Scale/Scope**: Um documento por execucao, com todos os chunks e frases mantidos em memoria; alvo de
validacao de ate 60 minutos de audio por artefato

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Result |
|-----------|------|--------|
| Spec-Driven Development | Spec e clarificacoes registradas antes do design | PASS |
| Local-First Ownership | MP3 e timeline permanecem locais; temporarios sao removidos | PASS |
| Simple and Modular Backend | Usa componentes atuais e biblioteca padrao, sem infraestrutura nova | PASS |
| Mandatory Tests | Preve testes unitarios, integracao real e preservacao da suite atual | PASS |
| Incremental Pipeline Compatibility | Mantem APIs atuais e adiciona fluxo estruturado explicito | PASS |
| Security by Default | Restringe caminhos ao destino, evita execucao e nao adiciona logs de texto | PASS |
| No Overengineering | JSON sidecar e modulos focados, sem alinhamento forcado ou novos servicos | PASS |
| Phase-Bounded Delivery | Escopo permanece apenas metadata de sincronizacao | PASS |
| Architecture Ready for Evolution | Modelos e contrato versionado isolam provider e serializacao | PASS |
| Explicit Technical Decisions | Decisoes e alternativas constam em `research.md` | PASS |

No gate violations. Complexity tracking is not required.

## Project Structure

### Documentation (this feature)

```text
specs/001-text-audio-timeline/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── timeline-v1.schema.json
└── tasks.md
```

`tasks.md` sera criado posteriormente por `/speckit.tasks`.

### Source Code (repository root)

```text
backend/
├── app/
│   └── services/
│       ├── text/
│       │   ├── models.py          # documento, chunk, frase e fragmento preparados
│       │   ├── chunker.py         # segmentacao canonica e agrupamento
│       │   └── pipeline.py        # API atual e fluxo estruturado
│       └── audio/
│           ├── timeline.py        # modelo, validacao, serializacao e SHA-256
│           ├── renderer.py        # WAVs ordenados dos fragmentos
│           ├── concatenator.py    # concatenacao PCM existente
│           ├── exporter.py        # unica codificacao MP3 existente
│           └── orchestrator.py    # contabilizacao, staging, publicacao e rollback
└── tests/
    ├── unit/
    │   ├── test_chunker.py
    │   ├── test_pipeline.py
    │   ├── test_timeline.py
    │   ├── test_audio_renderer.py
    │   └── test_audio_orchestrator.py
    └── integration/
        └── test_audio_pipeline.py
```

**Structure Decision**: Manter o backend unico e os limites atuais entre texto e audio. Adicionar
somente um modulo de modelos textuais e um modulo profundo de timeline; o orquestrador continua
responsavel pela sequencia completa e pela publicacao do par.

## Phase 0: Research Summary

As decisoes consolidadas em [research.md](research.md) resolvem todos os pontos tecnicos:

- frases sao definidas uma vez no texto normalizado antes dos chunks;
- `process()` e `chunk()` preservam seus retornos atuais e um fluxo estruturado carrega identidade;
- cada fragmento renderizado conserva o vinculo com chunk e frase;
- frames sao lidos dos WAVs e conferidos contra o WAV concatenado;
- a timeline usa contrato JSON v1 fechado e SHA-256 do MP3 final;
- staging no diretorio de destino, backups e rollback implementam atomicidade no limite da operacao.

## Phase 1: Design Summary

- [data-model.md](data-model.md) define modelos, invariantes e estados de publicacao.
- [contracts/timeline-v1.schema.json](contracts/timeline-v1.schema.json) define o sidecar publico.
- [quickstart.md](quickstart.md) define validacao unitaria e ponta a ponta.
- Nenhuma rota de API ou componente frontend e criado.

## Post-Design Constitution Check

Todos os gates continuam PASS. O design nao introduz dependencia, servico, armazenamento remoto ou
quebra de contrato existente. A complexidade adicional esta limitada aos dados necessarios para
preservar identidade de frase e publicar dois artefatos de forma recuperavel.
