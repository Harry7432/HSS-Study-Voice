---

description: "Task list for Deploy em VPS do HSS Study Voice"
---

# Tasks: Deploy em VPS do HSS Study Voice

**Input**: Design documents from `/specs/007-deploy-vps/` (`spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`), `.specify/memory/constitution.md`

**Prerequisites**: `plan.md` (obrigatório), `spec.md` (user stories), `research.md` (decisões técnicas), `data-model.md` (unidades systemd, roteamento, retenção, verificações)

**Tests**: Esta fase não altera código de aplicação (Constitution Check, Princípio IV — N/A). Não há tasks de teste automatizado; a validação é o roteiro manual de `quickstart.md`, incorporado às tasks de cada fase e consolidado na Fase 9.

**Organization**: Tasks agrupadas por categoria operacional pedida (Setup, Deploy Backend, Deploy Frontend, Reverse Proxy/TLS, Retenção, Rollback, Validação), com rótulo `[Story]` mantido para rastreabilidade com as User Stories de `spec.md`.

**Escopo explícito**: Nenhuma task abaixo edita arquivos dentro de `backend/` ou `frontend/` (código-fonte). Apenas `frontend/dist/` é gerado como artefato de build e copiado; toda configuração nova vive em `deploy/`. Nenhuma infraestrutura além de Caddy e systemd é introduzida (Princípio III/VII).

**Revisão de 2026-10-04**: esta versão corrige um erro de caminho identificado por análise contra a constitution (`OUTPUT_DIR` real é `output/` na raiz do repositório, não `backend/output/`) e adiciona tasks de verificação que antes faltavam: rollback real do backend, marcador explícito do release publicado, permissão de leitura do Caddy sobre `frontend/dist`, verificação de logs (FR-012), verificação de hardening de SSH/UFW, completude da unit systemd (crash-loop, boot), verificação de propagação de DNS, e acompanhamento pós-deploy não bloqueante para SC-002/SC-005. Ver histórico da conversa para a análise completa.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode ser executada em paralelo (arquivos/hosts diferentes, sem dependência)
- **[Story]**: User story associada (US1–US4) quando aplicável; tasks de Setup/Foundational/Polish não têm rótulo de story
- Caminhos exatos (no repositório e no VPS) estão incluídos em cada descrição

## Path Conventions (VPS)

- Repositório clonado em `/opt/hss-study-voice` no VPS, sob o usuário de serviço dedicado (ex. `hssdeploy`, sem root)
- Backend: `/opt/hss-study-voice/backend` (`WorkingDirectory` da unit systemd)
- Frontend servido: `/opt/hss-study-voice/frontend/dist`, com `/opt/hss-study-voice/frontend/dist.prev` preservado para rollback
- **Diretório de saída do backend (`OUTPUT_DIR` real)**: `/opt/hss-study-voice/output` — **na raiz do checkout**, irmão de `backend/` e `frontend/` (confirmado em `backend/app/core/config.py`: `OUTPUT_DIR = BASE_DIR.parent / "output"`). **Não é** `/opt/hss-study-voice/backend/output` — esse caminho existe no repositório mas contém só uma fixture `voice_samples/` residual, não relacionada e não gerenciada pelo timer de limpeza. Qualquer task ou comando de limpeza que aponte para `backend/output/` está incorreto.
- **Marcador do release publicado**: tag Git `deploy-<timestamp>` no HEAD atual, **ou** arquivo `/opt/hss-study-voice/deploy/CURRENT_RELEASE` contendo o hash do commit — escrito **antes** de cada `git pull` de uma nova versão (`data-model.md`, Deploy/Rollback Procedure State)
- Fonte de configuração no repositório: `deploy/Caddyfile`, `deploy/hss-backend.service`, `deploy/output-cleanup.service`, `deploy/output-cleanup.timer`, `deploy/README.md`
- Destino da configuração no VPS: `/etc/caddy/Caddyfile`, `/etc/systemd/system/hss-backend.service`, `/etc/systemd/system/output-cleanup.service`, `/etc/systemd/system/output-cleanup.timer`

---

## Phase 1: Setup (Bootstrap do VPS)

**Purpose**: Preparar o VPS do zero antes de qualquer configuração operacional deste repositório

