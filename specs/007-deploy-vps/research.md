# Phase 0 Research: Deploy em VPS do HSS Study Voice

## Decisão 1 — Caddy como reverse proxy e terminador TLS

**Decision**: Usar Caddy como único processo de borda no VPS, responsável por HTTPS
automático (emissão e renovação de certificado), redirecionamento HTTP→HTTPS, roteamento
same-origin (Decisão 2) e serviço dos arquivos estáticos do frontend (`file_server`).

**Rationale**: FR-004 exige renovação automática do certificado sem intervenção manual
recorrente. O modo nativo de HTTPS automático do Caddy cobre emissão e renovação dentro do
próprio processo de borda, sem exigir um cron/timer separado para `certbot renew` coordenado
com o reload do proxy. Isso é uma peça móvel a menos que Nginx + certbot, consistente com o
Princípio VII (Sem Overengineering) sem perder nenhuma garantia de FR-001 a FR-004.

**Alternatives considered**:
- Nginx + certbot — amplamente documentado e já conhecido por muitos operadores, mas exige
  configurar um timer de renovação separado e coordenar o reload do Nginx após cada renovação;
  mais peças para manter corretas ao longo do tempo pelo mesmo resultado funcional.
- Terminar TLS em um load balancer gerenciado (ex.: do provedor de VPS) — rejeitado: amarra o
  plano a um provedor específico, contrariando a Assumption do spec de que o provedor ainda não
  foi escolhido.

## Decisão 2 — Roteamento same-origin: `/api/*` e `/health` para o backend, resto para o frontend

**Decision**: O Caddyfile roteia `/api/*` e `/health` para `127.0.0.1:8000` (backend FastAPI) e
qualquer outro caminho para o `file_server` servindo `frontend/dist/`.

**Rationale**: Implementa a Clarification de FR-007 (mesma origem, sem CORS). O endpoint de
health (`backend/app/main.py`) está montado em `/health`, fora do prefixo
`settings.API_V1_STR` (`/api/v1`) usado pelas rotas de estudo — por isso precisa de uma regra de
roteamento própria além de `/api/*`, senão FR-008 (health acessível publicamente) ficaria sem
rota. Nenhuma mudança no código do backend é necessária: o prefixo de rota já existente é
suficiente para o Caddy distinguir API de health de frontend.

**Alternatives considered**:
- Mover `/health` para dentro de `/api` no código do backend — resolveria o roteamento com uma
  única regra, mas é uma mudança de código de aplicação fora do escopo de uma fase de deploy
  (Princípio VIII — Phase-Bounded Delivery); rejeitado em favor de uma segunda regra de
  roteamento, puramente operacional.
- Subdomínio dedicado para a API — rejeitado pela Clarification já registrada em `spec.md`
  (mesma origem escolhida para evitar CORS).

## Decisão 3 — Backend como serviço systemd, Python 3.13 gerenciado por `uv`

**Decision**: O backend roda como unit systemd (`deploy/hss-backend.service`), executando
`uv run uvicorn app.main:app --host 127.0.0.1 --port 8000` sob um usuário dedicado sem
privilégios de root, com `Restart=on-failure`. O interpretador Python 3.13 exigido por
`pyproject.toml` (`requires-python = ">=3.13"`) é instalado e gerenciado pelo próprio `uv`, não
pelo gerenciador de pacotes do sistema operacional.

**Rationale**: FR-005 exige reinício automático sem login manual — systemd já está presente em
qualquer VPS Linux moderno e cobre isso nativamente, sem introduzir Supervisor, PM2 ou outro
gerenciador de processos (Princípio VII). Ubuntu LTS (Assumption do spec) tipicamente não
empacota Python 3.13 nos repositórios padrão; `uv` já é a ferramenta usada para
desenvolvimento local (`uv.lock` versionado) e sabe instalar e fixar a versão exata de Python
exigida, tornando o ambiente de produção reproduzível a partir do mesmo lockfile usado
localmente, sem exigir PPA de terceiros ou compilação manual do Python.

