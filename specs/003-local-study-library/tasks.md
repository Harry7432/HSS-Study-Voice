# Tasks: Biblioteca local-first de estudos

**Input**: Design documents from `/specs/003-local-study-library/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: obrigatórios pelo spec e pelo Princípio IV. Em cada story, escrever e executar os testes
RED antes da implementação GREEN correspondente.

**Organization**: tarefas agrupadas por user story. Todo código novo fica em `frontend/`; o
`backend/` é apenas executado para regressão e integração, nunca modificado.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: arquivo diferente e nenhuma dependência incompleta
- **[Story]**: `US1`, `US2`, `US3` ou `US4`
- Caminhos são relativos à raiz do repositório

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: criar o workspace frontend e suas ferramentas.

- [X] T001 Criar `frontend/package.json` com scripts `dev`, `build`, `test` e `test:e2e`, dependência de runtime `idb` e dependências de desenvolvimento TypeScript, Vite, Vitest, `fake-indexeddb` e Playwright
- [X] T002 [P] Configurar TypeScript estrito e Vite em `frontend/tsconfig.json` e `frontend/vite.config.ts`, incluindo proxy de desenvolvimento `/api` para `http://127.0.0.1:8000` com caminho preservado
- [X] T003 [P] Configurar Playwright e os servidores frontend/backend em `frontend/playwright.config.ts`, fazendo o navegador acessar a API exclusivamente pelo proxy Vite
- [X] T004 [P] Criar documento raiz e estilos mínimos responsivos/acessíveis em `frontend/index.html` e `frontend/src/styles.css`

**Checkpoint**: workspace instalável e proxy same-origin de desenvolvimento definido.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: definir contratos, banco e infraestrutura de testes compartilhados.

**CRITICAL**: nenhuma user story começa antes desta fase.

- [X] T005 [P] Implementar os tipos `StudyCreationResult`, `TimelineDocument`, `StudyMetadata`, `StudyAssets`, `SavedStudySummary`, `SavedStudyDetail`, `Progress`, `LibraryService` e `LibraryUnavailableError` em `frontend/src/library/types.ts`, com `saveStudy(result, label: string)` obrigatório e sem campo de texto original
- [X] T006 Implementar `hss-study-library` v1 em `frontend/src/library/db.ts` com stores `studyMetadata` e `studyAssets`, ambos `keyPath: "studyId"`, e índice não único `createdAt` somente em `studyMetadata`
- [X] T007 [P] Configurar Vitest, `fake-indexeddb`, limpeza entre testes, relógio controlável e fixtures válidas em `frontend/vitest.config.ts` e `frontend/tests/setup.ts`

**Checkpoint**: tipos, dois stores e harness de testes disponíveis.

---

## Phase 3: User Story 1 - Ver a biblioteca de estudos salvos localmente (Priority: P1) MVP

**Goal**: criar, validar, baixar e salvar um estudo completo; listar somente metadados locais, sem
rede e sem carregar Blob/timeline.

**Independent Test**: gerar três estudos, confirmar salvamento de metadata+assets, desligar o backend
e listar os três em ordem decrescente; biblioteca nova mostra estado vazio. Se áudio ou timeline
falhar/for inválido, nenhum store recebe entrada.

### Tests for User Story 1

> Executar T008–T012 e confirmar RED antes de T013–T019.

