# Runbook de Deploy — HSS Study Voice

Este runbook documenta o deploy do HSS Study Voice em um VPS Ubuntu LTS, usando Caddy (reverse
proxy + TLS automático) e systemd (supervisão de processos). Nenhuma infraestrutura além dessas
duas é introduzida (Princípio III/VII da constitution).

Convenções usadas abaixo:
- `<dominio>` — domínio público escolhido para a aplicação (no `deploy/Caddyfile` deste
  repositório, o placeholder é `exemplo.com` — substituir antes de usar em produção).
- `hssdeploy` — usuário de serviço dedicado, sem privilégios de root.
- `/opt/hss-study-voice` — caminho do checkout do repositório no VPS.

Status desta versão do runbook: **todas as seções (1 a 13) estão documentadas**, cobrindo
`tasks.md` T001–T051. Nenhum passo foi executado contra um VPS real em nenhuma fase — este
runbook foi escrito e validado localmente (lockfile, build, lógica dos units systemd, revisão
de código). Todo passo marcado **PENDENTE** abaixo exige execução real no VPS e ainda não foi
confirmado; passos marcados **COMPLETO** foram preparados e/ou validados localmente nesta
máquina de desenvolvimento.

---

## 1. Setup inicial do VPS

Pré-requisito de infraestrutura fora deste repositório: provisionar um VPS Ubuntu LTS e apontar
o DNS do domínio escolhido para o IP do VPS.

1. **Usuário de serviço e SSH por chave** (FR-011): criar um usuário dedicado sem root (ex.
   `hssdeploy`), configurar autenticação SSH apenas por chave pública e desabilitar
   `PasswordAuthentication` em `/etc/ssh/sshd_config`:
   ```bash
   adduser --disabled-password hssdeploy
   # copiar a chave pública para /home/hssdeploy/.ssh/authorized_keys
   # em /etc/ssh/sshd_config:
   #   PasswordAuthentication no
   systemctl reload sshd
   ```
2. **Firewall** (`ufw`): permitir apenas SSH, HTTP e HTTPS:
   ```bash
   ufw allow 22/tcp
   ufw allow 80/tcp
   ufw allow 443/tcp
   ufw enable
   ```
3. **`uv`** (gerencia o Python 3.13 exigido por `backend/pyproject.toml`, sem depender do
   Python do sistema):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
4. **Caddy** (repositório oficial do projeto):
   ```bash
   sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
   curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
   curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
   sudo apt update
   sudo apt install caddy
   ```
5. **Clonar o repositório**, sob o usuário de serviço, e fazer checkout do commit/tag aprovado
   para o primeiro deploy:
   ```bash
   sudo -u hssdeploy git clone <url-do-repositorio> /opt/hss-study-voice
   cd /opt/hss-study-voice && sudo -u hssdeploy git checkout <commit-ou-tag-aprovado>
   ```

**Checkpoint**: VPS acessível por SSH com chave (senha desativada), firewall restrito, `uv` e
Caddy instalados, repositório clonado.

## 2. Verificações de segurança (SSH / UFW)

Executar **depois** do passo 1, antes de prosseguir:

```bash
# 1. A partir de uma máquina cliente: login SSH por chave deve funcionar sem senha.
ssh hssdeploy@<ip-do-vps>

# 2. No VPS: autenticação por senha deve estar desabilitada.
sshd -T 2>/dev/null | grep -i passwordauthentication
# esperado: passwordauthentication no

# 3. No VPS: ufw deve listar exatamente 22, 80 e 443 como ALLOW.
ufw status verbose
```

Se qualquer verificação falhar, corrigir antes de avançar — esta é uma pré-condição de
segurança, não um passo opcional (FR-011).

**Hardening consolidado (FR-011)** — resumo do que este runbook garante, reunindo verificações
de fases distintas em um único lugar:

| Camada | Medida | Onde é configurada/verificada |
|---|---|---|
| SSH | Somente chave pública, `PasswordAuthentication no` | Seção 1 (passo 1), Seção 2 (verificação 1–2) |
| Usuário | `hssdeploy`, sem privilégios de root | Seção 1 (passo 1) |
| Firewall | `ufw` permitindo apenas `22`, `80`, `443` | Seção 1 (passo 2), Seção 2 (verificação 3) |
| Backend | Vinculado apenas a `127.0.0.1:8000`, nunca interface pública | `deploy/hss-backend.service` (`ExecStart --host 127.0.0.1`), Seção 4 |

