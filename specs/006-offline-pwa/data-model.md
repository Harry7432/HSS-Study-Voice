# Phase 1 Data Model: Offline e PWA consolidado

Esta fase não introduz nem altera nenhum dado persistido — nenhum campo novo em IndexedDB
(`frontend/src/library/db.ts`, Fase 5), nenhuma mudança de contrato HTTP (Fase 4) e nenhuma mudança
no formato da timeline (Fase 3.1), conforme FR-009. As quatro entidades abaixo — já nomeadas em
"Key Entities" no `spec.md` — são estado de runtime do navegador (gerenciado pelo service worker
ou mantido em memória pela aplicação) ou um descritor estático consumido pelo navegador, nunca
linhas em um banco de dados da aplicação.

## App Shell Cache

Não é modelado como um tipo TypeScript da aplicação — é o Cache Storage do navegador, populado e
mantido inteiramente pelo service worker gerado pelo `vite-plugin-pwa`/Workbox (`research.md`,
Decisão 1). A aplicação não lê nem escreve esse cache diretamente.

| Campo (conceitual) | Origem |
|---|---|
| Lista de URLs precacheadas | Gerada a partir do manifest de build do Vite a cada `npm run build` |
| Versão ativa | Hash de conteúdo por entrada (Workbox); comparado na ativação do novo service worker |

**Transições**: `install` (novo service worker baixa e compara hashes) → `waiting` (nova versão
pronta, aguardando) → `activate` (só após ação do usuário — ver Update Availability abaixo, Decisão
5 do `research.md`) → versão anterior descartada.

## Web App Manifest

Descritor estático (`manifest.webmanifest`, gerado pelo plugin a partir da configuração em
`vite.config.ts`), não um tipo em tempo de execução da aplicação.

| Campo | Valor/origem |
|---|---|
| `name` | "HSS Study Voice" |
| `short_name` | "Study Voice" |
| `description` | Mesma frase de `<meta name="description">` já existente em `frontend/index.html` |
| `start_url` | `/` |
| `scope` | `/` |
| `display` | `standalone` (US2: "sem a barra de endereço e controles padrão") |
| `background_color` | `#000000` (token `--bg-canvas`, `frontend/src/hss/tokens.css`) |
| `theme_color` | `#000000` (já usado hoje em `<meta name="theme-color">`) |
| `icons` | 192×192 (`purpose: "any"`), 512×512 (`purpose: "any"`), 512×512 (`purpose: "maskable"`) — cores derivadas de `--bg-canvas`/`--accent` (`research.md`, Decisão 8) |

## Connectivity Status

Estado em memória, um único valor global para toda a aplicação, exposto por
`frontend/src/platform/connectivity.ts`. Nunca persistido.

| Campo | Tipo | Derivação |
|---|---|---|
| `online` | `boolean` | `navigator.onLine` na leitura inicial; atualizado pelos eventos `online`/`offline` da `window` |

**Transições**:

```text
online = navigator.onLine (leitura inicial no boot da aplicação)
        │
        ├─ evento "offline" ──► online = false ──► indicador atualiza (research.md, Decisão 6)
        │                                      ──► criação de estudo passa a ser bloqueada (Decisão 4)
        └─ evento "online"  ──► online = true  ──► indicador atualiza
                                               ──► criação de estudo volta a ficar disponível
```

**Consumidores**: `frontend/src/ui/connectivityIndicator.ts` (exibição) e o handler de submit em
`frontend/src/main.ts` (guarda de FR-005) — ambos leem o mesmo valor, nenhum mantém cópia própria
divergente.

## Update Availability

Estado em memória derivado dos callbacks do módulo virtual `virtual:pwa-register`
(`vite-plugin-pwa`), mantido por `frontend/src/ui/updateNotice.ts`. Nunca persistido.

| Campo | Tipo | Derivação |
|---|---|---|
| `state` | `"idle" \| "available" \| "applying"` | `"idle"` até `onNeedRefresh` disparar → `"available"`; ação explícita do usuário → `"applying"` (chama `updateSW(true)`, que recarrega a aba) |

**Transições**:

```text
idle ──► onNeedRefresh() ──► available ──► usuário aciona o aviso ──► applying ──► updateSW(true)
 ▲                                                                                      │
 └──────────────────────────── nova aba/sessão já carrega a versão nova ◄──────────────┘
```

Enquanto `state !== "applying"`, nenhuma reprodução em andamento é afetada (FR-007) — a transição
para `applying` só ocorre por ação explícita do usuário, nunca automaticamente.
