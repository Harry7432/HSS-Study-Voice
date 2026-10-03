# Feature Specification: API de geração de estudos em áudio

**Feature Branch**: `master`

**Created**: 2026-10-03

**Status**: Draft

**Input**: User description: "Fase 4 — API FastAPI para geração de estudos em áudio"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Gerar um estudo em áudio a partir de texto (Priority: P1)

Como estudante ou educador, quero enviar um texto (bruto ou em Markdown) para o serviço e receber
de volta o áudio falado correspondente, para transformar material de estudo em algo que eu possa
ouvir em vez de ler.

**Why this priority**: É o valor central da Fase 4 — sem este fluxo, o pipeline de síntese já
construído nas fases anteriores permanece inacessível a qualquer cliente externo.

**Independent Test**: Enviar um texto de exemplo com múltiplas frases e Markdown básico (títulos,
negrito, listas) ao endpoint de criação e verificar que a resposta contém um identificador do
estudo, metadados de geração (duração, número de chunks, tamanho do arquivo, tempo de
processamento) e que o áudio final está disponível para download.

**Acceptance Scenarios**:

1. **Given** um texto válido não vazio, **When** o cliente submete o texto para geração, **Then** o
   serviço processa o texto pelo pipeline de normalização/chunking existente, sintetiza o áudio e
   retorna um identificador único do estudo junto com os metadados de geração.
2. **Given** um texto em Markdown com formatação (títulos, ênfase, listas), **When** o estudo é
   gerado, **Then** o áudio resultante não contém marcações de Markdown lidas em voz alta — apenas o
   conteúdo semântico.
3. **Given** um texto vazio ou somente espaços em branco, **When** o cliente submete a requisição,
   **Then** o serviço rejeita a requisição com um erro claro, sem gerar nenhum artefato de áudio.
4. **Given** parâmetros opcionais de voz, velocidade ou taxa de bits informados na requisição,
   **When** o estudo é gerado, **Then** o serviço usa esses valores em vez dos padrões configurados.

---

### User Story 2 - Baixar o áudio de um estudo já gerado (Priority: P2)

Como consumidor da API, quero poder buscar o arquivo de áudio de um estudo usando o identificador
retornado na criação, para poder baixar ou reproduzir o resultado sem precisar reenviar o texto
original.

**Why this priority**: Gerar o áudio sem uma forma de recuperá-lo depois (ex.: após a conexão
inicial ser interrompida, ou para reuso em outra tela) reduz bastante o valor prático da User
Story 1.

**Independent Test**: Gerar um estudo via User Story 1, anotar o identificador retornado, e então
buscar o áudio desse estudo em uma requisição separada, confirmando que o arquivo retornado
corresponde ao que foi gerado originalmente (mesmo conteúdo/tamanho).

**Acceptance Scenarios**:

1. **Given** um estudo gerado com sucesso, **When** o cliente solicita o áudio pelo identificador
   retornado, **Then** o serviço retorna o arquivo de áudio correspondente.
2. **Given** um identificador que não corresponde a nenhum estudo gerado, **When** o cliente solicita
   o áudio desse identificador, **Then** o serviço retorna um erro claro indicando que o estudo não
   foi encontrado, sem expor detalhes internos do sistema.

---

### User Story 3 - Obter a timeline sincronizada do estudo (Priority: P3)

Como consumidor da API que vai construir uma experiência de reprodução (ex.: destacar o texto
conforme o áudio avança), quero recuperar a timeline de sincronização frase-a-frase de um estudo já
gerado, para poder acompanhar visualmente a leitura em voz alta sem reprocessar o áudio.

**Why this priority**: A timeline sincronizada já é produzida internamente pelo pipeline (Fase 3),
mas hoje não é acessível via API; expô-la é valor adicional sobre o áudio puro, porém não bloqueia o
uso básico de ouvir o estudo (por isso prioridade P3).

**Independent Test**: Gerar um estudo via User Story 1 e buscar sua timeline pelo identificador
retornado, verificando que ela contém uma entrada ordenada por frase, com limites de tempo
consistentes com a duração do áudio gerado.

**Acceptance Scenarios**:

1. **Given** um estudo gerado com sucesso, **When** o cliente solicita a timeline pelo identificador
   retornado, **Then** o serviço retorna a timeline sincronizada por frase associada a esse áudio.
2. **Given** um identificador que não corresponde a nenhum estudo gerado, **When** o cliente solicita
   a timeline desse identificador, **Then** o serviço retorna um erro claro indicando que o estudo
   não foi encontrado.

---

### Edge Cases

- O que acontece quando o texto enviado excede um tamanho muito grande (ex.: um livro inteiro)?
  Dentro do limite configurado (`MAX_REQUEST_TEXT_CHARS`), o serviço continua processando via
  chunking existente, sem travar indefinidamente nem falhar silenciosamente. Acima desse limite, a
  requisição é rejeitada com um erro claro antes de iniciar o chunking ou a síntese.
- Como o sistema se comporta quando o motor de síntese de voz (TTS) ou o `ffmpeg` não estão
  disponíveis no momento da requisição? O cliente deve receber um erro claro e acionável, sem
  stack trace interno exposto.
- O que acontece se a geração falhar no meio do processamento (ex.: uma frase não pode ser
  sintetizada)? Nenhum artefato parcial ou corrompido deve ficar disponível para download.
- Como o sistema trata um identificador de estudo malformado (não apenas inexistente, mas em
  formato inválido) na busca de áudio ou timeline?
