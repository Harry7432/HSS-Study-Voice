# Implementation Plan: Migração do frontend para o Design System HSS Music

**Branch**: `master` | **Date**: 2026-10-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-hss-music-design-system/spec.md`

## Summary

Fazer o frontend Study Voice (`frontend/`) consumir o design system HSS Music como única fonte
visual — tokens e componentes vendorizados em `frontend/src/hss/`, regras de uso documentadas em
`DESIGN.md` — em vez de qualquer estilo próprio. A maior parte deste trabalho já está implementada e
commitada (`3619557`, `923dd1d`); esta é a documentação retroativa exigida pelo Princípio I, mais o
fechamento dos itens que ficaram pendentes de verificação: comportamento de `is-playing` em
pausa/conclusão, tema claro e largura mobile estreita, e a causa raiz do `UnicodeDecodeError`/`cp1252`
no servidor de desenvolvimento. Nenhuma mudança de dados, API ou pipeline de síntese.

## Technical Context

**Language/Version**: TypeScript estrito, compilado/servido via Vite (sem mudança de stack desta
fase); CSS puro para os tokens/componentes (`frontend/src/hss/*.css`).

**Primary Dependencies**: nenhuma dependência nova de runtime ou build — reaproveita o workspace
`frontend/` da Fase 5 (Vite, Vitest, `fake-indexeddb`, Playwright, `idb`). Os únicos arquivos novos de
produto são os CSS/README do design system vendorizado.

**Storage**: inalterado (IndexedDB `hss-study-library`, Fase 5).

**Testing**: a suíte já existente (`frontend/tests/unit/*`, 8 arquivos, 71 testes Vitest; 1 arquivo
`frontend/e2e/library.spec.ts`, 2 testes Playwright) cobre o comportamento funcional da biblioteca e
continua verde após a migração visual (confirmado nesta sessão: `npm run build`, `npm test` e
`npm run test:e2e` passam). Os itens pendentes desta fase (tema claro, largura mobile, `is-playing`
em pausa/conclusão) exigem verificação manual registrada em `quickstart.md`, já que são
comportamentos visuais/de integração de eventos do DOM sem asserção automatizada hoje.

**Target Platform**: navegador desktop moderno e largura mobile estreita (≤390px), temas `dark`
(padrão) e `light`.

**Project Type**: aplicação web cliente já existente (`frontend/`) — esta fase não adiciona workspace
novo, apenas uma pasta de assets de design (`frontend/src/hss/`) dentro dele.

**Performance Goals**: nenhuma meta nova; a troca de estilos não deve alterar o comportamento de
carregamento/renderização já estabelecido na Fase 5.

**Constraints**: nenhum valor de cor/fonte/raio/sombra fora de `frontend/src/hss/tokens.css` (FR-001);
no máximo um acento de cor por tela (FR-003); `<audio controls>` nativo mantido nesta fase (FR-008);
nenhuma mudança de backend além da eventual correção de codificação do `cp1252` (FR-011); nenhum
token/componente novo inventado para preencher lacunas do design system (FR-010).

**Scale/Scope**: a mesma aplicação de usuário único por navegador da Fase 5; mudança é
inteiramente visual/markup, concentrada em `frontend/index.html`, `frontend/src/styles.css`,
`frontend/src/main.ts`, `frontend/src/ui/libraryView.ts` e a pasta nova `frontend/src/hss/`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Result |
|-----------|------|--------|
| I. Spec-Driven Development | O código desta fase já existia quando a documentação começou; por decisão explícita do usuário, o fluxo `specify → clarify → plan → tasks` foi executado retroativamente (mesmo padrão de transparência usado em `003-local-study-library/tasks.md` para sua "Phase 6" interna), e os itens ainda não implementados/verificados (FR-006, FR-009, SC-005) seguem o fluxo normal daqui em diante | PASS |
| II. Local-First Ownership | Nenhuma mudança de armazenamento ou propriedade de dados; a fase é puramente visual | PASS (N/A) |
| III. Simple and Modular Backend | O backend não é alterado por esta fase, exceto a eventual correção pontual de codificação (`encoding="utf-8"`) em duas chamadas de `subprocess.run` já existentes — não introduz módulo, serviço ou infraestrutura nova | PASS |
| IV. Mandatory Tests | A suíte unitária (71 testes) e e2e (2 testes) existentes permanece verde após a migração; os itens visuais pendentes (tema/mobile/`is-playing`) ganham verificação manual documentada em `quickstart.md`, já que não há asserção automatizada de CSS computado nesta stack | PASS |
| V. Incremental Pipeline Compatibility | `normalization → chunking → TTS → WAV → concatenation → MP3` não é tocado; a correção de `cp1252` prevista altera apenas como a saída de texto do subprocesso é decodificada, não o pipeline em si | PASS |
| VI. Security by Default | Nenhuma superfície de entrada nova; a migração não introduz manipulação de dados externos | PASS (N/A) |
| VII. No Overengineering | Nenhum token, componente, framework ou dependência nova é introduzido; lacunas do design system (sucesso, botão destrutivo, input) são resolvidas reaproveitando primitivas existentes, não inventando novas (FR-010, research.md §5) | PASS |
| VIII. Phase-Bounded Delivery | Escopo restrito à camada visual do frontend; o player customizado `hss-player` (User Story 4) é explicitamente adiado para uma fase futura, não misturado a esta | PASS |
| IX. Architecture Ready for Evolution | `frontend/src/hss/` isola os tokens/componentes do design system do restante do app; trocar ou atualizar o design system no futuro não exige reescrever `styles.css`/`main.ts`, apenas os dois arquivos vendorizados | PASS |
| X. Explicit Technical Decisions | Todas as decisões (vendorização do design system, `is-playing` derivado de estudo-aberto, player nativo mantido, tema claro sem seletor, lacunas reaproveitadas, causa raiz do `cp1252`) documentadas em `research.md` | PASS |

Nenhuma violação não justificada. `Complexity Tracking` não é necessário.

## Project Structure

### Documentation (this feature)

```text
specs/004-hss-music-design-system/
├── spec.md               # Este spec
├── checklists/
│   └── requirements.md
├── plan.md                # Este arquivo
├── research.md            # Fase 0: decisões já tomadas + causa raiz do cp1252
├── quickstart.md           # Fase 1: guia de validação (build/testes + verificação manual)
└── tasks.md                # Será criado por /speckit.tasks
```

Esta feature **não define** `data-model.md` nem `contracts/`: não há dado novo nem interface pública
nova — `DESIGN.md`, na raiz do repositório, já cumpre o papel de contrato visual que `contracts/`
cumpre em `002-study-audio-api` e `003-local-study-library`.

### Source Code (repository root)

```text
backend/                               # Inalterado por esta fase (Fases 1-4), exceto eventual
                                        # correção pontual de encoding (research.md §6)

frontend/
├── index.html                         # lang="pt-BR", data-theme="dark", hss-surface, fontes
├── DESIGN.md                          # (raiz do repo) regras de uso do design system
├── src/
│   ├── styles.css                     # Só importa hss/tokens.css + hss/bundle.css, resto é layout
│   ├── main.ts                        # Usa hss-btn/hss-panel; monta player nativo + biblioteca
│   ├── hss/                           # NOVO nesta fase: design system vendorizado
│   │   ├── tokens.css                 # Tokens dark/light + tipografia/espaçamento/raio
│   │   ├── tokens.json
│   │   ├── bundle.css                 # Classes hss-btn/hss-chip/hss-row/hss-player/hss-menu/...
│   │   ├── README.md
│   │   └── components/                # Um README.md + preview.html por componente
│   └── ui/
│       ├── libraryView.ts             # hss-row + is-playing + glifo de reprodução
│       └── player.ts                  # <audio controls> nativo; isOpen() alimenta is-playing
└── (demais arquivos inalterados desde a Fase 5)
```

**Structure Decision**: nenhuma pasta nova de domínio — apenas `frontend/src/hss/` como pasta de
assets de design vendorizados, consumida por `styles.css` e pelas classes usadas em `main.ts`/
`libraryView.ts`. A separação `library/`/`api/`/`application/`/`ui/` estabelecida na Fase 5
permanece intacta; esta fase só altera `ui/` (markup/classes) e `styles.css`.

## Phase 0: Research Summary

As decisões consolidadas em [research.md](research.md):

- Tokens e componentes do HSS Music vendorizados em `frontend/src/hss/`, importados uma única vez.
- `is-playing`/glifo derivados de `player.isOpen(studyId)` (estudo carregado), recalculados apenas
  quando `libraryView.refresh()` roda — cobre corretamente "abrir outro estudo" e "remover", mas não
  "pausar sem trocar" nem, de fato, "concluir" (o glifo permanece ativo mesmo após `ended`). Vira
  item de correção em `tasks.md`.
- `<audio controls>` nativo mantido nesta fase; `hss-player` customizado adiado (User Story 4).
- Tema claro definido em `tokens.css`, sem seletor de interface para o usuário alternar — fora de
  escopo ligar esse controle agora.
- Três lacunas do design system (sucesso, botão destrutivo, input) resolvidas reaproveitando tokens
  existentes, nunca inventando novos.
- Causa raiz do `UnicodeDecodeError`/`cp1252` identificada: `subprocess.run(..., text=True)` sem
  `encoding="utf-8"` em `concatenator.py`/`exporter.py`, decodificando a saída UTF-8 do FFmpeg como
  `cp1252` (locale padrão do Windows). Correção mínima proposta, não aplicada nesta sessão de
  documentação.

## Phase 1: Design Summary

- Não há `data-model.md`: nenhum dado novo é introduzido ou alterado.
- Não há `contracts/`: `DESIGN.md` já é o contrato visual consumido por este frontend; os
  `README.md`/`preview.html` de cada componente em `frontend/src/hss/components/` documentam o uso
  de cada classe.
- [quickstart.md](quickstart.md) define: (1) verificação automatizada (`npm run build`, `npm test`,
  `npm run test:e2e`); (2) roteiro manual para tema claro e largura mobile estreita; (3) roteiro
  manual para os três gatilhos de `is-playing` (pausar, concluir, trocar de estudo); (4) passo de
  reprodução do `cp1252` e critério de aceite da correção.
- Nenhuma mudança de schema de banco local, de contrato HTTP existente, ou de comportamento do
  pipeline de síntese.

## Post-Design Constitution Check

Todos os gates continuam PASS. O design não introduz nenhuma dependência, serviço ou infraestrutura
nova; a única mudança potencial de código de produto fora de `frontend/` é a correção pontual de
codificação no backend (research.md §6), que é aditiva, reversível e não toca no pipeline de síntese.
