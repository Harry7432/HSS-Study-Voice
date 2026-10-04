Item da biblioteca lateral com miniatura de 48px, nome e tipo.

## O que o consumidor fornece

Um `div.hss-libitem` com `hss-libitem-thumb` (imagem, cor `cover-*` ou glifo), `hss-libitem-title` e `hss-libitem-sub`. O item aberto recebe `aria-current="true"`. Artistas usam `is-artist` para a miniatura ficar redonda.

## Quando usar

Lista de playlists, artistas e álbuns salvos no painel de biblioteca.

## Regras

- Padding `space-2`, hover `bg-raised`, atual `bg-hover` com título em `accent-text`.
- Subtítulo no formato `Tipo • Dono`, em `body-sm` `text-secondary`.
- Miniatura quadrada com `radius-sm`; artista com `radius-circle`.
- Nomes longos terminam em reticências; nunca quebram a linha.