- [ ] T001 Provisionar um VPS Ubuntu LTS e apontar o DNS do domínio escolhido para o IP do VPS (pré-requisito de infraestrutura, fora do repositório — Assumption de `spec.md`)
- [ ] T002 Criar um usuário de serviço dedicado sem privilégios de root no VPS (ex. `hssdeploy`), configurar autenticação SSH apenas por chave pública e desabilitar `PasswordAuthentication` em `sshd_config` (FR-011, `research.md` Decisão 7)
- [ ] T003 Verificar o hardening de SSH do passo anterior: confirmar login SSH por chave bem-sucedido a partir de uma máquina cliente **e** confirmar que `sshd -T 2>/dev/null | grep -i passwordauthentication` retorna `passwordauthentication no` no VPS (FR-011; `data-model.md`, Verificação de Segurança: SSH e Firewall)
- [ ] T004 [P] Configurar o firewall `ufw` no VPS permitindo apenas as portas 22 (SSH), 80 e 443 (HTTP/HTTPS) (`research.md` Decisão 7)
- [ ] T005 [P] Verificar a configuração de firewall do passo anterior: `ufw status verbose` deve listar exatamente as portas `22`, `80` e `443` como `ALLOW` — nenhuma outra regra presente (FR-011; `data-model.md`, Verificação de Segurança: SSH e Firewall)
- [ ] T006 [P] Instalar `uv` no VPS sob o usuário de serviço, para gerenciar o Python 3.13 exigido por `backend/pyproject.toml` (`research.md` Decisão 3)
- [ ] T007 [P] Instalar o Caddy no VPS a partir do repositório oficial do projeto (`research.md` Decisão 1)
- [ ] T008 Clonar o repositório em `/opt/hss-study-voice` no VPS sob o usuário de serviço e fazer checkout do commit/tag aprovado para o primeiro deploy

**Checkpoint**: VPS acessível por SSH com chave (senha desativada, confirmado), firewall restrito e confirmado, `uv` e Caddy instalados, repositório clonado.

---

## Phase 2: Foundational (Compartilhado entre todas as User Stories)

**Purpose**: Estrutura mínima no repositório que todas as fases seguintes consomem

**⚠️ CRITICAL**: Nenhuma task de User Story pode começar antes desta fase

- [ ] T009 Criar o diretório `deploy/` na raiz do repositório, paralelo a `backend/`, `frontend/` e `specs/` (`plan.md`, Structure Decision)
- [ ] T010 [P] Criar `deploy/README.md` com o esqueleto de seções: Setup inicial, Verificações de segurança (SSH/UFW), Deploy backend, Deploy frontend, Reverse proxy/TLS, Retenção de output, Marcador de release, Rollback, Verificação de logs, Health check, Acompanhamento pós-deploy — preenchido progressivamente pelas fases seguintes
- [ ] T011 Confirmar no VPS que a configuração de produção do backend (variáveis lidas por `backend/app/core/config.py`, ex. `OUTPUT_DIR`, `VOICES_DIR`, `DEFAULT_VOICE`) está definida fora do controle de versão (ex. arquivo de ambiente local ao serviço), sem segredos commitados no repositório

**Checkpoint**: `deploy/` existe com README esqueleto; configuração de produção do backend definida no VPS.

---

## Phase 3: Deploy Backend (User Story 1 — P1) 🎯 parte do MVP

**Goal**: Backend FastAPI rodando no VPS como serviço supervisionado, vinculado apenas a `127.0.0.1:8000`, com proteção contra crash loop e persistência através de reboot

**Independent Test**: `systemctl status hss-backend` mostra `active (running)`; `curl 127.0.0.1:8000/health` responde localmente no VPS

