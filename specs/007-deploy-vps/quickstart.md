# Quickstart: Deploy em VPS do HSS Study Voice

Esta fase não adiciona testes automatizados (nenhum código de aplicação é alterado — ver
Constitution Check em `plan.md`, Princípio IV). A validação é este roteiro manual, executado
contra o VPS publicado. O procedimento de setup/deploy/rollback em si fica documentado em
`deploy/README.md`, criado durante a implementação (`/speckit.tasks` + `/speckit.implement`);
este arquivo é o checklist de aceite, mapeado às User Stories e Success Criteria de `spec.md`.

## Pré-requisitos

- `deploy/README.md` seguido do início ao fim em um VPS Ubuntu LTS limpo (Caddyfile, unit
  systemd do backend, timer de limpeza de output, firewall, SSH por chave — `research.md`).
- Domínio próprio apontando para o IP do VPS, com **propagação confirmada** (`dig +short
  <dominio>` retornando o IP do VPS a partir de uma rede externa) antes de declarar o domínio no
  `Caddyfile` — sem isso a primeira emissão automática de certificado falha (`research.md`,
  Decisão 1, nota de 2026-10-04).
- Usuário de sistema do Caddy com permissão de leitura recursiva em `frontend/dist` e
  `frontend/dist.prev` confirmada (`data-model.md`, Reverse Proxy — Pré-condições e Permissões).

## Pré-validação de Segurança (antes de qualquer teste de aceite abaixo)

1. A partir de uma máquina cliente, confirmar login SSH por chave bem-sucedido no VPS.
2. No VPS, `sshd -T 2>/dev/null | grep -i passwordauthentication` deve retornar
   `passwordauthentication no`.
3. No VPS, `ufw status verbose` deve listar exatamente as portas `22`, `80` e `443` como
   permitidas — nenhuma outra regra `ALLOW` presente (FR-011; `data-model.md`, Verificação de
   Segurança: SSH e Firewall).

## US1 — Aplicação acessível publicamente (P1)

1. A partir de um dispositivo fora da rede de desenvolvimento, acessar `https://<dominio>/`.
   - Esperado: a aplicação carrega (SC-001).
2. Colar um texto de estudo, gerar o áudio e reproduzi-lo.
   - Esperado: mesmo resultado do ambiente local, servido via `/api` (Decisão 2 de
     `research.md`).
3. Acessar `http://<dominio>/` (sem HTTPS).
   - Esperado: redirecionamento automático para `https://` (FR-003).

## US2 — Processo de deploy repetível (P2)

1. Antes de publicar, confirmar que o commit atualmente publicado está registrado
   explicitamente (tag `deploy-<timestamp>` ou arquivo `deploy/CURRENT_RELEASE` no VPS) —
   **não** depender de `git log`/memória para saber qual é a versão anterior
   (`research.md`, Decisão 8, nota de 2026-10-04; `data-model.md`, Deploy/Rollback Procedure
   State).
2. Seguir `deploy/README.md` para publicar uma alteração trivial (ex.: um commit já aprovado).
   - Esperado: nova versão disponível em menos de 15 minutos, sem passo improvisado (FR-009,
     SC-003).
3. Interromper deliberadamente uma publicação do **frontend** (ex.: encerrar o comando de build
   no meio) e em seguida seguir o procedimento de rollback de `deploy/README.md`.
   - Esperado: a versão anterior continua disponível publicamente durante e após a
     interrupção (FR-010).
4. Executar um rollback **real do backend**: fazer checkout do commit/tag registrado no passo 1
   (anterior ao publicado no passo 2), rodar `uv sync --frozen`, `systemctl restart
   hss-backend`, e então validar `GET /health` e uma chamada real de API (gerar um áudio de
   teste) confirmando que o comportamento volta ao da versão anterior.
   - Esperado: backend volta a responder corretamente na versão anterior, sem indisponibilidade
     permanente (FR-010).

## US3 — Preservação da propriedade local dos dados (P2)

1. Gerar um áudio em produção; logo depois, inspecionar `output/` **na raiz do repositório** no
   VPS (via SSH) — **não** `backend/output/`, que contém apenas uma fixture `voice_samples/`
   residual e não é o `OUTPUT_DIR` real (`data-model.md`, Output Retention Policy, corrigido em
   2026-10-04).
   - Esperado: o par `.mp3`/`.timeline.json` dessa geração existe imediatamente após a
     resposta (comportamento inalterado do pipeline).
