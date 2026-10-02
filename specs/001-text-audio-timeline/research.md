# Research: Timeline de sincronizacao texto-audio

## Canonical sentence structure

**Decision**: Definir frases no texto normalizado antes do agrupamento. Adicionar uma representacao
estruturada com documento, chunks, frases logicas e fragmentos de sintese. Manter `chunk()` e
`process()` retornando `list[str]` exatamente como hoje; o fluxo sincronizado usa a nova
representacao explicita.

**Rationale**: A lista atual perde a identidade da frase ao juntar sentencas e ao dividir frases
longas. Reparsing posterior nao consegue reconstruir essa identidade com seguranca. Uma estrutura
paralela preserva compatibilidade concreta sem esconder metadata em strings ou estado mutavel.

**Alternatives considered**:

- Alterar `process()` para retornar objetos: rejeitado por quebrar contratos e testes existentes.
- Separar novamente cada chunk no audio: rejeitado porque diverge da fronteira canonica.
- Usar o texto como identidade: rejeitado porque frases repetidas sao validas.
- Adicionar alinhamento forcado: rejeitado por complexidade e escopo excessivos.

## PCM frame accounting

**Decision**: Renderizar um WAV por fragmento de sintese, ler `getnframes()` e `getframerate()` de
cada WAV fechado, acumular fragmentos na frase e frases no chunk, e conferir a soma contra o WAV
concatenado.

**Rationale**: Frames reais sao a unica medida exata disponivel antes da compressao. Frases longas
podem ter varios fragmentos internos sem vazar essa divisao para o contrato publico.

**Alternatives considered**:

- Estimar por caracteres, palavras ou duracao: rejeitado por imprecisao e pela spec.
- Medir somente o WAV concatenado: rejeitado porque nao fornece fronteiras internas.
- Medir MP3 decodificado: rejeitado por delay e padding dependentes do decoder.

## Timeline contract and versioning

**Decision**: Usar JSON UTF-8 fechado com `schema_version: 1`, propriedades de audio, arrays
ordenados de chunks e frases, indices posicionais base zero e intervalos semiabertos inteiros.
Campos desconhecidos sao invalidos na versao 1.

**Rationale**: O contrato e pequeno, local e canonico. Uma versao inteira torna mudancas semanticas
explicitas; arrays e indices detectam reordenacao; intervalos inteiros evitam arredondamento.

**Alternatives considered**:

- Tempos em segundos: rejeitado por arredondamento e duplicacao de dados derivados.
- UUIDs: rejeitado porque a identidade posicional no documento imutavel e suficiente.
- WebVTT: rejeitado como fonte canonica por perder propriedades e invariantes do dominio PCM.
- Versionamento semantico em string: rejeitado por complexidade sem beneficio no formato.

## MP3 binding

**Decision**: Finalizar o unico MP3, calcular SHA-256 sobre todos os seus bytes e somente entao
serializar a timeline. O digest e hexadecimal minusculo com 64 caracteres.

**Rationale**: O hash identifica exatamente o artefato entregue, nao apenas sua origem PCM. Qualquer
alteracao posterior, inclusive tags, invalida a associacao e pode ser detectada localmente.

**Alternatives considered**:

- Hash do WAV: rejeitado porque nao identifica o MP3 entregue.
- Hash antes da finalizacao: rejeitado porque bytes posteriores quebrariam a associacao.
- Hash adicional da timeline: adiado; a timeline nao e assinada nem distribuida remotamente.

## Atomic pair publication

**Decision**: Criar staging unico dentro do diretorio final, preparar e validar MP3/JSON antes da
publicacao, copiar qualquer par anterior para backup, substituir MP3 e timeline com `os.replace` e
executar rollback compensatorio se uma substituicao falhar. A timeline e publicada por ultimo como
marcador logico de commit.

**Rationale**: `os.replace` e atomico para um destino e exige o mesmo filesystem. Staging no destino
evita movimentacao entre volumes; backups preservam o estado anterior se o segundo replace falhar.
No limite da chamada, o consumidor recebe o novo par completo ou o estado anterior restaurado.

**Alternatives considered**:

- Escrita direta sequencial: rejeitada por expor arquivos parciais.
- Diretorio versionado com ponteiro: rejeitado por mudar descoberta e criar artefatos permanentes.
- Arquivo unico contendo MP3 e JSON: rejeitado pelo contrato sidecar.
- Banco, lock distribuido ou fila: rejeitado pelo escopo local e pela constituicao.

**Known limitation**: Dois caminhos nao podem ser substituidos como uma unica transacao portavel.
Existe uma janela curta entre replaces e uma queda do processo pode deixar estado misto. O MVP nao
suporta escritores concorrentes para o mesmo nome-base; leitores devem validar o SHA-256.

## Compatibility and orchestration

**Decision**: Adicionar um fluxo sincronizado explicito ao orquestrador e preservar o fluxo MP3
atual. Os campos existentes de `AudioResult` permanecem e o caminho da timeline e acrescentado sem
remover metadata. A codificacao continua ocorrendo uma vez, depois da concatenacao PCM.

**Rationale**: A entrada legada `list[str]` nao contem informacao suficiente para recuperar frases
longas fragmentadas. Um caminho estruturado torna a garantia explicita sem alterar chamadas atuais.

**Alternatives considered**:

- Uniao implicita de tipos na mesma entrada: rejeitada por ambiguidade.
- Inferir estrutura de `list[str]`: rejeitado porque nao recupera identidade perdida.
- Reescrever renderer, concatenador e exporter: rejeitado; os componentes atuais sao reutilizaveis.

## Performance validation

**Decision**: Medir uma execucao de referencia de 60 minutos com e sem timeline, mesma entrada,
voz, velocidade e bitrate. O overhead inclui leitura de headers, hash, serializacao e publicacao,
mas exclui download inicial de voz.

**Rationale**: A medicao comparativa torna o limite de 5% reproduzivel sem estabelecer uma meta de
hardware absoluta.

**Alternatives considered**:

- Limite fixo em segundos: rejeitado porque varia muito com hardware e duracao.
- Nao medir: rejeitado por deixar SC-005 sem verificacao.

## Primary references

- Python `wave`: https://docs.python.org/3/library/wave.html
- Python `os.replace`: https://docs.python.org/3/library/os.html#os.replace
- Python `tempfile`: https://docs.python.org/3/library/tempfile.html
- RFC 8259 JSON: https://www.rfc-editor.org/rfc/rfc8259
- RFC 7493 I-JSON: https://www.rfc-editor.org/rfc/rfc7493
- NIST FIPS 180-4 SHA-256: https://csrc.nist.gov/pubs/fips/180-4/upd1/final
- FFmpeg concat demuxer: https://ffmpeg.org/ffmpeg-formats.html#concat