- [ ] T012 [US1] Criar `deploy/hss-backend.service` com os atributos completos de `data-model.md` (Backend Service Unit): `ExecStart=uv run uvicorn app.main:app --host 127.0.0.1 --port 8000`, `WorkingDirectory=/opt/hss-study-voice/backend`, `User=hssdeploy`, `After=network.target`, `Restart=on-failure`, `RestartSec=5`, `StartLimitIntervalSec=60`, `StartLimitBurst=5`, e uma seção `[Install]` com `WantedBy=multi-user.target` (sem esta seção, `systemctl enable` não persiste através de reboots — FR-005)
- [ ] T013 [US1] No VPS, em `/opt/hss-study-voice/backend`, executar `uv sync --frozen` sob o usuário de serviço para instalar Python 3.13 e as dependências fixadas em `uv.lock`
- [ ] T014 [US1] Copiar `deploy/hss-backend.service` para `/etc/systemd/system/hss-backend.service` no VPS e executar `systemctl daemon-reload`
- [ ] T015 [US1] Executar `systemctl enable --now hss-backend` no VPS; confirmar via `systemctl status hss-backend` que está `active (running)` e vinculado apenas a `127.0.0.1:8000` (nunca uma interface pública — invariante de `data-model.md`)
- [ ] T016 [US1] Executar uma chamada de "aquecimento" local no VPS (`curl` contra `127.0.0.1:8000`, gerando um áudio de teste) para provisionar o modelo de voz padrão via `PiperProvider.ensure_voice_downloaded`, confirmando que o VPS tem acesso de saída HTTPS a `huggingface.co` (`research.md` Decisão 6)

**Checkpoint**: Backend responde localmente no VPS; modelo de voz padrão já provisionado; serviço resistente a crash loop e a reboot.

---

## Phase 4: Deploy Frontend (User Story 1 — P1) 🎯 parte do MVP

**Goal**: Build de produção do frontend disponível como arquivos estáticos no VPS, sem processo Node.js em produção

**Independent Test**: `/opt/hss-study-voice/frontend/dist/index.html` existe no VPS; nenhum processo Node.js está em execução

- [ ] T017 [US1] Gerar o build de produção: `npm ci && npm run build` em `frontend/`, produzindo `frontend/dist/` — sem alterar nenhum arquivo de código-fonte dentro de `frontend/` (`research.md` Decisão 4)
- [ ] T018 [US1] Copiar `frontend/dist/` para `/opt/hss-study-voice/frontend/dist` no VPS, sob o usuário de serviço
- [ ] T019 [US1] Confirmar no VPS que não existe processo Node.js supervisionado em produção — apenas os arquivos estáticos em `/opt/hss-study-voice/frontend/dist` (`research.md` Decisão 4)

**Checkpoint**: Build do frontend presente no VPS, pronto para ser servido pelo Caddy.

---

## Phase 5: Reverse Proxy / TLS (User Story 1 — P1, base para User Story 4) 🎯 completa o MVP

**Goal**: Caddy como único processo de borda, roteando same-origin e terminando HTTPS automaticamente — apenas depois de confirmadas as pré-condições de DNS e permissão de arquivo

**Independent Test**: `https://<dominio>/` carrega o frontend; `https://<dominio>/api/...` e `https://<dominio>/health` chegam ao backend; `http://<dominio>/` redireciona para HTTPS

- [ ] T020 [US1] Verificar a propagação de DNS do domínio escolhido: `dig +short <dominio>` a partir de uma rede externa ao VPS deve retornar o IP do VPS — **antes** de declarar o domínio no `Caddyfile` (FR-001/FR-004; `research.md` Decisão 1, nota de 2026-10-04; Edge Case de `spec.md` sobre DNS não propagado)
- [ ] T021 [US1] Criar `deploy/Caddyfile` com as regras de roteamento same-origin: `/api/*` → `reverse_proxy 127.0.0.1:8000`, `/health` → `reverse_proxy 127.0.0.1:8000`, demais caminhos → `file_server` servindo `/opt/hss-study-voice/frontend/dist` (`data-model.md`, Reverse Proxy Routing Table; `research.md` Decisão 2; Clarification de FR-007)
- [ ] T022 [US1] Declarar o domínio público no `deploy/Caddyfile` (após T020 confirmar a propagação) para que o Caddy emita e renove automaticamente o certificado HTTPS, com redirecionamento HTTP→HTTPS nativo (FR-003, FR-004, `research.md` Decisão 1)
- [ ] T023 [US1] Garantir que o usuário de sistema do Caddy tem permissão de leitura recursiva em `/opt/hss-study-voice/frontend/dist` e `/opt/hss-study-voice/frontend/dist.prev` (ajustar propriedade/grupo/ACL conforme a forma de instalação do Caddy) — **antes** de recarregar o serviço, para evitar `403` no `file_server` (`data-model.md`, Reverse Proxy — Pré-condições e Permissões; `research.md` Decisão 1, nota de 2026-10-04)
- [ ] T024 [US1] Copiar `deploy/Caddyfile` para `/etc/caddy/Caddyfile` no VPS e executar `systemctl enable --now caddy` (primeira vez) ou `systemctl reload caddy` (atualizações)
- [ ] T025 [US1] A partir de um dispositivo fora da rede de desenvolvimento, acessar `https://<dominio>/`, colar um texto de estudo, gerar o áudio e reproduzi-lo, confirmando paridade com o ambiente local (SC-001; `quickstart.md` US1 passo 2)
- [ ] T026 [US1] Acessar `http://<dominio>/` (sem HTTPS) e confirmar o redirecionamento automático para `https://` (FR-003; `quickstart.md` US1 passo 3)

