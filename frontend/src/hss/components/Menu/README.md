Menu de contexto sobre `bg-overlay` com sombra, usado para conta e ações de item.

## O que o consumidor fornece

Um `div.hss-menu` com `role="menu"` e botões `hss-menu-item`. Use `hss-menu-sep` para separar grupos e `is-danger` para a ação destrutiva. Posicionamento e abertura ficam com o consumidor.

## Quando usar

Menu da conta no topo, menu de três pontos em faixa e playlist.

## Regras

- Padding `space-1`, `radius-sm`, `shadow-menu`; itens com 40px de altura e hover `bg-hover`.
- Texto `body-sm` em `text-primary`; destrutivo em `danger` e sempre separado.
- Abra em foco no primeiro item; Esc fecha. Itens que saem do app mostram um ícone à direita.
- Rótulos de uma a quatro palavras, sem ponto final.
