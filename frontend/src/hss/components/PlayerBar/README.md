Barra de player fixa no rodapé, com faixa atual, controles, progresso e volume.

## O que o consumidor fornece

Um `div.hss-player` com três filhos: `hss-player-now` (capa 56px, título, artista, curtir), `hss-player-center` (`hss-player-controls` e `hss-player-scrub` com a `hss-bar` e os dois tempos) e `hss-player-right` (volume com `hss-bar`). A largura de `span` dentro de `hss-bar` é o valor em porcentagem.

## Quando usar

Uma barra por app, ancorada na base da janela.

## Regras

- Altura `size-player`, fundo `bg-canvas`; o Reproduzir/Pausar central é um disco `text-primary` com ícone `bg-panel`.
- Tempos em `time` e `text-muted`, com números tabulares.
- Trilho `progress-track`, preenchimento `text-primary`, `accent` em hover.
- Todo botão de ícone tem `aria-label`; a barra de progresso expõe `role="progressbar"` com valores.
