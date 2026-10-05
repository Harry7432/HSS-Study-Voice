# Implementation Plan: Deploy em VPS do HSS Study Voice

**Branch**: `007-deploy-vps` | **Date**: 2026-10-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/007-deploy-vps/spec.md`

## Summary

O HSS Study Voice (backend FastAPI/Piper/FFmpeg em `backend/`, frontend PWA em `frontend/`) hoje
só roda em `localhost`. Esta fase publica a aplicação já existente — sem alterar nenhum código
de aplicação — em um VPS Linux, atrás de Caddy como terminador TLS e proxy same-origin: `/` serve
o build estático do frontend, `/api/*` e `/health` são roteados para o backend
(`127.0.0.1:8000`, Decisão 2 de `research.md`), eliminando a necessidade de CORS (Clarification
de FR-007). O backend roda como serviço systemd com Python 3.13 gerenciado por `uv`
(`pyproject.toml`), reiniciando automaticamente em falha ou reboot (FR-005). Durante o
levantamento técnico, confirmou-se que o diretório de saída final (`output/` na raiz do
repositório — `OUTPUT_DIR` real de `app/core/config.py`, irmão de `backend/` e `frontend/`, não
um subdiretório de `backend/`) nunca é limpo pelo pipeline — diferente do diretório temporário,
que já é — então um timer systemd passa a remover esses arquivos com mais de 24h, puramente como
infraestrutura operacional, sem tocar o código do pipeline. Deploy e rollback são um procedimento Git documentado e manual
(sem CI/CD automatizado nesta fase, por decisão explícita durante a clarificação), registrado em
`deploy/README.md`.

## Technical Context

**Language/Version**: Backend inalterado — Python 3.13 (`pyproject.toml`, `requires-python
= ">=3.13"`), FastAPI, Piper TTS, FFmpeg. Frontend inalterado — TypeScript estrito/Vite 7. A
camada nova desta fase é declarativa/operacional: Caddyfile, units systemd, e um script de
deploy em shell POSIX — nenhuma linguagem de aplicação nova.

**Primary Dependencies**: Caddy (novo — reverse proxy e terminador TLS, processo do sistema
operacional, não uma dependência de `pyproject.toml`/`package.json`) e systemd (já presente em
qualquer VPS Linux moderno, usado para supervisão do backend e para o timer de limpeza de
output). Nenhuma dependência de aplicação nova.

**Storage**: Inalterado do ponto de vista de dados — IndexedDB no navegador continua a única
biblioteca persistente do usuário (Local-First Ownership). `output/` na raiz do repositório
(filesystem local do VPS — `OUTPUT_DIR` real; **não** `backend/output/`, que é apenas uma
fixture residual não relacionada) passa a ter uma política de retenção explícita de 24h via
timer systemd (`research.md`, Decisão 5; `data-model.md`, Output Retention Policy), em vez de
acumular sem limite como hoje. Nenhum banco de dados é introduzido.

**Testing**: Nenhum teste automatizado novo — esta fase não altera código de aplicação
(Constitution Check, Princípio IV). A validação é o roteiro manual em `quickstart.md`,
executado contra o VPS publicado: acesso público HTTPS, geração de áudio fim-a-fim, endpoint de
health (liveness — `data-model.md`, Health Endpoint Semantics), validade pontual do certificado,
reinício automático do backend (incluindo o limite de crash loop, `data-model.md` Backend
Service Unit), execução do timer de limpeza sobre `output/` na raiz do repositório, verificação
de que logs de produção não contêm texto completo do usuário (FR-012), verificação de hardening
de SSH/firewall (FR-011), e um ensaio completo de rollback que inclui o backend (checkout +
`uv sync --frozen` + restart + validação de `/health`/API), não só o frontend. SC-002 (7 dias de
health) e a cláusula de ciclo de renovação de SC-005 exigem janelas de observação maiores que o
tempo desta implementação — são tratados como acompanhamento operacional pós-deploy, documentado
e iniciado nesta fase, mas não como gate de conclusão (`data-model.md`, Validação de Longo
Prazo).

**Target Platform**: VPS Linux único (Ubuntu LTS recomendado — Assumption do spec; provedor
ainda não escolhido). Sem balanceamento de carga nem múltiplas instâncias.

**Project Type**: Aplicação web já existente (frontend + backend). Esta fase adiciona apenas
tooling operacional (`deploy/`); nenhum workspace de aplicação novo.

**Performance Goals**: Nenhuma meta de latência nova. A geração de áudio (Piper/FFmpeg) é
limitada por CPU e deve se comportar de forma equivalente ao ambiente local em um VPS com CPU
suficiente — o dimensionamento exato do VPS é uma decisão operacional fora desta fase (ver
Edge Cases do spec sobre múltiplas gerações simultâneas).

**Constraints**: Mesma origem obrigatória para frontend e backend, sem CORS entre eles
(Clarification de FR-007); backend vinculado apenas a `127.0.0.1` (FR-011, Decisão 7); rollback
manual, porém documentado — sem automação nesta fase (Clarification de FR-010); nenhuma
infraestrutura de fila/cache/banco de dados introduzida (Princípio III da constituição); limpeza
de `output/` não pode depender de mudança no código do pipeline (decisão do usuário durante o
planejamento).

**Scale/Scope**: Mesma aplicação de usuário único por sessão de navegador das fases anteriores,
agora alcançável publicamente; nenhuma mudança de modelo de uso (ainda não é multiusuário com
contas, autenticação ou particionamento de dados no servidor).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Resultado | Justificativa |
|---|---|---|
| I. Spec-Driven Development | PASS | `spec.md` aprovado, com a sessão de Clarifications (FR-007, FR-010) resolvida antes deste plano |
| II. Local-First Ownership | PASS | Nenhuma persistência nova no servidor; a retenção de `OUTPUT_DIR` (real: `output/` na raiz do repositório, corrigido em 2026-10-04 — era documentado por erro como `backend/output/`) passa a ter um limite explícito (timer de 24h) em vez de acúmulo indefinido, reforçando o princípio em vez de o violar (`research.md`, Decisão 5) |
| III. Simple and Modular Backend | PASS | Stack do backend inalterada (Python/FastAPI/Piper/FFmpeg); nenhuma fila, Redis ou Celery introduzida; Caddy e systemd são infraestrutura operacional de borda/supervisão, não componentes do pipeline |
| IV. Mandatory Tests | N/A (PASS) | Nenhuma mudança de código de aplicação; a verificação desta fase é o roteiro manual de `quickstart.md` |
| V. Incremental Pipeline Compatibility | N/A (PASS) | O pipeline `normalization -> chunking -> TTS -> WAV -> concatenation -> MP3` não é tocado |
| VI. Security by Default | PASS | HTTPS obrigatório com redirecionamento automático (FR-003); backend vinculado só a `127.0.0.1`, nunca exposto diretamente (FR-011); SSH apenas por chave, usuário de deploy sem root, firewall restrito a 22/80/443 (`research.md`, Decisão 7) — agora com tasks de **verificação** explícita (não só configuração) em `tasks.md`; nenhuma mudança de logging — a garantia de não logar texto completo (FR-012) permanece inalterada e passa a ter uma task de auditoria pontual pós-deploy, cobrindo também o access log do Caddy |
| VII. No Overengineering | PASS | Caddy escolhido por automatizar HTTPS nativamente, uma peça móvel a menos que Nginx+certbot; systemd (já presente no VPS) reaproveitado em vez de Supervisor/PM2/Docker; rollback documentado manualmente em vez de um pipeline de CI/CD completo, consistente com a Clarification de FR-010 |
| VIII. Phase-Bounded Delivery | PASS | Escopo restrito a tornar a aplicação já existente publicamente acessível; nenhuma feature de produto nova; monitoramento formal e CI/CD automatizado explicitamente fora do escopo (Assumptions do spec) |
| IX. Architecture Ready for Evolution | PASS | Toda a configuração de proxy/systemd/retenção fica isolada em `deploy/`, substituível (ex.: troca de Caddy por outro proxy, ou de systemd timer por outro agendador) sem tocar código da aplicação |
| X. Explicit Technical Decisions | PASS | Oito decisões registradas em `research.md`: proxy/TLS, roteamento same-origin, supervisão do backend via systemd + `uv`, build/serving estático do frontend, retenção de `OUTPUT_DIR`, provisionamento do modelo de voz Piper, hardening de SSH/firewall, e processo de deploy/rollback |

Nenhuma violação. `Complexity Tracking` não é necessário.

## Project Structure

### Documentation (this feature)

```text
specs/007-deploy-vps/
├── spec.md               # Spec aprovada, com Clarifications resolvidas
├── plan.md                # Este arquivo
├── research.md            # Fase 0: oito decisões técnicas
├── data-model.md          # Fase 1: tabela de roteamento, unit systemd, política de retenção, estado de deploy/rollback
├── quickstart.md           # Fase 1: roteiro de validação manual contra o VPS publicado
└── tasks.md                # Será criado por /speckit.tasks
```

Sem pasta `contracts/`: esta fase não introduz nenhuma interface nova entre serviços — o
Caddyfile e as units systemd são consumidos pelo próprio sistema operacional do VPS, não por
outro sistema; a API pública exposta sob `/api` é exatamente a mesma já existente, sem endpoint
novo além de `/health` (que já existe hoje). As formas exatas de cada arquivo de configuração
estão documentadas em `data-model.md`.

### Source Code (repository root)

```text
backend/                               # Inalterado — nenhum código de aplicação tocado
frontend/                              # Inalterado no código; apenas o build de produção
                                        # (`npm run build` → dist/) passa a ser publicado

deploy/                                # NOVO — toda a configuração operacional desta fase
├── Caddyfile                          # NOVO — roteamento same-origin: /api/*, /health ->
                                        # 127.0.0.1:8000; demais caminhos -> file_server servindo
                                        # frontend/dist/; HTTPS automático e redirect HTTP->HTTPS
                                        # nativos do Caddy (research.md, Decisões 1 e 2)
├── hss-backend.service                # NOVO — unit systemd: uv run uvicorn app.main:app --host
                                        # 127.0.0.1 --port 8000, usuário de serviço sem root,
                                        # Restart=on-failure (research.md, Decisão 3)
├── output-cleanup.service             # NOVO — unit systemd oneshot: remove output/* (raiz do
                                        # repositório, NÃO backend/output/) com mtime > 24h
                                        # (research.md, Decisão 5)
├── output-cleanup.timer               # NOVO — dispara output-cleanup.service diariamente
└── README.md                          # NOVO — runbook: setup inicial do VPS (SSH, firewall,
                                        # Caddy, units systemd), publicar uma nova versão, e
                                        # rollback (research.md, Decisão 8)
```

**Structure Decision**: Toda a configuração operacional desta fase fica isolada em um diretório
novo no nível do repositório, `deploy/`, paralelo a `backend/`, `frontend/` e `specs/` — nenhum
arquivo dentro de `backend/` ou `frontend/` é modificado. Isso mantém o princípio de
substituibilidade (Princípio IX): o Caddyfile ou as units systemd podem ser trocados por outra
ferramenta de borda/supervisão sem qualquer alteração no código de aplicação. `deploy/README.md`
concentra o runbook operacional (setup, deploy, rollback) para que ele continue acessível e
mantido junto da configuração que descreve, em vez de arquivado dentro de `specs/` depois que
esta fase for concluída.

## Complexity Tracking

> Não aplicável — nenhuma violação do Constitution Check acima.
