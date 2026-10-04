Prateleira com título, link "Mostrar tudo" e uma grade de cartões de mídia.

## O que o consumidor fornece

Uma `section` com `hss-shelf-head` (um `h2.hss-shelf-title` e `button.hss-shelf-more`) e `hss-shelf-grid` com `MediaCard`s. A grade preenche as colunas conforme a largura (mínimo 160px por cartão).

## Quando usar

Home, busca e páginas de detalhe, uma prateleira por critério de recomendação.

## Regras

- Título em `title` (24/32, peso 700), `text-primary`; link em `label` e `text-secondary`, que vai a `text-primary` em hover.
- O título diz o motivo da recomendação: `Recomendado para hoje`, `Feito para você`.
- Gap de `space-2` entre cartões e `space-5` entre prateleiras.
- Mostre uma linha de cartões; o excedente fica atrás de "Mostrar tudo".
