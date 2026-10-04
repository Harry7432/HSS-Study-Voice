# Phase 0 Research: Player com texto sincronizado

## Decisão 1 — Busca binária sobre array achatado, recalculado uma vez por `open()`

**Decision**: Resolver a frase atual com uma busca binária por `start_sample` sobre um array de
frases achatado (`flattenSentences`), recalculado uma única vez quando o estudo é aberto — não a
cada `timeupdate`.

**Rationale**: `timeupdate` dispara repetidamente durante toda a reprodução; estudos podem ter
muitas frases (edge case explícito do spec: "texto muito longo, com muitas frases"). Uma busca
binária mantém cada resolução em O(log n) independentemente do tamanho do texto (≈13 comparações
para 10 mil frases). O achatamento acontece só uma vez por abertura de estudo, não em cada tick.

**Alternatives considered**:
- Varredura linear a cada tick — O(n) por tick; aceitável para textos curtos mas viola o edge case
  de responsividade para textos longos. Rejeitada.
- Cache do último índice resolvido com busca incremental a partir dele (aproveitando que a posição
  normalmente avança monotonicamente) — otimização válida, mas exige tratar separadamente saltos
  (clique, arrasto de barra) caindo de volta para busca completa, adicionando estado e complexidade
  por um ganho que a busca binária já entrega com folga. Rejeitada por Princípio VII (No
  Overengineering).

## Decisão 2 — Reaproveitar `parseTimeline` para detectar timeline corrompida localmente

**Decision**: Usar `parseTimeline` (já existente em `frontend/src/api/validators.ts`) dentro de um
`try/catch` em `readingView.open()` para decidir se uma timeline armazenada localmente pode ser
exibida.

**Rationale**: `parseTimeline` já é o validador exato de forma/ordem/contiguidade usado quando a
timeline chega do backend. Uma timeline armazenada localmente tem o mesmo contrato de forma, então
reaproveitar a mesma função cobre FR-011/SC-007 sem duplicar lógica de validação já existente e
testada.

**Alternatives considered**:
- Escrever um checker "leve" dedicado para leitura local — rejeitado por duplicar lógica já
  existente sem benefício real, violando Princípio VII.

## Decisão 3 — Destaque combinando `aria-current="true"` + peso de fonte (não-cor) + fundo (cor)

**Decision**: A frase atual recebe `aria-current="true"`, `font-weight: 700` e um fundo
`var(--bg-hover)` simultaneamente.

**Rationale**: FR-015 exige mais de um sinal visual, com pelo menos um deles não dependente de cor,
e exige identificação por tecnologia assistiva. `aria-current="true"` resolve a parte de
acessibilidade (mesmo padrão já usado no componente `LibraryItem` do design system vendorizado,
`frontend/src/hss/bundle.css`); `font-weight: 700` é o sinal não-cor exigido; o fundo é o reforço de
cor adicional — duas marcas, consistente com a regra "cor nunca é o único sinal" já aplicada no
componente `TrackRow` (também vendorizado, consumido hoje em `frontend/src/ui/libraryView.ts` via a
classe `is-playing` + troca de glifo).

**Alternatives considered**:
- Replicar o glifo de `TrackRow` por frase — rejeitado por gerar ruído visual por frase em textos
  com centenas delas.
- Usar só `aria-current` com fundo de cor (padrão puro de `LibraryItem`) — rejeitado por violar
  FR-015 (cor seria o único sinal).

## Decisão 4 — Suspensão de rolagem automática via janela transitória em torno de `scrollIntoView`

**Decision**: Cada chamada própria a `element.scrollIntoView({ block: 'nearest', behavior: 'smooth' })`
marca uma janela curta como "rolagem programática"; qualquer evento `scroll` do contêiner fora dessa
janela é tratado como rolagem manual do usuário, suspendendo o acompanhamento automático (FR-006). A
retomada ocorre nos eventos nativos `seeked`/`play` do próprio `<audio>`.

**Rationale**: `block: 'nearest'` já evita rolar quando a frase atual já está visível, então não é
necessário calcular visibilidade separadamente. `seeked`/`play` já cobrem tanto "clicar em outra
frase" (FR-007, dispara `seeked`) quanto interagir com a barra de progresso nativa ou o botão de
play — exatamente os gatilhos citados nas Assumptions do spec, sem precisar de um controle de UI
dedicado para "retomar rolagem".

**Alternatives considered**:
- `IntersectionObserver` observando se a frase atual está visível — não resolve por si só a
  detecção de rolagem manual (ainda seria necessário ouvir `scroll` para isso), tornando-se
  maquinário redundante. Rejeitada por Princípio VII.

## Decisão 5 — Amostra de reprodução via `Math.floor`, não `Math.round`

**Decision**: `samplePosition = Math.floor(audio.currentTime * sample_rate_hz)`.

**Rationale**: os intervalos de frase são semiabertos `[start_sample, end_sample)`; `floor` garante
que uma posição só é considerada "dentro" de uma frase quando a reprodução de fato alcançou essa
amostra, evitando que arredondamento antecipe o destaque em até meia amostra perto de um limite.

## Decisão 6 — Fim de áudio e overshoot tratados pela mesma regra de clamp

**Decision**: Tanto "áudio chegou ao fim" (FR-010) quanto "posição ultrapassa levemente o total de
amostras por arredondamento" (edge case) se resolvem pela mesma regra genérica em
`findSentenceIndexAtSample`: qualquer `samplePosition >= total_samples` resolve para a última frase.
Um listener explícito de `ended` ainda é adicionado (forçando `samplePosition = total_samples`) por
determinismo e testabilidade direta de FR-010.

**Rationale**: em jsdom, `timeupdate` não dispara sozinho — os testes despacham eventos sintéticos —
então depender só do último `timeupdate` implícito seria frágil de testar; um listener dedicado de
`ended` torna o comportamento determinístico e diretamente testável.

## Decisão 7 — Dependência de ordem entre `player.ts` e `readingView.ts` no `loadedmetadata`

**Decision**: `readingView` deve ser criado e ter seus listeners registrados no `<audio>` **depois**
de `player` em `main.ts`.

**Rationale**: `player.ts` já reposiciona `audio.currentTime` para a posição salva dentro do seu
próprio handler de `loadedmetadata`. Como `addEventListener` dispara na ordem de registro para o
mesmo evento/alvo, o handler de `loadedmetadata` de `readingView` só vê `audio.currentTime` já
corrigido se for registrado depois do de `player`. Essa dependência é implícita na plataforma (DOM)
e por isso precisa ficar documentada explicitamente (Princípio X), com um comentário no código
apontando para esta decisão, para não ser quebrada por uma reordenação futura em `main.ts`.

**Alternatives considered**:
- Fazer `readingView` ler a posição salva diretamente de `study.progress` em vez de depender de
  `audio.currentTime` no `loadedmetadata` — não usado como abordagem principal porque o destaque
  inicial já precisa calcular a partir de `study.progress` de qualquer forma antes mesmo de qualquer
  evento disparar (ver `data-model.md`); o listener de `loadedmetadata` é apenas uma re-sincronização
  de segurança caso o navegador ajuste a posição de forma assíncrona entre o `open()` e o evento.
