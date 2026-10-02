# Feature Specification: Timeline de sincronizacao texto-audio

**Feature Branch**: `master`

**Created**: 2026-10-01

**Status**: Draft

**Input**: User description: "Fase 3.1 - Timeline de sincronizacao texto-audio. Gerar metadata
temporal por frase junto ao MP3 final, mantendo chunks como agrupamento pai, usando limites de
amostras PCM reais e vinculando a timeline ao audio por SHA-256."

## Clarifications

### Session 2026-10-01

- Q: Se a timeline falhar apos o audio ser gerado, quais artefatos devem permanecer disponiveis? →
  A: Nao publicar nenhum artefato novo; preservar o par anterior, se existir.
- Q: Qual etapa deve definir as fronteiras canonicas das frases usadas pela timeline? → A:
  Segmentar frases no texto normalizado antes de formar os chunks.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Localizar frases no audio (Priority: P1)

Como consumidor do artefato de estudo, quero receber limites temporais para cada frase falada para
que uma experiencia de reproducao futura possa destacar e acompanhar o texto correto sem analisar
novamente o audio.

**Why this priority**: A correspondencia entre frase e audio e o valor central desta fase; sem ela,
nao existe base confiavel para sincronizacao futura.

**Independent Test**: Gerar um audio com varias frases de duracoes conhecidas e verificar que cada
frase aparece uma unica vez, na ordem correta, com limites que correspondem ao audio produzido.

**Acceptance Scenarios**:

1. **Given** um texto com varias frases, **When** o MP3 e gerado com sucesso, **Then** uma timeline
   canonica acompanha o audio e contem uma entrada ordenada para cada frase falada.
2. **Given** uma frase da timeline, **When** seus limites sao convertidos pela taxa de amostragem
   declarada, **Then** o intervalo resultante identifica a parte correspondente do audio.
3. **Given** um audio com uma unica frase, **When** a geracao termina, **Then** a timeline contem uma
   unica entrada que comeca na amostra zero e termina no total de amostras do audio PCM.

---

### User Story 2 - Preservar o contexto dos chunks (Priority: P2)

Como consumidor da timeline, quero que as frases continuem agrupadas por seus chunks de origem para
que seja possivel navegar tanto pela unidade de leitura quanto pelo agrupamento usado no pipeline.

**Why this priority**: O agrupamento preserva a estrutura ja usada pelo produto e evita que a nova
metadata quebre a rastreabilidade do pipeline existente.

**Independent Test**: Gerar audio a partir de dois ou mais chunks, cada um com frases conhecidas, e
confirmar que todas as frases pertencem ao chunk correto e que os limites do chunk abrangem
exatamente suas frases.

**Acceptance Scenarios**:

1. **Given** varios chunks com uma ou mais frases, **When** a timeline e produzida, **Then** os chunks
   permanecem na ordem original e cada frase aparece dentro de um unico chunk pai.
2. **Given** um chunk com varias frases, **When** seus limites sao examinados, **Then** o inicio do
   chunk coincide com o inicio da primeira frase e o fim coincide com o fim da ultima frase.

---

### User Story 3 - Verificar a correspondencia com o MP3 (Priority: P3)

Como consumidor local dos artefatos, quero verificar que a timeline pertence exatamente ao MP3 que
estou reproduzindo para evitar sincronizacao incorreta causada por arquivos trocados ou alterados.

**Why this priority**: A verificacao de integridade impede o uso silencioso de metadata valida com o
audio errado.

**Independent Test**: Comparar a identificacao criptografica declarada com o MP3 original e com uma
copia alterada; somente o arquivo original deve ser aceito como correspondente.

**Acceptance Scenarios**:

1. **Given** um MP3 e sua timeline, **When** a identificacao do arquivo e recalculada, **Then** ela
   corresponde ao valor registrado na timeline.
2. **Given** um MP3 alterado ou diferente, **When** ele e comparado com a timeline, **Then** a
   divergencia pode ser detectada sem consultar qualquer servico externo.

