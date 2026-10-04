# Phase 0 Research: Biblioteca local-first de estudos

Todas as decisões abaixo resolvem os pontos técnicos abertos pelo Technical Context e pelo
Constitution Check de `plan.md`. Nenhum item permanece como `NEEDS CLARIFICATION`.

## 1. Stack do cliente

- **Decision**: um novo workspace `frontend/` em TypeScript, construído com Vite, sem framework de
  UI (nenhum React/Vue/etc.). Expõe um serviço de domínio (`libraryService`) isolado da UI, e uma
  UI mínima (DOM + TypeScript puro) para satisfazer os cenários de aceite do spec (ver a lista, tocar,
  retomar, remover, ver detalhes).
- **Rationale**: confirmado diretamente com o usuário (ver sessão de `/speckit.plan`). O backend
  Python é hoje o único código do produto; não existe decisão prévia de framework de SPA. Adotar um
  framework completo agora seria comprometer uma escolha de produto que ainda não foi tomada, violando
  o Princípio VII (No Overengineering). Um módulo TS testável com uma UI mínima satisfaz todas as
  User Stories do spec sem essa amarração prematura.
- **Alternatives considered**: React + TypeScript + Vite (rejeitado pelo usuário — comprometeria a
  escolha de SPA antes de o produto precisar de uma); apenas o módulo de armazenamento sem UI
  (rejeitado — o spec define cenários de aceite observáveis pelo usuário, como "abrir a biblioteca" e
  "continuar de onde parei", que exigem alguma superfície visual nesta fase).

## 2. Acesso ao IndexedDB

- **Decision**: usar a biblioteca `idb` (wrapper fino baseado em Promises sobre a API nativa de
  IndexedDB, sem camada de query própria) como única dependência de runtime nova do frontend.
- **Rationale**: a API nativa de IndexedDB é baseada em callbacks/eventos, verbosa e propensa a erro
  (fácil esquecer de tratar `onerror`, versionamento de schema, etc.). `idb` elimina esse boilerplate
  mantendo a mesma superfície de dados (object stores, índices, transações), sem introduzir um ORM ou
  camada de query pesada. É uma dependência pequena (≈1kb), amplamente usada e mantida.
