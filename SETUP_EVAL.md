# Configuração Oficial do Eval (definida em 11/08/2026)

**Objetivo:** evals via OpenCode Go usando Aerobiz Supersonic, em **single player e multiplayer**, comparando um modelo fraco contra um forte, com **adversários na dificuldade máxima** no **cenário dos anos 2000**.

## Parâmetros da partida

| Item | Valor | Confirmado na tela |
|---|---|---|
| Cenário | **4 — Supersonic Travel (2000-2020)** | ✅ |
| Dificuldade | **Nível 5 — Supersonic (máxima)** | ✅ |
| Companhia do agente | **Federal (MAN)** — base **Washington** | ✅ |
| Rivais (COM) | MetLink/New York, AirRoma/Roma, Aussie/Sydney | ✅ |
| Caixa inicial | **$1.220.000K** (lido da RAM) | ✅ |
| Meta (lida na tela Info->victory) | hub em TODA região + #1 em passageiros no ano na América do Norte + **#1 em passageiros em TODAS as 7 regiões** + lucro no ano | ✅ |

> ⚠️ **No nível 5 a exigência é #1 em TODAS as regiões**, não em 6 como no nível 3. A tela traz o rótulo `SUPERSONIC 2000-2020` e as 7 regiões (Europa, África, Oriente Médio, Sudeste Asiático, Oceania, América do Norte, América do Sul), cada uma com um status — `N/A` no turno 1.
>
> **Essa tela é o placar do eval**: o status por região é a métrica de sub-objetivo, lida direto do motor do jogo. Caminho: `Info` (ícone r1c3) → 6º item. Captura de referência: `logs/run_f0/placar_t1.png`.
>
> ⚠️ **O savestate precisa estar DEPOIS das falas de introdução.** Salvo antes, toda run começa presa nos diálogos e o `back_to_menu` (que usa B) não os dispensa — só A dispensa. Já corrigido em `eval_single_2000_lv5.state`.

## Savestates

| Arquivo | Ponto |
|---|---|
| `states/eval_single_2000_lv5.state` | **partida single player pronta**, turno 1 |
| `states/eval_players_screen.state` | tela "How many people will play?" — **ponto de ramificação para o multiplayer** (descer N−1 e confirmar seleciona N jogadores) |

## Como reproduzir o setup

`harness/setup_game.py` automatiza cenário/nível/jogadores. Sequência verificada:

```
boot: advance 600 + Start×10 com advance(180) entre eles   → tela de título
A → lista de cenários → Down×3 → cenário 4 → A → A (confirma resumo)
Down×4 → nível 5 (Supersonic) → A
tela de jogadores: 1 = direto A | N = Down×(N−1) + A
região: Right até "N America" (o ponto inicial varia — verificar o rótulo) → A
cidade: posicionar cursor VISUAL (locate.goto) em Washington+(4,4) → A×3
resumo das companhias → Down×2 → A (Exit) → A (confirma início)
```

⚠️ **Na tela de escolha da base o cursor NÃO usa `0x257F`/`0x2581`** (esses valem para o mapa em jogo). Ali é preciso usar o posicionamento visual `locate.goto`. Levou 3 tentativas até acertar — registrado para não repetir.

## Multiplayer (pendente)

O jogo suporta 4 companhias controladas. Para a arena multi-LLM: carregar `eval_players_screen.state`, selecionar 4 jogadores, e repetir região/cidade para cada jogador. O harness precisará rotear cada fase para o modelo dono daquela companhia, com diário isolado por modelo.

## Modelos — par escolhido (medido em 11/08/2026, sem fallback)

⚠️ **A chave do OpenCode Go só libera os modelos `-free`.** Todos os pagos testados devolvem **401**: `claude-sonnet-5`, `claude-haiku-4-5`, `gpt-5.5`, `gemini-3.5-flash-lite`. O contraste fraco vs forte precisa sair da faixa free.

🐞 **Bug de medição corrigido:** o probe rodava com a cadeia de fallback ligada, então quando um modelo dava 401 a resposta de OUTRO modelo era creditada a ele — o ranking anterior era ficção. Probes agora usam `fallbacks=False`. **O eval também precisa registrar qual modelo de fato respondeu em cada turno**, senão a comparação é inválida.

| Papel | Modelo | Medição (2 prompts de decisão econômica) |
|---|---|---|
| **Fraco** | `ling-3.0-tiny-free` | **1/2** — devolveu resposta vazia em um dos casos |
| **Forte** | `deepseek-v4-flash-free` | **2/2**, ~2s (reasoning model) |
| Reserva | `nemotron-3-ultra-free` | 2/2, ~12s |

## Notas anteriores sobre modelos

O objetivo pede um modelo **fraco** e um **forte**. Health check de 11/08 nos free: `laguna-s-2.1-free`, `longcat-2.0-free`, `mimo-v2.5-free` e `deepseek-v4-flash-free` respondem; os dois `ling` estavam 503 e `north-mini-code-free` dá 401. A assinatura Go também expõe modelos maiores (claude/gpt/gemini) — escolher o par por contraste real de capacidade.
