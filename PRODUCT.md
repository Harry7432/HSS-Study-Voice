# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

TypeScript estrito com Vite e DOM nativo, sem framework de UI. FastAPI permanece como backend separado; IndexedDB via `idb` é a fonte local da biblioteca.

## Users

Estudantes e educadores que transformam textos em estudos de áudio e precisam reencontrar, ouvir e retomar esse material no próprio navegador.

## Product Purpose

O HSS Study Voice gera áudio sincronizado a partir de texto e mantém a biblioteca resultante sob controle do usuário. Sucesso significa criar um estudo, reproduzi-lo imediatamente e continuar acessando a cópia local sem depender do backend.

## Positioning

A biblioteca pertence ao navegador do usuário: áudio, timeline, progresso e metadados permanecem locais, enquanto o servidor atua somente como processador temporário.

## Operating Context

Uso individual em navegador desktop moderno. O usuário cola texto, gera áudio, reconhece estudos por um rótulo curto e consulta uma biblioteca ordenada do mais recente para o mais antigo.

## Capabilities and Constraints

- Geração consome os três endpoints existentes da API por `/api/v1/...`.
- O frontend valida respostas em runtime antes de persistir.
- IndexedDB separa `studyMetadata` de `studyAssets` e salva ambos atomicamente.
- O texto original não é persistido como metadado; a timeline mantém frases normalizadas do contrato.
- Nenhum framework de UI, autenticação, sincronização, paginação ou histórico no backend nesta fase.

## Evidence on Hand

Especificação, plano, modelo de dados, contratos e quickstart em `specs/003-local-study-library/`. Não há identidade visual, logotipo, imagens comerciais ou depoimentos fornecidos.

## Product Principles

- Propriedade local antes de conveniência do servidor.
- Falhas da biblioteca nunca bloqueiam a reprodução recém-gerada.
- Dados externos são validados antes do uso.
- Operações centrais permanecem pequenas, explícitas e testáveis.
- A interface prioriza reconhecimento, leitura e continuidade da escuta.

## Accessibility & Inclusion

Controles utilizáveis por teclado, foco visível, contraste WCAG AA, estados e erros anunciados semanticamente e layout responsivo.
