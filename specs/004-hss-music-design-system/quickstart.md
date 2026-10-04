# Quickstart: Migração do frontend para o Design System HSS Music

## Pré-requisitos

- Workspace `frontend/` instalado (`npm install`), como na Fase 5.
- Backend da Fase 4 funcional localmente (necessário apenas para `npm run test:e2e`).

## 1. Verificação automatizada

Executado nesta sessão de documentação, a partir de `frontend/`:

```bash
npm run build     # tsc --noEmit && vite build
npm test          # vitest run
npm run test:e2e  # playwright test (sobe backend real + vite dev via proxy)
```

**Resultado observado em 2026-10-04**:

- `npm run build`: sucesso, sem erros de TypeScript, bundle gerado em `dist/`.
- `npm test`: **8 arquivos de teste, 71 testes, todos passando** (`labels`, `validators`,
  `studiesClient`, `createStudy`, `player`, `libraryView`, `main`, `libraryService`).
- `npm run test:e2e`: **2 testes passando** em `e2e/library.spec.ts`. O log do backend mostrou o
  traceback de `UnicodeDecodeError`/`cp1252` descrito em `research.md` §6 — não falhou nenhum teste,
  mas confirma que o problema é reproduzível a cada geração de áudio real.

**Re-execução em 2026-10-04 (sessão T012–T014/T020), após T011 e T016**:

- `npm run build`: sucesso, sem erros de TypeScript.
- `npm test`: **8 arquivos de teste, 73 testes, todos passando** (os 2 testes novos de T011 em
  `player.test.ts`/`main.test.ts`, sem regressão nos demais).
- `npm run test:e2e`: **2 testes passando** novamente; o log do backend **não** mostrou o traceback de
  `UnicodeDecodeError`/`cp1252` desta vez — consistente com a correção de T016.

## 2. Verificação manual — tema claro

1. Com o app rodando (`npm run dev`), abrir o DevTools e executar:
   `document.documentElement.dataset.theme = "light"`.
2. Percorrer: mastro, mesa de criação (formulário + player), arquivo local (lista + detalhes de um
   estudo aberto).
3. Confirmar: painéis usam divisórias (`--border-subtle`), não camadas cinza; nenhum texto perde
   contraste; `--accent-text` permanece legível sobre `--bg-panel`/`--bg-raised` claros.
4. Voltar para `"dark"` ao final.

- [ ] Resultado a registrar aqui após a verificação (`tasks.md` T012). **Status em 2026-10-04**: a
  inspeção visual real acima **não foi feita nesta sessão** (o Chrome conectado não tem acesso de rede
  ao `localhost` deste ambiente, mesma limitação de T009). Em vez disso, foi feita uma validação
  estática: paleta `[data-theme="light"]` completa e independente em `tokens.css`, divisórias (não
  camadas cinza) confirmadas em `bundle.css:102-106`, e contraste calculado (WCAG, luminância relativa)
  de `--text-secondary`, `--accent-text` e `--danger` sobre `--bg-panel`/`--bg-raised` claros, todos
  ≥6.5:1 (acima do mínimo AA de 4.5:1). Nenhum problema encontrado por essa via, mas a conferência
  visual real do roteiro acima segue pendente para quem tiver acesso direto ao `npm run dev`.

## 3. Verificação manual — largura mobile estreita

1. Redimensionar a janela/DevTools para ≤390px de largura.
2. Confirmar que o breakpoint de 820px em `frontend/src/styles.css:246` já reorganiza `.workspace`
   em uma coluna; verificar que nenhum elemento (botões, linhas da biblioteca, painel de detalhes)
   é cortado ou força rolagem horizontal.

- [ ] Resultado a registrar aqui após a verificação (`tasks.md` T013). **Status em 2026-10-04**: a
  inspeção visual real acima **não foi feita nesta sessão** (mesma limitação de acesso ao `localhost`).
  Validação estática feita em seu lugar: `html`/`body.hss-surface` fixam `min-width: 320px`, abaixo do
  pior caso de 390px; o breakpoint de 820px já reorganiza `.workspace` bem antes de qualquer aperto;
  cálculo de largura disponível a 390px pela cadeia de paddings (`.shell` → `.desk`/`.archive` →
  `.study-row`) não encontra nenhuma largura mínima fixa maior que o espaço sobrando — os textos de
  `.hss-row` truncam com `text-overflow: ellipsis` em vez de forçar rolagem, `.row-actions` quebra linha
  (`flex-wrap: wrap`). Nenhum problema encontrado por essa via, mas a conferência visual real do roteiro
  acima segue pendente para quem tiver acesso direto ao `npm run dev`.

## 4. Verificação manual — `is-playing` nos três gatilhos

1. Gerar ou abrir um estudo salvo → confirmar `hss-row.is-playing` + glifo na linha correspondente.
2. **Pausar** sem trocar de estudo → conferir se o glifo/`is-playing` permanecem (comportamento atual
   esperado, por `research.md` §2) ou se foram corrigidos para sumir.
