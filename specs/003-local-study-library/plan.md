# Implementation Plan: Biblioteca local-first de estudos

**Branch**: `master` | **Date**: 2026-10-03 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-local-study-library/spec.md`

## Summary

Introduzir um novo workspace de cliente (`frontend/`, TypeScript + Vite, sem framework de UI) que
baixa, valida em runtime e armazena localmente, no navegador (IndexedDB), o áudio e a timeline de
cada estudo gerado pela API já existente da Fase 4. Metadados/progresso e assets pesados ficam em
stores separados para que a listagem nunca carregue MP3/timeline, mas salvamento e remoção continuam
atômicos por transação multi-store. O backend não é alterado; em desenvolvimento, o Vite encaminha
`/api` para ele. Toda a complexidade nova fica isolada no workspace frontend.

## Technical Context

**Language/Version**: TypeScript (strict), compilado/servido via Vite; alvo de execução é o
navegador (ES2020+).

**Primary Dependencies**: Vite (build/dev server e proxy `/api` em desenvolvimento); `idb` (wrapper
fino baseado em Promises sobre IndexedDB, ver `research.md` §2) — única dependência de runtime
nova. A validação runtime usa type guards/assertion functions locais, sem biblioteca adicional.
Nenhum framework de UI (React/Vue/etc.) nesta fase. Backend: nenhuma dependência nova.

**Storage**: IndexedDB do navegador (banco `hss-study-library`, stores `studyMetadata` e
`studyAssets`); sem armazenamento novo no backend/VPS. Uma transação multi-store salva ou remove
as duas partes atomicamente. Ver `data-model.md`.

**Testing**: Vitest + `fake-indexeddb` para validators, cliente HTTP, coordenador de criação e
`libraryService`; Playwright para o fluxo real gerar → salvar → listar → recarregar → retomar →
remover, contra o backend da Fase 4 através do proxy Vite.

**Target Platform**: Navegador desktop moderno com suporte a IndexedDB, rodando no dispositivo do
próprio usuário; usa `/api` relativo, via proxy Vite no desenvolvimento e mesma origem na
implantação.

**Project Type**: Aplicação web cliente (frontend) consumindo uma API backend já existente — a
primeira peça de frontend do projeto (o backend permanece um serviço separado, inalterado).

**Performance Goals**: Listagem deve renderizar sem ler `studyAssets`, mesmo com dezenas a poucas
centenas de estudos salvos localmente e sem chamada de rede — resolvido consultando apenas
`studyMetadata` pelo índice `createdAt`. Sem meta de throughput.

**Constraints**: Deve funcionar offline para estudos já salvos (FR-001, FR-006, SC-004); falha do
armazenamento local não bloqueia reprodução direta (FR-012, SC-006); nenhum endpoint novo no backend
(FR-013); texto original completo não é persistido como metadado, embora a timeline retenha as
frases normalizadas exigidas pelo contrato (FR-014); respostas HTTP são validadas em runtime antes
do uso/persistência (FR-015); nenhuma escrita começa antes de áudio e timeline estarem completos e
válidos; retomada respeita FR-007/SC-002.

**Scale/Scope**: Usuário único por navegador/dispositivo, sem sincronização; um `libraryService` com
cinco operações, um coordenador do fluxo criar/baixar/validar/salvar e uma UI mínima.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Result |
|-----------|------|--------|
| I. Spec-Driven Development | Spec aprovado com sessão de `/speckit.clarify` concluída (decisão arquitetural + 3 perguntas resolvidas); stack do plano confirmada com o usuário antes do Technical Context | PASS |
| II. Local-First Ownership | Esta fase corrige o ponto mais sensível do princípio: o áudio/timeline passam a residir na cópia local do usuário (IndexedDB do navegador), não apenas no backend; o backend continua podendo tratar sua cópia como temporária sem perda de acesso do usuário (FR-001, SC-004) | PASS |
| III. Simple and Modular Backend | O backend não é alterado por esta fase (FR-013) — gate não se aplica a nenhuma mudança nova | PASS (N/A) |
| IV. Mandatory Tests | Plano exige testes unitários nos seams públicos de validators, cliente HTTP, coordenador e `libraryService`, mais integração real Playwright; a falha parcial de download prova ausência de persistência e a suíte do backend é preservada | PASS (a confirmar na execução) |
| V. Incremental Pipeline Compatibility | `normalization → chunking → TTS → WAV → concatenation → MP3` não é tocado; esta fase apenas consome a saída já existente da Fase 4 via HTTP | PASS |
| VI. Security by Default | Metadados retêm apenas rótulo curto; frases normalizadas permanecem somente na timeline contratual; criação, áudio e timeline são validados em runtime antes do uso/persistência (FR-015); nenhum dado sensível é logado | PASS |
| VII. No Overengineering | Uma única dependência nova (`idb`), nenhum framework de UI e apenas dois stores diretamente exigidos para separar a listagem leve dos assets pesados; nenhuma expulsão automática ou sincronização | PASS |
| VIII. Phase-Bounded Delivery | Escopo restrito a armazenamento/listagem/leitura/exclusão/progresso no cliente; exclusões explícitas (sem mudança de backend, sem sincronização, sem paginação) documentadas no spec e reiteradas aqui | PASS |
| IX. Architecture Ready for Evolution | `libraryService` isola a UI do mecanismo de armazenamento (IndexedDB via `idb`); trocar o mecanismo de persistência no futuro não exige mudar quem o consome (contrato em `contracts/library-service.interface.ts`) | PASS |
| X. Explicit Technical Decisions | Todas as decisões arquiteturalmente relevantes (stack do cliente, biblioteca de acesso a IndexedDB, esquema de armazenamento, rótulo automático, estratégia de progresso, tratamento de indisponibilidade, atomicidade) documentadas em `research.md` | PASS |

Nenhuma violação não justificada. `Complexity Tracking` não é necessário.

## Project Structure

### Documentation (this feature)

```text
specs/003-local-study-library/
├── plan.md              # Este arquivo
├── research.md          # Fase 0: decisões técnicas
├── data-model.md         # Fase 1: esquema de armazenamento local
├── quickstart.md         # Fase 1: guia de validação
├── contracts/            # Fase 1: contrato interno do libraryService
│   ├── README.md
│   ├── library-service.interface.ts
│   ├── study-metadata.schema.json
│   └── study-assets.schema.json
└── tasks.md              # Será criado por /speckit.tasks
```

### Source Code (repository root)

```text
backend/                               # Inalterado por esta fase (Fases 1-4)

