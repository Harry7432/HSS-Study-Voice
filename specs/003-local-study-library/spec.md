# Feature Specification: Biblioteca local-first de estudos

**Feature Branch**: `master`

**Created**: 2026-10-03

**Status**: Draft

**Input**: User description: "Fase 5 — Biblioteca local-first"

## Clarifications

### Session 2026-10-03

- Q: Onde a biblioteca de estudos deve ser mantida como fonte de verdade: em um índice/histórico
  persistente no backend/VPS, ou no armazenamento local do navegador do cliente? → A: No
  armazenamento local do navegador do cliente (ex.: IndexedDB). A API da Fase 4 continua
  responsável apenas por processar texto e entregar MP3 + timeline; não ganha nenhum endpoint de
  listagem, detalhe ou remoção de histórico.
- Q: O áudio e a timeline de um estudo devem ser baixados e guardados localmente no navegador
  (cache offline), ou a biblioteca deve guardar apenas metadados e buscar o áudio na API a cada
  reprodução? → A: Cache local do áudio e da timeline no momento em que o estudo é gerado, para que
  continuem disponíveis mesmo se o backend ficar indisponível ou remover sua cópia depois.
- Q: O que o "progresso" de um estudo deve registrar: a posição exata de reprodução para retomar de
  onde parou, apenas se foi concluído, ou ambos? → A: Ambos — posição de retomada em segundos e uma
  marcação explícita de conclusão quando o estudo é ouvido até o fim.
- Q: Como o sistema deve se comportar quando o armazenamento local do navegador estiver
  indisponível ou com espaço esgotado? → A: Bloquear apenas as operações de biblioteca com um erro
  claro; gerar e ouvir um estudo diretamente pela API da Fase 4 continua funcionando normalmente,
  apenas sem ser salvo na biblioteca.
- Q: Como o frontend acessa a API sem alterar o backend para CORS? → A: Em desenvolvimento, o Vite
  encaminha `/api` para `http://127.0.0.1:8000`; em produção, frontend e API são servidos sob a mesma
  origem. O cliente usa URLs relativas `/api/...` nos dois ambientes.
- Q: Como evitar carregar todos os MP3s ao listar a biblioteca? → A: Metadados/progresso e assets
  pesados ficam em object stores separados no mesmo IndexedDB; salvar e remover usam uma única
  transação abrangendo os dois stores.
- Q: Onde o rótulo automático é derivado? → A: O fluxo de criação deriva e valida o rótulo antes de
  chamar o `libraryService`; o serviço recebe sempre um `label` obrigatório e nunca recebe o texto
  original.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver a biblioteca de estudos salvos localmente (Priority: P1)

Como estudante ou educador que já gerou vários estudos em áudio ao longo do tempo, quero ver, no
meu próprio navegador, uma lista de todos os estudos que já gerei anteriormente, para encontrar e
retomar um estudo sem precisar guardar manualmente cada identificador e sem depender de um
histórico mantido pelo servidor.

