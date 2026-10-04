Atalho circular de humor com ícone de traço e rótulo, para escolher o que ouvir de acordo com o momento.

## O que o consumidor fornece

Um grupo de `button.hss-mood` com `aria-pressed="true|false"`, cada um com `span.hss-mood-disc` contendo um SVG de traço (24x24, sem preenchimento) e o rótulo logo depois. Envolva em `div.hss-mood-row` com `role="group"` e um `aria-label`.

## Quando usar

Linha de atalhos na Home ("Ouvir de acordo como se sente"), com cinco a oito humores de uma palavra: `Feliz`, `Exercício`, `Chill`, `Noite`, `Amor`.

## Regras

- Disco de 96px em `bg-raised`, ícone em `accent-text` com traço de 1.5px; hover para `bg-hover`.
- Selecionado: disco `accent` e ícone `on-accent`. Só um humor selecionado por vez.
- Ícones sempre de traço e redondos nas pontas; nunca preenchidos nem com emoji.
- Rótulo em `body-sm` `text-primary`, centralizado, uma palavra.