**Alternatives considered**:
- Imagem de contêiner (Docker) — adiaria o problema de versão do Python para a imagem base, mas
  introduz um motor de contêiner como infraestrutura nova sem necessidade demonstrada
  (Princípio III/VII); nenhuma Assumption ou FR do spec pede isolamento por contêiner.
  Rejeitado por agora; pode ser revisitado em fase futura se houver motivo concreto.
- Python do sistema (`apt install python3`) — rejeitado: normalmente mais antigo que 3.13 em
  Ubuntu LTS, e divergiria da versão fixada em `uv.lock`, arriscando comportamento diferente do
  ambiente de desenvolvimento.

**Hardening mínimo da unit (adicionado em 2026-10-04)**: a unit `deploy/hss-backend.service`
MUST incluir, além do já descrito acima, `After=network.target` (ordem de boot — só inicia após
a rede subir), uma seção `[Install]` com `WantedBy=multi-user.target` (sem isso,
`systemctl enable` não persiste o serviço através de reboots, contradizendo FR-005) e um limite
explícito de reinício para evitar um crash loop consumir CPU indefinidamente
(`RestartSec` + `StartLimitIntervalSec`/`StartLimitBurst`). Os valores exatos estão em
`data-model.md` (Backend Service Unit), que passa a ser a fonte única desses atributos.

## Decisão 4 — Frontend publicado como build estático, sem processo Node.js em produção

**Decision**: `frontend/dist/` (saída de `npm run build`, já existente no pipeline de build
atual) é copiado para o VPS e servido diretamente pelo `file_server` do Caddy. Nenhum processo
Node.js roda em produção.

**Rationale**: O frontend já é uma SPA estática (Vite); não há SSR nem API própria do Node a
servir. Servir arquivos estáticos pelo mesmo processo de borda que já termina TLS e faz o
roteamento same-origin (Decisão 1 e 2) evita manter um segundo processo supervisionado só para
servir arquivos imutáveis.

**Alternatives considered**:
- Servir via `vite preview` em produção — rejeitado: documentação do próprio Vite recomenda
  `preview` apenas para inspecionar o build localmente, não para produção; exigiria um processo
  Node.js adicional supervisionado sem necessidade.

## Decisão 5 — Retenção de `OUTPUT_DIR` via timer systemd, sem mudança de código do backend

**Decision**: Um timer systemd (`deploy/output-cleanup.timer` + `.service`) executa diariamente
um comando que remove arquivos em `output/` **na raiz do repositório** (não dentro de
`backend/`) com `mtime` maior que 24 horas. Nenhum código Python é alterado.

**Correção registrada em 2026-10-04**: a redação original desta decisão e de `data-model.md`
apontava o alvo como `backend/output/`. Isso estava **errado** e foi corrigido após verificação
direta do código: `backend/app/core/config.py` define
`OUTPUT_DIR: Path = BASE_DIR.parent / "output"`, onde `BASE_DIR` resolve para `backend/` — logo
`OUTPUT_DIR` real é `<raiz-do-repositório>/output/`, **irmão** de `backend/` e `frontend/`, não
um subdiretório de `backend/`. Confirmado no filesystem: `output/` na raiz tinha 268 arquivos
acumulados (o "mais de 200 arquivos" citado abaixo refere-se a este diretório), enquanto
`backend/output/` continha apenas uma pasta `voice_samples/` não relacionada — fixture de teste
residual, não gerenciada por este timer e que não deve ser confundida com o alvo real da
limpeza. Toda referência a este diretório em `plan.md`, `data-model.md`, `quickstart.md` e
`tasks.md` foi corrigida para `output/` (raiz).