**Why this priority**: É exatamente a lacuna deixada em aberto pela Fase 4 ("Fora de escopo nesta
fase: ... listagem/histórico de estudos já gerados"). Sem isso, a única forma de reacessar um
estudo é o próprio cliente ter guardado o identificador opaco em outro lugar. É o valor central de
uma "biblioteca" — e, por ser local ao navegador, não exige que o backend retenha histórico
algum, em linha com o princípio de que o servidor não é a biblioteca permanente do usuário.

**Independent Test**: Gerar dois ou três estudos usando o endpoint de criação já existente (Fase
4), confirmando que cada um é salvo automaticamente no armazenamento local do navegador, e então
abrir a biblioteca e verificar que todos aparecem, cada um com identificador, rótulo legível e
metadados básicos (data de criação, duração), sem nenhuma chamada ao backend para descobrir quais
estudos existem.

**Acceptance Scenarios**:

1. **Given** nenhum estudo salvo localmente ainda, **When** o usuário abre a biblioteca, **Then** o
   cliente exibe uma lista vazia, não um erro.
2. **Given** três estudos gerados e salvos localmente em momentos diferentes, **When** o usuário
   abre a biblioteca, **Then** o cliente exibe os três estudos, ordenados do mais recente para o
   mais antigo, cada um com identificador, rótulo, data de criação e duração.
3. **Given** um estudo já salvo localmente, **When** o backend/API da Fase 4 fica temporariamente
   indisponível, **Then** o estudo continua aparecendo na biblioteca e pode ser reproduzido
   normalmente a partir da cópia local, sem exigir uma nova chamada à API.

---

### User Story 2 - Continuar um estudo de onde parei (Priority: P2)

Como usuário que ouve estudos longos em várias sessões, quero que o sistema lembre onde parei de
ouvir cada estudo, para continuar exatamente daquele ponto na próxima vez, em vez de recomeçar do
início ou precisar procurar manualmente o trecho onde parei.

**Why this priority**: É o segundo maior ganho de uma biblioteca pessoal depois de simplesmente
encontrar os estudos (User Story 1) — sem retomada de progresso, uma lista de estudos salvos ainda
obriga o usuário a lembrar manualmente onde parou em cada um.

**Independent Test**: Abrir um estudo salvo, ouvir parte dele, pausar, recarregar a página e reabrir
o mesmo estudo, confirmando que a reprodução retoma com diferença máxima de 1 segundo em relação à
posição persistida. Durante reprodução contínua e visível, confirmar que a posição persistida fica
no máximo 5 segundos atrás da posição observada. Em seguida, ouvir um estudo até o fim e confirmar
que ele passa a aparecer marcado como concluído na biblioteca.

**Acceptance Scenarios**:

1. **Given** um estudo salvo que o usuário começou a ouvir e parou em um ponto intermediário,
   **When** o usuário reabre esse estudo, **Then** a reprodução retoma a partir da posição salva,
   em vez de recomeçar do início.
2. **Given** um estudo salvo sendo ouvido pela primeira vez, **When** a reprodução chega ao fim do
   áudio, **Then** o cliente marca esse estudo como concluído e essa marcação fica visível na
   biblioteca.
3. **Given** um estudo marcado como concluído, **When** o usuário o reabre e ouve novamente desde o
   início, **Then** a posição de retomada é atualizada normalmente, refletindo a nova sessão de
   escuta.

---

### User Story 3 - Remover um estudo da biblioteca local (Priority: P3)

Como usuário local e único do sistema, quero poder remover um estudo que já gerei e não quero mais
manter, para controlar o espaço ocupado no meu navegador e manter minha biblioteca organizada,
exercendo minha propriedade total sobre os meus próprios dados.

**Why this priority**: Complementa as User Stories 1 e 2 dando controle sobre o que é retido
localmente; sem isso, a biblioteca só cresceria indefinidamente, consumindo espaço de
armazenamento do navegador sem necessidade.

**Independent Test**: Gerar um estudo, confirmar que ele aparece na biblioteca (User Story 1),
removê-lo pela operação de remoção e verificar que ele deixa de aparecer na biblioteca e que o
áudio/timeline/progresso salvos localmente para ele não existem mais.

**Acceptance Scenarios**:

1. **Given** um estudo existente na biblioteca local, **When** o usuário solicita a remoção,
   **Then** o cliente apaga o áudio, a timeline, os metadados e o progresso desse estudo do
   armazenamento local, e ele deixa de aparecer na biblioteca.
2. **Given** um identificador que não corresponde a nenhum estudo salvo localmente (ex.: já
   removido anteriormente), **When** uma remoção é solicitada para ele, **Then** o cliente trata a
   operação de forma consistente, sem erro técnico exposto, e sem afetar nenhum outro estudo salvo.

---

### User Story 4 - Ver os detalhes de um estudo específico da biblioteca (Priority: P4)

Como usuário da biblioteca, quero consultar os metadados detalhados de um estudo específico salvo
localmente, para ver informações (rótulo, data, duração, progresso) sem precisar iniciar a
reprodução só para isso.

**Why this priority**: É valor incremental sobre a listagem (User Story 1) — a lista já permite
reconhecer e localizar estudos sem uma tela de detalhes dedicada; por isso a prioridade mais baixa.

**Independent Test**: Gerar e salvar um estudo, consultar seus detalhes pelo identificador local e
confirmar que os metadados retornados (rótulo, data de criação, duração, progresso) coincidem com
o que aparece na listagem e com o estado real de reprodução.

**Acceptance Scenarios**:

1. **Given** um estudo salvo localmente, **When** o usuário consulta seus detalhes, **Then** o
   cliente exibe rótulo, data de criação, duração, tamanho do áudio salvo e o progresso de
   reprodução atual (posição e se foi concluído).
2. **Given** um identificador que não corresponde a nenhum estudo salvo localmente, **When** seus
   detalhes são solicitados, **Then** o cliente trata a ausência de forma consistente com o
   comportamento de remoção (sem erro técnico exposto).

---

### Edge Cases

- O que acontece se o usuário limpar os dados/armazenamento do navegador (ex.: limpar cache do
  site, modo de navegação privada encerrado)? Toda a biblioteca local é perdida, já que não existe
  nenhuma cópia equivalente persistida no backend; o usuário precisaria gerar os estudos novamente
  pela API da Fase 4.
- O que acontece quando dois estudos recebem rótulos automáticos muito parecidos (mesmo início de
  texto)? Cada um mantém seu próprio identificador único; o rótulo pode se repetir visualmente, o
  que é aceitável.
- O que acontece se o salvamento local (download do áudio + timeline + metadados) falhar no meio do
  processo (ex.: conexão cai durante o download)? O estudo não deve ficar parcialmente salvo (ex.:
  só áudio sem timeline); áudio e timeline devem ser totalmente baixados e validados antes de
  qualquer escrita. Se qualquer download ou validação falhar, `saveStudy` não é chamado, nada é
  persistido e o usuário é informado.
- Como o sistema se comporta quando a mesma biblioteca é aberta em um navegador ou dispositivo
  diferente daquele onde os estudos foram gerados? Nenhum estudo aparece nesse outro
  navegador/dispositivo — comportamento esperado, pois a biblioteca é local a cada instalação (ver
  Assumptions), não um erro de sincronização.
- O que acontece com a listagem quando há um volume grande de estudos acumulados localmente (ex.:
  centenas)? A listagem deve continuar respondendo em tempo hábil a partir do armazenamento local,
  sem exigir nenhuma chamada ao backend para ser montada.
- O que acontece quando o armazenamento local está indisponível ou com cota esgotada no momento de
  salvar um novo estudo? A biblioteca não salva esse estudo e informa o usuário claramente, mas a
  geração e a reprodução imediata do áudio pela API da Fase 4 continuam funcionando normalmente.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O cliente DEVE baixar e validar completamente o áudio (MP3) e a timeline de cada
  estudo gerado pela API da Fase 4 antes de iniciar qualquer escrita local; somente depois DEVE
  armazená-los no navegador do usuário, junto com os metadados, para que permaneçam disponíveis
  mesmo que o backend fique indisponível ou remova sua própria cópia depois. Se um download ou
  validação falhar, nenhum registro local pode ser criado.
- **FR-002**: O cliente DEVE manter, junto com o áudio e a timeline armazenados localmente, um
  registro de metadados por estudo: identificador, rótulo legível, data de criação e duração.
- **FR-003**: O cliente DEVE exibir todos os estudos salvos localmente em uma listagem (a
  biblioteca), ordenada do mais recente para o mais antigo por padrão, obtida inteiramente do
  armazenamento local, sem depender de uma chamada ao backend para descobrir quais estudos
  existem.
- **FR-004**: O cliente DEVE exibir uma lista vazia, não um erro, quando nenhum estudo tiver sido
  salvo localmente ainda.
- **FR-005**: O cliente DEVE associar a cada estudo salvo um rótulo legível de 1–80 caracteres,
  definido por um valor opcional fornecido pelo usuário no momento da criação ou, quando omitido,
  derivado automaticamente do início do texto original enviado. O fluxo de criação DEVE normalizar
  e validar esse rótulo antes de chamar o `libraryService`, cujo parâmetro `label` é obrigatório;
  o texto original nunca é repassado ao serviço.
- **FR-006**: O cliente DEVE permitir reproduzir o áudio de um estudo salvo diretamente a partir da
  cópia armazenada localmente, sem exigir uma nova chamada à API da Fase 4 quando essa cópia já
  existir.
- **FR-007**: O cliente DEVE registrar e atualizar, para cada estudo salvo, a posição de reprodução
  em segundos. Após `pause`, `seeked` ou recarga normal, a retomada DEVE ocorrer com diferença
  máxima de 1 segundo em relação à posição persistida; durante reprodução ativa com a página
  visível, a posição persistida DEVE ficar no máximo 5 segundos atrás da posição observada.
- **FR-008**: O cliente DEVE marcar um estudo salvo como concluído quando sua reprodução chegar ao
  fim do áudio, mantendo essa marcação visível na biblioteca e nos detalhes do estudo.
- **FR-009**: O cliente DEVE permitir remover permanentemente um estudo salvo localmente —
  incluindo áudio, timeline, metadados e progresso — a pedido do usuário.
- **FR-010**: A remoção de um estudo salvo DEVE ser atômica no armazenamento local: ao final da
  operação, o estudo deve estar totalmente ausente (áudio, timeline, metadados e progresso), sem
  deixar artefatos parciais.
- **FR-011**: O cliente DEVE permitir consultar os metadados completos de um estudo salvo (rótulo,
  data de criação, duração, tamanho do áudio e progresso de reprodução) sem precisar buscar
  novamente o áudio na API.
- **FR-012**: O cliente DEVE sinalizar claramente ao usuário quando uma operação de biblioteca
  (salvar, listar, atualizar progresso, remover, consultar detalhes) não puder ser concluída por
  indisponibilidade ou esgotamento do armazenamento local do navegador, sem interromper a
  capacidade de gerar e ouvir um novo estudo diretamente pela API da Fase 4.
- **FR-013**: Esta fase NÃO DEVE introduzir nenhum índice, listagem, detalhe ou histórico
  persistente de estudos no backend/VPS — a API da Fase 4 permanece responsável apenas por
  processar texto e entregar o áudio e a timeline de um estudo por vez, por identificador, como já
  definido.
- **FR-014**: O cliente NÃO DEVE persistir o texto original completo submetido na criação como
  parte dos metadados locais da biblioteca — apenas um rótulo curto é retido para exibição.
- **FR-015**: O cliente DEVE validar em runtime toda resposta recebida da API antes de usá-la ou
  persisti-la: a resposta de criação deve respeitar o contrato da Fase 4 e seus limites; o áudio
  deve ter resposta bem-sucedida, tipo `audio/mpeg` e conteúdo não vazio; a timeline deve respeitar
  `001-text-audio-timeline/contracts/timeline-v1.schema.json`. Dados inválidos DEVEM ser rejeitados
  sem escrita parcial no IndexedDB.
- **FR-016**: Em desenvolvimento, o frontend DEVE acessar URLs relativas `/api/...` encaminhadas
  pelo proxy Vite para `http://127.0.0.1:8000`; em produção, frontend e API DEVEM operar sob a mesma
  origem. Esta fase NÃO adiciona configuração CORS nem qualquer endpoint ao backend.

### Key Entities

- **Estudo salvo (entrada de biblioteca local)**: representa a cópia local, no navegador do
  usuário, de um estudo gerado pela API da Fase 4 — inclui o áudio (MP3) e a timeline baixados, além
  de identificador, rótulo e data de criação. É a única fonte de verdade da biblioteca; não existe
  um registro equivalente persistido no backend.
- **Progresso de reprodução**: posição em segundos onde o usuário parou de ouvir um Estudo salvo
  específico, e uma marcação de conclusão quando o estudo é ouvido até o fim; associado 1:1 a um
  Estudo salvo.
- **Biblioteca local**: a coleção de todos os Estudos salvos e ainda não removidos no armazenamento
  local do navegador do usuário.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário consegue ver todos os estudos que já gerou anteriormente diretamente no
  próprio navegador, sem precisar ter guardado identificadores manualmente e sem que o backend
  mantenha nenhum histórico.
- **SC-002**: Após pausar, buscar outra posição ou recarregar normalmente, um usuário retoma o
  estudo com diferença máxima de 1 segundo em relação à posição persistida; durante reprodução
  ativa e visível, a posição persistida fica no máximo 5 segundos atrás da posição observada.
- **SC-003**: Um usuário consegue remover um estudo que não quer mais manter, e esse estudo deixa
  de ocupar espaço local e de aparecer na biblioteca imediatamente após a remoção.
- **SC-004**: Um estudo já salvo localmente pode ser ouvido integralmente mesmo quando o backend/API
  da Fase 4 está temporariamente indisponível.
- **SC-005**: Nenhum conteúdo de texto original completo é exposto ou retido como parte dos
  metadados da biblioteca — apenas um rótulo curto por estudo.
- **SC-006**: Quando o armazenamento local está indisponível ou esgotado, o usuário ainda consegue
  gerar e ouvir um novo estudo diretamente pela API, apenas sem conseguir salvá-lo na biblioteca.

## Assumptions

- **Uso local, sem autenticação**: como nas fases anteriores, o produto é local-first e de usuário
  único (Non-goals do `SPEC.md`); esta fase não introduz autenticação ou autorização.
- **Biblioteca por navegador/dispositivo, sem sincronização**: a biblioteca local não é
  sincronizada entre navegadores ou dispositivos diferentes nesta fase; cada instalação local
  (navegador) mantém sua própria biblioteca independente.
- **Salvamento automático na criação**: todo estudo gerado com sucesso pela API da Fase 4 é salvo
  automaticamente na biblioteca local no momento da criação (sem um passo explícito separado de
  "salvar"), desde que o armazenamento local esteja disponível — mantendo a experiência simples e
  evitando estudos "órfãos" que o usuário esqueceu de salvar.
- **Backend da Fase 4 não é alterado por esta fase**: nenhum endpoint de listagem, detalhe ou
  remoção de histórico é adicionado ao backend; a Fase 5 consome apenas os endpoints já existentes
  (criação, download de áudio, download de timeline) para obter os dados que serão armazenados
  localmente.
- **Mesma origem fora do desenvolvimento**: o proxy Vite existe apenas no ambiente de
  desenvolvimento. A implantação serve frontend e `/api` sob a mesma origem; suportar frontend e
  backend em origens distintas por CORS permanece fora do escopo.
- **Remoção permanente**: a remoção de um estudo salvo é definitiva (hard delete) nesta fase — não
  há lixeira ou período de recuperação, consistente com "No Overengineering" e com o fato de o
  usuário ser o único dono dos seus dados locais.
- **Sem expulsão automática de estudos antigos**: quando o armazenamento local está indisponível ou
  com cota esgotada, a biblioteca bloqueia apenas a operação afetada (ver FR-012); esta fase não
  implementa uma política automática de remoção de estudos antigos para liberar espaço.
- **Sem paginação nesta fase**: o volume esperado de estudos de um único usuário local é pequeno o
  suficiente para que a listagem local responda rapidamente sem paginação; isso pode ser revisado
  depois, caso uma necessidade real seja observada.
- **Rótulo automático é um resumo curto, não o texto completo**: o rótulo derivado do início do
  texto original é curto (poucas dezenas de caracteres) e não reproduz o conteúdo integral enviado,
  preservando a mesma proteção de privacidade já estabelecida na Fase 4.