**Invariante**: mesmo que a regra de firewall seja esquecida ou mal aplicada, o backend
continua inacessível de fora do VPS porque nunca escuta em `0.0.0.0` — defesa em profundidade
(`research.md`, Decisão 7).

## 3. Variáveis de ambiente de produção

A configuração lida por `backend/app/core/config.py` (ex. `OUTPUT_DIR`, `VOICES_DIR`,
`DEFAULT_VOICE`) já tem defaults de código que funcionam sem um `.env` customizado. Caso seja
necessário sobrescrever algum valor em produção, usar um arquivo `.env` local ao serviço, em
`/opt/hss-study-voice/backend/.env`, **fora do controle de versão** — `.env` já está listado em
`.gitignore` na raiz do repositório. Nenhum segredo deve ser commitado.

## 4. Deploy do backend

1. Instalar dependências com a versão exata fixada em `uv.lock`:
   ```bash
   cd /opt/hss-study-voice/backend
   sudo -u hssdeploy uv sync --frozen
   ```
2. Instalar a unit systemd (`deploy/hss-backend.service` deste repositório):
   ```bash
   sudo cp /opt/hss-study-voice/deploy/hss-backend.service /etc/systemd/system/hss-backend.service
   sudo systemctl daemon-reload
   ```
3. Habilitar e iniciar o serviço:
   ```bash
   sudo systemctl enable --now hss-backend
   sudo systemctl status hss-backend
   # esperado: active (running), vinculado apenas a 127.0.0.1:8000
   ```
4. Chamada de "aquecimento" (provisiona o modelo de voz padrão via
   `PiperProvider.ensure_voice_downloaded`, confirmando acesso de saída HTTPS a
   `huggingface.co`):
   ```bash
   curl 127.0.0.1:8000/health
   # gerar um áudio de teste via /api/v1/... para forçar o download do modelo padrão
   ```

**Checkpoint**: backend responde localmente no VPS; modelo de voz padrão provisionado; serviço
resistente a crash loop e a reboot (`[Install] WantedBy=multi-user.target` na unit).

## 5. Deploy do frontend

1. Gerar o build de produção **na máquina de desenvolvimento ou CI** (não altera nenhum arquivo
   de código-fonte dentro de `frontend/`):
   ```bash
   cd frontend
   npm ci
   npm run build
   # saída em frontend/dist/
   ```
2. Copiar `frontend/dist/` para o VPS, sob o usuário de serviço:
   ```bash
   rsync -av --delete frontend/dist/ hssdeploy@<ip-do-vps>:/opt/hss-study-voice/frontend/dist/
   ```
3. Confirmar que não há processo Node.js supervisionado em produção — apenas os arquivos
   estáticos em `/opt/hss-study-voice/frontend/dist` são servidos (pelo Caddy, seção 6):
   ```bash
   ps aux | grep -i node   # esperado: nenhum processo de servidor Node.js
   ```

**Checkpoint**: build do frontend presente no VPS, pronto para ser servido pelo Caddy.

## 6. Reverse proxy / TLS (Caddy)

1. **Verificar a propagação de DNS antes de declarar o domínio** (FR-001/FR-004):
   ```bash
   dig +short <dominio>
   # esperado: IP do VPS, a partir de uma rede externa ao VPS
   ```
2. O roteamento same-origin já está declarado em `deploy/Caddyfile` deste repositório:
   `/api/*` e `/health` → `reverse_proxy 127.0.0.1:8000`; qualquer outro caminho →
   `file_server` servindo `/opt/hss-study-voice/frontend/dist`. Isso implementa a Clarification
   de FR-007 (mesma origem, sem CORS) — `/health` precisa de uma regra própria porque está
   montado fora do prefixo `/api/v1` usado pelas rotas de estudo.
3. **Declarar o domínio** em `deploy/Caddyfile` (substituir o placeholder `exemplo.com`) —
   **somente depois** do passo 1 confirmar a propagação. Isso faz o Caddy emitir e renovar o
   certificado HTTPS automaticamente, com redirecionamento HTTP→HTTPS nativo (nenhuma
   configuração adicional necessária).
4. **Permissões**: garantir que o usuário de sistema do Caddy tem leitura recursiva em
   `frontend/dist` e `frontend/dist.prev` **antes** de recarregar o serviço, para evitar `403`:
   ```bash
   sudo -u caddy test -r /opt/hss-study-voice/frontend/dist/index.html && echo OK
   # se falhar, ajustar propriedade/grupo/ACL conforme a forma de instalação do Caddy
   ```
