Cartão de mídia com capa, título e descrição de até duas linhas; o botão Reproduzir sobe sobre a capa ao passar o mouse.

## O que o consumidor fornece

Um `<a class="hss-card">` com uma `div.hss-card-cover` (imagem ou cor `cover-*`), dentro dela um `div.hss-card-play` com `hss-iconbtn hss-iconbtn-play`, e depois `hss-card-title` e `hss-card-sub`. Artistas usam `hss-card-cover is-artist` para virar círculo.

## Quando usar

Dentro de uma prateleira (`hss-shelf-grid`) para álbuns, playlists, artistas e podcasts.

## Regras

- Padding `space-3`, hover `bg-raised`, capa quadrada com `radius-md`; artista é círculo.
- Título: `subtitle` em `text-primary`, uma linha com reticências. Descrição: `body-sm` em `text-secondary`, até duas linhas.
- Reproduzir aparece em hover e em foco dentro do cartão, e fica sempre acessível por teclado.
- Capa sem borda e sem sombra.