**Checkpoint**: 🎯 **MVP completo** — User Story 1 entregue: aplicação publicamente acessível via HTTPS, fim-a-fim, com DNS e permissões de arquivo verificados antes do teste de aceite.

---

## Phase 6: Retenção de Output (User Story 3 — P2)

**Goal**: `output/` na raiz do repositório (nunca limpo pelo pipeline hoje) passa a ter retenção explícita de 24h, sem mudar código do backend

**Independent Test**: um arquivo de teste com `mtime` > 24h é removido pelo timer; arquivos recentes permanecem

- [ ] T027 [P] [US3] Criar `deploy/output-cleanup.service` (unit `Type=oneshot`) que remove arquivos em `output/` **na raiz do repositório** (`/opt/hss-study-voice/output/`, **não** `backend/output/`) com `mtime` maior que 24 horas, sem tocar `backend/temp/` (`data-model.md`, Output Retention Policy — corrigida em 2026-10-04; `research.md` Decisão 5)
- [ ] T028 [P] [US3] Criar `deploy/output-cleanup.timer` disparando `output-cleanup.service` diariamente
- [ ] T029 [US3] Copiar as duas units para `/etc/systemd/system/` no VPS, executar `systemctl daemon-reload` e `systemctl enable --now output-cleanup.timer`
- [ ] T030 [US3] Gerar um áudio em produção e, via SSH, inspecionar `/opt/hss-study-voice/output/` (raiz do checkout) confirmando que o par `.mp3`/`.timeline.json` existe imediatamente após a resposta (`quickstart.md` US3 passo 1)
- [ ] T031 [US3] Criar um arquivo de teste em `/opt/hss-study-voice/output/` (raiz — **não** em `backend/output/`, que é a fixture residual `voice_samples/` não gerenciada por este timer) com `mtime` forçado para mais de 24h no passado, executar `systemctl start output-cleanup.service` manualmente e confirmar que apenas o arquivo de teste é removido, preservando arquivos recentes (SC-004; `quickstart.md` US3 passo 2)
- [ ] T032 [US3] Confirmar no navegador que a biblioteca do estudo gerado em T030 continua acessível via IndexedDB mesmo após a limpeza do passo anterior (`quickstart.md` US3 passo 3 — comportamento da Fase 3, inalterado aqui)

**Checkpoint**: User Story 3 completa — nenhum arquivo de usuário se acumula indefinidamente no VPS, no diretório correto.

---

## Phase 7: Processo de Deploy e Rollback (User Story 2 — P2)

**Goal**: Publicar uma nova versão e reverter — **backend e frontend** — seguindo apenas passos documentados em `deploy/README.md`, com uma referência explícita de para onde reverter

**Independent Test**: seguir o runbook do início ao fim publica uma alteração aprovada; o rollback documentado restaura a versão anterior tanto do frontend quanto do backend, validado contra `/health` e a API

