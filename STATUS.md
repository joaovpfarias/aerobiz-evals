## 18/08 (sessão adicional 2) — ETAPA 12-HubsCompleto: `close_hub` calibrado, entra em `pilot.SUPPORTED`

Retomada da ETAPA 6-Reversos (que tinha deixado `close_hub` "IMPLEMENTAÇÃO
INCOMPLETA" — ver `ETAPA6_STATUS.md`). As 4 perguntas do aceite:

1. **Close hub: custo + efeito nas rotas** — MEDIDO. A navegação até a aba
   Close estava ERRADA na especulação anterior (não é Left; é Down 1x +
   Right 2x, mesma geometria de Return em r0c2 — validado sistematicamente
   testando 7 combinações de d-pad, `_probe_close_visual6.py`). A cadeia de
   confirmação tem DUAS perguntas YES/NO (não uma), e a 1ª tentativa de
   calibração parou cedo demais entre elas — saiu por B, que numa tela
   YES/NO equivale a NO, cancelando o close em silêncio (caixa 0K, mas o
   jogo continuava recusando reabertura do mesmo hub). Corrigido com uma
   cadeia de até 6 `_step()` parando no menu principal. Round-trip completo
   MEDIDO: fechar credita caixa (+32.300K num teste com 1 hub + 1 rota — não
   é constante, não reusar o número), fecha em CASCATA toda rota que PARTE
   do hub (rotas que só chegam sobrevivem), e NÃO consome negociador.
2. **Hubs por região / limite global** — máximo 1 por região RECONFIRMADO
   ("You already have a regional hub in X"). Limite global entre regiões
   diferentes não testado ao vivo (seria caro: slots+rota+hub em 2+ regiões).
3. **Hub muda a oferta da cidade** — INCONCLUSIVO. Uma comparação rápida de
   slots antes/depois do close não deu sinal limpo (confundida pela regra já
   documentada de exclusão de dígito sob o cursor). O que segue medido
   (17/08): o hub tem custo de manutenção próprio ($1.760K), slots continuam
   sendo negociados à parte via r0c2, não concedidos pelo hub.
4. **Hub pode ser movido/reaberto** — reabertura na MESMA cidade CONFIRMADA
   (round-trip completo, sem passar turnos, custo normal de novo). Em
   cidade DIFERENTE da mesma região: não executado ponta a ponta, mas a
   mecânica (candidato = "cidade que já recebe nossa rota") dá suporte
   claro a isso.

**Bug ativo corrigido no harness** (não só "gate fraco" como a ETAPA 6
suspeitava): o oracle antigo exigia funcionário saindo — sempre falso para
close_hub — e cada reprovação por esse motivo *desfazia via
`_restore_guard()` um close que tinha de fato funcionado no jogo*. Oracle
novo: caixa sobe (crédito), não desce.

`close_hub` adicionado a `pilot.SUPPORTED` (`harness/pilot.py`).

Evidência: `logs/close_hub_full_18ago/`, `logs/close_hub_final_18ago/`,
scripts `harness/_probe_close_visual6.py`, `_probe_close_extra_a.py`,
`_verify_close_hub_final.py`. Detalhe completo em `ACTION_SPACE.md` (seção
"Aba Close" sob r1c0) e `CALIBRATION.md` (`_do_close_hub`).

---

## 18/08 (sessão adicional) — ETAPA 10-Marketing: `ad_campaign` (r1c1) entra em `pilot.SUPPORTED`

Retomada da etapa: o macro `_do_ad_campaign` já existia em `executor.py`
(escrito em sessão anterior no mesmo dia, "CALIBRADO 18/08" na docstring),
mas **não estava em `pilot.SUPPORTED`** — o modelo continuava sem acesso a
marketing. Esta sessão:

1. Re-executou ao vivo `_verify_adcampaign.py` a partir de
   `states/_venture_pronto.state`: sucesso confirmado de novo, caixa
   $1.040.220K → $1.038.420K, **-1.800K exatos** (Standard Expense da
   campanha "Culture and Arts"), funcionários livres 4→3.
2. Re-executou a recusa (`states/eval_single_2000_lv5.state`, sem venture) e
   achou uma armadilha na evidência antiga: chamar `_do_ad_campaign`
   diretamente (sem `Executor.run`) faz `_restore_guard()` recarregar um
   `_guard.state` desatualizado de outra sessão, produzindo um delta de
   caixa (-28.800K) que não pertence a esta ação. Corrigido testando pelo
   caminho real do piloto, `Executor.run({"action":"ad_campaign"})`: recusa
   limpa, **delta 0** (`_verify_adcampaign_refusal2.py`).
3. Adicionou `"ad_campaign"` a `SUPPORTED` em `pilot.py`.
4. Documentou em `ACTION_SPACE.md` (seção r1c1) a relação entre `ad_campaign`
   (gasto pontual -1.800K, exige venture cultural pronto) e o orçamento
   recorrente de Ad (`set_budget(category="ad")`, r0c4) — duas alavancas de
   demanda cumulativas, não substitutas; `set_budget` continua FORA de
   `pilot.SUPPORTED` (calibração de 17/08 refutada em 18/08, ver §20
   CALIBRATION.md — não confundir com o achado desta sessão).

Evidência: `harness/_verify_adcampaign.py`, `harness/_verify_adcampaign_refusal2.py`,
`logs/run_f0/adcamp_fim.png`, `logs/run_f0/adcamp_semstaff.png`.

**Ainda não medido**: campanha com 2+ ventures culturais prontos na mesma
região, campanha em região != América do Norte, e se `Right` alterna
Standard↔Promotion Expense antes de confirmar (a macro sempre usa o default).

---

# Status — Aerobiz Evals (fim da sessão de 11/08/2026)

## Objetivo
Evals via OpenCode Go usando Aerobiz Supersonic, **single e multiplayer**, comparando um modelo **fraco** vs um **forte**, com adversários na **dificuldade máxima** no **cenário 2000-2020**.

## Pronto e verificado

| Item | Evidência |
|---|---|
| Partida configurada (cenário 4, nível 5) | `states/eval_single_2000_lv5.state` — Federal/Washington vs MetLink/NY, AirRoma/Roma, Aussie/Sydney, caixa $1.220.000K |
| Ponte BizHawk↔Python com execução em lote | op `BATCH` no Lua: ação de ~120s → ~45s; `end_turn` de 103s (falhando) → ~35s |
| Caixa lido da RAM | `0x25F9` × 10, batido contra a tela em 3 savestates |
| Cursor do mapa por RAM | `0x257F`/`0x2581`, offset cidade−(3,3); `0x900` é só cópia de renderização |
| Fim de turno | detectado pela mudança do caixa (o byte `0x106` NÃO serve: variou 7→14) |
| Slots por cidade | lidos do mapa pelos dígitos; **validado 6/6** com exclusão da vizinhança do cursor |
| Par de modelos | fraco `ling-3.0-tiny-free` (1/2) vs forte `deepseek-v4-flash-free` (2/2) |
| Registro do modelo real por turno | `model_solicitado` + `model_respondeu` no log |
| Gate mecânico | run de 8 turnos: **100% de execução** |

## O harness agora NAO MENTE (12/08)

O executor verifica EFEITO: abrir rota e negociar custam caixa, entao se o caixa
nao muda a acao e reportada como falha, nao como sucesso. Teste ao vivo:

    open_route NA14 -> (False, '... | SEM EFEITO: caixa inalterado (1220000K)')

Antes isso teria contado como sucesso e inflado a taxa de execucao. Com a
verificacao ligada fica evidente que **as rotas nao estao abrindo de fato** —
o fluxo de menu ainda esta errado (falta o remapeamento, tarefa #13), mesmo
depois de eu adicionar a tela de distancia/custo que faltava.

Esse e o estado honesto: infraestrutura de leitura e verificacao pronta,
execucao das acoes ainda quebrada e agora VISIVEL.

## PONTO EXATO ONDE ESTA TRAVADO (12/08) — retomar por aqui

Diagnostico ate o fim do fio, com evidencia de tela:

1. O texto "The new route will depart from Washington. Choose destination." datilografa
   e o jogo IGNORA input durante a animacao. Corrigido: `wait_stable()` antes de selecionar.
2. Com o texto ja completo, o cursor logico esta em (128,128) — posicao neutra — e a
   escrita na RAM o move para o alvo (209,71 para NA14), MAS o sprite nao e desenhado
   e o A nao seleciona nada.

**Hipotese a testar primeiro:** o cursor do mapa so "existe" apos um movimento REAL de
d-pad que o jogo processe; o toque que  faz antes da escrita esta sendo
consumido pela transicao de tela. Testar: apos , dar 2-3 toques reais de
d-pad, CONFIRMAR pela RAM que a posicao mudou por conta do input (nao da escrita), e so
entao escrever o alvo.

**Segunda hipotese:** as coordenadas de  vieram do mapa do cenario 1970. No
mapa de 2000 os numeros de slot aparecem em cidades diferentes (11, 9, 12, 2 e 34 em
Washington). Revalidar o catalogo com  neste cenario antes de confiar.

## Falta (bloqueia o objetivo)

1. **Placar** (`Info→victory`, P&L, ranking trimestral) — é a métrica do eval; sem ela não há como pontuar modelo nenhum.
2. **Calibração** dos parâmetros de ação — `CALIBRATION.md` lista o que é medido e o que é suposto. Sem ela, "pediu X, executou Y" passa despercebido.
3. **Ações faltantes**: sliders de frequência/tarifa, compra de avião, alteração de rota, orçamentos. Sem elas a companhia é deficitária por construção.
4. **Multiplayer**: `setup_multi.py` escrito, **não testado**. Parte de `states/eval_players_screen.state`.
5. **Baselines** no jogo real (`baselines.py` nunca rodou no emulador).

## Armadilhas que custaram caro (não repetir)

- Texto anima e depois **auto-limpa**; o jogo **ignora input durante a animação**, mas reapertar cedo **avança dois passos**. Padrão certo: esperar estabilizar → apertar → esperar mudar.
- Cursor de ícones **fica onde foi deixado** → sempre "homing" antes de navegar.
- Ganho de desempenho vem do **lote**, não de cortar frames: reduzir hold/wait quebrou a navegação.
- **Dois cursores diferentes**: na tela de escolha da base a RAM do mapa não vale — usar `locate.goto` visual.
- Probes e runs **precisam de `fallbacks=False`** ou registro do modelo real: a cadeia de fallback creditava a um modelo a resposta de outro (fez `claude-sonnet-5` parecer funcional quando dá 401).
- Chave do OpenCode Go **só libera os modelos `-free`**; todos os pagos dão 401.
- Estado inventado pelo harness paralisa o modelo: a lista de "negociações pendentes" nunca era limpa e ele passou 8 trimestres em `wait`.

## Próximo passo recomendado
Ler o placar (`Info→victory`) — desbloqueia a pontuação e fecha o ciclo de feedback do agente. Depois calibrar os parâmetros, então rodar fraco vs forte com `compare.py` (que já agrupa pelo modelo que realmente respondeu).

## LACUNA CRITICA ENCONTRADA (12/08, apontada pelo usuario)

O catalogo tinha **so a America do Norte (16 cidades)**. A vitoria exige **hub em TODA
regiao e #1 em passageiros nas 7 regioes** — confinado a um continente, o modelo
**nao pode vencer**, e o eval mediria um jogo truncado.

Levantado agora percorrendo o mapa com **R** durante a criacao de rota (o botao troca
de regiao e mantem Washington como origem — confirmado em tela):

| Regiao (ordem do ciclo) | Cidades |
|---|---|
| 0 America do Norte | 16 |
| 1 America do Sul | 9 |
| 2 Europa | 25 |
| 3 | 8 |
| 4 | 9 |
| 5 | 18 |
| 6 | 10 |
| **total** | **95** |

Coordenadas brutas em `logs/regioes/catalogo_bruto.json`; capturas por regiao em
`logs/regioes/reg_N.png`. O ciclo fecha em 7 (a 8a leitura repete a 1a).

**Consequencia para o eval:** o alcance da aeronave passa a ser decisivo (rota
transatlantica exige aviao de longo alcance), e `aircraft_index` — hoje NAO CALIBRADO —
vira parametro de primeira ordem, nao detalhe.


---

## 15/08 — MUNDO INTEIRO LIGADO AO EXECUTOR (criterio de aceite cumprido)

| Criterio | Resultado | Evidencia |
|---|---|---|
| (a) negociacao de slots fora da America do Norte | **OK** | `negotiate_slots EU11` (Bruxelas) e `SA01` (Havana) pelo `Executor.run`; painel Info->staff 0px -> 517/597px com `Area: Brussels` / `Area: Havana` |
| (b) rota para outra regiao com o caixa caindo | **OK** | `open_route SA01`: caixa **1.210.980K -> 1.166.820K (-44.160K)**; tabela de rotas passa a mostrar `NEW Washington Havana` e `1 Rte` |

Encadeamento provado ponta a ponta: negociar no outro continente -> 3 `end_turn`
(9 meses) -> slot confirmado na tela de detalhe (`0/96` -> `1/96`) -> rota abre.

### O que isso revelou (ver CALIBRATION §6-§10 e INVENTARIO §13)

- **`FLEET_START` estava errada**: descrevia a frota de 1970. O eval tem
  **MD100 x6, alcance 4680 mi** — o prompt anunciava um aviao inexistente.
- **`aircraft_index` nao e alavanca**: o seletor so cicla modelos que possuimos;
  com um modelo, 5 capturas com hash identico. Saiu do schema junto com `from` e
  `aircraft` (que a macro sempre ignorou e a validacao exigia).
- **Europa e inalcancavel neste savestate**: com 1 slot ja negociado em Bruxelas
  a rota ainda e recusada por **alcance**. Sem `buy_aircraft`, so America do
  Norte e o norte da America do Sul estao ao alcance — logo a condicao de
  vitoria ("hub em toda regiao") e **impossivel por construcao** e `buy_aircraft`
  vira bloqueio de primeira ordem, nao refinamento.
- Detector novo `world.on_plane_screen()` para a tela de recusa por alcance
  (antes o erro so aparecia tres telas depois, como "fluxo travou em voos/semana").


---

## 15/08 (2) — `buy_aircraft` IMPLEMENTADO E CALIBRADO

| Criterio | Resultado | Evidencia |
|---|---|---|
| macro no Executor | **OK** | `_do_buy_aircraft(model, qty)`; entrou em `pilot.SUPPORTED` e o catalogo de avioes vai no prompt |
| calibracao dos seletores | **OK** | fabricante: 1 Right = proximo (ciclo 6); modelo: 1 **Down** = proximo; quantidade: 1 Right = +1, base 1, teto 10 |
| catalogo (alcance/assentos/preco) | **OK** | 8 modelos lidos da tela — CALIBRATION §12.1 |
| verificacao de efeito | **OK** | o caixa cai **exatamente** o preco de tabela x qtd em 4 compras diferentes (81.600 / 108.000 / 28.800 / 110.000K), com `Info->fleet` marcando Order e depois Avail |
| `aircraft_index` (tela de rota) | **CALIBRADO** | a §7 estava errada: com 2 modelos o seletor cicla; indice = posicao em `Info->fleet`. Fica fora do prompt ate o harness ler essa tabela |

**Resultado negativo importante:** comprar o aviao de maior alcance do jogo
(A340, 8870 mi) **nao** abre Washington->Bruxelas — a recusa por alcance
persiste, inclusive depois de vender os MD100 para o A340 virar o indice 0.
O que se mediu e a recusa em si — o jogo nunca mostra a distancia, entao a
escala entre continentes segue NAO CARACTERIZADA. A condicao de vitoria
"hub em toda regiao" segue bloqueada.

Regressao reproduzivel: `python prova_buy.py chain` (compras e rotas
intercaladas, delta de caixa conferido contra o preco de tabela).

Tres bugs do harness caiam no caminho e foram corrigidos com evidencia
(CALIBRATION §15): falso positivo de `at_main_menu_img` no showroom, seletor
de fabricante **pegajoso** (custou uma compra acidental de $550.000K) e falso
negativo na verificacao de `negotiate_slots`.


---

## 16/08 — BUG DE ESTADO DA 2a NEGOCIACAO: ELIMINADO (criterio de aceite cumprido)

| Criterio | Resultado | Evidencia |
|---|---|---|
| `negotiate_slots EU11` -> `negotiate_slots SA01` -> `open_route NA06` -> `open_route NA02` | **4/4 True** | funcionarios livres 4->3->2; caixa 1.220.000K -> 1.203.800K -> 1.187.600K |
| 3 negociacoes em REGIOES diferentes no mesmo turno | **3/3 True** | EU11 Bruxelas, SA01 Havana, **ME01 Tashkent**; livres 4->3->2->1; 3 bonecos no mini-mapa |
| o retry de cursor nao mascarou nada | **`retries_fired = 0` nos 3 aceites** | contador novo em `Executor` |

Regressao: `python prova_neg_multi.py [a|b|c]` (c intercala compra de aviao).

### Causa raiz (o jogo dizia em voz alta e ninguem tinha fotografado)

`"Sorry, I'm busy making a bid for some airport slots."` — a macro apertava A as
cegas com o destaque parado no funcionario **0**, que depois da 1a negociacao
esta em missao. O jogo recusa e **fica na tela de staff**; os A's seguintes
morriam ali e o erro so aparecia tres passos depois, em `activate_cursor`, como
*"cursor do mapa nao respondeu"*. O invariante de regiao (15/08) tinha corrigido
as ROTAS porque o problema delas era outro — por isso a negociacao continuava
falhando.

### Segundo bug, achado pelo aceite B

`switch_to_region` mandava os R's **em lote**: como o jogo **engole as duas
primeiras teclas R**, a contagem ficava atras do alvo e cada correcao perdia
mais uma. Pedir Oriente Medio (regiao 4) parava na Africa (3). Agora e malha
fechada: **um R, uma leitura**.

### Terceira coisa, que nao era bug mas era risco

A celula (1,2) da grade de funcionarios **nao e funcionario**: e o **Return**
(devolver slots), a um toque de Right da ultima celula valida. O executor le a
acao destacada e **aborta se nao for Bid** — uma negociacao que virasse
devolucao de slots corromperia a partida sem erro nenhum.

### O gate de efeito da negociacao mudou (e por que o antigo ia mentir)

Era o painel `Info->staff`, que descreve **so o funcionario destacado** (sempre o
0) — a partir da 2a negociacao ele nao muda e a acao seria reprovada tendo
funcionado. Agora o gate e o **contador de funcionarios livres lido da barra do
menu principal** (23 px por boneco: 92 px = 4, 69 px = 3): cumulativo, por acao,
e sem navegacao extra. O mesmo numero vai ao modelo como
`company.negociadores_livres`.

Documentacao: CALIBRATION §17, INVENTARIO §15, ACTION_SPACE revisao 4.


---

## 17/08 (2) — `adjust_route` IMPLEMENTADO E CALIBRADO (r0c1, Flts/Fare)

| Critério | Resultado | Evidência |
|---|---|---|
| macro no Executor | **OK** | `_do_adjust_route(route, flights_week?, fare_level?)` em `executor.py`; entrou em `pilot.SUPPORTED` |
| alavanca Flts/Fare | **CALIBRADA — igual à criação** | 1 toque = +1 voo, 1 toque = +5% tarifa; confirmado $720→$792 (2 toques, "10% above avg.") e $410→$450 |
| navegação da barra de abas | **CALIBRADA** | 7 células fixas (Susp/Close/Model/Planes/Flts/Fare/SET), leitura por brilho médio, 5/5 acertos; malha fechada (um toque, uma leitura) |
| persistência do commit | **CONFIRMADA** | round-trip completo até o menu principal e reabertura mostrou os valores editados intactos |
| aceite (N→N+2 Flts + Fare mid→high) | **PARCIAL, por restrição real do jogo** | Fare mid→high funciona em qualquer rota testada; Flts tem TETO POR ROTA (Havana=1, San Fran=2) que não escala com nº de aviões e bloqueia N+2 na rota prescrita da etapa — reportado honestamente, não escondido |

### Causa da etapa anterior ter falhado (hipótese, não confirmada em log)

A rota prescrita pela etapa (`probe_hub_open_sa.state`, Washington-Havana)
tem teto de Flts = **1**, ou seja N+2 é fisicamente impossível ali — o jogo
recusa silenciosamente (o campo simplesmente para de responder ao `Right`,
sem mensagem). Um harness sem detecção de teto reportaria sucesso falso
(exatamente o bug pego e corrigido nesta sessão, ver CALIBRATION §18) ou
ficaria girando sem nunca fechar o critério "N+2" literal.

### Correção ao ACTION_SPACE.md (17/08, escrito antes de qualquer A ser
realmente apertado nas abas)

A 7ª célula da barra ("SEL(ECT)") tinha sido hipotetizada como "volta à
lista de rotas" sem nunca ter sido acionada. Medição real: é **SET**, o
botão de commit da edição inteira ("Is it OK to change this flight as
shown?"). A navegação entre múltiplas rotas abertas continua não mapeada —
por isso `adjust_route` recusa com mais de uma rota aberta em vez de supor.

### Armadilha nova, no molde das antigas

Um recorte de "detectar se o valor mudou" que inclui um elemento animado
(aqui: a borda pontilhada do popup do campo, que pisca a cada frame) dá
falso positivo — reportou "Flts 1→3" com a tela mostrando 1 o tempo todo.
Mesma classe de bug que already tinha quebrado `_step()` com as setinhas do
slider; corrigido isolando o recorte no dígito puro (evidência
`logs/adjust_aceite/stable*.png`: hash idêntico parado E no teto real).

Regressão: `python prova_adjust.py` (Havana, mostra o teto) e
`python prova_adjust_sf.py` (San Fran, mostra Flts+Fare funcionando juntos).

Documentação: CALIBRATION §18, ACTION_SPACE.md r0c1 revisado.

---

## 17/08 (3) — `open_venture` IMPLEMENTADO E CALIBRADO (r0c5, Business Venture)

| Critério | Resultado | Evidência |
|---|---|---|
| macro no Executor | **OK** | `_do_open_venture(city, type_index=0)` em `executor.py`; entrou em `pilot.SUPPORTED` |
| compra real 1 (via `_step` cru, sondagem) | **OK** | Washington, tipo 0 (Concert Hall): caixa 1.184.900K → 1.040.900K (-144.000K), 1 funcionário a menos |
| compra real 2 (via `Executor.run()`, API pública) | **OK** | Denver, tipo 0 (Arts Pavilion): caixa 1.184.900K → 1.157.900K (-27.000K), 1 funcionário a menos |
| recusa de `type_index` além do catálogo | **OK** | Washington só tem 3 tipos; pedir o 5º recusa e restaura estado (caixa intocado) |
| Info→facilities incrementa na hora? | **NÃO** (achado) | ícones seguem `×0` antes e depois da compra confirmada — venture fica "em negociação" (meses), mesmo padrão do hub |

### Achado que invalida o mapeamento anterior: catálogo de tipos NÃO é fixo por jogo, é por CIDADE

A tabela antiga (Concert Hall/City Hotel/Grand Hotel/Commuter Airline, 4
tipos sempre disponíveis, todos vistos supostamente em Washington) **estava
errada**. Medido ao vivo: Washington só oferece 3 tipos (Concert Hall
$144.000K, Grand Hotel $288.000K, Commuter Airline $576.000K — **sem City
Hotel**, `Right` sem wrap para no tipo 2); Denver abre no tipo 0 com um nome
nunca antes catalogado ("Arts Pavilion", $27.000K); o mesmo tipo (Concert
Hall) custa $126.000K em Philadelphia contra $144.000K em Washington. A
etapa pedia comprar especificamente "City Hotel, o mais barato" — não foi
possível porque **esse tipo não existe no catálogo de Washington** (só
descoberto tentando de verdade, não por leitura de tela parada). Em vez
disso, mediu-se e implementou-se o mecanismo genérico por `type_index`
(posição no catálogo real DESSA cidade), que é o que de fato existe no jogo.

### Armadilha cara: `_select_city` não serve para r0c5

A primeira tentativa (`probe_venture.py` v1) usou o helper genérico
`_select_city` (usado por r0c0/r0c2), que martela A até sair da tela do mapa.
Nesta tela específica isso ultrapassa a seleção de tipo — o "sair do mapa" só
acontece DEPOIS da tela de escolha, então o loop cego respondia YES ao "Is
this OK?" sem nenhum `Right` ter sido dado. Custou $144.000K de verdade antes
de ser diagnosticado (savestate `_venture_guard.state` salvo ANTES permitiu
retomar sem perder progresso). `_do_open_venture` não usa `_select_city`.

Documentação: CALIBRATION.md §21, ACTION_SPACE.md r0c5 revisado. Evidência:
`logs/run_f0/v2_*.png` .. `v10_*.png`, `logs/run_f0/venture_*.png`.


---

## 17-18/08 — ETAPA 1-EndTurn: o fim de turno ficou CONFIAVEL

| Criterio | Resultado | Evidencia |
|---|---|---|
| 6 `end_turn` seguidos a partir de `eval_single_2000_lv5.state` | **6/6**, 6 trimestres (contador 181 -> 187, APR.2000 -> OCT.2001) | `logs/etapa1/aceite_endturn.log`, capturas `aceite_t0..t6.png` |
| Prova independente da RAM | data lida dos **pixels** da barra do menu bate com o contador em **6/6** | `world.read_date_px` |
| Repeticao noutro savestate (com rota e hub) | **6/6**, 186 -> 192 (JUL.2001 -> JAN.2003) | `logs/etapa1/aceite_endturn_sa.log` |
| Corrida longa no mesmo savestate | **12/12**, 186 -> 198 (JUL.2001 -> JUL.2004), RAM x pixels 12/12 | `logs/etapa1/stress_endturn.log` |
| Custo de navegacao | quedas de caixa de 1.550K a 3.910K por trimestre, nenhuma perto da sentinela de 20.000K — inclusive na virada de ano | mesma tabela |
| **Re-verificacao 18/08 07:41-07:52** (depois das mudancas no `executor.py` de 18/08 02:22) | **6/6** nos dois savestates, RAM x pixels **6/6** nos dois, 1 disparo por chamada nos 12; contadores 181 -> 187 e 186 -> 192, iguais aos da primeira corrida | `logs/etapa1/aceite_endturn_reverify.log` + `reverify_t0..t6.png`, `logs/etapa1/aceite_endturn_sa_reverify.log` + `reverify_sa_t0..t6.png` |
| Reprodutibilidade dos numeros | `eval_single_2000_lv5`: log **byte a byte igual** ao de 17/08 (`diff` vazio). `probe_hub_open_sa`: contadores, datas e disparos iguais, mas as **quedas de caixa variam** entre corridas — `[1580, 3370, 3360, 3880, 3900, 3910]` vs `[1580, 3390, 3380, 3420, 3430, 3910]`. Fato medido: so o estado com rota operando varia; a causa NAO foi medida (hipotese: o numero de frames que a cadeia de relatorios fica aberta muda com o tempo de resposta da ponte). Consequencia pratica: **nao usar delta de caixa como assinatura de regressao em estados com rota** — use contador, data por pixels e disparos | `diff logs/etapa1/aceite_endturn_sa.log logs/etapa1/aceite_endturn_sa_reverify.log` |

Rodar de novo: `python prova_endturn.py 6` (ou `... 6 ../states/<state>.state <tag>`).
Passe o savestate por caminho ABSOLUTO: a assercao estrita de ancora
(`contador==181`, `data_px==(2000,2)`) so dispara quando `argv[2]` compara igual
a `states/eval_single_2000_lv5.state`; com caminho relativo ela e pulada em
silencio.

### O que estava errado (e o que era mito)

- O detector era **"o caixa mudou"**. MEDIDO (`probe_endturn_caixa.py`): nem o
  caixa nem o contador se atualizam antes de a cadeia de relatorios ser
  atravessada — quem lia cedo concluia "nao passou" e **redisparava o r1c5**,
  passando um trimestre a mais sem contar.
- O comando r1c5 em si **nunca falhou**: **24 chamadas de aceite pos-correcao**
  (6 + 6 + 12), todas com **1 disparo** de r1c5. O sintoma "4 chamadas, 2
  mudancas de caixa" era do detector, nao do comando.
- Sinal novo: `world.QUARTER_ADDR = 0x259F`, trimestres desde JAN/1955, com
  prova de **escrita** em 12 valores (ate OCT.2020, o fim do cenario do eval).

### Achado caro desta etapa

A cadeia de fim de turno pode parar numa caixa **(YES NO)** pedindo patrocinio
("Rep. of EC ... **$372000K is requested**"), com o cursor em YES. O fallback
de navegacao apertava A em tela travada — **A ali custa −372.000K** (medido).
Nao pagou por sorte: o destaque pisca, e o teste de "tela parada" nunca fechava.
Agora `world.yesno_prompt` detecta a caixa e o `dismiss_to_menu` proibe o A;
B atravessa de graca. Politica do harness: **recusar**. Aceitar so entra como
acao do modelo quando estiver medido o que o dinheiro compra.

### Proximo passo

O `end_turn` deixou de ser o gargalo: a cadeia de expansao (negociar slot ->
3 trimestres -> rota) ja pode ser encadeada sem desalinhar a data do prompt.

---

## 18/08 — ETAPA 5-Venture (retomada): pendências de `open_venture` fechadas, City Hotel refutado

`open_venture(city, type_index)` já estava implementado e calibrado (17/08,
commit `a36e348`). Esta sessão não reimplementou — verificou o que faltava
no aceite pedido e achou evidência já capturada em disco (`_probe_ad1..3.py`,
não documentada) fechando as duas pendências abertas em CALIBRATION.md §21:

| Pendência (17/08) | Resultado (18/08) | Evidência |
|---|---|---|
| Quando o contador de Info→facilities sobe? | **1 `end_turn` basta** (não "meses") — `x0 x0 x0` -> `x0 x0 x1` | `logs/run_f0/ad1_facilities_pos1turno.png` |
| `r1c1` com sucesso? | Sim — campanha "Culture and Arts" completa, -1.800K exatos | `logs/action_space_map/ad3_step4..7.png` |

**Sobre o aceite literal desta etapa ("comprar 1 City Hotel, o mais
barato"):** premissa falsa, não perseguida gastando caixa. A tabela de 4
tipos fixos (Concert Hall $144.000K/**City Hotel $72.000K**/Grand Hotel
$288.000K/Commuter Airline $576.000K) já estava marcada "não confie nela"
em CALIBRATION.md §21 — medido ao vivo em 3 cidades (Washington, Denver,
Philadelphia) e "City Hotel" **nunca apareceu** em nenhuma. O tipo mais
barato medido de verdade é Arts Pavilion ($27.000K, Denver), não City Hotel.
`type_index` é posição no catálogo real da cidade, não um tipo fixo — a
mecânica de compra por cidade+índice está provada duas vezes com caixa
batendo exato (Concert Hall -144.000K Washington; Arts Pavilion -27.000K
Denver). Sobrescrever essa mecânica para perseguir um nome de tipo não
confirmado violaria a REGRA 3 (nada entra sem calibração).

Novo savestate: `states/_venture_pronto.state` (venture comprado + 1
end_turn já passado, facilities em `x0 x0 x1` — ponto de partida para medir
`r1c1`/facilities sem repetir compra).

**Pendência nova, não fechada:** `r1c1` ainda não tem macro em
`executor.py` (`_do_ad_campaign` não existe); fluxo medido via
`Executor._step()` cru nos probes. Fica para a próxima etapa que tocar
`r1c1`.

---

## 18/08 (1) — ETAPA 4-Orcamentos: Correções Críticas em `_do_set_budget` (executor.py)

**Problema identificado pelo Advisor:**

A calibração anterior de Repair (17/08, §20 CALIBRATION.md) era um falso-positivo:
- O script `calib_budget_fixed.py::goto_col_order()` usa **apenas Down** para navegar ordem
- Se o savestate começava em MAXIMUM (idx 0), então:
  - level 0 (MAXIMUM): 0 Downs → confirma MAXIMUM (nada muda)
  - level 1 (RAISE): 1 Down → muda para RAISE (efeito)
  - level 2 (MAINTAIN): 2 Downs → muda para MAINTAIN (efeito)
  - level 3 (REDUCE): 3 Downs → muda para REDUCE (efeito, $100K)
  - level 4 (STOP): 4 Downs → muda para STOP (efeito, $90K)
- Resultado: tabela [110K, 110K, 110K, 100K, 90K] = 3 falsos positivos + 2 verdadeiros

**Tentativas de Ad em 18/08 (antes da correção):** 3 logs diferentes (00:47, 00:54, 01:03) mostraram navegação falhando ou tela sendo deixada cedo — **nenhum completou**.

### Correções implementadas em `_do_set_budget()`:

1. **Navegação de ordem em malha fechada:**
   - Ler `read_budget_orders()` após cada Down
   - Comparar com ordem alvo e fazer mais Downs se necessário
   - Verificação em 3 pontos: pré-confirmação, pós-confirmação, final

2. **Guard `on_budget_screen()` entre os `_step` chamados:**
   - Antes: duas chamadas `_step()` cegas → risco de "YES" em prompt de patrocínio (−$372.000K, ver §17)
   - Depois: verificar `on_budget_screen()` entre elas, abortar se deixou a tela

3. **Retorno de False em mismatch de rótulo:**
   - Antes: `print("AVISO: ordem selecionada é X, esperava Y")` + retorna True (warn-and-continue)
   - Depois: retorna False com mensagem clara (aceite exige "com LEITURA do rótulo confirmando")

### Descoberta pendente: a popup envolve (wrap)?

A navegação atual assume que Down clamps em STOP. Não testado ainda:
- De STOP (idx 4), um Down vai para MAXIMUM (idx 0)? **Não confirmado**
- Se não envolve, seria necessário implementar Up key para navegação reversa

### Scripts de testes prontos:

- `probe_wrap_test.py`: testa se STOP + Down = MAXIMUM
- `calib_budget_complete.py`: sweep corrigido para as 3 colunas (Repair, Ad, Service)

Uso:
```bash
python probe_wrap_test.py          # Descobre behavior de wrap
python calib_budget_complete.py wrap        # Confirma wrap
python calib_budget_complete.py sweep 0    # Sweep Repair
python calib_budget_complete.py sweep 1    # Sweep Ad
python calib_budget_complete.py sweep 2    # Sweep Service
python calib_budget_complete.py all         # Wrap test + sweep tudo
```

**Status:** Código corrigido e testes prontos. Aguarda EmuHawk + execução.

---

## 18/08 — ETAPA 7-LerFrota (parcial, BLOQUEADA)

Objetivo: fleet (In Use/Avail/Order) + Load% de rota no `build_state`. **Nao
fechado.** Medido via `harness/probe_fleet_ram.py` (interseccao de dump da
WRAM inteira em 4 savestates com valor de tela conhecido):

- `Avail[MD100] = 0x2840` — CONFIRMADO (unico candidato da WRAM inteira em 4 estados).
- `Order[MD100] = 0x28bc` — candidato, so 1 estado com Order != 0 (falta 2a confirmacao).
- `In Use[MD100]` — NAO encontrado (156 candidatos restantes; hipotese de ser campo calculado, nao armazenado).
- 2o modelo (A340) — stride entre linhas nao mapeado (1 unica observacao).
- Load% da tela de rotas — nao comecado.

Detalhe completo, savestates e proximos passos em CALIBRATION.md ("ETAPA
7-LerFrota"). Nada disto entra em `pilot.py`/`build_state` ainda (REGRA 3).

---

## 18/08 — ETAPA 11-Conselho (FECHADA)

Reinvestigação a fundo de r1c2 (reunião/conselho) pedida pelo usuário
("há decisão ali"). Os 4 tópicos (New Rtes / Adjust Rtes / Planes /
Businesses) foram todos abertos e lidos até "Meeting is adjourned", em 2
savestates (fresh e com 1 rota + hub SA já abertos).

**Veredito: continua LEITURA, sem decisão executável** — nenhum dos 4
tópicos abre cursor, seleção ou confirmação ligada a uma ação; todo
`(YES NO)` visto é "avançar para o próximo tópico?", nunca "aprovar isto?".
Caixa idêntica do início ao fim nas 2 corridas completas ($1.220.000K e
$1.138.020K).

**Achado novo (não estava no mapeamento de 17/08): o conteúdo É sensível ao
estado real do jogo**, não é tutorial fixo:
- tópico Planes narra a contagem real de frota ("6 total aircraft, 1 in
  service" — bateu com o savestate);
- tópico Adjust Rtes muda de "sem rotas, comentário genérico sobre aviões"
  para "com 1 rota real, comenta a própria rota" — e nesse caso pula
  silenciosamente a transição para o tópico Planes (parece já coberto);
- tópico New Rtes sugere uma 2ª rota citando uma cidade-hub que o jogador
  de fato possui (Havana, quando havia hub lá) — mas as sugestões 1 e 3 são
  fixas ("Washington-NewYork", "Washington-Tóquio") nos 2 testes, então não
  é um motor de recomendação real, é tutorial com 1 slot dinâmico.
- as ~8 dicas de tutorial do passo 0 só aparecem na PRIMEIRA vez que a
  reunião é chamada na sessão — reaberturas pulam direto para "Shall I
  conduct the meeting?".

**Recomendação**: não entra em `pilot.SUPPORTED` (não há efeito a
calibrar). Se o eval quiser dar ao LLM esse "conselheiro", expor como
leitura opcional de baixo custo, igual a `Info`.

Detalhe completo com a árvore de prompts, screenshots e savestates em
ACTION_SPACE.md ("r1c2 — Reunião / Conselho"). Savestates de guarda criados:
`states/_conselho_guard.state`, `states/_conselho_guard2.state`. Script:
`harness/probe_conselho.py`.

## 18/08 — Leitura de estado: atlas de fonte + tabelas de rotas e frota

**Contexto:** a partida de validacao mostrou que o gargalo nao e mais executar
acoes (8/8 sem falha) e sim o que o modelo VE. Rotas sem ocupacao, frota
rastreada pelo harness em vez de lida do jogo.

**Virada de abordagem:** a etapa anterior (7-LerFrota) tentou achar a frota na
RAM e travou — `Avail` achado, `In Use` com 156 candidatos, `Order` com 1 so
observacao. Mas `Info->fleet` e `Info->map` mostram TUDO na tela. Ler a tela
custou uma tarde; a RAM tinha custado uma etapa inteira sem fechar.

| Entrega | Arquivo | Estado |
|---|---|---|
| Leitor de texto generico (celula 8x13 na grade) | `harness/screen_text.py` | OK, aceite offline |
| Atlas de 39 glifos | `harness/glyphs.json` | OK |
| Rotulador de glifo novo (arte ASCII) | `harness/harvest_glyphs.py` | OK |
| `read_routes` / `read_fleet` / rodape | `harness/world.py` (fim) | OK, aceite offline |
| Aceite offline (sem emulador) | `harness/prova_tabelas.py` | **TUDO OK** |
| Aceite ao vivo (2 savestates) | `harness/prova_leitura_viva.py` | em execucao |

Detalhe da calibracao em CALIBRATION.md §24.

**Ainda NAO feito** (nao confundir com feito): hubs lidos do jogo, orcamentos no
estado, ventures, e a integracao em `pilot.build_state` — que precisa APAGAR os
campos que viraram leitura (`fleet_inicial_do_savestate`,
`avioes_comprados_nesta_run`, `AVISO_frota`) em vez de somar-se a eles. Deixar
ledger e leitura no mesmo prompt e entrada contraditoria.

### Turno AO VIVO com o estado novo (18/08) — integracao verificada

`pilot.py --turns 1 --state eval_single_2000_lv5.state --fresh --no-fallback`
(log: `logs/pilot_leitura/turns.jsonl`). O JSON que foi para o modelo:

| Campo | Valor | Fonte |
|---|---|---|
| `fleet` | `MD100 InUse 0 / Avail 6 / Order 0` | LIDO de Info->fleet |
| `orcamentos` | repair 58/max, ad 2/max, service 30/max | LIDO da tela r0c4 (as TRES colunas) |
| `routes_open` | `[]` + explicacao "sem rota aberta ainda" | partida nova |
| campos de ledger | **nenhum sobrou** | removidos de proposito |
| `model_respondeu` | `laguna-s-2.1-free` | sem fallback |

Isto era o risco real da integracao e nao dava para checar com teste de unidade:
a ordem por turno virou victory -> map -> budgets(r0c4) -> fleet, e a cadeia
`open_cmd` + `back_to_menu` + `info_screen` e a mesma que o §14.4 documenta como
capaz de cair no seletor de fabricante quando uma suposicao de dismiss falha.
Nao caiu: a frota leu certo DEPOIS do desvio pelos orcamentos.

Observacao util para o eval: o orcamento de **Ad esta em nivel 2** contra 58 de
Repair e 30 de Service. E exatamente o tipo de assimetria que um modelo bom
deveria notar e um modelo fraco ignora — e ate agora nao estava no prompt.

### O que continua em aberto

| Item | Estado |
|---|---|
| Hubs lidos do jogo | hipotese do mapa **rejeitada** (CALIBRATION §27); proximo caminho e a tela r1c0 |
| Ventures (`x N` por regiao) | tela identificada e correta (§26), mas usa fonte MENOR fora da grade 8x13 |
| `set_budget` no action space | continua FORA; agora ha leitura, entao da para calibrar de verdade |
| Tabela de rotas vazia | nao medido se existe (hoje `(None,None)` = "nao lido") |

**O turno fechou completo:** 4 acoes, taxa de execucao 100%, negociadores
4 -> 0 conferidos na barra, `end_turn` exato (contador 181 -> 182, APR.2000 ->
JUL.2000), caixa 1.220.000K -> 1.218.090K.

**A prova de que a leitura chegou ao raciocinio** (e nao so ao JSON): o diario
do modelo cita *"6 MD100 aircraft (200 seats, 4680mi range)"* — numero que so
existe porque `Info->fleet` foi lido neste turno. Antes o prompt carregava a
frota reconstruida pelo harness.

Um contraste com a rodada anterior que vale acompanhar: latencia 8,2s e
**parse_error nenhum**, contra 7-190s e reparo de JSON em 60% dos turnos. Uma
amostra de 1 turno nao prova causa; anotado para conferir na proxima corrida.

## 19/08 — ETAPA 3b: `negotiate_slots.slots` calibrado; `employee` REPROVADO por medição

Duas alavancas que estavam marcadas "NÃO CALIBRADO — aceita padrão" na tabela do
topo de `CALIBRATION.md`. Medidas separadamente (§32), deram respostas opostas.

**(a) `slots` — ENTRA no action space (1..5, default 1).** A tela "How many
slots?" sempre existiu e a macro atravessava sem olhar. `Right` = +1 slot, base
1, **teto 5 sem wrap** (toques 5..8 não mexem em nada). Lido de volta a cada
toque por um **medidor de bonequinhos** (`world.read_slots_qty`, contagem de
pixels — o texto de diálogo não está na grade 8×13 do §24 e sai `??????` no OCR).
Descoberta com consequência estratégica: **pedir 5 slots ocupa o mesmo
negociador pela mesma espera declarada que pedir 1** (tela de confirmação byte a
byte idêntica). Com só 4 negociadores, pedir 1 por vez desperdiça o recurso mais
escasso do jogo.

**(b) `employee` — NÃO ENTRA.** A premissa da etapa era falsa: `Area/Type/Wait`
descreve a **missão corrente**, não uma perícia do funcionário (0 px de painel
para os 4 na base; 856 px depois do despacho, mostrando
`Philadelphia / Airport Slots / 6 months`). Os quatro funcionários, mesma cidade,
mesmo savestate → **mesma duração declarada, texto byte a byte idêntico**. Sem
diferença medida, o parâmetro não entra (R1/R5).

**Bug de fluxo encontrado no caminho (§32.0):** `Executor._select_city` martelava
`A` "até sair do mapa", e `on_map_screen` devolve **True também na tela de
quantidade e na de confirmação** — a negociação inteira fechava dentro dele, no
padrão, e os dois `_step()` seguintes caíam no seletor de funcionário. Corrigido.

**Armadilha de medição (§32.3):** o recorte `world.TEXTBOX` **inclui o retrato do
interlocutor**, que muda com o funcionário — quatro telas com texto idêntico deram
quatro hashes diferentes. Comparação entre funcionários exige `(62,152,196,188)`.

**Ponta a ponta, medido:** ação `{"city":"NA14","slots":3}` pelo `Executor.run`
→ `slots pedidos=3 LIDOS DE VOLTA=3`, negociadores 4→3; **2 trimestres** depois
(ABR→OUT/2000, contador da RAM 181→183) os negociadores voltam a 4 e o cabeçalho
da cidade passa de **`Total slots 0/ 75` para `3/ 75`** — o jogo concedeu
exatamente o que foi pedido. Os "6 months" declarados = 2 trimestres reais.

Aceites: `harness/prova_slots_qty.py` (offline, 15 telas de quantidade + 8
negativos, TUDO OK) + a corrida ao vivo acima.

Evidência: `logs/etapa3b/`. Savestate base: `states/_e3b_base.state`.
