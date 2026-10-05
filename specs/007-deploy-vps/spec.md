# Feature Specification: Deploy em VPS do HSS Study Voice

**Feature Branch**: `007-deploy-vps`

**Created**: 2026-10-04

**Status**: Draft

**Input**: User description: "Fase 9 — Deploy VPS do HSS Study Voice"

## Clarifications

### Session 2026-10-04

- Q: Como o frontend e o backend devem ser expostos em produção (topologia de domínio)? →
  A: Mesma origem — domínio único, frontend em `/` e backend FastAPI exposto em `/api` via
  reverse proxy. Sem necessidade de CORS entre frontend e backend em produção.
- Q: Qual nível de rollback é esperado para esta fase, caso uma nova versão publicada falhe?
  → A: Rollback manual, porém documentado (ex.: checkout do commit/tag anterior e reinício do
  serviço). Automação de rollback não faz parte do escopo desta fase.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Aplicação acessível publicamente (Priority: P1)

Como usuário, acesso o HSS Study Voice por uma URL pública HTTPS (fora da máquina de
desenvolvimento) e consigo colar texto, gerar áudio e reproduzi-lo, exatamente como no
ambiente local.

**Why this priority**: Sem isso o produto não existe fora da máquina do desenvolvedor. É o
valor central desta fase — tudo o mais (processo repetível, saúde, certificado) só importa
depois que o fluxo fim-a-fim funciona em produção.

**Independent Test**: A partir de um dispositivo fora da rede de desenvolvimento, acessar a
URL pública, colar um texto de estudo, gerar o áudio e reproduzi-lo com sucesso.

**Acceptance Scenarios**:

1. **Given** o backend e o frontend publicados no VPS, **When** o usuário acessa a URL pública
   via HTTPS, **Then** a aplicação carrega e a geração de áudio funciona fim-a-fim, com o
   mesmo resultado observado no ambiente local.
2. **Given** uma tentativa de acesso por HTTP (inseguro), **When** o usuário acessa a URL,
   **Then** é redirecionado automaticamente para HTTPS.

---

### User Story 2 - Processo de deploy repetível (Priority: P2)

Como mantenedor, publico uma nova versão da aplicação no VPS seguindo um processo documentado
e repetível, sem depender de comandos improvisados ou de memória do que foi feito na última
vez.

**Why this priority**: Sem um processo repetível, cada publicação é manual, arriscada e
intransferível. É pré-requisito para qualquer fase futura (10+) chegar a produção.

**Independent Test**: Executar o processo de deploy documentado (do início ao fim) e verificar
que a aplicação sobe corretamente apenas com os passos registrados.

**Acceptance Scenarios**:

1. **Given** uma alteração de código já aprovada, **When** o processo de deploy documentado é
   executado, **Then** a nova versão fica disponível publicamente sem exigir passos não
   documentados.
2. **Given** uma falha durante a publicação de uma nova versão, **When** o processo é
   interrompido, **Then** a versão anterior em produção continua disponível (sem
   indisponibilidade permanente).

---

### User Story 3 - Preservação da propriedade local dos dados (Priority: P2)

Como usuário, confio que meu texto, áudio e progresso continuam vivendo no meu navegador
mesmo com a aplicação publicada remotamente, e que o servidor não retém cópias desnecessárias
depois de processar minha solicitação.

**Why this priority**: É um princípio já estabelecido da constituição do projeto
(Local-First Ownership) e o maior risco de regressão ao sair do ambiente local — um servidor
remoto mal configurado pode acumular dados de usuários sem que ninguém note.

**Independent Test**: Gerar um áudio em produção e inspecionar o sistema de arquivos do
servidor para confirmar que nenhum arquivo temporário de texto/áudio do usuário permanece após
a resposta, em sucesso ou falha.

**Acceptance Scenarios**:

1. **Given** uma geração de áudio concluída com sucesso em produção, **When** o processamento
   termina, **Then** nenhum arquivo temporário de texto/áudio do usuário permanece no
   servidor.
