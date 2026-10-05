# Phase 1 Data Model: Deploy em VPS do HSS Study Voice

Esta fase não introduz entidades de domínio (nenhum dado de usuário novo é criado, alterado ou
persistido). Os elementos a seguir são configuração operacional declarada em `deploy/`
(`research.md`, Decisões 1–8) — documentados aqui pela mesma razão que um modelo de dados: para
que seus atributos e invariantes fiquem explícitos antes da implementação.

## Reverse Proxy Routing Table

Regras declaradas no `Caddyfile` (Decisão 2).

| Atributo | Valor |
|---|---|
| `/api/*` | `reverse_proxy 127.0.0.1:8000` |
| `/health` | `reverse_proxy 127.0.0.1:8000` |
| qualquer outro caminho | `file_server` servindo `frontend/dist/` |
| HTTP (porta 80) | redirecionamento automático para HTTPS (nativo do Caddy) |

**Invariante**: nenhuma outra rota aponta para o backend — qualquer caminho novo exposto pela
API no futuro precisa ser adicionado explicitamente a esta tabela (ou mover para debaixo de
`/api`), senão fica inacessível publicamente.

## Backend Service Unit (systemd)

Atributos de `deploy/hss-backend.service` (Decisão 3; hardening complementado em 2026-10-04).

| Atributo | Valor |
|---|---|
| `ExecStart` | `uv run uvicorn app.main:app --host 127.0.0.1 --port 8000` |
| `WorkingDirectory` | caminho absoluto de `backend/` no VPS |
| `User` | usuário de serviço dedicado, sem root |
| `After` | `network.target` (só inicia depois que a rede sobe) |
| `Restart` | `on-failure` |
| `RestartSec` | `5` (intervalo entre tentativas de reinício) |
| `StartLimitIntervalSec` | `60` |
| `StartLimitBurst` | `5` (no máximo 5 tentativas em 60s; systemd para de reiniciar e marca `failed` se exceder, evitando crash loop consumindo CPU indefinidamente) |
| `[Install] WantedBy` | `multi-user.target` (obrigatório para `systemctl enable` persistir através de reboots — sem esta seção, FR-005 falha silenciosamente após um `reboot`) |
| Porta vinculada | `127.0.0.1:8000` apenas (nunca uma interface pública) |

**Invariante**: o processo nunca escuta em `0.0.0.0`; todo tráfego público chega só pelo Caddy
(Reverse Proxy Routing Table acima). Depois de `StartLimitBurst` falhas em `StartLimitIntervalSec`
segundos, o serviço MUST parar de tentar reiniciar sozinho (fica `failed`) em vez de consumir CPU
em loop — um operador precisa investigar e rodar `systemctl reset-failed && systemctl start
hss-backend` manualmente, o que é aceitável para esta fase (sem automação de recuperação).

## Reverse Proxy — Pré-condições e Permissões

Pré-condições operacionais que precisam ser verdadeiras antes de Decisão 1/2 funcionarem na
prática (adicionado em 2026-10-04 — eram riscos implícitos, agora são invariantes explícitos):

| Pré-condição | Verificação |
|---|---|
| DNS do domínio já resolve para o IP do VPS | `dig +short <dominio>` (de fora do VPS) retorna o IP do VPS, antes de declarar o domínio no `Caddyfile` |
| Usuário de sistema do Caddy consegue ler `frontend/dist` e `frontend/dist.prev` | leitura recursiva confirmada (ex. `sudo -u caddy test -r .../frontend/dist/index.html`) antes de `systemctl reload caddy` |

**Invariante**: se qualquer uma destas pré-condições falhar, o Caddy responde `403` (permissão)
ou falha a emitir o certificado (DNS) — ambos sintomas silenciosos se não verificados
explicitamente antes do teste de aceite de US1.

## Health Endpoint Semantics

`/health` (roteado pela Reverse Proxy Routing Table acima) é hoje um check de **liveness**
apenas — confirma que o processo Python está no ar e que o binário `ffmpeg` é encontrado via
`shutil.which`. Ele **não** verifica *readiness* completa (ex.: modelo de voz padrão já
provisionado em `VOICES_DIR`, espaço em disco disponível em `output/`). Esta fase documenta essa
distinção (FR-008) sem expandir o endpoint — uma eventual verificação de readiness é uma mudança
de código do backend e, portanto, fora do escopo de uma fase de deploy (Princípio VIII).

## Output Retention Policy

Atributos de `deploy/output-cleanup.timer` + `.service` (Decisão 5).

| Atributo | Valor |
|---|---|
| Diretório alvo | `output/` **na raiz do repositório** (irmão de `backend/` e `frontend/`) — é o `OUTPUT_DIR` real de `app/core/config.py` (`BASE_DIR.parent / "output"`, onde `BASE_DIR` resolve para `backend/`). **Não é** `backend/output/`: esse caminho existe no repositório mas contém apenas `voice_samples/`, uma fixture de teste residual não relacionada e não gerenciada por este timer. |
| Critério de remoção | `mtime` do arquivo maior que 24 horas |
| Frequência | diária |
| Escopo | somente arquivos finais (`*.mp3`, `*.timeline.json`) dentro de `output/` (raiz); `TEMP_DIR` (`backend/temp/`) já é limpo pelo próprio backend e não é tocado por este timer |