frontend/                              # Novo workspace desta fase
├── package.json
├── vite.config.ts
├── tsconfig.json
├── src/
│   ├── main.ts                        # Monta a UI mínima da biblioteca
│   ├── api/
│   │   ├── studiesClient.ts           # Cliente HTTP fino para os 3 endpoints já existentes da Fase 4
│   │   └── validators.ts              # Validação runtime das respostas de criação, áudio e timeline
│   ├── application/
│   │   └── createStudy.ts             # Coordena criar → baixar → validar → salvar sem estado parcial
│   ├── library/
│   │   ├── db.ts                      # Banco com stores studyMetadata e studyAssets
│   │   ├── libraryService.ts          # saveStudy/listStudies/getStudy/updateProgress/removeStudy
│   │   ├── labels.ts                  # Derivação do rótulo automático (research.md §4)
│   │   └── types.ts                   # SavedStudy, Progress, LibraryUnavailableError
│   └── ui/
│       ├── libraryView.ts             # Lista + detalhes (User Stories 1 e 4)
│       └── player.ts                  # Reprodução + rastreio de progresso (User Story 2) + remoção (User Story 3)
├── tests/
│   └── unit/
│       ├── labels.test.ts
│       ├── validators.test.ts
│       ├── studiesClient.test.ts
│       ├── createStudy.test.ts
│       └── libraryService.test.ts
└── e2e/
    └── library.spec.ts                # Playwright, fluxo ponta a ponta contra o backend real
```

**Structure Decision**: backend permanece exatamente como está; esta fase adiciona um workspace
irmão `frontend/` com sua própria configuração de build/teste. Dentro dele, `library/` concentra
toda a lógica de domínio (testável sem DOM/navegador via `fake-indexeddb`), `api/` isola o acesso
HTTP à Fase 4, e `ui/` é a única camada que depende do DOM — mantendo o mesmo espírito de
separação de responsabilidades já usado no backend (`StudyService` isolado do router FastAPI). O
coordenador de aplicação torna testável a regra de que falha parcial de download nunca chama
`saveStudy`.

## Phase 0: Research Summary

As decisões consolidadas em [research.md](research.md) resolvem todos os pontos técnicos:

- Stack confirmada com o usuário: TypeScript + Vite, sem framework de UI.
- `idb` como única dependência nova, evitando o boilerplate de callbacks do IndexedDB cru sem
  trazer uma camada de query pesada como Dexie.
- Dois object stores: `studyMetadata` (índice `createdAt`, progresso embutido) e `studyAssets`
  (áudio/timeline), atualizados atomicamente por transação multi-store.
- Rótulo automático: primeiros 80 caracteres do texto original, cortado em limite de palavra.
- Progresso é persistido em `pause`/`seeked`/a cada 5 segundos/`visibilitychange`, com tolerância
  máxima de 1 segundo após eventos explícitos e de 5 segundos durante reprodução ativa visível.
- Falha de armazenamento local vira um único tipo de erro (`LibraryUnavailableError`), tratado pela
  UI sem afetar a geração/reprodução direta via API.
- Salvar e remover um estudo usam uma única transação IndexedDB sobre os dois stores.
- Respostas HTTP são validadas em runtime por validators locais antes de qualquer persistência.
- Vite encaminha `/api` ao backend em desenvolvimento; produção usa mesma origem.
- Testes: Vitest nos seams públicos e Playwright para integração real.

## Phase 1: Design Summary

- [data-model.md](data-model.md) define `StudyMetadata` (com `progress`), `StudyAssets`, a composição
  `SavedStudyDetail`, os índices e as transações multi-store.
- [contracts/](contracts/) define a interface pública do `libraryService`
  (`library-service.interface.ts`) e os formatos persistidos
  (`study-metadata.schema.json`/`study-assets.schema.json`); reaproveita o contrato de timeline já publicado em
  `001-text-audio-timeline` e os três endpoints já publicados em `002-study-audio-api`, sem
  duplicá-los nem alterá-los.
- [quickstart.md](quickstart.md) define validação unitária (Vitest + `fake-indexeddb`), de
  integração real (Playwright + backend real) e do caso de armazenamento local indisponível.
- Nenhuma mudança de schema de banco de dados do backend, de contrato HTTP existente, ou de
  comportamento do pipeline de síntese.

## Post-Design Constitution Check

Todos os gates continuam PASS. O design não introduz nenhuma mudança no backend nem infraestrutura
além de um banco IndexedDB local por navegador; a única dependência de runtime nova (`idb`) é
pequena e justificada em `research.md` §2. A complexidade adicional está limitada a um workspace de
frontend com uma camada de domínio isolada (`libraryService`) e uma UI mínima sobre ela.
