# Feature Specification: Offline e PWA consolidado

**Feature Branch**: `master`

**Created**: 2026-10-04

**Status**: Draft

**Input**: User description: "Fase 8 — Offline e PWA consolidado"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Continuar usando a biblioteca e os estudos salvos sem rede (Priority: P1)

Como estudante que já usou o aplicativo antes, quero abrir a biblioteca, tocar estudos salvos e
acompanhar o texto sincronizado mesmo sem conexão de internet, para estudar em qualquer lugar sem
depender de estar online.

**Why this priority**: É o valor central desta fase. A biblioteca, o áudio e o texto já vivem
localmente desde a Fase 5 e a Fase 7; sem o próprio aplicativo carregando offline, essa propriedade
local fica incompleta — o usuário ainda depende de rede só para abrir a aplicação.

**Independent Test**: Visitar o aplicativo uma vez online, colocar o navegador/dispositivo em modo
avião, reabrir o aplicativo e verificar que a biblioteca carrega, um estudo salvo reproduz
normalmente e o texto sincronizado aparece, tudo sem nenhuma requisição de rede bem-sucedida.

**Acceptance Scenarios**:

1. **Given** o usuário já visitou o aplicativo com sucesso ao menos uma vez online, **When** ele o
   reabre sem conexão de rede, **Then** a aplicação carrega normalmente a partir de uma cópia local
   do aplicativo, sem tela de erro do navegador.
2. **Given** o aplicativo carregado offline, **When** o usuário abre a biblioteca, **Then** todos os
   estudos previamente salvos aparecem exatamente como apareceriam online.
3. **Given** um estudo salvo com áudio e timeline válidos, **When** o usuário o reproduz offline,
   **Then** o áudio toca, o progresso é registrado e o texto sincronizado funciona como descrito na
   Fase 7, sem nenhuma chamada de rede.
4. **Given** o usuário volta a ficar online depois de usar o aplicativo offline, **When** a conexão é
   restabelecida, **Then** nenhuma funcionalidade já disponível offline é interrompida ou recarregada
   de forma disruptiva por causa da mudança de conectividade.

---

### User Story 2 - Instalar o aplicativo como um app (Priority: P2)

Como estudante que usa o aplicativo com frequência, quero poder instalá-lo na tela inicial ou na
dock do meu dispositivo, para abri-lo como um app independente em vez de precisar navegar até a URL
em uma aba do navegador toda vez.

**Why this priority**: Reforça o valor de propriedade local e acesso rápido, mas depende do
aplicativo já carregar offline (US1) para ser útil; sem instalabilidade, o acesso continua possível,
apenas menos conveniente.

**Independent Test**: Abrir o aplicativo em um navegador compatível, usar a ação de instalação do
próprio navegador/sistema operacional e verificar que o aplicativo passa a abrir em janela própria,
com nome e ícone reconhecíveis, sem a interface padrão de abas do navegador.

**Acceptance Scenarios**:

1. **Given** o aplicativo carregado em um navegador compatível com instalação de aplicativos web,
   **When** o usuário aciona a instalação, **Then** o navegador reconhece o aplicativo como
   instalável e completa a instalação com nome e ícone definidos para o HSS Study Voice.
2. **Given** o aplicativo instalado, **When** o usuário o abre a partir do ícone instalado, **Then**
   ele é exibido em janela própria, sem a barra de endereço e controles padrão de uma aba de
   navegador comum.
3. **Given** um navegador que não oferece suporte à instalação de aplicativos web, **When** o usuário
   acessa o aplicativo normalmente, **Then** ele continua funcionando em uma aba comum, sem erro
   nem oferta de instalação quebrada.

---

### User Story 3 - Saber quando uma ação exige conexão (Priority: P3)

Como estudante criando um novo estudo, quero saber claramente quando estou offline e que, por isso,
não é possível gerar um novo estudo agora, para não ficar esperando uma ação que não vai completar
nem receber um erro confuso.

**Why this priority**: Complementa o valor central ao evitar frustração e confusão, mas não bloqueia
o uso do que já está salvo; sem esse aviso, o usuário ainda consegue usar a biblioteca offline (US1),
apenas sem clareza sobre por que a criação de um novo estudo não funciona.

**Independent Test**: Colocar o aplicativo offline, tentar criar um novo estudo e verificar que o
sistema impede a tentativa com uma mensagem clara sobre a necessidade de conexão, em vez de tentar a
chamada de rede e falhar de forma genérica.

**Acceptance Scenarios**:

1. **Given** o aplicativo sem conexão de rede, **When** o usuário tenta criar um novo estudo,
   **Then** o sistema impede a tentativa e exibe uma mensagem clara informando que essa ação requer
   conexão com a internet.