- [X] T008 [P] [US1] Criar testes de rótulo em `frontend/tests/unit/labels.test.ts`: trim/espaços normalizados, manual obrigatório após derivação, rejeição manual acima de 80 caracteres, fallback automático para omitido/vazio, palavra completa e `…` incluída no máximo final de 80
- [X] T009 [P] [US1] Criar testes dos validators runtime em `frontend/tests/unit/validators.test.ts`: criação com `chunks_count >= 1`, `duration_seconds >= 0`, `file_size_bytes >= 1` inteiro e `processing_time_seconds >= 0`, rejeitando shape/ID/limites inválidos; áudio `audio/mpeg` não vazio; timeline-v1 válida e rejeições de versão, SHA-256, sample rate, amostras e intervalos inválidos
- [X] T010 [P] [US1] Criar testes do cliente HTTP em `frontend/tests/unit/studiesClient.test.ts`, exigindo URLs relativas `/api/v1/...`, mapeamento `snake_case`→`camelCase`, execução dos validators e propagação de HTTP/contrato inválido
- [X] T011 [P] [US1] Criar testes de `saveStudy()`/`listStudies()` e erro de listagem em `frontend/tests/unit/libraryService.test.ts` e `frontend/tests/unit/libraryView.test.ts`: transação atômica nos dois stores, progresso inicial, label obrigatório 1–80, ordem reversa, lista vazia, leitura exclusiva de `studyMetadata`, ausência de texto original nos metadados, `LibraryUnavailableError` e aviso claro sem substituir a página por erro técnico
- [X] T012 [P] [US1] Criar testes do coordenador e integração da criação em `frontend/tests/unit/createStudy.test.ts` e `frontend/tests/unit/main.test.ts`: derivar label antes do serviço, só chamar `saveStudy` após bundle válido, não persistir nas duas ordens de falha parcial e, quando apenas IndexedDB falhar, manter Blob reproduzível e mostrar aviso claro

### Implementation for User Story 1

- [X] T013 [P] [US1] Implementar normalização, validação manual e derivação automática de rótulo em `frontend/src/library/labels.ts`, garantindo resultado obrigatório de 1–80 caracteres e nunca retornando o texto completo
- [X] T014 [P] [US1] Implementar assertion functions de criação, áudio e timeline-v1 em `frontend/src/api/validators.ts`, sem dependência runtime adicional
- [X] T015 [US1] Implementar cliente dos três endpoints existentes em `frontend/src/api/studiesClient.ts`, usando apenas `/api/v1/...` relativo e retornando dados tipados somente após T014 validar cada resposta
- [X] T016 [P] [US1] Implementar `saveStudy()` e `listStudies()` em `frontend/src/library/libraryService.ts`: uma transação `readwrite` sobre os dois stores por salvamento, índice reverso apenas em `studyMetadata` e tradução uniforme de falhas para `LibraryUnavailableError`
- [X] T017 [US1] Implementar criar → baixar ambos → validar → derivar label → salvar em `frontend/src/application/createStudy.ts`, sem iniciar persistência até o bundle completo e preservando o Blob para reprodução quando somente `saveStudy` falhar
- [X] T018 [US1] Implementar estado vazio, lista de summaries e aviso claro de falha de listagem em `frontend/src/ui/libraryView.ts`, sem acessar assets nem expor erro técnico
- [X] T019 [US1] Integrar formulário, coordenador, reprodução imediata e atualização da biblioteca em `frontend/src/main.ts`, exibindo aviso não bloqueante quando a biblioteca falhar

**Checkpoint**: US1 entrega o MVP local-first, com runtime validation e ausência comprovada de estado parcial.

---

## Phase 4: User Story 2 - Continuar um estudo de onde parei (Priority: P2)

**Goal**: reproduzir o Blob local, retomar com tolerância objetiva e marcar conclusão.

**Independent Test**: após `pause`/`seeked` e recarga, retomar com diferença máxima de 1 segundo; em
reprodução ativa visível, persistir checkpoint no máximo 5 segundos atrás; ao terminar, marcar
conclusão visível.

### Tests for User Story 2

> Executar T020–T021 e confirmar RED antes de T022–T024.

