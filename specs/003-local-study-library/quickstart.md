# Quickstart: Validar a biblioteca local-first de estudos

## Prerequisites

- Backend da Fase 4 funcional localmente (ver
  `../002-study-audio-api/quickstart.md` para os pré-requisitos de Python/FFmpeg/Piper).
- Node.js LTS e um gerenciador de pacotes (`npm`) instalados para o novo workspace `frontend/`.
- Navegador moderno com DevTools (para inspecionar o IndexedDB manualmente no passo 3).

Execute os comandos de backend a partir de `backend/` e os de frontend a partir de `frontend/`,
salvo indicação contrária.

## 1. Validar que o backend da Fase 4 continua inalterado

```powershell
uv run pytest tests
```

Resultado esperado: toda a suíte das Fases 1–4 continua verde — esta fase não modifica nenhum
arquivo em `backend/`.

## 2. Validar o `libraryService` isoladamente (sem navegador real)

```powershell
npm install
npm run test
```

Resultado esperado: os testes unitários com Vitest + `fake-indexeddb` cobrem, sem precisar de um
navegador:

- validators rejeitam criação, áudio ou timeline fora dos contratos em runtime;
- o coordenador não chama `saveStudy` se áudio ou timeline falhar, mesmo quando o outro download já
  tiver concluído;
- `saveStudy` grava metadata e assets nos dois stores, com progresso inicial (`positionSeconds: 0`,
  `completed: false`), em uma única transação multi-store;
- `listStudies` retorna os estudos ordenados do mais recente para o mais antigo, e uma lista vazia
  quando não há nenhum estudo salvo, sem abrir `studyAssets`;
- `getStudy` retorna `undefined` para um `studyId` inexistente, e o registro completo (incluindo
  `audio`/`timeline`) para um existente;
- `updateProgress` atualiza `positionSeconds`/`completed` sem afetar outros campos;
- `removeStudy` apaga o registro inteiro; chamar novamente para o mesmo `studyId` não lança erro;
- rótulo automático derivado do início do texto quando nenhum rótulo é informado (`research.md`
  §4);
- uma falha simulada de IndexedDB (ex.: `QuotaExceededError` injetado no dublê de `fake-indexeddb`)
  é relançada como `LibraryUnavailableError` em cada método público, e testes de UI confirmam aviso
  claro para salvar, listar, atualizar progresso, remover e consultar detalhes sem erro técnico.

## 3. Validação de integração real ponta a ponta

Em um terminal, suba o backend real:

```powershell
cd backend
uv run uvicorn app.main:app --reload
```

Em outro terminal, suba o frontend (o Vite encaminha `/api` para `http://127.0.0.1:8000`):

```powershell
cd frontend
npm run dev
```

Abra a URL impressa pelo Vite no navegador e:

1. Gere um novo estudo pela UI (texto de exemplo com ao menos duas frases).
2. Confirme que ele aparece imediatamente na biblioteca, com um rótulo derivado do texto, data de
   criação e duração.
3. Abra o DevTools → Application → IndexedDB → `hss-study-library` e confirme a mesma chave em
   `studyMetadata` (campos leves/progresso) e `studyAssets` (Blob/timeline).
4. Toque o áudio parcialmente, recarregue a página (F5) e reabra o mesmo estudo: a reprodução deve
   retomar com diferença máxima de 1 segundo da posição persistida.
5. Ouça o estudo até o fim e confirme que ele passa a aparecer marcado como concluído na
   biblioteca.
6. Pare o backend (`Ctrl+C` no terminal do Uvicorn) e confirme que o estudo já salvo continua
   aparecendo na biblioteca e pode ser reproduzido normalmente a partir da cópia local (SC-004).
7. Suba o backend novamente, remova o estudo pela UI e confirme que ele desaparece da biblioteca e
   dos dois stores IndexedDB.

## 4. Validação automatizada de integração (Playwright)

```powershell
npx playwright test
```

Resultado esperado: o teste e2e reproduz o fluxo do passo 3 automaticamente (gerar → validar →
salvar → listar → recarregar → retomar dentro de 1 segundo → concluir → remover) em um navegador
real, acessando o backend real exclusivamente pelo proxy Vite.

## 5. Validação do comportamento sem armazenamento local disponível

No navegador, abra a mesma URL em uma aba anônima/privada com armazenamento de terceiros/local
bloqueado (ou reduza a cota via DevTools → Application → Storage, se o navegador suportar simular
`QuotaExceededError`). Gere um novo estudo e confirme que:

- a geração e a reprodução imediata do áudio funcionam normalmente (a chamada à API da Fase 4 não
  depende do `libraryService`);
- a UI exibe um aviso claro de que o estudo não pôde ser salvo na biblioteca, em vez de travar ou
  falhar silenciosamente (FR-012, SC-006).

## 6. Evidências de execução (2026-10-04)

### Gates automatizados

| Gate | Resultado |
|------|-----------|
| `frontend`: `npm run test` | PASS — 8 arquivos, 71 testes |
| `frontend`: `npm run build` | PASS — TypeScript estrito e build Vite |
| `backend`: `uv run pytest tests` | PASS — 183 testes, 1 aviso de depreciação do Starlette |
| `frontend`: `npm run test:e2e` | PASS — 2 cenários Playwright com backend real e proxy Vite |

O primeiro cenário E2E gera e valida um estudo, confirma a mesma entrada nos stores reais
`studyMetadata` e `studyAssets`, persiste uma posição, recarrega e retoma com diferença máxima de um
segundo. Depois bloqueia `/api/v1`, recarrega novamente, lista e abre o Blob local, conclui o estudo
e confirma a remoção dos dois stores. O segundo cenário torna o IndexedDB indisponível antes da
montagem, confirma as três chamadas same-origin via proxy e verifica aviso claro com o áudio gerado
ainda reproduzível.

### Rastreabilidade dos requisitos

| Requisitos | Evidência | Estado |
|------------|-----------|--------|
| FR-001–FR-005 | Testes de validators, criação, labels e `libraryService`; E2E nos dois stores | PASS |
| FR-006–FR-010 | Testes de player/remoção; E2E de retomada, conclusão, backend bloqueado e remoção atômica | PASS |
| FR-011 | T028–T030: composição local metadata+assets e painel com rótulo, data, duração, tamanho e progresso; testes cobrem ausência, par incompleto e indisponibilidade sem erro técnico exposto | PASS |
| FR-012 | Testes unitários de indisponibilidade e E2E com `QuotaExceededError` | PASS |
| FR-013–FR-016 | Backend sem alterações; validators verdes; metadados sem texto original; E2E usa somente `/api/v1` same-origin | PASS |
| SC-001–SC-006 | Fluxo E2E completo, retomada, remoção, reprodução local e falha de IndexedDB, apoiado pela suíte unitária | PASS |

### Gates constitucionais

Os princípios I–X permanecem atendidos: os artefatos de spec/plan/tasks governaram o trabalho; os
dados e a reprodução permanecem local-first; o backend e o pipeline não foram modificados; testes
unitários, integração real e regressão estão verdes; nenhuma dependência ou abstração foi adicionada;
e URLs relativas, validação runtime e retenção mínima preservam os limites de segurança. T028–T030
foram concluídas porque FR-011 é requisito obrigatório do escopo aprovado da Fase 5; a “Phase 6” de
`tasks.md` é uma etapa interna dessa feature, não a próxima fase do produto. Nenhum trabalho da fase
seguinte do produto foi iniciado.
