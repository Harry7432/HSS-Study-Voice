# Quickstart: Player com texto sincronizado

Guia de validação ponta a ponta para `specs/005-synced-text-player`. Não contém código de
implementação — veja `data-model.md` e `research.md` para as decisões técnicas, e `tasks.md` (gerado
por `/speckit.tasks`) para a divisão do trabalho.

## Pré-requisitos

- `cd frontend && npm install` (workspace já inicializado nas fases anteriores).
- Nenhum serviço de backend é necessário para os testes automatizados (unitários e a maior parte dos
  cenários manuais usam dados já gerados/salvos localmente).
- Para o cenário e2e novo (Playwright) e para gerar um estudo do zero durante a validação manual, o
  backend local deve estar rodando, como já exigido por `frontend/e2e/library.spec.ts`.

## Verificação automatizada

```bash
cd frontend
npm run build        # tsc --noEmit && vite build
npm test              # vitest run — inclui sentenceLookup.test.ts e readingView.test.ts novos
npm run test:e2e      # playwright test — inclui o novo cenário de texto sincronizado
```

Critério de aprovação: as três etapas terminam sem erro, com os testes novos e todos os já
existentes (incluindo `player.test.ts` e `main.test.ts`) passando.

## Cenários manuais

Cada cenário referencia a história de usuário e os critérios de sucesso correspondentes no
`spec.md`.

> **Resultado da validação (T017)**: `npm run build`, `npm test` (107 testes) e `npm run test:e2e`
> (5 testes, Chromium real + backend real com Piper TTS) passaram sem falhas — ver seção
> "Verificação automatizada" acima. Para os cenários §1–§7 abaixo, cada um tem cobertura
> automatizada equivalente citada inline (unitária em `readingView.test.ts`/jsdom ou e2e em
> `library.spec.ts`/navegador real). A tentativa de também dirigir o app real via automação de
> navegador, dentro da sessão que implementou a feature, não foi possível: o navegador controlado
> pela extensão Claude in Chrome não conseguiu alcançar o dev server local
> (`http://127.0.0.1:5173`) rodando no ambiente onde aquele agente executava comandos — isolamento
> de rede entre os dois, não uma falha da aplicação. A parte verdadeiramente manual/perceptual —
> ouvir o áudio e confirmar que a frase destacada corresponde à fala real (segunda metade de
> SC-001), além dos cenários §1–§6 de ponta a ponta — foi executada e confirmada pelo usuário
> rodando a aplicação real localmente, em sessão separada: destaque acompanha a fala corretamente,
> sem atraso perceptível relevante, clique navega para o trecho correto, retomada destaca a frase
> certa, e a última frase permanece destacada ao final do áudio. **T017 concluída.**

### Resultado por cenário

| § | Cenário | Cobertura automatizada | Validação manual humana |
|---|---|---|---|
| 1 | Destaque acompanha reprodução real | `readingView.test.ts` (timeupdate → destaque único); `library.spec.ts` "SC-001, componente de latência" (navegador real, Piper TTS, <300ms, 5/5 passou) | Confirmado pelo usuário: destaque acompanha a frase falada corretamente, sem atraso perceptível relevante |
| 2 | Auto-scroll + suspensão por rolagem manual | `readingView.test.ts` "FR-005/FR-006" (scrollIntoView stubado, scroll manual suspende, seeked/play retoma) | Confirmado pelo usuário |
| 3 | Clique pula a reprodução | `readingView.test.ts` "FR-007/FR-008" + concorrência; `library.spec.ts` "SC-002" (navegador real — passou) | Confirmado pelo usuário: clique navega para o trecho correto |
| 4 | Retomar com o texto certo | `readingView.test.ts` "FR-009" (frase intermediária, completed, sem progresso) | Confirmado pelo usuário: retomada destaca a frase correta |
| 5 | Timeline corrompida | `readingView.test.ts` "FR-011" (timeline inválida → mensagem, sem exceção, sem bloquear eventos futuros) | Confirmado pelo usuário |
| 6 | Fim do áudio | `readingView.test.ts` "FR-010" (ended mantém última frase destacada) | Confirmado pelo usuário: última frase permanece destacada no fim |
| 7 | Leitura offline | `library.spec.ts` "FR-012/SC-006" (navegador real, `setOffline(true)`, zero requisições de rede — passou) | Confirmado pelo usuário |

### 1. Acompanhar o destaque durante a reprodução real (US1 · SC-001)

1. Gere um estudo novo com um texto de várias frases (ou reabra um estudo salvo existente).
2. Inicie a reprodução.
3. Observe o texto: confirme que exatamente uma frase está destacada a qualquer momento, que o
   destaque muda de frase continuamente acompanhando o áudio, e que nunca fica sem nenhuma frase
   destacada.

### 2. Rolagem automática e suspensão por rolagem manual (US1 · FR-005/FR-006)

1. Com o áudio tocando e a frase atual fora da área visível do texto, confirme que a visualização
   rola automaticamente até trazê-la para dentro da área visível.
2. Role manualmente o texto para outro trecho enquanto o áudio continua tocando.
3. Confirme que a rolagem automática não "briga" de volta enquanto você está lendo outro trecho.
4. Clique em qualquer frase (ou interaja com os controles de reprodução); confirme que o
   acompanhamento automático volta a funcionar a partir daí.

### 3. Clicar no texto para pular a reprodução (US2 · SC-002)

1. Com o áudio tocando, clique numa frase diferente da atual, no meio do texto.
2. Confirme que a reprodução salta imediatamente para o início exato dessa frase e continua tocando,
   com o destaque já atualizado.
3. Pause o áudio e repita o clique em outra frase.
4. Confirme que a posição é atualizada e o destaque muda, mas o áudio permanece pausado (o clique não
   inicia nem para a reprodução).

### 4. Retomar um estudo com o texto certo (US3 · SC-004)

1. Abra um estudo, avance a reprodução até o meio, pause, e feche/saia da tela.
2. Reabra esse mesmo estudo pela biblioteca local.
3. Confirme que a frase correspondente à posição salva já aparece destacada e visível **antes** de
   iniciar a reprodução.
4. Repita com um estudo marcado como concluído — confirme que a última frase aparece destacada.
5. Repita com um estudo sem progresso salvo (recém-criado, nunca reproduzido) — confirme que a
   primeira frase aparece destacada.

### 5. Timeline ausente ou corrompida (edge case · SC-007)

1. Abra as DevTools do navegador → Application → IndexedDB → banco `hss-study-library` → object
   store de assets do estudo.
2. Edite manualmente o registro de timeline de um estudo salvo para torná-lo inválido (por exemplo,
   remova um campo obrigatório ou quebre a contiguidade de uma frase).
3. Reabra esse estudo pela biblioteca.
4. Confirme que o áudio ainda toca normalmente e que uma mensagem clara informa que o texto
   sincronizado não está disponível para aquele estudo — sem erro no console nem tela quebrada.

### 6. Fim do áudio (edge case · FR-010)

1. Deixe um estudo curto tocar até o fim.
2. Confirme que, após o áudio terminar, a última frase permanece destacada (não fica sem destaque).

### 7. Leitura offline (US1 · SC-006)

1. Com um estudo já salvo localmente, ative o modo offline do navegador (DevTools → Network →
   Offline).
2. Reabra esse estudo pela biblioteca.
3. Confirme que o texto completo aparece e a sincronização funciona normalmente, sem nenhum erro de
   rede.