2. **Given** uma falha durante o processamento em produção, **When** o erro ocorre, **Then**
   os arquivos temporários também são removidos, preservando a mesma garantia do ambiente
   local.

---

### User Story 4 - Visibilidade de saúde do serviço (Priority: P3)

Como mantenedor, consigo verificar rapidamente se a aplicação publicada está saudável
(endpoint de health, certificado HTTPS válido) para detectar indisponibilidade antes que um
usuário reclame.

**Why this priority**: Prioridade menor que o deploy funcionar — mas necessário para operar o
serviço com um mínimo de confiança depois que ele está no ar.

**Independent Test**: Consultar o endpoint de health público e confirmar resposta saudável;
verificar a validade do certificado TLS com uma ferramenta padrão.

**Acceptance Scenarios**:

1. **Given** a aplicação publicada, **When** o endpoint de health é consultado publicamente,
   **Then** retorna um status saudável e metadados de configuração não sensíveis.
2. **Given** o certificado HTTPS configurado, **When** verificado a qualquer momento,
   **Then** está válido e configurado para renovação automática.

---

### Edge Cases

- O que acontece se múltiplas gerações de áudio simultâneas saturarem a CPU/memória do VPS
  (Piper TTS/FFmpeg são sensíveis a CPU)?
- Como o sistema se comporta se a renovação automática do certificado HTTPS falhar?
- O que acontece se o processo de deploy de uma nova versão falhar no meio do caminho (ex.:
  dependência ausente no VPS)?
- Como o backend se recupera de uma reinicialização inesperada do VPS (reboot)? Ele deve
  voltar a rodar sem intervenção manual?
- O que acontece se o DNS do domínio ainda não tiver propagado quando o deploy for concluído?
- Como requisições vindas de origens não autorizadas são tratadas pela API em produção (CORS)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST expor o backend FastAPI publicamente via HTTPS em um domínio
  próprio.
- **FR-002**: O sistema MUST expor o frontend (build de produção do PWA) publicamente via
  HTTPS.
- **FR-003**: O sistema MUST redirecionar automaticamente todo tráfego HTTP para HTTPS.
- **FR-004**: O sistema MUST renovar automaticamente o certificado HTTPS antes da expiração,
  sem exigir intervenção manual recorrente.
- **FR-005**: O backend MUST ser reiniciado automaticamente após falha do processo ou
  reinicialização do servidor, sem exigir login manual para religá-lo.
- **FR-006**: O sistema MUST preservar em produção a limpeza de arquivos temporários de
  processamento (texto/áudio) após sucesso ou falha, mantendo a garantia já existente no
  ambiente local (constituição — Local-First Ownership e Segurança por Padrão).
- **FR-007**: O sistema MUST servir frontend e backend sob o mesmo domínio em produção —
  frontend nas rotas raiz (`/`) e backend FastAPI sob `/api`, roteado pelo reverse proxy. Por
  serem mesma origem, a API MUST NOT depender de CORS entre frontend e backend; apenas
  requisições de outras origens, se existirem, MUST ser rejeitadas por padrão.
- **FR-008**: O sistema MUST expor um endpoint de health acessível publicamente para
  verificação de disponibilidade, sem vazar segredos de configuração.
- **FR-009**: O processo de deploy MUST ser documentado e repetível, permitindo publicar uma
  nova versão sem passos manuais não registrados.
- **FR-010**: O processo de deploy MUST incluir um procedimento documentado de rollback
  manual (ex.: checkout do commit/tag anterior e reinício do serviço) capaz de restaurar a
  versão anterior em caso de falha da nova versão. Automação de rollback está fora do escopo
  desta fase.
- **FR-011**: O acesso administrativo ao VPS MUST usar autenticação SSH por chave e um usuário
  sem privilégios de root para as operações de deploy do dia a dia.
- **FR-012**: O sistema MUST manter, em produção, os logs do backend livres do texto completo
  submetido pelos usuários, preservando a garantia já existente localmente (constituição —
  Segurança por Padrão).
- **FR-013**: O backend em produção MUST continuar usando exclusivamente Python, FastAPI,
  Piper TTS e FFmpeg; nenhuma infraestrutura adicional (fila, banco de dados, cache) MUST ser
  introduzida sem justificativa documentada, conforme a constituição do projeto.