5. Copiar o `Caddyfile` e (re)carregar:
   ```bash
   sudo cp /opt/hss-study-voice/deploy/Caddyfile /etc/caddy/Caddyfile
   sudo systemctl enable --now caddy   # primeira vez
   sudo systemctl reload caddy         # atualizações subsequentes
   ```
6. Validar de fora da rede de desenvolvimento:
   ```bash
   # https://<dominio>/ deve carregar o frontend e permitir gerar/reproduzir um áudio via /api
   # http://<dominio>/ deve redirecionar automaticamente para https://
   ```

**Checkpoint**: 🎯 MVP completo — aplicação publicamente acessível via HTTPS, DNS e permissões
de arquivo verificados antes do teste de aceite.

---

## 7. Retenção de output

**COMPLETO (local)**: `deploy/output-cleanup.service` (oneshot) e `deploy/output-cleanup.timer`
(diário) já existem neste repositório. Alvo: `/opt/hss-study-voice/output/` **na raiz do
checkout** (nunca `backend/output/`, que é só a fixture residual `voice_samples/` — ver
`data-model.md`, Output Retention Policy). Critério: `mtime` > 24h (`-mmin +1440`), apenas
`*.mp3` e `*.timeline.json`; `backend/temp/` nunca é tocado (já é limpo pelo próprio backend).

A lógica do `find` usada nas duas `ExecStart=` da unit foi validada localmente contra arquivos
sintéticos (um "antigo" com `mtime` forjado para 48h atrás, um "recente") em um diretório
temporário fora do repositório: apenas o arquivo antigo foi removido, o recente permaneceu.
Isso confirma a lógica de corte etário, mas **não** substitui o teste real em T031 (que exige o
caminho `/opt/hss-study-voice/output/` e o systemd real do VPS).

Instalação no VPS (**PENDENTE** — T029):
```bash
sudo cp /opt/hss-study-voice/deploy/output-cleanup.service /etc/systemd/system/
sudo cp /opt/hss-study-voice/deploy/output-cleanup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now output-cleanup.timer
```

Verificações (**PENDENTE** — exigem o VPS real):
- **T030**: gerar um áudio em produção; via SSH, `ls -la /opt/hss-study-voice/output/` deve
  mostrar o par `.mp3`/`.timeline.json` imediatamente após a resposta.
- **T031**: forçar o timer manualmente sobre um arquivo de teste com `mtime` > 24h:
  ```bash
  sudo -u hssdeploy touch -d "48 hours ago" /opt/hss-study-voice/output/teste-retencao.mp3
  sudo systemctl start output-cleanup.service
  ls /opt/hss-study-voice/output/ | grep teste-retencao   # esperado: nenhuma saída (removido)
  ```
  Arquivos com menos de 24h devem permanecer intocados.
- **T032**: confirmar no navegador que a biblioteca gerada em T030 continua acessível via
  IndexedDB mesmo depois da limpeza acima (comportamento inalterado da Fase 3 do produto).

## 8. Marcador de release, deploy e rollback (backend + frontend)

**COMPLETO (doc)** — procedimento abaixo é executável a partir do primeiro deploy real; nenhuma
parte dele depende de automação nova (Clarification de FR-010: rollback manual, documentado).

### 8.1 Marcador do release publicado (T033)

Antes de **qualquer** `git pull`/checkout para uma nova versão, registrar explicitamente o
commit atualmente publicado — nunca depender de `git log`/memória do operador. Escolher **uma**
das duas formas abaixo e manter consistência entre deploys:

- **Opção A — tag Git** (recomendada: visível em `git log --oneline --decorate`):
  ```bash
  cd /opt/hss-study-voice
  git tag "deploy-$(date +%Y%m%d%H%M%S)" HEAD
  ```
- **Opção B — arquivo marcador**:
  ```bash
  git rev-parse HEAD > /opt/hss-study-voice/deploy/CURRENT_RELEASE
  ```

### 8.2 Publicar uma nova versão (T034)

1. Registrar o marcador (8.1) — **antes** do pull, sempre.
2. `git pull` (ou `git checkout <tag/commit aprovado>`) em `/opt/hss-study-voice`.
3. **Backend**, se alterado:
   ```bash
   cd /opt/hss-study-voice/backend
   sudo -u hssdeploy uv sync --frozen
   sudo systemctl restart hss-backend
   curl 127.0.0.1:8000/health
   ```
