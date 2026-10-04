# Feature Specification: Player com texto sincronizado

**Feature Branch**: `master`

**Created**: 2026-10-04

**Status**: Draft

**Input**: User description: "Fase 7 — Player com texto sincronizado"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Acompanhar o texto enquanto o áudio toca (Priority: P1)

Como estudante ouvindo um estudo já arquivado, quero ver o texto completo na tela com a frase que
está sendo falada destacada em tempo real, para conseguir acompanhar a leitura junto com o áudio sem
perder o lugar.

**Why this priority**: É o valor central desta fase. Sem o destaque sincronizado, o texto fica apenas
estático e a timeline gerada na Fase 3.1 permanece sem uso visível para o usuário.

**Independent Test**: Abrir um estudo salvo com timeline conhecida, iniciar a reprodução e verificar
que, a cada instante, a frase destacada na tela corresponde à frase cujo intervalo de amostras
contém a posição atual do áudio.

**Acceptance Scenarios**:

1. **Given** um estudo salvo com texto e timeline, **When** o usuário o abre, **Then** o texto
   completo é exibido agrupado por chunk, na mesma ordem da timeline.
2. **Given** a reprodução em andamento, **When** o áudio avança de uma frase para a próxima, **Then**
   o destaque visual muda da frase anterior para a nova frase sem deixar nenhuma frase destacada por
   engano nem destacar duas frases ao mesmo tempo.
3. **Given** a frase atualmente destacada, **When** ela não está visível na área de leitura, **Then**
   a visualização rola automaticamente até trazê-la para dentro da área visível.
4. **Given** o usuário rolou manualmente o texto para ler outro trecho, **When** a reprodução
   continua avançando, **Then** o sistema não força a rolagem de volta até que o usuário indique que
   deseja retomar o acompanhamento automático.

---

### User Story 2 - Pular para um trecho clicando no texto (Priority: P2)

Como estudante revisando um estudo, quero clicar em qualquer frase do texto para que a reprodução
pule imediatamente para aquele ponto, para não depender apenas da barra de progresso para navegar.

**Why this priority**: Navegação direta pelo texto é o principal ganho de usabilidade depois do
acompanhamento em si, permitindo revisar um trecho específico sem procurar no áudio por tentativa e
erro.

**Independent Test**: Com um estudo aberto, clicar em uma frase no meio do texto e verificar que a
posição de reprodução do áudio passa a ser exatamente o início daquela frase, com o destaque
atualizado para ela.

**Acceptance Scenarios**:

1. **Given** o áudio em reprodução, **When** o usuário clica em uma frase diferente da atual,
   **Then** a reprodução salta para o início da frase clicada e continua tocando a partir dali.
2. **Given** o áudio pausado, **When** o usuário clica em uma frase, **Then** a posição de reprodução
   é atualizada para o início daquela frase e o áudio permanece pausado até o usuário iniciar a
   reprodução.
3. **Given** o usuário clica repetidamente em frases diferentes, **When** cada clique ocorre,
   **Then** apenas a frase clicada mais recentemente fica destacada.

---

### User Story 3 - Retomar um estudo já iniciado com o texto certo (Priority: P3)

Como estudante retornando a um estudo com progresso salvo, quero que o texto já abra mostrando a
frase correspondente à minha última posição destacada e visível, para retomar a leitura sem precisar
iniciar a reprodução apenas para me situar.

**Why this priority**: Complementa o valor central ao preservar o contexto de leitura entre sessões,
mas não é indispensável para o primeiro uso da sincronização.

**Independent Test**: Abrir um estudo com progresso salvo no meio do áudio e verificar que a frase
correspondente a essa posição aparece destacada e visível antes de qualquer interação do usuário com
os controles de reprodução.

**Acceptance Scenarios**:

1. **Given** um estudo com posição salva correspondente a uma frase intermediária, **When** o
   usuário o abre, **Then** essa frase aparece destacada e dentro da área visível antes de o áudio
   começar a tocar.
2. **Given** um estudo com posição salva igual a zero ou sem progresso anterior, **When** o usuário o
   abre, **Then** a primeira frase do texto aparece destacada.
