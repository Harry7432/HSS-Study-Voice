HSS Music é um design system escuro-primeiro para players e catálogos de música. A estrutura vem da análise do player web aberto: painéis planos em camadas, controles em pílula, capas quadradas com cantos suaves, uma cor de destaque usada com economia. A identidade é própria: acento Pulse (verde-menta frio), fonte Figtree e tokens nomeados pelo papel, não pela cor. Nenhuma marca, logo ou fonte do site analisado é usada.

## Fundamentos de conteúdo

O texto fala direto com a pessoa, em português do Brasil, no tom de quem ajuda sem enfeitar. Use "você" e "sua" (`Sua Biblioteca`), verbos no imperativo nas chamadas (`Busque, navegue e escute seus artistas favoritos`) e uma única ação por botão (`Buscar`, `Criar`, `Instalar aplicativo`).

- Escreva em caixa de frase: só a primeira palavra e nomes próprios em maiúscula. Nunca TUDO MAIÚSCULO em títulos ou botões.
- Títulos de prateleira dizem por que o conteúdo está ali: `Como começar`, `Recomendado para hoje`, `Inspirado na sua atividade recente`.
- Metadado de item usa tipo, ponto médio e dono: `Playlist • Harry Sousa`, `Artista`. Nunca emoji; nunca ponto de exclamação.
- Estado vazio explica o que aparecerá e como começar: `Você está em dia. Fique de olho neste espaço para saber das novidades.`
- Erro diz o que houve e o que fazer: `Não foi possível tocar esta faixa. Verifique sua conexão e tente de novo.`

## Fundamentos visuais

**Superfícies.** O app é uma pilha de planos chapados, sem borda e sem sombra. `bg-canvas` fica atrás de tudo e aparece como fresta de `space-2` entre painéis. Os painéis (`bg-panel`, `radius-lg`) carregam o conteúdo. Sobre eles, `bg-raised` marca campos, chips e cartões, e `bg-hover` marca o estado hover. Sombra só existe em coisas que flutuam: menus e popovers usam `bg-overlay` com `shadow-menu`; o botão Reproduzir usa `shadow-play`.

**Cor.** O tema `dark` é o original. O tema `light` é editorial: `bg-canvas` e `bg-panel` são brancos e os painéis se separam por linhas `border-subtle` (classe `hss-panel`), sem camadas de cinza e sem raio de painel; os cinzas levam um leve tom de menta. Texto em três níveis: `text-primary` para o que se lê primeiro, `text-secondary` para apoio, `text-muted` para duração e legendas. O acento `accent` aparece em no máximo um ponto por tela: o botão Reproduzir ou a ação primária. Texto sobre o acento é sempre `on-accent`, nunca branco. Acento como texto ou ícone usa `accent-text`, que escurece no tema claro para passar de 4.5:1. As quatro cores `cover-*` existem só para arte de capa de exemplo e cartões de destaque.

**Tipografia.** Use apenas a família `sans` (Figtree) em pesos 400, 700 e 800, e `mono` (DM Mono) para duração e posição, com números tabulares. Título de prateleira é `title`; nome de faixa e de cartão é `subtitle`; artista e descrição são `body-sm` em `text-secondary`; botões e chips usam `label`. Chamadas de cartão de destaque usam `headline`; páginas de artista usam `display`. Hierarquia por peso e cor, não por tamanho: o corpo fica em 14 e 16px.

**Forma.** Tudo que se clica sozinho é pílula (`radius-pill`): botões, chips, busca. Capas de álbum e playlist são quadradas com `radius-md`; artistas são círculos (`radius-circle`); miniaturas pequenas e itens de menu usam `radius-sm`. Painéis usam `radius-lg`. Capa nunca recebe borda nem sombra.

**Espaçamento.** Escala de 4px. O gutter de conteúdo é `space-4`; cartões têm `space-3` de padding; painéis ficam a `space-2` um do outro. Controles seguem `size-control-sm` (32px) para chips e botões compactos, `size-control-md` (48px) para busca e botões de ícone, `size-control-lg` (56px) para o Reproduzir sobre a capa.

**Estados e movimento.** Hover clareia a superfície para `bg-hover`; botões crescem 4% e voltam ao pressionar. O botão Reproduzir sobe 8px e aparece em 250ms ao passar o mouse sobre a capa. Foco é um anel sólido de 2px `focus-ring`, nunca removido. Quem pede movimento reduzido não recebe escala nem deslocamento.

**Sem gradiente.** A identidade é chapada. O único degradê permitido é o véu de uma cor `cover-*` que se dissolve em `bg-panel` no topo de uma página de detalhe, nunca em botões, cartões ou texto.

## Iconografia

Este sistema não traz arquivos de ícone nem logotipo. O nome "HSS Music" é composto em `headline` com peso 800 até que exista uma marca própria. Use glifos de 16px (inline) e 24px (navegação e player), sólidos para o estado ativo e de contorno para o inativo, sempre em `currentColor` herdando `text-secondary` ou `text-primary`. Nunca use emoji como ícone. Os previews desenham glifos simples em SVG apenas para demonstrar tamanho e cor; troque pelo seu conjunto de ícones.

## Componentes

Use as classes de `bundle.css` (prefixo `hss-`) sobre uma superfície `hss-surface`.

- **Button** (`hss-btn`): `primary` para a única ação principal da tela, `inverse` para um destaque secundário forte, `secondary` e `tertiary` para o resto.
- **Chip** (`hss-chip`): filtro de uma escolha por vez; o selecionado inverte as cores.
- **SearchField** (`hss-search`): busca em pílula com ícone à esquerda.
- **MediaCard** (`hss-card`): capa, título e descrição, com Reproduzir em hover.
- **TrackRow** (`hss-row`): faixa em lista; a que toca usa `accent-text`.
- **LibraryItem** (`hss-libitem`): item da biblioteca lateral.
- **PlayerBar** (`hss-player`): barra de player em `bg-canvas`.
- **Menu** (`hss-menu`): menu de contexto em `bg-overlay`.
- **MoodShortcut** (`hss-mood`): atalho circular de humor com ícone de traço.
- **Shelf** (`hss-shelf-*`): título de prateleira, "Mostrar tudo" e grade de cartões.

## Regras

- Um acento por tela. Se há dois botões `primary`, um deles deveria ser `secondary`.
- Nunca troque `text-primary` por cor fixa; todo texto usa um dos três níveis.
- Status (`danger`, `warning`, `info`) sempre vem com palavra ou ícone, nunca só com cor.
- Texto `text-disabled` só em controle desabilitado.
