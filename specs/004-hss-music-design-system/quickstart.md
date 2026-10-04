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

## 2. Verificação manual — tema claro

1. Com o app rodando (`npm run dev`), abrir o DevTools e executar:
   `document.documentElement.dataset.theme = "light"`.
2. Percorrer: mastro, mesa de criação (formulário + player), arquivo local (lista + detalhes de um
   estudo aberto).
3. Confirmar: painéis usam divisórias (`--border-subtle`), não camadas cinza; nenhum texto perde
   contraste; `--accent-text` permanece legível sobre `--bg-panel`/`--bg-raised` claros.
4. Voltar para `"dark"` ao final.

- [ ] Resultado a registrar aqui após a verificação (`tasks.md` T0XX).

## 3. Verificação manual — largura mobile estreita

1. Redimensionar a janela/DevTools para ≤390px de largura.
2. Confirmar que o breakpoint de 820px em `frontend/src/styles.css:246` já reorganiza `.workspace`
   em uma coluna; verificar que nenhum elemento (botões, linhas da biblioteca, painel de detalhes)
   é cortado ou força rolagem horizontal.

- [ ] Resultado a registrar aqui após a verificação (`tasks.md` T0XX).

## 4. Verificação manual — `is-playing` nos três gatilhos

1. Gerar ou abrir um estudo salvo → confirmar `hss-row.is-playing` + glifo na linha correspondente.
2. **Pausar** sem trocar de estudo → conferir se o glifo/`is-playing` permanecem (comportamento atual
   esperado, por `research.md` §2) ou se foram corrigidos para sumir.
3. Deixar a reprodução **concluir** → conferir se o glifo/`is-playing` somem ou se permanecem ao lado
   do rótulo "Concluído" (comportamento atual esperado é permanecerem, por `research.md` §2).
4. **Abrir outro estudo** → confirmar que o destaque migra corretamente para a nova linha (este
   gatilho já funciona hoje).

- [ ] Resultado a registrar aqui após a verificação, com decisão de corrigir ou aceitar cada caso
  (`tasks.md` T0XX).

## 5. Investigação `cp1252`

1. Rodar `npm run test:e2e` (ou gerar um estudo manualmente com o backend local) e observar o log do
   servidor Python.
2. Confirmar a origem exata (arquivo:linha) do traceback — já localizada em `research.md` §6:
   `backend/app/services/audio/concatenator.py:101-106` e
   `backend/app/services/audio/exporter.py:93-98`.
3. Se a correção (`encoding="utf-8", errors="replace"`) for aplicada, repetir o passo 1 e confirmar
   que o traceback não aparece mais, sem alterar o arquivo MP3 final nem os testes verdes.

- [ ] Resultado a registrar aqui após a correção ou decisão de adiá-la (`tasks.md` T0XX).

### Rastreabilidade dos requisitos

| Requisitos | Evidência | Estado |
|------------|-----------|--------|
| FR-001–FR-005, FR-007, FR-008 | Inspeção de `styles.css`/`index.html`/`main.ts`/`libraryView.ts`/`bundle.css` nesta sessão | PASS |
| FR-006 | `research.md` §2 — comportamento atual mapeado; correção pendente | PENDENTE |
| FR-009 | Seções 2–3 deste quickstart | PENDENTE |
| FR-010 | `research.md` §5 — três lacunas documentadas e resolvidas por reaproveitamento | PASS |
| FR-011 | `research.md` §6 — causa raiz localizada; correção proposta, não aplicada nesta sessão | PENDENTE |
| SC-001 | Inspeção de `styles.css` (só `var(--...)`, dois `@import`) | PASS |
| SC-002 | Seções 2–3 deste quickstart | PENDENTE |
| SC-003 | Seção 4 deste quickstart | PENDENTE |
| SC-004 | `npm run build`/`npm test`/`npm run test:e2e` executados nesta sessão | PASS |
| SC-005 | Seção 5 deste quickstart | PENDENTE |

### Gates constitucionais

Os princípios I–X permanecem atendidos conforme `plan.md`. Esta sessão documentou retroativamente o
que já estava implementado (Princípio I) e deixou registrado, sem implementar, o que ainda depende de
verificação manual ou de uma correção pontual de backend (FR-006, FR-009, FR-011/SC-005) — essas
ficam como tarefas abertas em `tasks.md`, não como trabalho desta etapa de documentação.