2. Forçar o timer de limpeza a rodar (`systemctl start output-cleanup.service`) sobre um
   arquivo de teste com `mtime` alterado para mais de 24h no passado, criado dentro de `output/`
   na raiz (não em `backend/output/`).
   - Esperado: o arquivo de teste é removido; arquivos com menos de 24h permanecem
     (`data-model.md`, Output Retention Policy; SC-004).
3. Confirmar que a biblioteca do estudo gerado no passo 1 está acessível no navegador mesmo
   depois da limpeza (IndexedDB local, Fase 3 — inalterado por esta fase).

## US4 — Visibilidade de saúde do serviço (P3)

1. `curl -s https://<dominio>/health` a partir de fora do VPS.
   - Esperado: resposta `200` com `status: ok` e metadados não sensíveis (FR-008).
   - **Nota de escopo**: `/health` é um check de **liveness** (processo ativo, `ffmpeg`
     encontrado) — não é um check de *readiness* completo (ex. modelo de voz já provisionado,
     espaço em disco). Essa distinção é documentada aqui e em `data-model.md` (Health Endpoint
     Semantics); expandir o endpoint para readiness completa é mudança de código do backend e
     fica fora do escopo desta fase.
2. Verificar o certificado: `curl -vI https://<dominio>/ 2>&1 | grep -i "expire\|SSL certificate"`
   (ou ferramenta equivalente).
   - Esperado: certificado válido no momento da verificação, emitido automaticamente pelo Caddy.
   - **Nota de escopo**: isto é uma checagem **pontual** de validade — não é, por si, a
     confirmação de "um ciclo completo de renovação automática" exigida por SC-005. Essa
     confirmação é tratada como acompanhamento pós-deploy (ver seção abaixo) e não bloqueia o
     aceite inicial desta fase.

## Verificação de Logs (FR-012)

1. Gerar um áudio de teste com um texto identificável e único (ex. uma frase que não apareça em
   nenhum outro teste).
2. Inspecionar o log do backend (`journalctl -u hss-backend`) e, se o access log do Caddy
   estiver habilitado, inspecioná-lo também.
   - Esperado: nenhum dos dois registra o texto completo submetido — apenas metadados
     operacionais (FR-012; `data-model.md`, Verificação de Conteúdo de Logs).

## Acompanhamento Pós-Deploy (não bloqueante — SC-002 e SC-005)

Estes itens **não** fazem parte do critério de conclusão imediato desta fase (ver `data-model.md`,
Validação de Longo Prazo); são iniciados no deploy inicial e confirmados depois, operacionalmente:

1. Registrar diariamente o resultado de `GET /health` por 7 dias consecutivos (ex. em um
   arquivo/planilha simples), confirmando SC-002 apenas quando os 7 dias estiverem completos
   sem indisponibilidade não planejada.
2. Acompanhar o log do Caddy em torno de ~30 dias antes da expiração do certificado (validade
   típica de 90 dias) e registrar evidência da primeira renovação automática bem-sucedida,
   confirmando SC-005 apenas quando esse ciclo ocorrer.

## Resiliência (edge cases do spec)

1. `systemctl stop hss-backend` manualmente no VPS, sem usar o painel do provedor.
   - Esperado: systemd reinicia o serviço automaticamente (`Restart=on-failure`, FR-005); `/api`
     volta a responder sem login manual.
2. Forçar um crash loop controlado (ex. renomear temporariamente o executável/arquivo exigido
   pelo `ExecStart` e reiniciar o serviço repetidamente).
   - Esperado: depois de `StartLimitBurst` tentativas em `StartLimitIntervalSec` segundos, o
     systemd para de reiniciar automaticamente (fica `failed`) em vez de consumir CPU em loop
     (`data-model.md`, Backend Service Unit). Restaurar o arquivo e confirmar que
     `systemctl reset-failed && systemctl start hss-backend` retoma a operação normal.
3. Reiniciar o VPS (`reboot`) em uma janela controlada.
   - Esperado: Caddy e o backend voltam a rodar sozinhos após o boot (unidades systemd
     habilitadas via `[Install] WantedBy=multi-user.target`), sem intervenção manual.

## Critério de conclusão desta fase

Todos os itens acima — exceto a seção "Acompanhamento Pós-Deploy" — passam em sequência, em um
VPS que começou limpo (sem estado de uma tentativa anterior) — isso corresponde a
`deploy/README.md` estar completo e correto o suficiente para ser seguido por outra pessoa além
do autor original (SC-003). SC-002 (7 dias) e a cláusula de ciclo de renovação de SC-005 são
validados depois, pelo acompanhamento operacional já documentado e iniciado — eles **não**
bloqueiam o aceite inicial desta fase.
