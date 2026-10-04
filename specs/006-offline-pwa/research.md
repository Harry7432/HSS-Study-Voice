# Phase 0 Research: Offline e PWA consolidado

## Decisão 1 — `vite-plugin-pwa` (Workbox `generateSW`) para o App Shell Cache

**Decision**: Usar `vite-plugin-pwa` como única dependência nova (dev), configurado com a
estratégia `generateSW` e `registerType: 'prompt'`, para gerar o service worker e o manifesto de
precache do app shell a partir da própria saída do `vite build`.

**Rationale**: o manifesto de precache precisa listar exatamente os arquivos com hash gerados em
cada build (FR-002: "atualizando essa cópia automaticamente quando uma nova versão é publicada e
detectada"). `vite-plugin-pwa`/Workbox já resolve isso lendo o manifest real do build, revalida por
hash de conteúdo e trata corretamente ciclo de vida de `install`/`activate`/`skipWaiting`. É uma
biblioteca madura e amplamente testada para exatamente este problema, consistente com o Princípio
IX (componente de infraestrutura substituível, isolado em `vite.config.ts`).

**Alternatives considered**:
- Service worker escrito à mão com `cache.addAll([...caminhos fixos...])` — rejeitado: a lista de
  arquivos teria que ser mantida manualmente sincronizada com os nomes com hash que o Vite gera a
  cada build, o que é frágil e viola a própria FR-002. Reimplementar invalidação de cache,
  deduplicação entre abas e fallback de quota é reinventar o que o Workbox já resolve (Princípio
  VII — No Overengineering).
- `injectManifest` (service worker próprio que só injeta a lista de precache do Workbox) —
  rejeitado por não ser necessário: esta fase não precisa de lógica de runtime além de precache do
  shell e cache dos dois domínios de fonte (Decisão 2); `generateSW` cobre isso com configuração
  declarativa, sem código de service worker próprio para manter.

## Decisão 2 — `runtimeCaching` (CacheFirst) apenas para os dois domínios de fonte já carregados

**Decision**: Configurar `runtimeCaching` no Workbox só para `fonts.googleapis.com` (a folha de
estilo) e `fonts.gstatic.com` (os arquivos de fonte), estratégia `CacheFirst`. Nenhum outro domínio,
e explicitamente **nenhum** runtime caching para `/api/*`.

**Rationale**: `index.html` já carrega essas duas origens hoje (`frontend/index.html`); sem
cacheá-las, a primeira renderização offline ficaria sem a tipografia correta mesmo com o app shell
funcionando, por causa de uma requisição cross-origin que vai falhar. Cachear essas duas origens
públicas e estáticas não introduz nenhum dado do usuário nem contraria FR-009 (API, IndexedDB e
timeline continuam fora do precache). Excluir `/api/*` é deliberado: FR-005 e a Scope Boundary
("fila de criação de estudos offline... fora do escopo") exigem que uma chamada de criação de
estudo offline continue falhando de forma natural (ou, preferencialmente, nem ser tentada — Decisão
4) em vez de responder com uma resposta cacheada desatualizada.

**Alternatives considered**:
- Hospedar as fontes localmente (`frontend/public/fonts/`) em vez de cacheá-las via Workbox —
  tecnicamente mais simples a longo prazo, mas exige mudar o pipeline de build/assets além do
  escopo desta fase; a Scope Boundary não pede isso, e a mudança de runtime caching é estritamente
  menor. Rejeitada por ir além do necessário agora.
- Não cachear fontes — aceitável tecnicamente (o navegador cai para uma fonte do sistema sem
  travar), mas entrega uma experiência offline degradada sem necessidade, quando a opção declarativa
  já resolve. Rejeitada.

## Decisão 3 — Conectividade via `navigator.onLine` + eventos `online`/`offline`, sem sondagem ativa

**Decision**: Um módulo isolado (`frontend/src/platform/connectivity.ts`) expõe o estado atual
(`navigator.onLine`) e permite inscrição nos eventos nativos `online`/`offline` da `window`. Nenhuma
chamada de rede própria (ping/heartbeat) é adicionada para verificar conectividade real.

**Rationale**: é a API padrão da plataforma para exatamente este sinal, suficiente para todos os
cenários e edge cases descritos no spec (nenhum deles exige distinguir "interface de rede ativa mas
sem internet real" de "sem rede"). Adicionar uma sondagem ativa exigiria um endpoint de
health-check, o que tocaria o backend — fora do escopo desta fase (FR-009) — e seria Princípio VII
(No Overengineering) sem necessidade comprovada pelo spec.

**Alternatives considered**:
- Sondagem periódica contra um endpoint próprio (`/api/health` ou similar) — rejeitada: exigiria
  mudança de backend/API fora do escopo e adicionaria tráfego de rede periódico sem requisito que
  justifique.
- Biblioteca de terceiros para detecção de conectividade — rejeitada: `navigator.onLine` e os
  eventos nativos já resolvem o requisito sem dependência nova.

**Limitação aceita**: `navigator.onLine` reflete a interface de rede do dispositivo, não
necessariamente alcance real à internet (ex.: Wi-Fi conectado a um roteador sem internet). O spec
não lista esse cenário como requisito; a limitação é consistente com a Assumption do spec sobre
navegadores modernos e fica registrada aqui para não ser reaberta como bug depois.

## Decisão 4 — Bloqueio de criação offline verificado antes da chamada de rede, não depois da falha

**Decision**: O handler de submit do formulário de criação de estudo (`frontend/src/main.ts`)
consulta o estado de conectividade (Decisão 3) **antes** de chamar `dependencies.createStudy`. Se
offline, a tentativa é interrompida imediatamente com uma mensagem clara reaproveitando o elemento
`role="status"` já existente; nenhum `fetch` chega a ser disparado.

**Rationale**: atende literalmente a FR-005 ("impedir a tentativa... em vez de tentar a chamada de
rede e expor um erro genérico"). Verificar antes, não só tratar o erro de rede depois, é a diferença
entre uma mensagem clara e um erro genérico de `fetch` — exatamente a distinção que a FR-005 faz.

**Alternatives considered**:
- Deixar a chamada de rede ser tentada e tratar a falha no `catch` existente — rejeitada
  explicitamente pela própria FR-005 ("em vez de tentar a chamada de rede e expor um erro
  genérico").

## Decisão 5 — Atualização do app shell via prompt explícito, nunca recarregamento forçado

**Decision**: `registerType: 'prompt'` (não `autoUpdate`). O módulo `virtual:pwa-register` expõe
`onNeedRefresh`/`onOfflineReady`; `onNeedRefresh` apenas habilita um aviso não bloqueante
(`frontend/src/ui/updateNotice.ts`) que o usuário aciona explicitamente para aplicar a atualização.
Nenhum timer nem recarregamento automático é adicionado.

**Rationale**: FR-007 exige que uma atualização publicada não interrompa uma reprodução em
andamento, e o edge case correspondente no spec reforça "só passa a valer em uma próxima abertura ou
mediante ação explícita do usuário". `registerType: 'prompt'` é literalmente o modo do
`vite-plugin-pwa` desenhado para esse requisito, sem código próprio de controle de ciclo de vida do
service worker.

**Alternatives considered**:
- `registerType: 'autoUpdate'` (o plugin recarrega sozinho quando percebe uma nova versão) —
  rejeitada diretamente por FR-007/edge case: recarregaria mesmo com áudio tocando.
- Recarregar automaticamente só quando nenhum áudio estiver tocando — rejeitada por adicionar
  estado e heurística própria (quando é "seguro" recarregar sozinho) sem necessidade, quando o
  modo `prompt` já delega essa decisão ao usuário de forma mais simples (Princípio VII).

## Decisão 6 — Indicador de conectividade e mensagem de bloqueio com sinal duplo (não só cor)

**Decision**: O indicador de conectividade (`frontend/src/ui/connectivityIndicator.ts`) combina um
texto (`"Online"`/`"Offline"`) com um glifo/ícone, dentro de um elemento com `role="status"` e
`aria-live="polite"`; a mudança de estado atualiza o texto, não só uma cor. A mensagem de bloqueio
de criação (Decisão 4) é texto no mesmo padrão de `role="status"` já usado por `main.ts`.

**Rationale**: FR-011 exige mais de um sinal visual (não só cor) e identificação por tecnologia
assistiva — mesmo padrão já estabelecido na Fase 7 para o destaque de frase (`research.md` da Fase
005, Decisão 3: nunca só cor). Reaproveitar `role="status"`/`aria-live` já usado no `status` de
`main.ts` evita inventar um segundo mecanismo de anúncio para leitores de tela.

**Alternatives considered**:
- Indicador só de cor (ponto verde/vermelho) — rejeitado diretamente por FR-011.

## Decisão 7 — Sem botão de instalação dentro do app

**Decision**: Esta fase não adiciona um botão "Instalar" customizado nem escuta
`beforeinstallprompt`. A instalabilidade depende só do manifesto (FR-003) e do service worker
ativo; o próprio navegador/SO oferece a ação de instalação.

**Rationale**: o teste de independência da User Story 2 descreve explicitamente "usa a ação de
instalação do próprio navegador/sistema operacional" — não um botão da aplicação. Evitar esse
código extra é menos superfície para manter e é consistente com o Princípio VII; em navegadores sem
suporte, não ter botão próprio também evita qualquer necessidade de tratamento de fallback para
FR-008 (não há botão que possa "oferecer instalação que não funcione").

**Alternatives considered**:
- Botão próprio de instalação via `beforeinstallprompt` — rejeitado como não necessário para
  cumprir a US2 como especificada; adiado para uma fase futura caso seja pedido explicitamente.

## Decisão 8 — Ícones do manifesto derivados dos tokens do Design System HSS Music

**Decision**: Os ícones (192×192, 512×512 "any" e 512×512 "maskable") usam o fundo
`--bg-canvas` (`#000000`) e o primeiro-plano `--accent` (`#19e3a1`) de
`frontend/src/hss/tokens.css`, sem introduzir nenhuma cor nova. A produção dos arquivos PNG em si é
trabalho de implementação (`tasks.md`), não desta fase de planejamento.

**Rationale**: atende FR-003 ("ícones e cores consistentes com o Design System HSS Music") sem
inventar uma paleta nova; os tamanhos escolhidos são o mínimo exigido pelos critérios de
instalabilidade do Chromium/Android (192/512) mais a variante `maskable` recomendada para adaptive
icons.

**Alternatives considered**: nenhuma — não há ícone/logo preexistente no repositório para
reaproveitar; os tokens do design system já são a fonte de verdade visual (Fase 6).

## Decisão 9 — Cenários e2e offline exigem build real (`vite build` + `vite preview`), não `vite dev`

**Decision**: Os novos cenários Playwright que dependem do service worker (recarregar offline,
reconhecer instalabilidade) rodam contra `vite build && vite preview`, não contra o servidor de
desenvolvimento (`vite dev`) usado hoje por `frontend/e2e/library.spec.ts`. O cenário de bloqueio de
criação offline (Decisão 4) não depende do service worker e pode continuar rodando contra o
servidor de desenvolvimento, como os testes e2e existentes.

**Rationale**: a estratégia `generateSW` do Workbox só gera o service worker real no build de
produção; `vite dev` não registra precache algum, então testar "recarregar offline" contra o
servidor de desenvolvimento não provaria nada sobre FR-001/FR-002. A divisão exata (novo projeto
Playwright vs. novo `webServer` vs. arquivo e2e separado) é decisão de `tasks.md`, não desta fase —
aqui fica registrada a restrição que qualquer divisão precisa respeitar.

**Alternatives considered**:
- `devOptions: { enabled: true }` do `vite-plugin-pwa` (ativa um service worker também em dev) —
  rejeitada como estratégia principal: valida o código do service worker mas não o comportamento
  real de build/precache que FR-002 exige; pode ser usada como apoio pontual durante
  desenvolvimento manual, não como substituto do cenário e2e contra build real.