2. **Given** o aplicativo sem conexão de rede, **When** o usuário navega pela interface, **Then** um
   indicador visível comunica o estado offline, sem a necessidade de tentar uma ação para descobrir
   que não há rede.
3. **Given** o aplicativo exibindo o estado offline, **When** a conexão é restabelecida, **Then** o
   indicador reflete o estado online e a criação de novos estudos volta a ficar disponível, sem exigir
   que o usuário recarregue manualmente a página.

### Edge Cases

- O usuário acessa o aplicativo pela primeira vez já sem conexão de rede, antes de qualquer visita
  online anterior: não há cópia local do aplicativo para carregar, e o sistema não pode fingir que
  isso é possível; o comportamento esperado é o mesmo de qualquer site inacessível offline sem visita
  prévia.
- A conexão cai no meio de uma criação de estudo já em andamento (requisição enviada, resposta ainda
  pendente): o usuário é informado de que a ação não pôde ser concluída, sem a interface travar
  esperando indefinidamente nem registrar um estudo parcial ou corrompido na biblioteca.
- Uma nova versão do aplicativo é publicada enquanto o usuário tem uma sessão aberta com áudio
  tocando: a reprodução em andamento não é interrompida pela atualização; a nova versão só passa a
  valer em uma próxima abertura ou mediante ação explícita do usuário.
- O navegador do usuário não suporta Service Worker ou instalação de aplicativos web: o aplicativo
  continua funcionando normalmente em modo online, sem erros nem funcionalidades quebradas por causa
  da ausência desse suporte.
- O armazenamento do navegador usado para manter a cópia local do aplicativo atinge um limite e a
  atualização do cache falha: a aplicação não perde os estudos já salvos na biblioteca (Fase 5) e
  continua tentando funcionar online quando necessário, em vez de falhar de forma silenciosa.
- O usuário tem o aplicativo aberto em mais de uma aba/janela ao mesmo tempo e uma nova versão é
  ativada em uma delas: as demais abas continuam operando de forma consistente, sem perda de
  progresso de reprodução em andamento.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Depois de ao menos uma visita online bem-sucedida, o sistema MUST permitir que a
  aplicação (interface, não os dados) seja carregada e utilizada integralmente sem nenhuma conexão de
  rede.
- **FR-002**: O sistema MUST manter uma cópia local dos arquivos estáticos necessários para carregar
  a aplicação (equivalente ao "app shell"), atualizando essa cópia automaticamente quando uma nova
  versão é publicada e detectada.
- **FR-003**: O sistema MUST expor um manifesto de aplicativo web com nome, ícones e cores
  consistentes com o Design System HSS Music (Fase 6), permitindo que navegadores compatíveis
  ofereçam a instalação do aplicativo.
- **FR-004**: O sistema MUST comunicar visivelmente ao usuário quando o aplicativo está sem conexão
  de rede, e MUST atualizar essa indicação automaticamente quando a conexão é restabelecida ou
  perdida, sem exigir recarregamento manual.
- **FR-005**: Quando o aplicativo estiver offline, o sistema MUST impedir a tentativa de criar um
  novo estudo e MUST informar claramente ao usuário que essa ação requer conexão com a internet, em
  vez de tentar a chamada de rede e expor um erro genérico.
- **FR-006**: Toda funcionalidade já suportada para estudos salvos localmente — listar a biblioteca,
  reproduzir áudio, acompanhar o texto sincronizado e registrar progresso — MUST continuar funcionando
  integralmente offline, sem regressão em relação ao comportamento já estabelecido nas Fases 5 e 7.
- **FR-007**: Quando uma nova versão do aplicativo for publicada, o sistema MUST oferecer ao usuário
  um caminho controlado para atualizar (nova abertura ou ação explícita), e MUST NOT interromper de
  forma abrupta uma reprodução de áudio em andamento para aplicar a atualização.
- **FR-008**: Se o navegador do usuário não suportar Service Worker, cache local de aplicativo ou
  instalação de aplicativos web, o sistema MUST continuar funcionando normalmente em modo online,
  sem travar, lançar erros não tratados ou oferecer instalação que não funcione.
- **FR-009**: Esta fase MUST NOT alterar o esquema de armazenamento local da biblioteca (IndexedDB,
  Fase 5), os contratos de API existentes (Fase 4) ou o formato da timeline (Fase 3.1); a cópia local
  do aplicativo introduzida aqui cobre apenas os arquivos estáticos da interface, não os dados do
  usuário.