3. **Given** um estudo marcado como concluído, **When** o usuário o abre, **Then** a última frase do
   texto aparece destacada.

### Edge Cases

- A posição de reprodução cai exatamente no limite entre duas frases (fim de uma e início da
  próxima): apenas uma das duas fica destacada, de forma consistente.
- O áudio chega ao fim (evento de conclusão): a última frase permanece destacada, sem erro nem
  ausência de destaque.
- A posição salva de um estudo, por arredondamento, ultrapassa ligeiramente o total de amostras da
  timeline: o sistema trata esse caso como a última frase, sem travar a interface.
- A timeline de um estudo salvo está ausente, corrompida ou inconsistente com o áudio correspondente:
  a reprodução de áudio continua disponível normalmente, e o usuário é avisado de que o texto
  sincronizado não pôde ser exibido para aquele estudo.
- O estudo tem um texto muito longo, com muitas frases: o destaque e a rolagem automática continuam
  respondendo em tempo real, sem atraso perceptível nem travamentos.
- O usuário clica em uma frase enquanto outra ação de busca (arrastar a barra de progresso) está em
  andamento: a ação mais recente do usuário prevalece.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Ao abrir um estudo salvo para reprodução, o sistema MUST exibir o texto completo
  daquele estudo, agrupado por chunk e frase, na mesma ordem registrada na timeline local.
- **FR-002**: O sistema MUST destacar visualmente, a qualquer momento durante a reprodução, exatamente
  uma frase: aquela cujo intervalo de amostras contém a posição atual de reprodução do áudio.
- **FR-003**: O sistema MUST converter a posição atual de reprodução do áudio em uma posição de
  amostra usando a taxa de amostragem declarada na timeline, e usar essa posição para resolver a
  frase atual pelos intervalos de amostras das frases.
- **FR-004**: O destaque da frase atual MUST acompanhar o avanço da reprodução em tempo real, sem
  atraso perceptível nem oscilação entre frases.
- **FR-005**: O sistema MUST manter a frase atualmente destacada visível na área de leitura, rolando
  automaticamente a visualização quando necessário.
- **FR-006**: Quando o usuário rolar manualmente o texto, o sistema MUST suspender a rolagem
  automática até que o usuário sinalize o desejo de retomar o acompanhamento, evitando competir com a
  rolagem manual.
- **FR-007**: Usuários MUST ser capazes de clicar ou tocar em qualquer frase do texto exibido para
  mover a posição de reprodução do áudio para o início exato dessa frase.
- **FR-008**: Mover a posição de reprodução por meio de um clique no texto MUST atualizar o destaque
  imediatamente para a frase clicada, independentemente de o áudio estar tocando ou pausado.
- **FR-009**: Ao abrir um estudo com posição de reprodução previamente salva, o sistema MUST destacar
  e exibir a frase correspondente a essa posição antes de qualquer interação do usuário com os
  controles de reprodução.
- **FR-010**: Quando a reprodução atingir o fim do áudio, o sistema MUST manter a última frase
  destacada em vez de remover o destaque.
- **FR-011**: Se a timeline local de um estudo estiver ausente, corrompida ou não puder ser
  interpretada, o sistema MUST continuar permitindo a reprodução normal do áudio e MUST informar ao
  usuário que o texto sincronizado não está disponível para aquele estudo, em vez de bloquear a
  reprodução ou falhar silenciosamente.
- **FR-012**: A exibição do texto e o destaque sincronizado MUST funcionar inteiramente a partir dos
  dados já armazenados localmente (áudio e timeline), sem exigir nenhuma requisição de rede.
- **FR-013**: O sistema MUST preservar, sem regressão, todo o comportamento de reprodução já suportado
  (reproduzir, pausar, retomar posição salva, registrar progresso e conclusão).
- **FR-014**: Esta fase MUST NOT introduzir nem exigir alteração no formato da timeline, em endpoints
  da API ou no esquema de armazenamento local já existentes; a timeline MUST ser consumida como já é
  produzida e armazenada.