- O que acontece com arquivos temporários se o cliente cancelar a requisição ou a conexão cair
  durante a geração? Nenhum arquivo temporário deve permanecer após a falha.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE expor uma operação para submeter texto (bruto ou Markdown) e iniciar a
  geração de um estudo em áudio, retornando o resultado pronto na mesma resposta (processamento
  síncrono).
- **FR-002**: O sistema DEVE rejeitar textos vazios ou compostos apenas por espaços em branco com um
  erro claro, sem gerar nenhum artefato de áudio.
- **FR-003**: O sistema DEVE processar o texto submetido através do pipeline de normalização de
  Markdown e chunking já existente antes da síntese de voz.
- **FR-004**: O sistema DEVE permitir que o cliente informe, opcionalmente, voz, velocidade e taxa de
  bits para a geração, usando os valores padrão configurados quando omitidos.
- **FR-005**: O sistema DEVE gerar um único arquivo de áudio final (MP3) por estudo submetido.
- **FR-006**: O sistema DEVE gerar a timeline sincronizada por frase para cada estudo, usando o
  mecanismo de sincronização já existente.
- **FR-007**: O sistema DEVE atribuir a cada estudo gerado um identificador único, que o cliente pode
  usar posteriormente para buscar o áudio e a timeline desse estudo.
- **FR-008**: O sistema DEVE retornar, na resposta de criação, metadados do estudo gerado: duração do
  áudio, quantidade de chunks processados, tamanho do arquivo e tempo total de processamento.
- **FR-009**: O sistema DEVE permitir recuperar o arquivo de áudio de um estudo previamente gerado a
  partir do seu identificador.
- **FR-010**: O sistema DEVE permitir recuperar a timeline sincronizada de um estudo previamente
  gerado a partir do seu identificador.
- **FR-011**: O sistema DEVE retornar um erro claro e não técnico quando o identificador informado não
  corresponder a nenhum estudo gerado, sem expor detalhes internos (stack traces, caminhos de
  arquivo, etc.).
- **FR-012**: O sistema DEVE retornar um erro claro quando a geração falhar por qualquer motivo
  (motor de síntese indisponível, falha de conversão de áudio, etc.), sem deixar artefatos parciais
  disponíveis para download.
- **FR-013**: O sistema DEVE remover quaisquer arquivos temporários de processamento ao final de cada
  requisição, com sucesso ou falha.

*Fora de escopo nesta fase (ver Assumptions): geração assíncrona com acompanhamento de progresso, e
listagem/histórico de estudos já gerados.*

### Key Entities

- **Estudo em Áudio**: representa uma submissão de texto processada pelo pipeline. Possui um
  identificador único, os parâmetros de geração usados (voz, velocidade, taxa de bits) e os
  metadados resultantes (duração, tamanho, tempo de processamento). O texto original enviado na
  criação não é persistido após a geração — apenas o identificador e os artefatos gerados (áudio e
  timeline) permanecem recuperáveis.
- **Áudio Gerado**: o arquivo MP3 final associado a um Estudo em Áudio, recuperável pelo
  identificador do estudo.
- **Timeline Sincronizada**: a sequência ordenada de frases com seus limites de tempo dentro do
  áudio gerado, associada a um Estudo em Áudio pelo mesmo identificador.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário consegue enviar um texto de estudo típico (até algumas páginas) e obter o
  identificador do estudo gerado em uma única interação com a API.
- **SC-002**: 100% das submissões com texto vazio ou inválido são rejeitadas com uma mensagem de erro
  compreensível, sem gerar arquivos de áudio órfãos.
- **SC-003**: Um usuário consegue recuperar o áudio e a timeline de um estudo gerado anteriormente
  usando apenas o identificador retornado na criação, sem precisar reenviar o texto original.
- **SC-004**: Markdown presente no texto de entrada nunca é lido em voz alta como marcação no áudio
  final gerado pela API.
- **SC-005**: Falhas de geração (motor de voz ou conversão de áudio indisponíveis) nunca deixam
  arquivos temporários ou parciais acessíveis via API.

## Assumptions

- **Processamento síncrono**: a operação de criação de um estudo bloqueia até o áudio e a timeline
  estarem prontos, devolvendo o resultado na própria resposta. Acompanhamento assíncrono de
  progresso (fila de jobs, polling de status) fica fora do escopo desta fase e é tratado como
  iteração futura, conforme já indicado em `SPEC.md` (seção 11).
- **Sem listagem/histórico**: esta fase cobre apenas criar um novo estudo e buscar esse mesmo estudo
  pelo identificador retornado. Não há endpoint para listar todos os estudos já gerados.
- **Uso local, sem autenticação**: como o produto é local-first e de usuário único (conforme
  Non-goals do `SPEC.md`), esta fase não introduz autenticação ou autorização de usuários.
- **Limite de tamanho de texto configurável e generoso**: o chunking já existente lida com textos
  longos; esta fase impõe apenas um limite explícito e configurável (`MAX_REQUEST_TEXT_CHARS`,
  padrão de 200.000 caracteres) como proteção de recurso, sem restringir o uso típico de textos de
  estudo — não é um teto artificial baixo, apenas uma fronteira de segurança explícita.
- **Reaproveitamento do pipeline existente**: a API reaproveita o `TextPreprocessingPipeline` e o
  `AudioOrchestrator` (incluindo geração de timeline) já implementados nas Fases 1–3, sem alterar o
  comportamento interno desses componentes.
