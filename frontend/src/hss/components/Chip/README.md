Chip em pílula para filtrar um conjunto de conteúdo, com uma escolha selecionada por vez.

## O que o consumidor fornece

Um grupo de `<button class="hss-chip" aria-pressed="true|false">`. O consumidor controla qual está selecionado e atualiza `aria-pressed`; o estilo selecionado vem do atributo.

## Quando usar

Filtros no topo de uma lista ou página (`Tudo`, `Música`, `Podcasts`). Mantenha de dois a seis chips; um deles ("Tudo") começa selecionado.

## Regras

- Altura `size-control-sm`, fundo `bg-raised`, texto `label` em `text-primary`.
- Selecionado: fundo `text-primary` e texto `bg-panel`. Nunca use o acento para chip selecionado.
- Rótulos de uma palavra, em caixa de frase.