### Edge Cases

- Uma entrada vazia ou sem conteudo falavel nao produz um par MP3/timeline concluido.
- Uma unica frase em um unico chunk produz limites validos sem exigir casos especiais do consumidor.
- Frases com texto identico continuam sendo entradas distintas, identificadas por sua posicao.
- Uma frase logica dividida internamente por limite de tamanho continua sendo uma unica entrada de
  frase, com limites que cobrem todos os seus fragmentos de audio.
- Diferencas de taxa de amostragem ou arquivos WAV invalidos interrompem a geracao com erro claro;
  um conjunto parcial nao e apresentado como resultado concluido.
- Falha ao finalizar ou gravar a timeline nao publica nenhum artefato novo e preserva o par anterior
  valido, se existir.
- Caracteres acentuados e demais caracteres Unicode sao preservados no texto associado a frase.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST gerar uma timeline JSON canonica para cada MP3 concluido com sucesso.
- **FR-002**: A timeline MUST declarar uma versao de formato que permita evolucao e validacao futura
  sem interpretacao ambigua.
- **FR-003**: A timeline MUST identificar o MP3 associado por seu SHA-256 calculado depois que o
  arquivo final estiver completo.
- **FR-004**: A timeline MUST declarar a taxa de amostragem, o total de amostras PCM e a identificacao
  do artefato de audio ao qual pertence.
- **FR-005**: A timeline MUST representar chunks em ordem, cada um contendo suas frases tambem em
  ordem e com identificadores posicionais estaveis dentro do documento.
- **FR-006**: Cada frase MUST registrar o texto normalizado efetivamente enviado para sintese,
  `start_sample` e `end_sample`.
- **FR-007**: Todo `start_sample` e `end_sample` MUST ser um inteiro nao negativo e MUST representar
  um intervalo semiaberto, incluindo `start_sample` e excluindo `end_sample`.
- **FR-008**: Os limites de frase MUST ser calculados com o numero real de frames dos WAVs no dominio
  PCM, antes da conversao para MP3, sem estimativas por caracteres, palavras ou duracao prevista.
- **FR-009**: A taxa de amostragem canonica desta versao MUST ser 22050 Hz; segmentos incompativeis
  MUST impedir que a geracao seja reportada como concluida.
- **FR-010**: Os intervalos MUST comecar na amostra zero, permanecer em ordem, nao se sobrepor e
  cobrir continuamente o audio PCM concatenado.
- **FR-011**: O `end_sample` da ultima frase MUST ser igual ao total real de frames do WAV
  concatenado usado para produzir o MP3.
- **FR-012**: Os limites de cada chunk MUST corresponder ao inicio de sua primeira frase e ao fim de
  sua ultima frase.
- **FR-013**: Frases repetidas MUST permanecer distinguiveis por sua posicao, sem usar o texto como
  identidade unica.
- **FR-014**: Quando uma frase logica precisar de mais de um segmento interno, a timeline MUST
  apresenta-la como uma unica frase e abranger todos os segmentos correspondentes.
- **FR-015**: O pipeline MUST realizar uma unica codificacao MP3, somente depois da concatenacao do
  audio PCM completo.
- **FR-016**: O MP3 e a timeline MUST ser publicados como um conjunto atomico; qualquer falha antes
  da publicacao completa MUST impedir a exposicao de artefatos novos e preservar o par anterior
  valido, se existir.
- **FR-017**: A inclusao da timeline MUST preservar as entradas, configuracoes, ordem, metadata e
  comportamento observavel ja suportados pelo pipeline de audio.
- **FR-018**: Arquivos temporarios MUST ser removidos em caso de sucesso ou falha, e os artefatos do
  usuario MUST permanecer locais conforme as regras do MVP.
- **FR-019**: A timeline JSON MUST ser a fonte canonica de sincronizacao; qualquer representacao
  WebVTT futura MUST ser derivada dela.
