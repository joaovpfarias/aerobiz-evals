# Resultado do Eval — Aerobiz Supersonic (17/08/2026)

Status: EM ANDAMENTO — laguna-s-2.1-free rodando, nemotron-3-ultra-free ainda não iniciado.
Este arquivo é atualizado incrementalmente conforme cada run termina.

## Escolha dos modelos

`probe_models.py` rodado ao vivo em 17/08 (não reaproveitado de sessão anterior — os
modelos "-free" caem sem aviso, conforme já registrado em STATUS.md):

| Modelo | JSON | Resposta certa | Latência |
|---|---|---|---|
| laguna-s-2.1-free | 2/2 | 2/2 | 18s, 9s |
| longcat-2.0-free | 0/2 | — | **401 morto** |
| mimo-v2.5-free | 2/2 | 2/2 | 9s, 14s |
| deepseek-v4-flash-free | 2/2 | 2/2 | 4s, 3s |
| nemotron-3-ultra-free | 2/2 | 2/2 | 8s, 10s |
| ling-3.0-flash-free | 0/2 | — | **401 morto** |
| ling-3.0-tiny-free | 0/2 | — | **401 morto** |

Os três modelos `ling-*`/`longcat-*` do par originalmente planejado (`ling-3.0-tiny-free`
vs `deepseek-v4-flash-free`) estão fora do ar (401 Unauthorized) nesta data. `deepseek-v4-flash-free`
está no ar mas o header deste projeto já registra um risco conhecido ("deepseek-free estoura
reasoning sem emitir JSON") — evitado por precaução, não porque falhou aqui.

**Par escolhido: `laguna-s-2.1-free` (referência/base) vs `nemotron-3-ultra-free` (candidato "maior").**

**IMPORTANTE — o contraste de capacidade é NOMINAL, não medido.** A escolha se apoia na
convenção de nomes (`-s-` vs `-ultra`) e no fato de `laguna-s-2.1-free` já ser o modelo
padrão documentado (`DEFAULT_MODEL` em `opencode_client.py`, "titular: passou 2/2 no
bake-off"). No bake-off dos dois prompts-armadilha os DOIS scoraram 2/2 — não há evidência
independente de que um seja mais capaz que o outro. Qualquer diferença observada no jogo
pode refletir estilo de decisão, não capacidade bruta.

Smoke test (1 turno, fresh, mesmo savestate) confirmou efeito real no jogo para os dois
modelos antes de comprometer 15 turnos:

- laguna: 4 ações (negotiate_slots x4 em NA06/NA14/NA02/SA01), caixa 1.220.000K -> 1.218.180K.
- nemotron: 5 ações (negotiate_slots x4 em SA01/EU11/AF01/ME01 + open_route NA13->NA06),
  caixa 1.220.000K -> 1.201.760K, com débito de rota **exatamente** -16.200K (consistente
  com a rota calibrada em CALIBRATION.md).

## Placar

(preencher após os dois runs completos — caixa final, rotas abertas, regiões com hub,
`world.read_victory` se disponível)

## Trajetória

(preencher — decisões por turno, ações aceitas vs recusadas, evolução do caixa)

## Comparação

(preencher — saída de `compare.py`, conferindo que os runs foram creditados a
`model_respondeu` diferentes)

## O que este eval MEDE

- Qualidade de decisão dentro do espaço de ações alcançável a partir do savestate
  `eval_single_2000_lv5.state`: negociação de slots, abertura de rota, compra de aeronave,
  ajuste de tarifa/frequência, gestão de caixa — verificado por efeito real no jogo
  (débito de caixa, contagem de negociadores livres), não apenas por "o modelo respondeu
  com uma ação válida".

## O que este eval NÃO MEDE

- **A condição de vitória do jogo ("hub em toda região") é inalcançável a partir deste
  savestate.** STATUS.md (15/08) registra, com evidência, que mesmo comprando a aeronave
  de maior alcance do jogo (A340, 8870mi) a rota Washington->Bruxelas continua sendo
  recusada por alcance. A escala real entre continentes nunca foi caracterizada. Logo,
  "regiões saindo de N/A no placar" **não é um critério válido** para este savestate — se
  nenhum dos dois modelos abrir rota intercontinental, isso não distingue os modelos, é
  uma restrição estrutural do estado inicial.
- Capacidade "real" dos modelos — o contraste é apenas nominal (ver acima).
- Confirmação da origem de toda rota: no smoke test do nemotron o harness reportou
  "banner de origem NAO catalogado (md5 39d79ee1)" para a rota NA13->NA06 — o débito de
  caixa bate com o valor de tabela, mas a origem exibida em tela não pôde ser confirmada
  contra o catálogo `ROUTE_ORIGIN_MD5`. Não foi adicionada nenhuma entrada nova ao
  catálogo nesta sessão (não foi medido, só observado).
- Qualquer coisa em Multiplayer — este run é single-player.