**Rationale**: Durante o levantamento técnico desta fase, confirmou-se que `TEMP_DIR` (chunks
WAV intermediários) já é limpo em sucesso e falha pelo `AudioOrchestrator`
(`app/services/audio/orchestrator.py`), mas o `OUTPUT_DIR` final (`.mp3` + `.timeline.json` por
estudo, servido pela API) nunca é apagado pelo backend — o `output/` local do repositório (raiz)
tem mais de 200 arquivos acumulados de execuções de desenvolvimento, confirmando o comportamento.
Isso é um risco real de esgotamento de disco em um VPS de longa duração e tensiona o Princípio
II (Local-First Ownership: "cópias do lado do servidor DEVEM ser temporárias"). A decisão do
usuário para esta fase foi tratar isso como infraestrutura operacional (timer), não como
mudança de pipeline — o frontend já baixa e persiste o MP3/timeline no IndexedDB do navegador
(Fase 3) imediatamente após a geração, então 24 horas é uma margem de segurança generosa, não um
acoplamento apertado ao fluxo síncrono de geração.

**Alternatives considered**:
- Alterar `AudioOrchestrator`/a rota de estudo para apagar o par MP3/timeline do `OUTPUT_DIR`
  assim que a resposta é servida com sucesso — resolveria a causa raiz no código, mas é uma
  mudança de pipeline fora do escopo desta fase de deploy (Princípio VIII); explicitamente
  rejeitada pelo usuário em favor da opção operacional.
- Não tratar a retenção nesta fase — rejeitada: deixaria SC-004/FR-006 falsos em produção e o
  disco do VPS cresceria sem limite.

## Decisão 6 — Modelo de voz Piper: nenhum provisionamento manual necessário

**Decision**: Nenhuma etapa de deploy precisa baixar manualmente o modelo de voz. O
`PiperProvider.ensure_voice_downloaded` (`app/providers/tts/piper_provider.py`) já baixa o
`.onnx`/`.onnx.json` do Hugging Face para `VOICES_DIR` na primeira vez que a voz é solicitada.
O runbook (`deploy/README.md`) documenta apenas que o VPS precisa de acesso de saída HTTPS a
`huggingface.co` e recomenda uma chamada de "aquecimento" (uma geração de teste) logo após o
primeiro deploy, para que o primeiro usuário real não pague a latência do download.

**Rationale**: Código existente já resolve o provisionamento; documentar um passo manual
duplicaria uma capacidade que já existe e poderia divergir dela. Não encontrada nenhuma
dependência de sistema adicional para o Piper além do FFmpeg já conhecido — os dados do
`espeak-ng` usados para fonemização vêm empacotados com o pacote Python `piper-tts`
(`piper.phonemize_espeak.ESPEAK_DATA_DIR`), sem exigir um pacote do sistema operacional em
Linux.

**Alternatives considered**:
- Baixar todos os modelos de voz do catálogo (`PIPER_PT_BR_CATALOG`) antecipadamente no deploy —
  rejeitado: nenhuma FR exige disponibilizar vozes além da padrão configurada
  (`DEFAULT_VOICE`); baixar todas aumentaria tempo de deploy e uso de disco sem necessidade
  comprovada (Princípio VII).

## Decisão 7 — Hardening mínimo de SSH e firewall

**Decision**: Acesso SSH ao VPS apenas por chave pública (`PasswordAuthentication no`), um
usuário de deploy/serviço dedicado sem root, e firewall (`ufw`) permitindo apenas as portas 22
(SSH), 80 e 443 (HTTP/HTTPS via Caddy). O backend nunca escuta em uma interface pública — está
vinculado a `127.0.0.1:8000` (Decisão 3) e por isso nem precisa de regra de firewall própria.

**Rationale**: Atende FR-011 com o mínimo necessário, sem introduzir uma ferramenta de
segurança dedicada (WAF, IDS) sem evidência de necessidade (Princípio VII). Vincular o backend a
`127.0.0.1` é uma defesa em profundidade simples: mesmo que a regra de firewall for esquecida ou
mal aplicada, o processo do backend continua inacessível de fora do próprio VPS.