- [X] T020 [P] [US2] Adicionar testes de `updateProgress()` em `frontend/tests/unit/libraryService.test.ts`: atualização parcial sem tocar assets/outros campos, limites `0 <= positionSeconds <= durationSeconds`, `updatedAt` ISO, nova posição em estudo concluído e `LibraryUnavailableError` antes da implementação
- [X] T021 [P] [US2] Criar testes do player com relógio falso em `frontend/tests/unit/player.test.ts`, cobrindo Object URL, retomada com tolerância de 1 segundo, escritas em `pause`/`seeked`/`visibilitychange`, checkpoint a cada 5 segundos visíveis, `ended`, revogação de URL e aviso claro sem interromper reprodução quando `updateProgress` falhar

### Implementation for User Story 2

- [X] T022 [P] [US2] Implementar `updateProgress()` em `frontend/src/library/libraryService.ts`, alterando somente `studyMetadata` e convertendo falhas para `LibraryUnavailableError`
- [X] T023 [P] [US2] Implementar player local, política de persistência/tolerância e aviso não bloqueante para falha de progresso em `frontend/src/ui/player.ts`, sem depender do backend depois de obter `StudyAssets`
- [X] T024 [US2] Integrar abertura do player, retomada e atualização visual de conclusão em `frontend/src/main.ts` e `frontend/src/ui/libraryView.ts`

**Checkpoint**: US2 retoma e conclui estudos exclusivamente a partir da cópia local.

---

## Phase 5: User Story 3 - Remover um estudo da biblioteca local (Priority: P3)

**Goal**: remover metadata e assets de forma atômica e idempotente.

**Independent Test**: remover estudo pré-semeado, confirmar ausência nos dois stores e na lista,
repetir sem erro e preservar os demais estudos.

### Tests for User Story 3

> Executar T025 e confirmar RED antes de T026–T027.

- [X] T025 [US3] Adicionar testes de serviço e UI para remoção em `frontend/tests/unit/libraryService.test.ts` e `frontend/tests/unit/libraryView.test.ts`: deletes multi-store, idempotência, preservação de outros IDs, rollback, `LibraryUnavailableError`, manutenção do item visível e aviso claro quando remover falhar

### Implementation for User Story 3

- [X] T026 [US3] Implementar `removeStudy()` multi-store atômico e idempotente em `frontend/src/library/libraryService.ts`, convertendo falhas para `LibraryUnavailableError`
- [X] T027 [US3] Adicionar remoção com confirmação, descarte do player/Object URL, atualização da lista no sucesso e aviso claro preservando o item na falha em `frontend/src/ui/libraryView.ts`, `frontend/src/ui/player.ts` e `frontend/src/main.ts`

**Checkpoint**: US3 remove integralmente a cópia local sem resíduos.

---

## Phase 6: User Story 4 - Ver os detalhes de um estudo específico (Priority: P4)

> **Escopo**: “Phase 6” é apenas a sexta etapa interna deste arquivo de tarefas; US4 e FR-011
> continuam pertencendo à Fase 5 do produto (`spec.md` linha 9). Concluí-los fecha o escopo aprovado
> da Fase 5 e não inicia a próxima fase do produto.

**Goal**: compor metadata+assets localmente e exibir metadados/progresso sem rede.

**Independent Test**: consultar um estudo e comparar todos os campos compostos; ID ausente ou par
incompleto retorna ausência consistente sem expor erro técnico.

### Tests for User Story 4

> Executar T028 e confirmar RED antes de T029–T030.

- [X] T028 [US4] Adicionar testes de serviço e UI para detalhes em `frontend/tests/unit/libraryService.test.ts` e `frontend/tests/unit/libraryView.test.ts`: composição metadata+assets, `undefined` para ausente/par incompleto, `LibraryUnavailableError` e aviso claro sem expor erro técnico quando a consulta falhar

### Implementation for User Story 4

- [X] T029 [US4] Implementar `getStudy()` com transação readonly nos dois stores em `frontend/src/library/libraryService.ts`, retornando detalhe composto ou `undefined`
- [X] T030 [US4] Implementar painel de detalhes com rótulo, data, duração, tamanho, posição e conclusão, incluindo ausência e aviso claro para indisponibilidade, em `frontend/src/ui/libraryView.ts` e `frontend/src/main.ts`