3. Deixar a reprodução **concluir** → conferir se o glifo/`is-playing` somem ou se permanecem ao lado
   do rótulo "Concluído" (comportamento atual esperado é permanecerem, por `research.md` §2).
4. **Abrir outro estudo** → confirmar que o destaque migra corretamente para a nova linha (este
   gatilho já funciona hoje).

- [x] Resultado registrado (`tasks.md` T009/T011, concluídas). Antes da correção: (a) pausar sem
  trocar de estudo não limpava `is-playing`; (b) concluir a reprodução não limpava `is-playing`; (c)
  trocar de estudo já funcionava. Decisão: corrigir (a) e (b) — `frontend/src/ui/player.ts` passou a
  expor `isPlaying()` e disparar `onPlaying`/`onPaused`, e `frontend/src/main.ts` passou a chamar
  `libraryView.refresh()` nos três eventos (`play`/`pause`/`ended`). Confirmado por
  `frontend/tests/unit/player.test.ts` e `frontend/tests/unit/main.test.ts` (73 testes verdes, sem
  regressão).

## 5. Investigação `cp1252`

1. Rodar `npm run test:e2e` (ou gerar um estudo manualmente com o backend local) e observar o log do
   servidor Python.
2. Confirmar a origem exata (arquivo:linha) do traceback — já localizada em `research.md` §6:
   `backend/app/services/audio/concatenator.py:101-106` e
   `backend/app/services/audio/exporter.py:93-98`.
3. Se a correção (`encoding="utf-8", errors="replace"`) for aplicada, repetir o passo 1 e confirmar
   que o traceback não aparece mais, sem alterar o arquivo MP3 final nem os testes verdes.

- [x] Resultado registrado (`tasks.md` T015/T016, concluídas). Causa raiz: `subprocess.run(...,
  text=True)` sem `encoding` em `backend/app/services/audio/concatenator.py:101-106` e
  `backend/app/services/audio/exporter.py:93-98`, decodificando a saída UTF-8 do FFmpeg como `cp1252`.
  Correção (`encoding="utf-8", errors="replace"`) aplicada e confirmada nesta sessão: `npm run test:e2e`
  (2 testes Playwright verdes) rodou de novo e o log do backend não mostrou o traceback de
  `UnicodeDecodeError`/`cp1252`.

### Rastreabilidade dos requisitos

| Requisitos | Evidência | Estado |
|------------|-----------|--------|
| FR-001–FR-005, FR-007, FR-008 | Inspeção de `styles.css`/`index.html`/`main.ts`/`libraryView.ts`/`bundle.css` nesta sessão | PASS |
| FR-006 | `tasks.md` T009/T011 — comportamento mapeado e corrigido (`player.ts` expõe `isPlaying()`/`onPlaying`/`onPaused`; `main.ts` chama `libraryView.refresh()` nos três gatilhos); confirmado por `player.test.ts`/`main.test.ts` | PASS |
| FR-009 | `tasks.md` T012/T013 — validação **estática** nesta sessão (tokens, box model, contraste) sem problema encontrado; inspeção visual real em navegador (roteiro `quickstart.md` §2–3) ainda não feita — limitação de acesso de rede do Chrome conectado a esta sessão | PARCIAL (estática PASS / visual PENDENTE) |
| FR-010 | `research.md` §5 — três lacunas documentadas e resolvidas por reaproveitamento | PASS |
| FR-011 | `research.md` §6 + `tasks.md` T016 — causa raiz localizada e corrigida (`encoding="utf-8", errors="replace"` em `concatenator.py`/`exporter.py`); `npm run test:e2e` reexecutado nesta sessão sem o traceback | PASS |
| SC-001 | Inspeção de `styles.css` (só `var(--...)`, dois `@import`) | PASS |
| SC-002 | Seções 2–3 deste quickstart — mesma situação de FR-009 (estática PASS, visual PENDENTE) | PARCIAL (estática PASS / visual PENDENTE) |
| SC-003 | Seção 4 deste quickstart — `tasks.md` T009/T011, confirmado por `player.test.ts`/`main.test.ts` (73 testes verdes) | PASS |
| SC-004 | `npm run build`/`npm test`/`npm run test:e2e` executados nesta sessão (73 testes unitários + 2 e2e, sem regressão) | PASS |
| SC-005 | Seção 5 deste quickstart — `tasks.md` T016, confirmado por reexecução de `npm run test:e2e` sem o traceback nesta sessão | PASS |

### Gates constitucionais

Os princípios I–X permanecem atendidos conforme `plan.md`. Esta sessão documentou retroativamente o
que já estava implementado (Princípio I) e deixou registrado, sem implementar, o que ainda depende de
verificação manual ou de uma correção pontual de backend (FR-006, FR-009, FR-011/SC-005) — essas
ficam como tarefas abertas em `tasks.md`, não como trabalho desta etapa de documentação.