**Alternatives considered**:
- Expor o backend em uma porta pública protegida só por firewall — rejeitado: depende de uma
  única camada de defesa (a regra de firewall) para uma garantia que o bind em loopback já dá
  de forma mais simples e redundante.

## Decisão 8 — Deploy e rollback por Git, documentados em `deploy/README.md`

**Decision**: Publicar uma nova versão é: `git pull` até o commit/tag aprovado, reconstruir
apenas o lado alterado (backend: `uv sync --frozen` + `systemctl restart hss-backend`;
frontend: `npm ci && npm run build`, copiando o novo `dist/` para o diretório servido pelo
Caddy só depois que o build termina com sucesso, preservando o build anterior como
`dist.prev/` até a próxima publicação). Rollback é o mesmo procedimento aplicado ao commit/tag
anterior — ou, para o frontend, restaurar `dist.prev/` imediatamente, sem precisar reconstruir.

**Rationale**: Resolve FR-009 e FR-010 conforme a Clarification (rollback manual, porém
documentado — sem automação nesta fase). Manter `dist.prev/` dá um caminho de rollback do
frontend em segundos, sem depender de reconstruir a versão anterior a partir do código-fonte
sob pressão. Reconstruir só o lado alterado evita reiniciar o backend (interrompendo gerações em
andamento) quando apenas o frontend mudou, e vice-versa.

**Alternatives considered**:
- Pipeline de CI/CD completo (build/push/deploy automatizado a cada merge) — explicitamente fora
  do escopo desta fase (Assumptions do spec); rejeitado por agora, pode ser uma fase futura.
- Rollback automatizado por script que decide sozinho quando reverter — rejeitado pela
  Clarification já registrada (rollback manual é suficiente para esta fase).

**Marcador explícito do release publicado (adicionado em 2026-10-04)**: depender de `git log`
ou da memória do operador para saber qual era "o commit anterior" é frágil, especialmente depois
de duas ou mais publicações sem rollback entre elas. Antes de qualquer `git pull`/checkout de uma
nova versão, o commit atualmente publicado MUST ser registrado explicitamente — via tag Git
(`deploy-<timestamp>`) criada no HEAD atual, **ou** um arquivo marcador simples
`deploy/CURRENT_RELEASE` no VPS contendo o hash do commit — antes de avançar para o novo commit.
O procedimento de rollback em `deploy/README.md` passa a referenciar esse marcador/tag como
fonte da verdade, não "o commit anterior" inferido manualmente. Isso não introduz automação de
rollback (ainda é um comando manual do operador), apenas remove a dependência de memória/`git
log` para decidir **para onde** reverter — consistente com a Clarification de FR-010 (rollback
manual, porém documentado).

**Verificação de permissões do Caddy (adicionado em 2026-10-04)**: o pacote Caddy normalmente
roda sob um usuário de sistema próprio (`caddy`), diferente do usuário de deploy (`hssdeploy`,
Decisão 7) que possui `frontend/dist`. O runbook MUST incluir um passo explícito que garanta
leitura recursiva para o usuário do Caddy em `frontend/dist` e `frontend/dist.prev` (ajuste de
grupo/ACL, conforme a forma de instalação do Caddy) antes de recarregar o serviço — sem isso, o
`file_server` responde `403` e a Decisão 1 fica inoperante na prática, apesar de corretamente
configurada no papel.

**Verificação de propagação de DNS (adicionado em 2026-10-04)**: o Edge Case de `spec.md` sobre
DNS não propagado é tratado como uma pré-condição verificável, não apenas um risco aceito. Antes
de declarar o domínio no `Caddyfile` (o que dispara a primeira tentativa de emissão automática
de certificado), o runbook MUST incluir a verificação de que o registro DNS do domínio já resolve
para o IP do VPS (ex. `dig +short <dominio>` a partir de uma rede externa). Sem essa verificação,
a primeira tentativa de emissão falha e o Caddy entra em backoff, atrasando o FR-001/FR-004 sem
que a causa seja óbvia a quem está seguindo o runbook.
