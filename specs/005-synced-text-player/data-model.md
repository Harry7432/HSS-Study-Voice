# Phase 1 Data Model: Player com texto sincronizado

Esta fase reaproveita `TimelineSentence`, `TimelineChunk` e `TimelineDocument`
(`frontend/src/library/types.ts`) sem alteração. As entidades abaixo são derivadas em memória,
nunca persistidas, e existem apenas enquanto um estudo está aberto na Reading View.

## Reutilizadas (sem alteração)

- **TimelineSentence**: `{ index: number, text: string, start_sample: number, end_sample: number }`.
  `index` é a posição da frase **dentro do seu chunk** (reinicia em cada chunk), não um
  identificador global — a identidade global de uma frase nesta fase é sua posição no array
  achatado (ver abaixo), não o campo `index`.
- **TimelineChunk**: `{ index, start_sample, end_sample, sentences: TimelineSentence[] }`.
- **TimelineDocument**: `{ schema_version: 1, audio: { filename, sha256, sample_rate_hz,
  total_samples }, chunks: TimelineChunk[] }`. Garantia já validada pelo backend (Fase 3.1): os
  intervalos de frases e chunks são semiabertos `[start, end)`, ordenados, contíguos e cobrem
  exatamente `[0, total_samples)` sem sobreposição nem lacunas.

## Novas (em memória, derivadas, não persistidas)

### Reading View State

Estado interno de uma instância de `createReadingView`, um por estudo aberto por vez.

| Campo | Tipo | Derivação / regra |
|---|---|---|
| `sentences` | `TimelineSentence[]` | `flattenSentences(timeline)` — concatenação de `chunk.sentences` na ordem dos chunks; calculado uma vez por `open()` |
| `elements` | `HTMLButtonElement[]` | Paralelo a `sentences` (mesmo índice) — o nó clicável de cada frase |
| `sampleRateHz` | `number` | Copiado de `timeline.audio.sample_rate_hz` no `open()` |
| `totalSamples` | `number` | Copiado de `timeline.audio.total_samples` no `open()` |
| `currentIndex` | `number \| undefined` | Índice em `sentences`/`elements` da frase destacada; `undefined` só antes da primeira resolução (nunca permanece assim após um `open()` bem-sucedido) |
| `autoScrollSuspended` | `boolean` | `false` no `open()`; `true` após um `scroll` do usuário no contêiner; volta a `false` em `seeked`/`play` do áudio |
| `available` | `boolean` | `false` quando `parseTimeline(timeline)` lança exceção ou `timeline` está ausente/indefinida em tempo de execução; controla se os demais campos têm sentido |

### Current Sentence Resolution (derivação pura, não é um valor armazenado)

`findSentenceIndexAtSample(sentences, samplePosition): number` — índice em `sentences`.

**Invariante**: para qualquer `samplePosition >= 0`, exatamente um índice é retornado (nunca
"nenhum"), porque o backend garante frases ordenadas, contíguas e sem lacunas sobre
`[0, total_samples)`, e o lookup clampa qualquer valor `>= total_samples` para o último índice e
qualquer valor negativo para o primeiro.

### Playback Position (derivada, não armazenada)

`samplePosition = clamp(Math.floor(audio.currentTime * sampleRateHz), 0, totalSamples)`.

`floor` (não `round`) é usado para que uma posição só seja considerada "dentro" de uma frase quando
a reprodução de fato alcançou sua primeira amostra (ver `research.md`, Decisão 5).

### Sentence Click Target (uso de `TimelineSentence`, não um novo tipo)

Clicar no elemento em `elements[i]` mapeia para `sentences[i].start_sample / sampleRateHz` segundos,
atribuído a `audio.currentTime`. Não altera `audio.paused`.

## Estados e transições da Reading View

```text
(nenhum estudo aberto)
        │ open(study)
        ▼
  parseTimeline(study.timeline) lança? ──sim──► available=false
        │ não                                    (mensagem de indisponibilidade;
        ▼                                         áudio continua tocando normalmente)
  available=true, sentences/elements montados,
  currentIndex resolvido a partir de study.progress
        │
        ├─ timeupdate / seeked / play / loadedmetadata ──► recalcula currentIndex
        ├─ ended ──► currentIndex = último índice (samplePosition = totalSamples)
        ├─ clique numa frase ──► audio.currentTime atualizado; currentIndex = frase clicada
        ├─ scroll manual do contêiner ──► autoScrollSuspended = true
        └─ seeked / play (novo) ──► autoScrollSuspended = false
        │
        ▼ discard() (troca de estudo ou remoção)
(nenhum estudo aberto)
```

## Regra de destaque inicial (`open()`, cobre FR-009)

Dado `study.progress = { positionSeconds, completed }`:

- `completed === true` → destaca a última frase (equivalente a resolver com
  `samplePosition = totalSamples`, mesma regra de clamp usada em todo o resto).
- Caso contrário → `samplePosition = Math.floor(positionSeconds * sampleRateHz)`, resolvido pela
  mesma função `findSentenceIndexAtSample` (cobre `positionSeconds = 0` → primeira frase, e qualquer
  overshoot por arredondamento → última frase, sem caso especial adicional).