**Invariante**: a limpeza é puramente baseada em idade do arquivo no disco, sem consultar
estado da aplicação — não depende de nenhuma API nova nem lê o IndexedDB do navegador. A unit
MUST apontar para `output/` na raiz do checkout (ex. `/opt/hss-study-voice/output/` no VPS,
conforme a convenção de `tasks.md`) — qualquer task ou comando que referencie
`backend/output/` para este propósito está incorreto.

## Verificação de Segurança: SSH e Firewall

Estado esperado, verificável, de FR-011 (Decisão 7) — declarado aqui para que a verificação seja
uma task explícita em vez de uma suposição não checada.

| Atributo | Valor esperado | Como verificar |
|---|---|---|
| Autenticação por senha (SSH) | desativada | `sshd -T 2>/dev/null \| grep -i passwordauthentication` retorna `passwordauthentication no` |
| Autenticação por chave (SSH) | funcional | login via chave pública bem-sucedido a partir de uma máquina cliente |
| Regras do `ufw` | somente `22`, `80`, `443` permitidas | `ufw status verbose` lista exatamente essas três portas/serviços como `ALLOW`; nenhuma outra regra `ALLOW` presente |

**Invariante**: a ausência de verificação explícita destas três linhas é, por si, um risco de
segurança não coberto — a configuração (Fase 1 de `tasks.md`) e a verificação (também Fase 1)
são tasks distintas e ambas obrigatórias.

## Verificação de Conteúdo de Logs (FR-012)

| Atributo | Valor esperado | Como verificar |
|---|---|---|
| Log do backend (`journalctl -u hss-backend`) | não contém o texto completo submetido pelo usuário | gerar um áudio de teste com um texto identificável único e confirmar, por busca no log, que esse texto não aparece |
| Access log do Caddy (se habilitado) | não registra corpo de requisição/resposta, apenas metadados (método, caminho, status, tamanho) | inspecionar a configuração de log do `Caddyfile` e confirmar que nenhum campo de log inclui `body` |

**Invariante**: esta verificação é pontual (executada uma vez após o primeiro deploy, Fase 9 de
`tasks.md`), mas documentada em `deploy/README.md` como um passo a repetir sempre que a
configuração de logging do Caddy ou do backend mudar.

## Validação de Longo Prazo (SC-002 e SC-005) — não bloqueante

SC-002 (health respondendo com sucesso por 7 dias consecutivos) e a cláusula de SC-005 ("pelo
menos um ciclo completo de renovação automática validado") exigem, por definição, uma janela de
observação maior do que o tempo de implementação desta fase. Para não bloquear o aceite inicial
do deploy (que usa checagens pontuais de health/TLS — ver Health Endpoint Semantics acima e
`quickstart.md`), estes dois critérios são tratados como **acompanhamento operacional
pós-deploy**, registrado como checklist em `deploy/README.md`:

| Critério | Forma de acompanhamento | Quando é considerado satisfeito |
|---|---|---|
| SC-002 (7 dias) | checagem diária de `GET /health`, resultado anotado (ex. arquivo/planilha simples com data + status) | 7 dias consecutivos sem falha não planejada registrados |
| SC-005 (ciclo de renovação) | observar o log do Caddy em torno de ~30 dias antes da expiração do certificado (validade típica de 90 dias) e confirmar a renovação automática | primeira renovação automática completada e evidenciada (ex. trecho do log do Caddy) |

**Invariante**: a conclusão desta fase (checkpoint de `tasks.md`, Fase 9) NÃO exige que estas
janelas já tenham decorrido — exige apenas que o mecanismo de acompanhamento esteja documentado
e iniciado. SC-002/SC-005 ficam formalmente confirmados depois, pela mesma pessoa que opera o
VPS, sem reabrir esta fase para isso.

## Deploy/Rollback Procedure State

O estado relevante entre duas publicações, mantido no próprio VPS (Decisão 8), não em um banco
de dados:

| Atributo | Valor |
|---|---|
| Commit/tag atualmente publicado | registrado **explicitamente** antes de cada `git pull` — via tag Git `deploy-<timestamp>` no HEAD atual, **ou** arquivo marcador `deploy/CURRENT_RELEASE` no VPS contendo o hash do commit (adicionado em 2026-10-04; não depende mais de `git log`/memória do operador) |
| Build anterior do frontend | preservado em `dist.prev/` até a próxima publicação |
| Versão anterior do backend | recuperável via `git checkout` do commit/tag registrado no marcador acima (sem artefato de build separado, já que o backend não é compilado) |

**Invariante**: sempre existe um caminho de volta para o estado publicado imediatamente
anterior até que uma nova publicação o substitua. O marcador/tag MUST ser escrito **antes** do
`git pull` da nova versão — se for escrito depois, já aponta para o commit errado e o rollback
perde sua referência confiável.
