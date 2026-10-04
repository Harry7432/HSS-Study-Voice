# Data Model: Biblioteca local-first de estudos

Modelo inteiramente no cliente (`frontend/`). O banco IndexedDB `hss-study-library` versão 1 usa
dois object stores com a mesma chave `studyId`: `studyMetadata` para dados leves/progresso e
`studyAssets` para MP3/timeline. O backend permanece inalterado.

## StudyMetadata

Registro persistido no store `studyMetadata` (`keyPath: "studyId"`). É a única fonte consultada por
`listStudies()`, portanto listar nunca lê ou materializa Blob/timeline.

| Campo | Tipo | Obrigatório | Regras de validação |
|-------|------|-------------|---------------------|
| `studyId` | `string` | Sim | `^[0-9a-f]{32}$`; chave primária. |
| `label` | `string` | Sim | 1–80 caracteres após normalização; já derivado/validado antes de `saveStudy`; a reticência conta no limite. |
| `createdAt` | `string` ISO 8601 | Sim | Definido no salvamento; chave do índice `createdAt`. |
| `durationSeconds` | `number` | Sim | `>= 0`; resposta de criação validada em runtime. |
| `fileSizeBytes` | `number` | Sim | `> 0`; resposta de criação validada em runtime. |
| `voice` | `string \| null` | Sim | Parâmetro enviado à geração, ou `null`. |
| `speed` | `number \| null` | Sim | `> 0` quando presente, ou `null`. |
| `bitrate` | `string \| null` | Sim | Parâmetro enviado à geração, ou `null`. |
| `progress` | `Progress` | Sim | Inicializado e atualizado conforme abaixo. |

### Progress

| Campo | Tipo | Obrigatório | Regras de validação |
|-------|------|-------------|---------------------|
| `positionSeconds` | `number` | Sim | `0 <= positionSeconds <= durationSeconds`; começa em `0`. |
| `completed` | `boolean` | Sim | Começa em `false`; passa a `true` no evento `ended`. |
| `updatedAt` | `string` ISO 8601 | Sim | Atualizado a cada escrita de progresso. |

## StudyAssets

Registro persistido no store `studyAssets` (`keyPath: "studyId"`). Só é lido por `getStudy()` ao
abrir detalhes/reprodução de um estudo específico.

| Campo | Tipo | Obrigatório | Regras de validação |
|-------|------|-------------|---------------------|
| `studyId` | `string` | Sim | Mesma chave de `StudyMetadata`; `^[0-9a-f]{32}$`. |
| `audio` | `Blob` | Sim | Tipo `audio/mpeg`, tamanho > 0, validado antes da transação. |
| `timeline` | `TimelineDocument` | Sim | Validada em runtime contra o contrato `timeline-v1` antes da transação; armazenada sem alteração. |

## SavedStudyDetail

Tipo público composto em memória por `getStudy(studyId)`: todos os campos de `StudyMetadata` mais
`audio` e `timeline` de `StudyAssets`. Não é um terceiro registro persistido.

`SavedStudySummary`, retornado por `listStudies()`, contém somente `studyId`, `label`, `createdAt`,
`durationSeconds` e `progress`.

## Stores e índices

| Object store | Chave/índice | Único | Uso |
|--------------|--------------|-------|-----|
| `studyMetadata` | primária `studyId` | Sim | Busca, progresso, remoção e composição de detalhes. |
| `studyMetadata` | índice `createdAt` | Não | Listagem do mais recente para o mais antigo. |
| `studyAssets` | primária `studyId` | Sim | Busca e remoção de áudio/timeline de um estudo. |

## Transações e ciclo de vida

```text
POST /api/v1/studies
   │ valida criação em runtime
   ├─ GET /audio ──── valida status + audio/mpeg + Blob não vazio
   └─ GET /timeline ─ valida timeline-v1
             │
             │ somente quando ambos estão completos e válidos
             ▼
libraryService.saveStudy(result, label obrigatório)
   └─ uma transação readwrite [studyMetadata, studyAssets]
      ├─ put StudyMetadata { ..., progress: { 0, false, now } }
      └─ put StudyAssets { studyId, audio, timeline }

libraryService.listStudies()
   └─ cursor reverso no índice studyMetadata.createdAt (não abre studyAssets)

libraryService.getStudy(studyId)
   └─ transação readonly nos dois stores → composição | undefined

libraryService.updateProgress(studyId, update)
   └─ readwrite somente em studyMetadata

libraryService.removeStudy(studyId)
   └─ uma transação readwrite [studyMetadata, studyAssets] → delete nas duas chaves
```

Se criação, download ou validação falhar, o coordenador não chama `saveStudy`; portanto nenhuma
transação de persistência é iniciada. Se uma escrita ou remoção multi-store falhar, a atomicidade do
IndexedDB aborta as duas alterações.

## Nota de desempenho

`listStudies()` percorre somente `studyMetadata`, cujo registro não contém Blob nem timeline. Essa
separação, e não uma projeção em memória de um registro pesado, garante que a listagem não carregue
assets. `getStudy()` consulta os dois stores apenas para o estudo aberto.

## Validações cruzadas com o spec

- FR-001/FR-015: validators HTTP + coordenador só chamam `saveStudy` com bundle completo e válido.
- FR-002–FR-004: `studyMetadata` e índice `createdAt` sustentam listagem local/vazia.
- FR-005/FR-014: `label` obrigatório no serviço; texto original não entra no modelo persistido.
- FR-006: `studyAssets.audio` permite reprodução offline.
- FR-007/FR-008: `StudyMetadata.progress` guarda retomada e conclusão.
- FR-009/FR-010: remoção multi-store atômica.
- FR-011: `getStudy()` compõe detalhes sem rede.
- FR-012: todos os métodos convertem falhas de IndexedDB em `LibraryUnavailableError`.
- FR-013/FR-016: dados permanecem no navegador e acesso à API usa proxy/mesma origem, sem backend novo.