4. **Frontend**, se alterado — build fora do VPS (máquina de dev/CI), preservando o `dist/`
   atual como `dist.prev/` **antes** de substituí-lo, e só depois que o build novo terminar com
   sucesso:
   ```bash
   # na máquina de dev/CI:
   cd frontend && npm ci && npm run build

   # copiar para um diretório novo no VPS (não sobrescrever dist/ diretamente):
   rsync -av --delete frontend/dist/ hssdeploy@<ip-do-vps>:/opt/hss-study-voice/frontend/dist.new/

   # no VPS, só depois que o rsync acima terminar com sucesso:
   rm -rf /opt/hss-study-voice/frontend/dist.prev
   mv /opt/hss-study-voice/frontend/dist /opt/hss-study-voice/frontend/dist.prev
   mv /opt/hss-study-voice/frontend/dist.new /opt/hss-study-voice/frontend/dist
   ```
5. Validar `GET /health` **e** uma chamada real de API (gerar um áudio de teste) antes de
   considerar a publicação concluída.

### 8.3 Rollback (T035)

Usar **sempre** o marcador de 8.1 como referência — nunca "o commit anterior" inferido de
memória.

- **Backend**:
  ```bash
  cd /opt/hss-study-voice
  git checkout <tag-ou-hash-do-marcador>
  cd backend && sudo -u hssdeploy uv sync --frozen
  sudo systemctl restart hss-backend
  curl 127.0.0.1:8000/health
  ```
- **Frontend** — imediato, sem reconstruir:
  ```bash
  mv /opt/hss-study-voice/frontend/dist /opt/hss-study-voice/frontend/dist.rejected
  mv /opt/hss-study-voice/frontend/dist.prev /opt/hss-study-voice/frontend/dist
  ```
  (o Caddy `file_server` lê do disco a cada requisição — nenhum reload é necessário só pela
  troca de arquivos, mas `sudo systemctl reload caddy` é seguro de rodar se houver dúvida.)

### 8.4 Execução real (PENDENTE)

- **T036**: seguir 8.1–8.2 do início ao fim para publicar uma alteração trivial já aprovada,
  cronometrando o tempo total (esperado: < 15 minutos, SC-003). **PENDENTE** — exige um deploy
  real.
- **T037**: rollback **real do backend** a partir do marcador, validando `GET /health` e uma
  geração de áudio real após o `git checkout` reverso. **PENDENTE**.
- **T038**: interromper deliberadamente um `npm run build` do frontend no meio e aplicar 8.3,
  confirmando que a versão anterior continua disponível publicamente durante e após a
  interrupção. **PENDENTE**.

## 9. Verificação de logs (FR-012)

**Achado de revisão de código (COMPLETO, local)** — inspecionei os pontos de logging do backend
que tocam o texto submetido pelo usuário:
- `backend/app/api/routes/studies.py`: em caso de erro, loga `len(payload.text)` (o
  **comprimento**, não o conteúdo) junto de `voice`/`elapsed`/`exc`.
- `backend/app/services/audio/orchestrator.py`: loga apenas contagem de chunks, voz, velocidade,
  nome de arquivo de saída, duração e tamanho em bytes — nunca o texto original.
- `deploy/Caddyfile` (deste repositório) **não declara nenhuma diretiva `log`** — portanto o
  Caddy não grava access log nenhum para este site, e consequentemente não há corpo de
  requisição persistido por ele.

Essa revisão dá confiança de que o código atual já satisfaz FR-012, mas **não substitui** a
confirmação exigida pela task contra o log real de produção:

- **T043 (PENDENTE)**: gerar um áudio de teste com um texto identificável e único em
  produção, depois `journalctl -u hss-backend | grep "<trecho do texto>"` — esperado: nenhuma
  ocorrência. Repetir esta checagem sempre que a configuração de logging do backend ou do Caddy
  mudar.

## 10. Health check e certificado TLS

**COMPLETO (doc)**:
- `/health` (roteado por `deploy/Caddyfile`, seção 6) é um check de **liveness** apenas —
  confirma que o processo está no ar e que `ffmpeg` é encontrado via `shutil.which`. **Não**
  verifica readiness completa (modelo de voz já provisionado, espaço em disco disponível).
  Expandir o endpoint para readiness é mudança de código do backend e fica fora do escopo de
  uma fase de deploy (`data-model.md`, Health Endpoint Semantics).
- Consulta: `curl -s https://<dominio>/health` deve responder `200` com `status: ok` e metadados
  não sensíveis (nome/versão do projeto, flag de ffmpeg, voz padrão, limite de chunk).