- [ ] T033 [US2] Documentar e implementar em `deploy/README.md` o marcador de release: **antes** de qualquer `git pull`, registrar explicitamente o commit atualmente publicado — via tag Git `deploy-<timestamp>` criada no HEAD atual, **ou** arquivo `/opt/hss-study-voice/deploy/CURRENT_RELEASE` contendo o hash do commit — para servir de referência confiável de rollback, sem depender de `git log`/memória do operador (`research.md` Decisão 8, nota de 2026-10-04; `data-model.md`, Deploy/Rollback Procedure State)
- [ ] T034 [US2] Documentar em `deploy/README.md` o procedimento de deploy: aplicar T033 (registrar o marcador) **antes** de `git pull` até o commit/tag aprovado em `/opt/hss-study-voice`; backend: `uv sync --frozen` + `systemctl restart hss-backend`; frontend: `npm ci && npm run build`, preservando o `dist/` atual como `dist.prev/` antes de substituí-lo pelo novo build (`research.md` Decisão 8; FR-009)
- [ ] T035 [US2] Documentar em `deploy/README.md` o procedimento de rollback usando o marcador de T033 como referência (nunca "o commit anterior" inferido manualmente): backend via `git checkout` do commit/tag registrado no marcador + `uv sync --frozen` + `systemctl restart hss-backend`; frontend via restauração imediata de `dist.prev/` sem reconstruir (`research.md` Decisão 8; FR-010)
- [ ] T036 [US2] Seguir `deploy/README.md` do início ao fim para publicar uma alteração trivial já aprovada, medindo o tempo total e confirmando menos de 15 minutos sem apoio do autor original do processo (SC-003; `quickstart.md` US2 passo 2)
- [ ] T037 [US2] Executar um rollback **real do backend**: a partir do marcador registrado em T033, fazer `git checkout` do commit/tag anterior ao publicado em T036, rodar `uv sync --frozen`, `systemctl restart hss-backend`, e validar `GET /health` **e** uma chamada real de API (gerar um áudio de teste) confirmando que o comportamento volta ao da versão anterior, sem indisponibilidade permanente (FR-010; `quickstart.md` US2 passo 4)
- [ ] T038 [US2] Interromper deliberadamente uma publicação do **frontend** (ex. encerrar o `npm run build` no meio) e aplicar o procedimento de rollback de `deploy/README.md` (restaurar `dist.prev/`), confirmando que a versão anterior continua disponível publicamente durante e após a interrupção (FR-010; `quickstart.md` US2 passo 3)

**Checkpoint**: User Story 2 completa — deploy e rollback (backend **e** frontend) são repetíveis por qualquer pessoa seguindo apenas o runbook, com uma referência explícita de versão anterior.

---

## Phase 8: Health e Validação de Certificado (User Story 4 — P3)

**Goal**: Saúde do serviço (liveness) e validade pontual do certificado HTTPS verificáveis publicamente, sem vazar configuração sensível — sem expandir o escopo para readiness completa

**Independent Test**: `curl https://<dominio>/health` responde `200`; certificado TLS válido no momento da verificação

- [ ] T039 [US4] `curl -s https://<dominio>/health` a partir de fora do VPS e confirmar resposta `200` com `status: ok` e metadados não sensíveis (FR-008; `quickstart.md` US4 passo 1 — rota já coberta pelo `deploy/Caddyfile` da Fase 5)
- [ ] T040 [US4] Documentar explicitamente em `deploy/README.md` que `/health` é um check de **liveness** (processo ativo, `ffmpeg` encontrado via `shutil.which`) e que readiness completa (ex. modelo de voz já provisionado, espaço em disco) fica fora do escopo desta fase — sem expandir o endpoint, que é código de aplicação (`data-model.md`, Health Endpoint Semantics)
- [ ] T041 [US4] Verificar a validade **pontual** do certificado TLS emitido automaticamente pelo Caddy (`curl -vI https://<dominio>/ 2>&1 | grep -i "expire\|SSL certificate"` ou ferramenta equivalente), registrando explicitamente que esta checagem não substitui a confirmação de um ciclo completo de renovação (SC-005 — ver Fase 9, Acompanhamento Pós-Deploy)
- [ ] T042 [US4] Documentar em `deploy/README.md` como consultar o endpoint de health, como interpretar a resposta e que a renovação do certificado é automática pelo Caddy, sem cron/timer adicional

**Checkpoint**: User Story 4 completa — saúde (liveness) e certificado (validade pontual) verificáveis a qualquer momento; readiness completa e ciclo de renovação documentados como fora do escopo imediato.

---

## Phase 9: Validação Final, Resiliência e Acompanhamento Pós-Deploy (Polish — cross-cutting)