- **FR-020**: A timeline MUST ser armazenada ao lado do MP3 com nome derivado do mesmo nome-base e
  sufixo `.timeline.json`, permitindo descoberta deterministica sem uma API.
- **FR-021**: Todos os testes existentes MUST continuar aprovados, e cada nova regra de dominio ou
  comportamento do pipeline MUST ter verificacao automatizada adequada ao seu nivel.
- **FR-022**: As fronteiras canonicas das frases MUST ser definidas no texto normalizado antes do
  agrupamento em chunks; agrupamentos e fragmentacoes posteriores MUST preservar a identidade da
  frase logica original.

### Scope Boundaries

- Sincronizacao palavra por palavra esta fora do escopo.
- Interface de reproducao, destaque ou rolagem de texto esta fora do escopo.
- Criacao ou alteracao de API esta fora do escopo.
- WebVTT nao sera produzido como fonte canonica nesta fase.
- Filas, processamento distribuido e armazenamento remoto permanente estao fora do escopo.

### Key Entities

- **Timeline**: Documento versionado que relaciona o MP3 aos chunks, frases e limites de amostras.
- **Audio Artifact**: MP3 final identificado por nome, SHA-256 e propriedades derivadas do PCM que o
  originou.
- **Chunk**: Agrupamento pai ordenado, com identidade posicional e limites agregados de suas frases.
- **Sentence**: Unidade principal de sincronizacao, contendo texto falado, posicao dentro do chunk e
  limites de amostras.
- **Sample Interval**: Faixa semiaberta de amostras PCM definida por `start_sample` e `end_sample`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em 100% dos casos de teste validos, cada frase falada aparece exatamente uma vez na
  timeline, no chunk e na ordem corretos.
- **SC-002**: Em 100% dos artefatos gerados, todos os intervalos sao inteiros, nao negativos,
  ordenados e sem sobreposicao, e o ultimo limite coincide exatamente com o total de amostras PCM.
- **SC-003**: Em 100% dos artefatos gerados, o SHA-256 registrado corresponde ao MP3 final e detecta
  qualquer MP3 diferente usado na validacao.
- **SC-004**: Um consumidor consegue localizar a frase correspondente para qualquer ponto de
  reproducao coberto pelo audio usando apenas a timeline, com precisao de uma amostra.
- **SC-005**: A timeline fica disponivel no mesmo resultado concluido que o MP3 e sua preparacao
  acrescenta no maximo 5% ao tempo total do pipeline em um cenario representativo de 60 minutos.
- **SC-006**: 100% dos cenarios de geracao anteriormente suportados continuam produzindo um MP3
  valido com as mesmas entradas, configuracoes selecionadas e campos de metadata existentes; o
  fluxo sincronizado acrescenta a timeline sem remover contratos atuais.
- **SC-007**: Cada execucao bem-sucedida realiza exatamente uma codificacao para MP3,
  independentemente da quantidade de chunks ou frases.
- **SC-008**: Em 100% das falhas ocorridas antes da publicacao completa, nenhum artefato novo fica
  disponivel e qualquer par anterior valido permanece inalterado.

## Assumptions

- A versao inicial do formato da timeline sera identificada como `1`.
- O texto de cada frase e o texto normalizado efetivamente falado, nao o Markdown original.
- Os limites usam a convencao semiaberta `[start_sample, end_sample)`, tornando a duracao da frase
  igual a `end_sample - start_sample`.
- Nao ha lacunas artificiais entre frases; qualquer silencio sintetizado faz parte dos frames da
  frase correspondente.
- O nome-base compartilhado e suficiente para descoberta local; a verificacao definitiva da
  associacao e feita pelo SHA-256.
- O pipeline atual de normalizacao, chunking, sintese, WAV, concatenacao e MP3 permanece disponivel
  como dependencia desta feature.
- O ambiente de validacao de desempenho sera documentado no plano para tornar SC-005 reproduzivel.