- **FR-010**: Todos os testes existentes MUST continuar aprovados, e a nova lógica de cache do
  aplicativo, manifesto, detecção de conectividade e bloqueio de criação offline MUST ter verificação
  automatizada adequada ao seu nível.
- **FR-011**: O indicador de estado offline/online e a mensagem de bloqueio de criação de estudo
  MUST ser perceptíveis por mais de um sinal visual (não depender apenas de cor) e MUST ser
  identificáveis por tecnologia assistiva.

### Scope Boundaries

- Geração ou fila de criação de estudos enquanto offline (sincronização em segundo plano quando a
  conexão retornar) está fora do escopo; a criação de estudos continua exigindo conexão no momento da
  ação, como já ocorre hoje.
- Notificações push estão fora do escopo.
- Empacotamento como aplicativo nativo para lojas de aplicativos (iOS/Android via wrappers como
  Capacitor ou similares) está fora do escopo; a instalabilidade desta fase é limitada ao padrão web
  de aplicativos instaláveis (Web App Manifest/Service Worker) em navegadores compatíveis.
- Alterações no backend, nos endpoints da API (Fase 4) ou no esquema de armazenamento local (Fase 5)
  estão fora do escopo.
- Sincronização de biblioteca entre dispositivos diferentes está fora do escopo; a propriedade local
  continua sendo por navegador/dispositivo, como já estabelecido desde a Fase 5.

### Key Entities

- **App Shell Cache**: Cópia local dos arquivos estáticos (interface, estilos, código da aplicação)
  necessários para carregar o aplicativo sem rede, mantida e atualizada automaticamente.
- **Web App Manifest**: Descritor de instalabilidade do aplicativo — nome, ícones e cores — usado
  pelo navegador para oferecer a instalação como aplicativo independente.
- **Connectivity Status**: Estado atual de conectividade do aplicativo (online/offline), refletido na
  interface e usado para decidir se ações que dependem de rede podem ser tentadas.
- **Update Availability**: Sinal de que uma nova versão do App Shell Cache está disponível e pronta
  para ser aplicada em uma próxima abertura ou mediante ação do usuário.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Depois de uma visita online bem-sucedida, 100% dos estudos já salvos podem ser abertos,
  reproduzidos e lidos com texto sincronizado totalmente sem conexão de rede nos cenários testados.
- **SC-002**: O aplicativo é reconhecido como instalável em 100% dos navegadores de desktop e mobile
  testados que suportam Web App Manifest e Service Worker, exibindo nome e ícone corretos após a
  instalação.
- **SC-003**: Em 100% das tentativas de criar um novo estudo offline nos cenários testados, o sistema
  bloqueia a ação com uma mensagem clara, sem erros não tratados nem travamentos da interface.
- **SC-004**: 100% dos cenários de biblioteca, reprodução, progresso e texto sincronizado já suportados
  antes desta fase continuam passando sem regressão depois da introdução do suporte offline.
- **SC-005**: Em 100% dos cenários testados de publicação de nova versão, usuários com reprodução de
  áudio em andamento não têm a reprodução interrompida pela atualização do aplicativo.
- **SC-006**: Em navegadores sem suporte a Service Worker ou instalação, o aplicativo mantém 100% das
  funcionalidades online já existentes, sem nenhuma funcionalidade quebrada pela ausência desse
  suporte.

## Assumptions

- A biblioteca local (IndexedDB, Fase 5) e o player com texto sincronizado (Fase 7) já funcionam sem
  rede para os próprios dados; esta fase cobre o carregamento do aplicativo em si e a comunicação
  clara do estado de conectividade, sem alterar como os dados já são armazenados ou consumidos.
- Os ícones e cores do manifesto do aplicativo reaproveitam os tokens visuais já definidos pelo Design
  System HSS Music (Fase 6).
- O backend/API da Fase 4 continua sendo exigido apenas para gerar novos estudos; esta fase não
  introduz capacidade de gerar áudio offline nem fila de geração pendente.
- O público-alvo desta fase usa navegadores desktop e mobile modernos com suporte padrão a Service
  Worker, Cache Storage e Web App Manifest, consistente com o contexto de uso já descrito para o
  produto; navegadores sem esse suporte continuam funcionando apenas em modo online (degradação
  graciosa, FR-008).
- A atualização do aplicativo segue um modelo de "pronta para a próxima abertura ou ação explícita do
  usuário", em vez de recarregamento forçado e imediato, para não interromper reprodução em
  andamento.
- Esta fase não cobre múltiplos dispositivos ou sincronização entre eles; cada instalação/navegador
  mantém sua própria cópia local do aplicativo e sua própria biblioteca, como já estabelecido.