**Purpose**: Consolidar hardening documentado, auditar logs, validar os edge cases do spec e registrar o acompanhamento não bloqueante de SC-002/SC-005

- [ ] T043 Verificar que logs de produção não registram o texto completo enviado pelo usuário: gerar um áudio de teste com um texto identificável e único, inspecionar `journalctl -u hss-backend` e, se habilitado, o access log do Caddy, confirmando que nenhum dos dois grava o corpo/texto completo da requisição (FR-012; `data-model.md`, Verificação de Conteúdo de Logs)
- [ ] T044 [P] Documentar em `deploy/README.md` a seção de hardening consolidada: SSH por chave (T003), usuário sem root, firewall `ufw` 22/80/443 (T005), bind do backend em `127.0.0.1` — reunindo o que já foi verificado nas Fases 1 e 3 (FR-011; `research.md` Decisão 7)
- [ ] T045 `systemctl stop hss-backend` manualmente no VPS e confirmar que o systemd reinicia o serviço automaticamente (`Restart=on-failure`), sem login manual, e que `/api` volta a responder (FR-005; `quickstart.md` Resiliência passo 1)
- [ ] T046 Forçar um crash loop controlado (ex. renomear temporariamente o executável/arquivo exigido pelo `ExecStart`) e confirmar que o limite de restart (`StartLimitBurst=5` em `StartLimitIntervalSec=60`, de T012) interrompe o loop em vez de consumir CPU indefinidamente; restaurar o arquivo e confirmar que `systemctl reset-failed && systemctl start hss-backend` retoma a operação normal (`data-model.md`, Backend Service Unit; `quickstart.md` Resiliência passo 2)
- [ ] T047 Reiniciar o VPS (`reboot`) em uma janela controlada e confirmar que Caddy e o backend voltam a rodar sozinhos após o boot, via `[Install] WantedBy=multi-user.target`, sem intervenção manual (`quickstart.md` Resiliência passo 3)
- [ ] T048 Executar o roteiro completo de `quickstart.md` do início ao fim (exceto a seção "Acompanhamento Pós-Deploy") em um VPS que começou limpo (sem estado de tentativa anterior), confirmando que todos os itens passam em sequência (SC-001, SC-003, SC-004 e as checagens pontuais de FR-008/TLS)
- [ ] T049 Revisar `deploy/README.md` de ponta a ponta confirmando que pode ser seguido por outra pessoa além do autor original, sem passos implícitos ou não documentados (SC-003)
- [ ] T050 Registrar em `deploy/README.md` o checklist de acompanhamento pós-deploy (não bloqueante) para SC-002: checagem diária de `GET /health` por 7 dias consecutivos, com resultado anotado (ex. arquivo/planilha simples) — explicitamente fora do gate de conclusão desta fase (`data-model.md`, Validação de Longo Prazo)
- [ ] T051 Registrar em `deploy/README.md` o checklist de acompanhamento pós-deploy (não bloqueante) para SC-005: observar o log do Caddy em torno de ~30 dias antes da expiração do certificado (validade típica de 90 dias) e anexar evidência da primeira renovação automática quando ela ocorrer — explicitamente fora do gate de conclusão desta fase (`data-model.md`, Validação de Longo Prazo)

**Checkpoint**: Todas as User Stories validadas; `deploy/README.md` completo e auditável; acompanhamento de longo prazo documentado e iniciado, sem bloquear a conclusão da fase.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Fase 1)**: sem dependências — pode começar imediatamente
- **Foundational (Fase 2)**: depende da Fase 1 — bloqueia todas as User Stories
- **Deploy Backend (Fase 3, US1)**: depende da Fase 2
- **Deploy Frontend (Fase 4, US1)**: depende da Fase 2; pode rodar em paralelo à Fase 3 (hosts/arquivos diferentes)
- **Reverse Proxy/TLS (Fase 5, US1)**: depende das Fases 3 e 4 (precisa do backend e do `dist/` já presentes no VPS para rotear/servir); T020 (DNS) pode ser verificado a qualquer momento após T001, mas é sequenciado aqui como gate imediatamente anterior a T022 — **completa o MVP**
- **Retenção (Fase 6, US3)**: depende da Fase 3 (precisa do backend rodando e gerando output no diretório correto); independente das Fases 5, 7 e 8
- **Deploy/Rollback (Fase 7, US2)**: depende das Fases 3, 4 e 5 (precisa de uma versão publicada para praticar deploy/rollback sobre ela, incluindo o rollback real do backend em T037); independente das Fases 6 e 8
- **Health/Certificado (Fase 8, US4)**: depende da Fase 5 (rota `/health` já roteada pelo Caddyfile); independente das Fases 6 e 7
- **Validação Final (Fase 9)**: depende de todas as User Stories desejadas estarem completas; T050/T051 (acompanhamento de longo prazo) não bloqueiam T048/T049