- **FR-015**: A indicação da frase atual MUST ser perceptível por mais de um sinal visual (por
  exemplo, não depender apenas de cor), e MUST ser identificável por tecnologia assistiva.
- **FR-016**: Todos os testes existentes MUST continuar aprovados, e a nova lógica de sincronização,
  destaque e navegação por clique MUST ter verificação automatizada adequada ao seu nível, incluindo
  a resolução da frase atual a partir de uma posição de amostra.

### Scope Boundaries

- Sincronização palavra por palavra permanece fora do escopo; o destaque opera no nível de frase.
- Edição do texto transcrito, troca de voz ou regeneração de áudio a partir desta tela estão fora do
  escopo.
- Criação, alteração ou remoção de endpoints de API está fora do escopo; a fonte de dados é a
  timeline já armazenada localmente.
- Compartilhamento, exportação ou impressão do texto sincronizado estão fora do escopo.
- Reprocessar ou corrigir timelines corrompidas de estudos existentes está fora do escopo; o
  tratamento previsto é a degradação graciosa descrita em FR-011.

### Key Entities

- **Reading View**: Representação textual de um estudo aberto para reprodução, composta pelos chunks
  e frases da timeline, exibida ao usuário durante a escuta.
- **Current Sentence**: A frase cujo intervalo de amostras contém a posição atual de reprodução;
  único ponto de destaque em qualquer instante.
- **Playback Position**: Posição corrente de reprodução do áudio, convertida para amostra pela taxa
  declarada na timeline, usada para resolver a Current Sentence.
- **Sentence Click Target**: Associação entre uma frase exibida na Reading View e o `start_sample`
  usado para reposicionar a reprodução quando essa frase é selecionada pelo usuário.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Durante a reprodução, a frase destacada corresponde à frase realmente falada em pelo
  menos 95% das verificações amostradas ao longo de um estudo de teste, com atraso perceptível
  inferior a 300 milissegundos.
- **SC-002**: Clicar em qualquer frase do texto reposiciona a reprodução para o início exato dessa
  frase e atualiza o destaque em até 1 segundo, de forma perceptível ao usuário como imediata.
- **SC-003**: 100% dos estudos já salvos com timeline válida exibem o texto completo e sincronizável
  ao serem abertos, sem exigir reprocessamento do áudio existente.
- **SC-004**: Reabrir um estudo com progresso salvo mostra a frase correta já destacada e visível em
  até 1 segundo após a abertura, sem exigir que a reprodução seja iniciada.
- **SC-005**: 100% dos cenários de reprodução previamente suportados (reproduzir, pausar, retomar,
  concluir, registrar progresso) continuam funcionando sem regressão após a introdução do texto
  sincronizado.
- **SC-006**: Usuários conseguem abrir e ler o texto completo de um estudo salvo sem conexão de rede
  em 100% dos casos testados.
- **SC-007**: Em 100% dos casos de timeline ausente ou corrompida simulados em teste, a reprodução de
  áudio permanece disponível e o usuário recebe um aviso claro sobre a indisponibilidade do texto
  sincronizado, sem travamentos ou erros não tratados.

## Assumptions

- Toda timeline consumida por esta fase já foi gerada e validada pelo pipeline da Fase 3.1
  (`001-text-audio-timeline`); esta fase não altera como as timelines são produzidas.
- A granularidade de sincronização desta fase é por frase; destaque por palavra é uma evolução futura
  fora deste escopo.
- O player de áudio local já existente (reprodução, posição salva, eventos de pausa/conclusão)
  permanece a base da reprodução; esta fase adiciona uma camada de texto sincronizada a ele, sem
  substituir sua lógica.
- Clicar em uma frase apenas reposiciona a reprodução; não altera automaticamente o estado de
  reproduzindo/pausado além do que o usuário já tinha antes do clique.
- A rolagem automática é retomada quando o usuário interage novamente com os controles de reprodução
  (por exemplo, ao clicar em outra frase) ou explicitamente solicita retomar o acompanhamento.
- Apenas uma frase é destacada por vez; não há ênfase simultânea em múltiplas frases.
- O texto exibido é somente leitura nesta fase.
