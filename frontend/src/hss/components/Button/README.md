Botão em pílula com cinco variantes. Use `hss-btn-primary` para a única ação principal da tela e as demais variantes para o resto.

## O que o consumidor fornece

Um `<button>` (ou `<a>`) com a classe `hss-btn` e uma variante: `hss-btn-primary`, `hss-btn-inverse`, `hss-btn-secondary` ou `hss-btn-tertiary`. Use `hss-btn-sm` para altura de 32px. Ícones são SVG de 16px com a classe `hss-icon`, antes do rótulo. Botões só de ícone usam `hss-iconbtn` (48px redondo) e sempre precisam de `aria-label`.

## Quando usar

- `primary` (Pulse): uma por tela, como `Buscar` ou o Reproduzir (`hss-iconbtn-play`, 56px).
- `inverse` (`text-primary` sobre `bg-panel`): destaque forte que não é a ação principal, como `Ver planos`.
- `secondary` (contorno `border-strong`): ação alternativa ao lado de uma primária.
- `tertiary`: ação de baixo peso, como `Mostrar mais dicas`.

## Regras

- Rótulo em caixa de frase, verbo no imperativo, `label` (14px, peso 700).
- Texto sobre `accent` é `on-accent`, nunca branco.
- Hover cresce 4% e `primary` passa para `accent-hover`; desabilitado fica a 50% e perde o hover.
- Nunca dois `primary` lado a lado.