**Checkpoint**: as quatro stories funcionam sobre a biblioteca local dividida em metadata/assets.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T031 Adicionar Playwright do fluxo gerar → validar → salvar → listar → tocar → recarregar → retomar dentro de 1 segundo → concluir → operar offline → remover em `frontend/e2e/library.spec.ts`, verificando os dois stores reais
- [X] T032 [P] Executar `npm run test` e `npm run build` definidos em `frontend/package.json` sem relaxar TypeScript estrito ou remover cobertura
- [X] T033 [P] Executar `uv run pytest tests` conforme `backend/pyproject.toml` e confirmar regressão verde sem modificar `backend/`
- [X] T034 Executar `npm run test:e2e` em `frontend/package.json` com backend real e proxy Vite, validando também armazenamento indisponível conforme `specs/003-local-study-library/quickstart.md`
- [X] T035 Revisar FR-001–FR-016, SC-001–SC-006 e gates constitucionais e registrar evidências em `specs/003-local-study-library/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup não tem dependências; Foundational depende de Setup e bloqueia as stories.
- US1 depende de Foundational e entrega o MVP.
- Domínio de US2, US3 e US4 depende de Foundational e dos registros definidos por US1; integrações visuais seguem a ordem US1 → US2 → US3/US4.
- Polish/E2E depende de US1–US4.

### User Story Graph

```text
Setup → Foundational → US1 (MVP) → US2
                              ├──→ US3
                              └──→ US4
US1 + US2 + US3 + US4 → Polish/E2E
```

### TDD Order Within Stories

- US1: T008–T012 RED → T013–T019 GREEN.
- US2: T020–T021 RED → T022–T024 GREEN.
- US3: T025 RED → T026–T027 GREEN.
- US4: T028 RED → T029–T030 GREEN.
- Nenhum comportamento de erro é implementado antes do teste que o exige.

### Parallel Opportunities

- T002–T004 em paralelo após T001; T005 e T007 em paralelo, com T006 após T005.
- T008–T012 usam arquivos de teste distintos e podem produzir RED em paralelo.
- T013, T014 e T016 usam arquivos distintos e podem avançar em paralelo após seus testes; T015 depende de T014 e T017 depende de T013/T015/T016.
- T020 e T021 podem executar em paralelo; T022 e T023 também após seus respectivos testes.
- Métodos de domínio de US3 e US4 podem ser desenvolvidos em branches/worktrees separados e integrados serialmente em `libraryService.ts`.
- T032 e T033 validam workspaces distintos em paralelo.

## Parallel Example: User Story 1

```text
Task: "T008 labels.test.ts"
Task: "T009 validators.test.ts"
Task: "T010 studiesClient.test.ts"
Task: "T011 libraryService.test.ts"
Task: "T012 createStudy.test.ts"

Após RED:
Task: "T013 labels.ts"
Task: "T014 validators.ts"
Task: "T016 libraryService.ts"
```

---

## Implementation Strategy

### MVP First

1. Completar Setup e Foundational.
2. Executar T008–T012 e registrar RED.
3. Implementar T013–T019 até GREEN.
4. Validar US1 com backend ativo, backend indisponível e uma falha parcial de download.

### Incremental Delivery

1. US1: bundle validado, persistência atômica e listagem leve.
2. US2: retomada mensurável e conclusão.
3. US3: remoção multi-store.
4. US4: detalhes compostos.
5. Polish: build, regressão e navegador real.

## Notes

- Nenhuma tarefa modifica `backend/`.
- O frontend usa `/api` relativo; não adicionar CORS.
- `listStudies()` nunca abre `studyAssets`.
- `saveStudy` recebe `label` obrigatório e nunca recebe texto original.
- Falha antes de bundle completo/validado não inicia transação IndexedDB.