- **Alternatives considered**: IndexedDB cru (rejeitado — mais código, mais superfície para bugs,
  sem ganho real); Dexie.js (rejeitado — oferece recursos de consulta e reatividade que esta fase não
  precisa; maior superfície de API para manter e testar do que o problema exige, violando "No
  Overengineering").

## 3. Esquema de armazenamento local

- **Decision**: um banco IndexedDB (`hss-study-library`, versão 1) com dois object stores, ambos com
  `keyPath: "studyId"`: `studyMetadata` contém rótulo, data, parâmetros de geração, duração, tamanho
  e progresso; `studyAssets` contém apenas o Blob MP3 e a timeline. `studyMetadata` possui índice
  não único `createdAt`. Salvar e remover usam uma única transação `readwrite` abrangendo os dois
  stores; `listStudies` consulta somente `studyMetadata`.
- **Rationale**: IndexedDB não oferece projeção de campos ao percorrer um store; um cursor sobre um
  registro que também contém Blob/timeline materializaria o valor pesado. Separar assets garante por
  construção que a listagem nunca os lê, mantendo atomicidade com transações multi-store nativas.
- **Alternatives considered**: store único (rejeitado — não cumpre a listagem leve); três stores com
  progresso separado (rejeitado — progresso é pequeno e sempre pertence aos metadados).

## 4. Rótulo automático do estudo (FR-005, FR-014)

- **Decision**: o fluxo de criação normaliza o rótulo manual (`trim` e espaços internos
  condensados) ou, quando ele é omitido/vazio, deriva o rótulo dos primeiros 80 caracteres do texto
  original, cortando na última palavra completa. A reticência (`…`) conta no limite final de 80
  caracteres. O fluxo passa um `label` obrigatório ao `libraryService`; o serviço nunca recebe o
  texto original como entrada ou metadado. A timeline validada continua contendo as frases
  normalizadas exigidas pelo contrato da Fase 3. Rótulo manual acima de 80 caracteres é rejeitado.
- **Rationale**: 80 caracteres é o suficiente para reconhecer visualmente um estudo em uma lista
  (aproximadamente uma linha de título) sem reproduzir o conteúdo original, preservando a mesma
  garantia de privacidade dos metadados estabelecida na Fase 4. Cortar em limite de palavra evita
  rótulos com uma palavra truncada no meio.
- **Alternatives considered**: usar o `study_id` como rótulo padrão (rejeitado — não ajuda o usuário
  a reconhecer o estudo, esvaziando o valor da User Story 1); permitir rótulos arbitrariamente longos
  (rejeitado — rótulos muito longos quebram a legibilidade da listagem e aumentam o risco de reter
  conteúdo sensível demais).

## 5. Atualização do progresso de reprodução (FR-007, FR-008)

- **Decision**: a posição é persistida em `pause` e `seeked`, a cada 5 segundos enquanto a reprodução
  está ativa e a página visível, e em `visibilitychange` quando a página deixa de estar visível. A
  conclusão é marcada em `ended`. Testes aceitam diferença máxima de 1 segundo após evento explícito
  ou recarga normal e comprovam que o checkpoint periódico não fica mais de 5 segundos atrás em
  reprodução ativa visível. `beforeunload` é apenas best effort e não sustenta o critério de aceite.
- **Rationale**: gravar a cada `timeupdate` (que dispara várias vezes por segundo) geraria escrita
  excessiva no IndexedDB sem benefício perceptível para o usuário. Os gatilhos escolhidos cobrem os
  pontos em que o progresso realmente precisa estar correto (pausar, navegar, fechar a aba) com um
  volume de escrita desprezível.
- **Alternatives considered**: gravar a cada `timeupdate` (rejeitado — volume de escrita
  desnecessário); gravar apenas ao fechar a aba (rejeitado — `beforeunload` não é garantido em todo
  navegador/cenário, ex. aba encerrada pelo sistema operacional; os gatilhos intermediários reduzem
  o risco de perda de progresso).

## 6. Indisponibilidade ou esgotamento do armazenamento local (FR-012)

- **Decision**: toda operação do `libraryService` que falhar ao abrir o banco ou lançar
  `QuotaExceededError` (ou equivalente) durante uma escrita é capturada e relançada como um erro de
  domínio único e reconhecível (`LibraryUnavailableError`). A UI trata esse erro mostrando um aviso
  específico para a operação de biblioteca afetada, sem interromper a geração/reprodução direta via
  API da Fase 4, que não depende do `libraryService`.
- **Rationale**: satisfaz FR-012/SC-006 isolando a falha de armazenamento em um tipo de erro único,
  evitando duplicar tratamento de erro específico de IndexedDB em cada ponto de chamada. Mantém a
  separação entre "consumir a API" (sempre funcional) e "biblioteca local" (pode falhar
  independentemente).
- **Alternatives considered**: liberar espaço automaticamente removendo estudos antigos (rejeitado
  pelo usuário na sessão de `/speckit.clarify`); falhar silenciosamente sem avisar o usuário
  (rejeitado pelo usuário na mesma sessão).

## 7. Atomicidade de salvamento e remoção (Edge Cases do spec)

- **Decision**: áudio e timeline são baixados e validados antes de qualquer transação. Só então
  `saveStudy` grava `StudyMetadata` e `StudyAssets` em uma única transação `readwrite` sobre ambos os
  stores. `removeStudy` apaga as duas entradas em outra transação multi-store. Se qualquer download
  ou validação falhar, o coordenador não chama `saveStudy`.
- **Rationale**: transações do IndexedDB são atômicas por definição da plataforma — ou todas as
  operações da transação são aplicadas, ou nenhuma é. Usar uma única transação por operação satisfaz
  diretamente FR-010 e os edge cases de atomicidade sem exigir nenhuma lógica manual de
  compensação/rollback.
- **Alternatives considered**: gravar assets e metadados em transações separadas (rejeitado — reabre
  o risco de estado parcial); iniciar a transação antes de concluir downloads (rejeitado — mantém
  transação longa e ainda mistura falha de rede com persistência).

## 8. Validação de integração real

- **Decision**: Vitest cobre cada seam público: validators runtime, cliente HTTP, derivação de
  rótulo, coordenador criar/baixar/validar/salvar e `libraryService` com `fake-indexeddb`. O teste do
  coordenador simula áudio bem-sucedido + timeline com falha (e o inverso) e prova que `saveStudy`
  não é chamado. Playwright roda a UI via Vite, que encaminha `/api` ao backend real, validando o
  fluxo gerar → salvar → listar → tocar → recarregar → retomar → remover.
- **Rationale**: `fake-indexeddb` cobre a lógica de domínio rapidamente em CI sem precisar de um
  navegador; o Princípio IV (Mandatory Tests) exige cobertura de integração para comportamento que
  depende de interação real entre componentes — aqui, a interação real é "IndexedDB de um navegador
  de verdade + um elemento de áudio real", que só o Playwright exercita fielmente.
- **Alternatives considered**: testar `libraryService` apenas manualmente no navegador (rejeitado —
  viola o Princípio IV); depender só de `fake-indexeddb` também para a validação de integração
  (rejeitado — não comprova nada sobre comportamento de um navegador real, como cotas de
  armazenamento reais e persistência entre recarregamentos de página).

## 9. Validação runtime dos contratos HTTP (FR-015)

- **Decision**: `frontend/src/api/validators.ts` implementa assertion functions sem dependência
  adicional. A criação valida objeto fechado, `study_id` hexadecimal de 32 caracteres,
  `chunks_count` inteiro `>= 1`, `duration_seconds >= 0`, `file_size_bytes` inteiro `>= 1` e
  `processing_time_seconds >= 0`, exatamente como o contrato da Fase 4; áudio valida status,
  `Content-Type: audio/mpeg` e Blob não vazio; timeline valida os
  campos e limites definidos em `001-text-audio-timeline/contracts/timeline-v1.schema.json`,
  incluindo versão, SHA-256, sample rate, amostras e intervalos ordenados. O cliente só retorna
  valores tipados após essas validações.
- **Rationale**: tipos TypeScript desaparecem em runtime e não satisfazem o Princípio VI para dados
  externos. Assertion functions locais cobrem apenas os três contratos estáveis desta fase sem
  adicionar uma biblioteca de schema ao bundle.
- **Alternatives considered**: confiar nos tipos estáticos (rejeitado — não valida rede); adicionar
  um validador genérico de JSON Schema (rejeitado — dependência desnecessária para três contratos).

## 10. Origem da API e proxy de desenvolvimento (FR-016)

- **Decision**: `vite.config.ts` encaminha `/api` para `http://127.0.0.1:8000`, preservando o caminho.
  `studiesClient` usa somente URLs relativas `/api/v1/...`. Em produção, frontend e API são servidos
  pela mesma origem; CORS e implantação multi-origem permanecem fora do escopo.
- **Rationale**: permite desenvolvimento e Playwright sem alterar o backend da Fase 4 e mantém um
  único comportamento de URL no cliente.
- **Alternatives considered**: habilitar CORS no FastAPI (rejeitado — alteraria o backend sem
  necessidade); URL absoluta configurável nesta fase (rejeitada — introduziria suporte multi-origem
  não solicitado).

## Resumo

Nenhum `NEEDS CLARIFICATION` permanece. O backend da Fase 4 não é alterado por nenhuma decisão
acima; toda a complexidade nova fica isolada no novo workspace `frontend/`.
