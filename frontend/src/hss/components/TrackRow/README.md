Linha de faixa em lista com índice, miniatura, título, artista, álbum e duração.

## O que o consumidor fornece

Um `div.hss-row` por faixa com `hss-row-index`, `hss-row-main` (miniatura 40px, título e artista), `hss-row-album` e `hss-row-time`. A faixa que está tocando recebe `is-playing` e troca o número pelo glifo de reprodução.

## Quando usar

Listas de playlist, álbum, resultados de busca e fila.

## Regras

- Altura 56px, `radius-sm`, hover `bg-hover`.
- Título em `subtitle`; artista e álbum em `body-sm` `text-secondary`; duração em `time` com números tabulares e `text-muted`.
- Faixa tocando: título e índice em `accent-text`. Cor nunca é o único sinal; o glifo de play também aparece.
- Em telas estreitas, esconda a coluna do álbum e mantenha título e duração.