### Parallel Opportunities

- T004 e T006/T007 (Fase 1) podem rodar em paralelo — ferramentas independentes no VPS; T003 depende de T002, T005 depende de T004
- T010 (Fase 2) pode rodar em paralelo a T011
- Fase 3 (Deploy Backend) e Fase 4 (Deploy Frontend) podem rodar em paralelo entre si — hosts/arquivos distintos, ambas pré-requisito da Fase 5
- T027 e T028 (Fase 6) podem rodar em paralelo — arquivos diferentes (`deploy/output-cleanup.service` e `deploy/output-cleanup.timer`)
- Após o MVP (Fase 5) completo, as Fases 6 (US3), 7 (US2) e 8 (US4) podem rodar em paralelo entre si
- T050 e T051 (Fase 9) podem rodar em paralelo entre si e com T044

---

## Implementation Strategy

### MVP First (User Story 1 apenas)

1. Completar Fase 1: Setup do VPS (com verificações de SSH/UFW)
2. Completar Fase 2: Foundational
3. Completar Fase 3: Deploy Backend (unit systemd completa)
4. Completar Fase 4: Deploy Frontend
5. Completar Fase 5: Reverse Proxy/TLS (com DNS e permissões verificados antes do teste de aceite)
6. **PARAR e VALIDAR**: executar `quickstart.md` seção US1 isoladamente
7. Aplicação já está publicamente acessível via HTTPS — valor central da fase entregue

### Entrega Incremental

1. Fases 1+2 → fundação pronta e verificada no VPS
2. Fases 3+4+5 → **MVP**: US1 (aplicação acessível publicamente)
3. Fase 6 → US3 (retenção de output no diretório correto, preservação da propriedade local dos dados)
4. Fase 7 → US2 (deploy e rollback — backend e frontend — repetíveis e documentados, com marcador de release)
5. Fase 8 → US4 (visibilidade de saúde do serviço — liveness — e certificado)
6. Fase 9 → validação final, resiliência (incluindo limite de crash loop), auditoria de logs, e início do acompanhamento pós-deploy de SC-002/SC-005

---

## Notes

- Nenhuma task altera arquivos dentro de `backend/` ou `frontend/` além de gerar o artefato de build (`frontend/dist/`, Fase 4) — toda configuração nova fica em `deploy/`, conforme `plan.md` (Structure Decision, Princípio IX).
- O diretório real de saída (`OUTPUT_DIR`) é `output/` na raiz do repositório, não `backend/output/` — corrigido em todos os artefatos em 2026-10-04 após verificação direta do código (`backend/app/core/config.py`).
- Rollback permanece manual e documentado (`deploy/README.md`, Fase 7), agora cobrindo backend e frontend com uma referência explícita de versão (marcador/tag, T033); nenhuma automação de rollback ou pipeline de CI/CD é introduzida nesta fase (Clarification de FR-010).
- Caddy + systemd permanecem a única infraestrutura operacional nova (Fases 1, 3, 5, 6); nenhuma fila, banco de dados, cache ou contêiner é adicionado (Princípio III/VII).
- Mesma origem é preservada em todas as fases: o backend nunca escuta em interface pública (Fase 3), e todo roteamento público passa pelo Caddy (Fase 5) — sem CORS entre frontend e backend (Clarification de FR-007).
- SC-002 e a cláusula de ciclo de renovação de SC-005 são acompanhamento pós-deploy não bloqueante (T050, T051) — o aceite inicial desta fase usa apenas as checagens pontuais de health/TLS (T039, T041, T048).
- `/health` permanece um check de liveness; readiness completa é explicitamente fora de escopo (T040) e não deve ser confundida com uma lacuna não documentada.