### Key Entities *(include if feature involves data)*

Esta fase não introduz dados de domínio novos (nenhuma entidade de negócio é criada,
alterada ou persistida no servidor). Os elementos conceituais envolvidos são operacionais:

- **Ambiente de Produção**: o VPS e sua configuração (sistema operacional, reverse proxy,
  certificado HTTPS, processos supervisionados do backend e dos arquivos estáticos do
  frontend).
- **Processo de Deploy**: a sequência documentada e repetível que leva uma versão aprovada do
  código até o ambiente de produção, incluindo o caminho de rollback.

## Success Criteria *(mandatory)*

**Nota de aceite (adicionada em 2026-10-04)**: SC-002 e a cláusula de ciclo de renovação de
SC-005 exigem, por definição, uma janela de observação (7 dias; ciclo de renovação do
certificado) maior do que o tempo de implementação desta fase. Eles não bloqueiam o aceite
inicial do deploy — o aceite inicial usa verificações pontuais de health e de validade do
certificado (`quickstart.md`). SC-002/SC-005 são confirmados depois, por acompanhamento
operacional documentado e iniciado nesta fase (`data-model.md`, Validação de Longo Prazo;
`quickstart.md`, Acompanhamento Pós-Deploy), sem reabrir esta fase para isso.

### Measurable Outcomes

- **SC-001**: Um usuário com acesso à internet, fora da rede de desenvolvimento, consegue
  carregar a aplicação publicada e concluir a geração de um áudio de estudo completo.
- **SC-002**: O endpoint de health da aplicação publicada responde com sucesso em
  verificações realizadas ao longo de 7 dias consecutivos após o deploy, sem indisponibilidade
  não planejada.
- **SC-003**: Uma nova versão aprovada pode ser publicada em produção seguindo o processo
  documentado em menos de 15 minutos, sem apoio do autor original do processo de deploy.
- **SC-004**: Uma auditoria manual do sistema de arquivos do servidor, realizada minutos após
  uma geração de áudio, não encontra nenhum arquivo de texto ou áudio de usuário remanescente.
- **SC-005**: O certificado HTTPS permanece válido de forma contínua, com pelo menos um ciclo
  completo de renovação automática validado sem intervenção manual.

## Assumptions

- O provedor de VPS ainda não foi escolhido; qualquer VPS Linux (recomendado: Ubuntu LTS) com
  capacidade suficiente para a inferência do Piper TTS e para o FFmpeg atende a esta fase, até
  que um provedor e um dimensionamento específicos (vCPU/RAM) sejam definidos no plano técnico.
- Um domínio próprio está disponível ou será adquirido antes da implementação; esta fase cobre
  a configuração de DNS/HTTPS do domínio, não o registro do domínio em si.
- Um reverse proxy (ex.: Nginx ou Caddy) é necessário para servir HTTPS, redirecionar
  HTTP→HTTPS e rotear entre o frontend estático e o backend FastAPI. Isso é tratado como
  infraestrutura mínima necessária para o objetivo da fase, não como uma adição especulativa
  (constituição — Princípio VII, Sem Overengineering).
- Um pipeline de CI/CD totalmente automatizado está fora do escopo desta fase; um processo de
  deploy manual, porém documentado, versionado e repetível (scripts), é aceitável para o MVP de
  publicação. Automação adicional pode ser proposta como iteração futura.
- Não há banco de dados a ser provisionado nesta fase, pois o backend permanece sem
  persistência própria (princípio Local-First Ownership), o que reduz significativamente o
  escopo de infraestrutura.
- Monitoramento e alertas formais (ferramentas de observabilidade dedicadas) estão fora do
  escopo desta fase; a verificação de saúde via endpoint existente é suficiente para o MVP de
  publicação.
- Backup de dados de usuário não se aplica, pois esses dados residem no navegador do usuário;
  apenas código-fonte e configuração de servidor precisam de uma estratégia de recuperação
  (ex.: reimplantação a partir do repositório Git).