- Renovação do certificado TLS é automática pelo Caddy — nenhum cron/timer adicional é
  necessário ou deve ser criado.

**PENDENTE** (exigem VPS real e domínio declarado):
- **T039**: `curl -s https://<dominio>/health` a partir de fora do VPS, confirmando `200`.
- **T041**: checagem pontual de validade do certificado:
  ```bash
  curl -vI https://<dominio>/ 2>&1 | grep -i "expire\|SSL certificate"
  ```
  Nota de escopo: isto confirma validade **no momento da checagem**, não um ciclo completo de
  renovação (ver seção 11, SC-005).

## 11. Acompanhamento pós-deploy (não bloqueante — SC-002 / SC-005)

**COMPLETO (checklist pronto para uso)** — estes itens **não** bloqueiam o aceite inicial desta
fase (`data-model.md`, Validação de Longo Prazo); são iniciados no primeiro deploy real e
confirmados depois, operacionalmente. Preencher a tabela abaixo (ou uma planilha equivalente) a
partir do primeiro deploy real — **PENDENTE o início do preenchimento**, que depende do VPS:

**SC-002 — `GET /health` por 7 dias consecutivos**

| Dia | Data | `curl -s https://<dominio>/health` | Observação |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |
| 4 | | | |
| 5 | | | |
| 6 | | | |
| 7 | | | |

Confirmado apenas quando os 7 dias estiverem completos sem indisponibilidade não planejada.

**SC-005 — primeiro ciclo de renovação automática do certificado**

Validade típica do certificado: 90 dias. Acompanhar o log do Caddy (`journalctl -u caddy`) em
torno de ~30 dias antes da expiração observada em T041, e registrar aqui a evidência da primeira
renovação automática bem-sucedida (ex. trecho do log com a data):

```
Data da 1ª renovação observada: _________________
Trecho do log do Caddy:          _________________
```

Confirmado apenas quando essa renovação ocorrer e for evidenciada.

## 12. Resiliência (crash loop, restart manual, reboot)

**COMPLETO (doc)** — procedimentos a executar uma vez após o primeiro deploy real para validar
os edge cases de resiliência do spec. Todos **PENDENTES** de execução (exigem o VPS real):

- **T045 — parada manual**: `sudo systemctl stop hss-backend` no VPS. Esperado: systemd reinicia
  automaticamente (`Restart=on-failure`, `deploy/hss-backend.service`) sem login manual, e
  `/api` volta a responder.
- **T046 — crash loop controlado**: renomear temporariamente o executável/arquivo exigido pelo
  `ExecStart` (ex. mover o `.venv` ou o `uv` do `PATH`) e reiniciar o serviço repetidamente.
  Esperado: após `StartLimitBurst=5` tentativas em `StartLimitIntervalSec=60`s, o systemd marca
  o serviço como `failed` em vez de reiniciar indefinidamente. Restaurar o arquivo e rodar:
  ```bash
  sudo systemctl reset-failed hss-backend
  sudo systemctl start hss-backend
  ```
- **T047 — reboot do VPS**: `sudo reboot` em uma janela controlada. Esperado: Caddy e
  `hss-backend` voltam a rodar sozinhos após o boot, via `[Install] WantedBy=multi-user.target`
  em ambas as units, sem intervenção manual.

## 13. Validação final (T048 / T049)

- **T048 (PENDENTE)**: executar o roteiro completo de `specs/007-deploy-vps/quickstart.md` do
  início ao fim (exceto "Acompanhamento Pós-Deploy") em um VPS que começou limpo — nenhuma etapa
  disto pode ser simulada localmente, exige o VPS real.
- **T049 (COMPLETO — autorrevisão feita nesta sessão)**: revisei este `README.md` de ponta a
  ponta buscando passos implícitos ou não documentados. Ajustes já aplicados como resultado
  dessa revisão: (a) o placeholder de domínio `exemplo.com` no `Caddyfile` está marcado com
  comentário explícito de substituição; (b) o procedimento de deploy do frontend (8.2) usa um
  diretório `dist.new/` intermediário em vez de sobrescrever `dist/` direto, evitando uma janela
  em que o `file_server` serve um build parcialmente copiado; (c) o marcador de release (8.1)
  documenta as duas opções (tag ou arquivo) e instrui a escolher uma e manter consistência, em
  vez de deixar ambíguo qual delas o rollback (8.3) deve assumir. Revisão independente por outra
  pessoa antes do primeiro deploy real continua recomendada (SC-003 exige isso na prática, não
  apenas em teoria).
