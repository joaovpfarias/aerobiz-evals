# Espaço de Ações Completo — inventário dos 12 comandos

Reescrito em 17/08/2026 a partir do jogo real (F0/F1 11/08 + sessões de calibração
12-16/08 + mapeamento exaustivo 17/08). Cada comando tem UMA seção com tabela
uniforme. Onde uma opção foi bloqueada por pré-requisito, a linha registra a
**recusa medida** (mensagem exata + estado de origem) — isso conta como
investigado; célula vazia é que não conta.

Mapa de comandos (grade 6x2 no menu principal, `macros.CMD`):

| | col0 | col1 | col2 | col3 | col4 | col5 |
|---|---|---|---|---|---|---|
| **linha0** | r0c0 nova rota | r0c1 editar rota | r0c2 negociar slots | r0c3 comprar avião | r0c4 orçamentos | r0c5 business venture |
| **linha1** | r1c0 hub regional | r1c1 campanha de anúncio | r1c2 reunião (conselho) | r1c3 info | r1c4 sistema | r1c5 passar turno |

Legenda de status: ✅ implementado e verificado | 🔶 mapeado, falta codificar |
❌ bloqueado por pré-requisito (recusa medida, evidência anexa) | 📖 leitura, não é decisão

---

## r0c0 — Nova rota (DECISÃO)

Fluxo: mapa (escolhe destino, com `R` trocando de região) → tela de distância/
custo → aeronave → nº de aviões → voos/semana → tarifa → confirmação.

| Parâmetro | Status | Detalhe |
|---|---|---|
| **Destino (`to`)** | ✅ | qualquer cidade das 95, calibrado com catálogo global `world.WORLD_CITIES` |
| **Origem (`from`/hub)** | ✅ | regra formal (REVISÃO 3): `a ∈ meus_hubs OU b ∈ meus_hubs` + slots nas duas pontas + alcance da aeronave ≥ distância |
| **Aeronave** | ✅ **calibrado ao vivo 19/08 (§31)** | `aircraft_index` = posição na tabela de frota; 1 toque Right = próximo modelo, **lido de volta da tela** (o seletor é percorrido comparando alcance+assentos; o nome vem do catálogo só quando ele conhece o modelo — a frota de 1970 é DC-9-30/B707-320, fora do catálogo). ⚠️ NÃO MEDIDO se o seletor é *pegajoso* entre entradas no fluxo: até lá o índice é deslocamento, não posição absoluta (§31.8). O ciclo tem só os modelos que POSSUÍMOS — com 1 modelo o parâmetro é inerte e índice fora do ciclo é recusado |
| **Nº de aviões** | ✅ **calibrado ao vivo 19/08 (§31)** | `planes`: 1 toque = +1, base 1, lido de volta pelo `x N` da tela; teto = unidades **disponíveis** do modelo. O bump em lote antigo perdia metade dos toques |
| **Voos/semana** | ✅ calibrado | 1 toque = +1 voo, base 1 (CALIBRATION) |
| **Tarifa** | ✅ calibrado | 1 toque = +5% sobre "average" (CALIBRATION) |
| **Custo/distância exibidos** | ✅ | lidos do cabeçalho `Origem ◁ N MI ▷ Destino`, substituem estimativa por pixel (CALIBRATION §8) |
| Recusa por alcance | ❌ medida | "We don't have any aircraft capable of flying such a great distance." (CALIBRATION §14) |
| Recusa por falta de hub | ❌ medida | "We don't have a regional hub here." — tela trava (cursor morto), não é seleção (REVISÃO 3) |
| Recusa por falta de slots no destino | ❌ medida 17/08 | `open_route SA01` sem negociação concluída: "nao temos slots no destino" (harness); jogo mostra fluxo de rejeição equivalente antes da tela de aeronave |

Consome 1 aeronave da frota por rota (CALIBRATION §11).

## r0c1 — Editar/suspender/fechar rota existente (DECISÃO) — ✅ Flts/Fare/Susp/Close IMPLEMENTADO 17/08

Mapeado 17/08 (`_edit_2rotas.state`, 2 rotas; `probe_hub_open_sa.state`,
Washington-Havana). Ao entrar na rota a partir da lista, aparece o resumo
(`Washington◁2430mi▷San Fran | MD100 x1 | Sales $100K | Load 0% | Fare $720 |
Flts 1`). Um segundo `A` abre a barra de abas no topo:

| Aba (ordem, cursor SO com Right/Left, sem wrap medido) | O que faz | Status |
|---|---|---|
| **Susp** | suspende a rota (pausa reversível, não fecha) | ✅ CALIBRADO 17/08 |
| **Close** | fecha a rota definitivamente (destrutivo, não reversível) | ✅ CALIBRADO 17/08 |
| **Model** | troca a aeronave alocada (mesmo índice de frota do r0c0); posição PADRÃO ao abrir a barra | 🔶 mapeado |
| **Planes** | nº de aviões alocados (mesmo campo do r0c0, A3) | 🔶 mapeado |
| **Flts** | ✅ CALIBRADO — voos/semana, mesma alavanca da criação (1 toque = +1 voo) | ✅ |
| **Fare** | ✅ CALIBRADO — tarifa, mesma alavanca da criação (1 toque = +5%; 2 toques mid→high verificado $720→$792) | ✅ |
| **SET** | ⚠️ CORRIGE a hipótese antiga ("SEL(ECT), volta à lista"): é o botão de **COMMIT**, não um seletor de rota. `A` aqui abre "Is it OK to change this flight as shown?" (YES/NO, cursor em YES); `A` confirma e escreve os valores editados — persistência confirmada round-trip até o menu principal e reabertura (`logs/edit_commit/n_reopen_summary.png`). Navegação entre MÚLTIPLAS rotas abertas segue **não mapeada**. | ⚠️ |

Fluxo de edição de um campo (Flts/Fare): `A` sobre a aba ativa um editor
inline (popup com o valor e ícones); `Right`/`Left` ajusta; `A` confirma o
campo (volta à barra, AINDA sem persistir — só `SET`+YES grava).

**TETO DE Flts, medido e NÃO caracterizado**: o campo para de responder ao
`Right` sem aviso, bem antes do range da aeronave importar. Washington-Havana
(1180mi) trava em **1** voo/semana mesmo com `Planes` subido de 1→3 (o teto
NÃO escala com nº de aviões, medido). Washington-San Fran (2430mi) trava em
**2**. Não é range nem nº de aviões — hipótese aberta é slots livres no
destino, não confirmada (negociar mais slots leva ~6 meses in-game, não
verificável no mesmo turno). Consequência prática: o alvo "N→N+2" do aceite
desta etapa **não é sempre alcançável** — é uma restrição real do jogo, não
uma falha do harness. O executor detecta o teto por hash do recorte do dígito
(nunca conta às cegas) e reporta o valor REALMENTE alcançado.

**ARMADILHA MEDIDA**: a primeira tentativa de recorte para detectar mudança
de valor incluía a borda pontilhada animada do topo do popup, que PISCA a
cada frame — resultado: "Flts: 1→3 (2 toques)" relatado com sucesso enquanto
a tela seguia mostrando `1` (mesmo padrão do aviso em `_step()` sobre
setinhas de slider piscando). Corrigido isolando só o dígito
(`FLTS_VALUE_BOX` em `executor.py`, evidência `logs/adjust_aceite/stable*`).

Implementado como ação `adjust_route` (`route`, `flights_week?`,
`fare_level?`) em `executor.py::_do_adjust_route`. Evidência dos dois casos
provados via `Executor.run()` real:
- `prova_adjust.py` (Havana): Fare mid→high confirmado ($410→$450); Flts
  pedido 1→3, teto real em 1 (reportado, não mentido).
- `prova_adjust_sf.py` (San Fran): Flts 1→2 (1 toque, dentro do teto) E Fare
  mid→high ($720→$792) confirmados juntos, persistência lida da tela.

**Limitação deliberada**: só opera sobre a rota default-mostrada ao abrir
`route_edit`; com mais de uma rota aberta a ação recusa (não decide às cegas
qual editar). Falta: mapear a navegação entre rotas; medir Susp/Close.

## r0c2 — Negociar slots (DECISÃO)

Já fechado em sessões anteriores (16/08, ver CALIBRATION §17-§17.7). Grade
2x2: **Bid** (0,0) / **Return** (1,2 — um Right a partir de Bid, MESMA grade,
não é tela separada) × escolha de funcionário (Area/Type/Wait).

| # | Item | Status |
|---|---|---|
| B1 | Negociar (Bid) | ✅ escolhe automaticamente o 1º funcionário livre; recusa antes do emulador se 0 livres |
| B2 | Quantos slots pedir | ✅ **CALIBRADO 19/08, CORRIGIDO 23/08 (§32, §36)** — a tela "How many slots?" tem um medidor de **N posições, N MUDA POR CIDADE** (medido: NA06=2, NA02=3, demais=5): 1 `Right` = +1 slot, base 1, **teto = N, sem wrap**; pedido acima de N é RECUSADO com o teto lido da tela (nunca reduzido em silêncio). Param `slots` (1..5, default 1) no action space, lido de volta a cada toque. **5 slots custam a mesma espera declarada que 1** |
| B3 | Qual funcionário enviar | ⛔ **NÃO É ALAVANCA — medido 19/08 (§32.3)**. `Area/Type/Wait` é a MISSÃO corrente, não perícia: 0 px de painel para os 4 na base, 856 px depois do despacho. Os quatro funcionários → mesma duração declarada, texto byte a byte idêntico. `employee` **não entra** no schema |
| B4 | Devolver (Return) | 🔶 isolado por segurança — o executor verifica que a ação em destaque é "Bid" antes de agir, para nunca devolver slots por engano |
| — | Funcionários livres (0-4) | ✅ lido dos bonecos da barra do menu principal, vai ao prompt como `company.negociadores_livres` |
| — | Prazo de negociação varia por cidade | ✅ medido (CALIBRATION §9) |
| — | Segunda negociação do turno | ✅ causa raiz e correção aplicadas (CALIBRATION §17, "Sorry, I'm busy" se todos ocupados) |

## r0c3 — Comprar aeronave (DECISÃO)

Fechado 15/08 (CALIBRATION §12). Fabricante → modelo → quantidade → 6
confirmações. Catálogo de 8 modelos com alcance/assentos/preço lidos da tela
(CALIBRATION §12.1). Índice de fabricante 2 = **"World Lease"**, canal de
**venda**, não de compra (vende a frota própria, ex.: MD100 por ~$20.520K,
limite de 3 por visita observado). `aircraft_index` calibrado mas fora do
prompt até o harness ler `Info→fleet` (§13). Comprar avião NÃO abre alcance
intercontinental por si só — é preciso hub (§14, ver r1c0 abaixo).

## r0c4 — Orçamentos (DECISÃO) — ⚠️ PENDENTE REVALIDAÇÃO 18/08

⚠️ **STATUS MUDOU**: Removido de `pilot.SUPPORTED` em 18/08 por falsa calibração (ver CALIBRATION.md §20)

**Histórico:**
- 17/08: Marcado como "CALIBRADO" via `calib_budget_fixed.py sweep 0`
- 18/08: Advisor apontou que o script usa Down-only, causando 3 falsos positivos
- 18/08: Tabela de Repair descartada; Ad/Service nunca foram validados

**O que está correto (mapeado, não calibrado):**

Tela única com 3 categorias lado a lado, cada uma com custo/nível/barra.

| Categoria | Baseline (pré-ação) | Efeito no jogo |
|---|---|---|
| Repair | ~$110K | manutenção/segurança |
| Ad | ~$460K | publicidade (demanda) |
| Service | ~$190K | serviço/ocupação/reputação |

Cada categoria é um seletor de **5 níveis discretos** ordenados por
**MAXIMUM (0) → RAISE (1) → MAINTAIN (2) → REDUCE (3) → STOP (4)**.

**Navegação (malha fechada, mapeada):**
- `Right/Left` = troca coluna (ciclo 3)
- `A` = abre popup da ordem
- `Down` = próxima ordem (comportamento de wrap NÃO CONFIRMADO — pode clamp em STOP)
- `A x2` = confirma ordem

**Efeito IMEDIATO** (esperado, não confirmado): não espera `end_turn`.
Lido por `read_budget_money()` (OCR dos dígitos "$XXXK").

**Implementação:**
- `_do_set_budget(category, level)` em `executor.py` — CORRIGIDA 18/08 com malha fechada
- Retirada de `pilot.SUPPORTED` até revalidação
- Testes prontos: `probe_wrap_test.py`, `calib_budget_complete.py`

**Próximos passos (ETAPA 4-Orcamentos):**
1. Executar `python calib_budget_complete.py all` com EmuHawk
2. Descobrir behavior de wrap (STOP + Down = MAXIMUM ou clamp?)
3. Recalibrar Repair, Ad, Service com navegação em malha fechada
4. Registrar tabela de valores reais em $ para cada nível de cada categoria
5. Re-adicionar a `pilot.SUPPORTED`

## r0c5 — Business Venture (DECISÃO) — CALIBRADO E IMPLEMENTADO 17/08 (ETAPA 5-Venture)

Estava catalogado como "comprar/vender via funcionário, nunca investigado".
**Errado**: o rótulo do menu (`Buy`/`Sell`) é enganoso — a tela é sempre de
**compra de empreendimento comercial na cidade**, não de aeronave nem slots.
17/08: **executado de verdade duas vezes** (Concert Hall em Washington,
Arts Pavilion em Denver — ver CALIBRATION.md §21). A ação `open_venture(city,
type_index)` está implementada em `executor.py::_do_open_venture` e entrou em
`pilot.SUPPORTED`.

**CORREÇÃO da mapeação anterior (a tabela de 4 tipos fixos abaixo estava
ERRADA):** o catálogo de tipos **não é fixo nem universal — varia por
cidade**. Washington só oferece 3 tipos (Concert Hall/Grand Hotel/Commuter
Airline, **sem City Hotel**); Denver abre com um tipo nunca antes catalogado
("Arts Pavilion", $27.000K); o mesmo tipo custa preços diferentes em cidades
diferentes (Concert Hall: $144.000K em Washington, $126.000K em
Philadelphia). A tabela original (Concert Hall $144.000K/City Hotel
$72.000K/Grand Hotel $288.000K/Commuter Airline $576.000K, todos sempre
disponíveis) provavelmente veio de uma cidade não registrada ou de leitura
apressada — **não confie nela**. Detalhe completo, evidência e a armadilha
que custou $144.000K numa primeira tentativa errada: CALIBRATION.md §21.

Fluxo real medido: seletor de funcionário (Buy/Sell, igual r0c2/r1c0) → A até
sair do mapa → **1 A sobre a cidade abre DIRETO a tela de tipo** (não há uma
tela separada "escolha a cidade" seguida de "escolha o tipo" — é a mesma
tela) já no tipo 0 (o "primeiro" desta cidade) com "Which business venture
will you purchase?" → `Right` cicla tipo/preço **sem wrap** (`Left`/`Up`/
`Down` sem efeito, testado) → A confirma o tipo → "You must negotiate...Is
this OK?" (YES/NO) → A confirma → **caixa debitada na hora** (mesmo padrão do
hub r1c0: a negociação "leva N meses", o pagamento não).

### Ligação com "Cultural Facilities" (resolve a lacuna E1) — RESOLVIDO 17/08

`Info→facilities` mostra 3 ícones ×0 por região. **Medido ao vivo**: comprar
um venture (Concert Hall, Washington) **NÃO** incrementa nenhum ícone na
hora — os 3 continuam em `×0` imediatamente após a compra confirmada e paga.
Segundo oráculo independente confirma o mesmo padrão: `r1c1` (campanha de
anúncio) continua recusando "There are no businesses in our North American
network to promote." logo após a compra. Conclusão: o venture recém-comprado
fica **em negociação** (mesmo mecanismo de `hubs_pending`) e só deve contar
em Info→facilities/r1c1 depois que a negociação completar. **RESOLVIDO
18/08**: não são "meses" — **1 `end_turn`** basta. A partir de
`states/_venture_comprado.state`, 1 `end_turn` levou Info→facilities de
`x0 x0 x0` para `x0 x0 x1` (`logs/run_f0/ad1_facilities_pos1turno.png`), e
`r1c1` deixou de recusar e completou uma campanha "Culture and Arts" de
verdade (-1.800K exatos, `logs/action_space_map/ad3_step4..7.png`).
Savestate pronto para reuso: `states/_venture_pronto.state`. Detalhe
completo: CALIBRATION.md §21 (RESOLVIDO 18/08).

A tela de detalhe da cidade (mesma usada aqui) também expõe **Pop/Econ/Trsm**
(Washington: Pop 1.2M, Econ 90, Trsm 48) — os dados de mercado que faltavam
para o modelo decidir rota (REVISÃO 2).

### RETOMADA 18/08 — "City Hotel" existe (achado por survey), é uma 2ª categoria de venture com efeitos diferentes de Concert Hall

Survey sem-compra (`survey_venture.py`) em 3 cidades novas achou "City
Hotel" de verdade em **Vancouver (NA01), tipo 0, $54.000K** (não $72.000K
como a tabela antiga assumia — mais uma vez preço varia por cidade).
Catálogo por cidade agora com 6 pontos de dados: Vancouver (City Hotel
$54.000K / Ferry $270.000K), Los Angeles (Arts Pavilion $27.000K / Grand
Hotel $216.000K / Catering Service $162.000K), Dallas (Arts Pavilion
$31.500K / Shuttle Service $126.000K) — somados a Washington/Denver/
Philadelphia de 17/08. **Nenhuma cidade repetiu o catálogo de outra.**

**Compra real de City Hotel executada** (`open_venture("NA01", 0)` via API
pública `Executor.run`): caixa 1.184.900K → 1.130.900K, **exato −54.000K**.

**Achado novo mais importante**: ao contrário de Concert Hall (conta em
`Info→facilities` após 1 `end_turn`, ver acima), **City Hotel NÃO aparece
em `Info→facilities` mesmo após 3 `end_turn` reais**, e `r1c1`
(ad_campaign) continua recusando "There are no businesses..." nos mesmos 3
turnos. Ou seja **o catálogo de venture tem pelo menos duas categorias com
consequências de jogo diferentes** — "cultural" (Concert Hall/Arts
Pavilion, contado em Cultural Facilities) vs. "lodging/hospedagem" (City
Hotel/Grand Hotel/Ferry/Shuttle/Catering, efeito ainda não localizado em
nenhuma das 6 telas de Info do jogo). Detalhe, evidência e savestates:
CALIBRATION.md §21, subseção "RETOMADA 18/08".

**Armadilha nova**: a ação `wait` do executor (`ex.run({"action":"wait"})`)
é **NO-OP** (não avança turno) — só passa o turno de verdade
`Game.end_turn()` (macros.py). Rodar `wait` em loop parece "passar turnos"
(retorna `ok=True`) mas o contador de trimestre (RAM `0x259F`) e o caixa
ficam parados; só usar `g.end_turn()` para medir efeitos "depois de N
turnos".

## r1c0 — Hub regional (DECISÃO) — MECÂNICA FECHADA 17/08

Achado em 15/08 (comando errado catalogado como "info da base"). **17/08:
fluxo completo medido com sucesso real**, a partir de `probe_hub_open_sa` /
`prova_ic_rota_sa.state` (rota Washington→Havana já aberta).

Age sobre a **região exibida no mapa principal** (trocar com `R` antes de
invocar). Três desfechos medidos:

| Estado da região | Mensagem/tela | Evidência |
|---|---|---|
| Região da BASE | "Our home base is here in North America. We don't need a regional hub." | REVISÃO 3 (15/08) |
| Região sem nenhuma rota chegando | "We can't open a regional hub in South America. We don't have any flights going there." | REVISÃO 3 (15/08) |
| **Região com rota chegando (ainda sem hub)** | **abre seletor de funcionário** (Area/Type/Wait, abas **Open/Close** — não Bid/Return) → "Who will you send to negotiate..." → "In South America, preparations for a regional hub are already underway in Havana." | **17/08**, `logs/action_space_map/r1c0_msgfull.png` |

**Custo medido: -$28.800K** (caixa $1.166.820K → $1.138.020K), debitado na
hora, mesmo padrão de negociação com funcionário (consome 1 negociador livre).
Confirma a linha `Hub Costs` do P&L observada e nunca investigada.

Isso fecha a regra de expansão por completo:

```
1. negociar slots numa cidade da região X          (r0c2)
2. abrir rota base(ou outro hub)→essa cidade        (r0c0)
3. trocar mapa para a região X (R) e invocar r1c0   (r1c0) -> custa $28.8M, 1 funcionário
4. hub em X liberado -> novas rotas podem partir de X
```

Savestate de referência com hub já aberto: `states/probe_hub_open_sa.state`.

### Aba Close (fechar hub) — CALIBRADA AO VIVO 18/08 (ETAPA 12-HubsCompleto)

Navegação para a aba Close: **NÃO é Left/Right/Up dentro da grade de fotos de
funcionário** (essas teclas nunca tocam Open/Close — testado sistematicamente
em `_probe_close_visual6.py`, 7 combinações). A geometria é **idêntica a
Return em r0c2**: a grade de staff tem uma coluna extra (col=2) fora das
fotos, com **Open na linha 0 e Close na linha 1**. Partindo do cursor
neutro (0,0), `Down 1x + Right 2x` chega em (1,2)=Close — confirmado por
`staff_action_is_bid()==False` e captura com "Close" destacado em laranja.

**Cadeia de confirmação tem DUAS perguntas YES/NO, não uma** (armadilha
medida: parar cedo demais e sair por B equivale a responder NO na 2ª e
cancela o close inteiro, em silêncio — caixa 0K, hub continua do jogo):

```
A (na célula Close)  -> "Are you sure you want to close the regional hub in Havana?" (YES/NO)
A (YES)               -> "1 regional hub and 1 route will be closed." (aviso, só info)
A                     -> detalhe por rota afetada: "All flights listed above will be closed."
A                     -> "Are you sure you want to close?" (2ª pergunta YES/NO, agora sobre a ROTA)
A (YES)               -> menu principal, caixa CREDITADA aqui
```

Testado com 1 hub + 1 rota partindo dele; lista de várias rotas/hubs
simultâneos na mesma região não testada (o jogo pula direto para a 1ª
pergunta quando só existe 1 hub — não mostra uma "lista de hubs" à parte).

**Evidência de tela**: `logs/close_hub_full_18ago/extra_a/01.png`..`06.png`
(as 5 telas da cadeia + retorno ao menu), `logs/close_hub_final_18ago/`
(round-trip fechar+reabrir via `Executor.run`, sem atalhos manuais).

**Efeitos MEDIDOS** (savestate `states/_hub_rota_do_hub.state`: hub em
Havana/SA01 + rota Washington→Havana + rota Havana→Kingston/SA03 **partindo
do hub**):

| Pergunta (ETAPA 12) | Resposta medida |
|---|---|
| **(a) Custo de fechar + efeito nas rotas** | Caixa **CREDITADA** em fechamento completo (+$32.300K no round-trip Havana com 1 hub + 1 rota — não é o inverso exato da Construction Cost de $28.800K; **não reusar 32.300K como constante fixa**, o valor provavelmente embute algo específico da rota fechada). O jogo fecha em CASCATA toda rota que **PARTE** do hub fechado (confirmado por texto explícito na tela, duas telas distintas). Rota que só **CHEGA** no hub (ex.: base→hub) sobrevive intacta — verificado por `route_edit` pós-close mostrando só Washington→Havana. Fechar hub **NÃO consome negociador** (funcionários livres inalterados, 4→4 em toda a cadeia) — a célula Close não é um funcionário. |
| **(b) Quantos hubs por região / limite global** | **Máximo 1 hub por região confirmado**: tentar `open_hub` numa região que já tem hub nosso (mesmo após um close mal-sucedido que não commitou) dá a recusa "You already have a regional hub in Havana" — mensagem nomeia a cidade, mas a checagem é de REGIÃO (mesmo padrão de `open_hub`, ver tabela acima). Limite GLOBAL entre regiões diferentes **NÃO testado ao vivo** nesta sessão (custaria negociar slots + abrir rota + hub em 2+ regiões simultaneamente); a condição de vitória exigir "hub em toda região" (7 regiões, `Info→victory`) é evidência de design de que múltiplos hubs simultâneos em regiões DIFERENTES são esperados e — presume-se, não confirmado por captura — permitidos. |
| **(c) Hub muda a oferta da cidade (slots/custo)?** | **INCONCLUSIVO** — uma comparação rápida de `cities_with_slots` antes/depois do close (`_probe_hub_slots_effect2.py`) mudou de `[]` para `['SA01']`, mas o resultado é consistente com a exclusão de dígito sob o cursor (regra já documentada) tanto quanto com um efeito real do hub; não há evidência limpa o suficiente para afirmar que o hub altera capacidade de slot da cidade. O que ESTÁ medido (17/08): o hub tem seu próprio custo fixo de manutenção ($1.760K, linha `Hub Costs` do P&L, nunca confirmada por trimestre) independente de slots — os slots continuam sendo um recurso negociado à parte (r0c2), não concedido pelo hub. |
| **(d) Hub pode ser movido/reaberto em outra cidade da região?** | **Reabertura na MESMA cidade, SIM, confirmada** — depois de um close que realmente commitou (caixa creditada), `open_hub` na mesma região volta a funcionar normalmente e cobra a Construction Cost de novo ($28.800K), sem nenhum bloqueio residual (round-trip completo em `_verify_close_hub_final.py`, mesma sessão, sem passar turnos). Abrir em uma cidade **DIFERENTE** da mesma região não testado (exigiria negociar slots + rota nova para outra cidade da região antes do open_hub oferecer outro candidato na lista — o candidato mostrado é sempre "a cidade que já recebe nossa rota", então tecnicamente já é possível "mover" o hub simplesmente fechando numa cidade e repetindo a cadeia r0c2→r0c0→r1c0 noutra cidade da mesma região; a mecânica de escolha dá suporte a isso, só não foi executada ponta a ponta). |

**Armadilha medida e corrigida no harness** (`executor.py::_do_close_hub`):
o oracle antigo exigia que um funcionário saísse (`livres_depois <
livres_antes`) — **sempre falso** para close_hub, e cada vez que isso
acontecia `_restore_guard()` desfazia um close que tinha de fato funcionado.
Um segundo oracle tentado (reabrir r1c0 e checar se aparece Open) também
era inútil: essa tela aparece **igual** com ou sem hub — a recusa "You
already have..." só vem **depois** de escolher funcionário e apertar A no
fluxo de Open. Oracle correto, agora em produção: **caixa sobe** (crédito).

## r1c1 — Campanha de anúncio (DECISÃO) — CALIBRADO E IMPLEMENTADO 18/08 (ETAPA 10-Marketing)

Medido 17/08 com DUAS recusas distintas (nenhuma execução bem-sucedida
alcançada na época — ver pré-requisitos):

| Situação | Mensagem exata | Estado de origem |
|---|---|---|
| Sem nenhum business venture na região | "There are no businesses in our North American network to promote." | `states/_edit_2rotas.state` (2 rotas, 0 ventures) |
| Guerra mundial em curso (evento aleatório) | "We're in the middle of a war! We can't conduct a campaign now!" | `states/prova_ic_rota_sa.state` e `states/probe_hub_open_sa.state` (ambos em Jul/2001) |

**Pré-requisito revelado**: campanha de anúncio promove os **business
ventures da região** (r0c5), não a rota em si — reforça que r0c5 não é
opcional para uma companhia que queira usar r1c1.

### Fluxo de SUCESSO — MEDIDO E RE-VERIFICADO AO VIVO 18/08

Pré-requisito completo: `open_venture` (compra um business venture **da
categoria "cultural"** — Concert Hall/Arts Pavilion; ver r0c5 acima, City
Hotel/Grand Hotel NÃO servem) + **1 `end_turn`** para o venture passar de
"em negociação" para "pronto" (confirmado por `Info→facilities` subindo de
`x0 x0 x0` para `x0 x0 x1`).

```
r1c1 -> seletor de funcionario (grade 4x2, SEM par Bid/Return — usar
        _pick_free_staff_single, nao _pick_free_staff) -> "We will sponsor
        cultural events at our facilities." -> tela "Culture and Arts":
        Standard Expense $1.800K = Promotion Expense $1.800K, "Chance for
        Success average" -> "Are you sure you want to run this Culture and
        Arts campaign?" YES/NO (default YES) -> A confirma -> "I'll get
        right on it."
```

Caixa medida (17/08, `_probe_ad2/3.py`): $1.040.220K → $1.038.420K, **-1.800K
exatos**. **RE-VERIFICADO AO VIVO nesta sessão (18/08)**, mesmo savestate
(`states/_venture_pronto.state`) via `Executor._do_ad_campaign` direto:
idêntico, $1.040.220K → $1.038.420K (**-1.800K**), funcionários livres 4→3
(`_verify_adcampaign.py`).

**Recusas (SEM custo) re-verificadas nesta sessão** (18/08), duas telas
diferentes dependendo do motivo — o executor NÃO distingue as duas causas
internamente (ambas caem em "nenhum funcionário livre detectado" porque
nenhuma tem crachá de funcionário na tela):

| Causa | Mensagem | Tela sem crachá? |
|---|---|---|
| Sem venture PRONTO na região (ausente ou ainda "em negociação") | "There are no businesses in our [região] network to promote." | sim |
| Região sem NENHUMA rota nossa | "We can't run an ad campaign in [região]. We don't have any routes there." | sim |
| Guerra mundial em curso | "We're in the middle of a war! We can't conduct a campaign now!" | sim (17/08) |

Re-verificação ao vivo via `Executor.run({"action":"ad_campaign"})` (API
pública, a mesma que `pilot.py` usa) a partir de `eval_single_2000_lv5.state`
(sem venture, caixa $1.220.000K): recusa limpa, **caixa idêntica no
final, delta 0** (`_verify_adcampaign_refusal2.py`). **Armadilha encontrada
ao medir**: chamar `_do_ad_campaign` diretamente (sem passar por
`Executor.run`, que salva o savestate de guarda `_guard.state` no início) faz
`_restore_guard()` recarregar um GUARD *desatualizado* de uma sessão
anterior — a 1ª tentativa de recusa (`_verify_adcampaign_refusal.py`, chamada
direta) reportou "delta -28.800K" enganoso, exatamente o custo de um
`open_hub` de uma sessão passada que ainda estava salvo em
`states/_guard.state`. Corrigido usando `Executor.run(...)`, que sempre salva
o GUARD atual antes de qualquer macro — é o caminho real do pilot, então a
recusa é seguramente sem custo em produção. **Lição**: os probes `_do_*`
chamados crus são válidos para medir o CAMINHO DE SUCESSO (nunca chegam a
`_restore_guard`), mas não para medir uma recusa isoladamente — use sempre
`Executor.run()` para isso.

**Entrada em `pilot.SUPPORTED`**: `ad_campaign` adicionado 18/08
(`pilot.py`). Macro em `executor.py::_do_ad_campaign` (existia desde antes
desta sessão, com o fluxo já medido; esta sessão apenas re-verificou ao vivo
e destravou a entrada no piloto).

### Relação entre `ad_campaign` (r1c1) e o orçamento de Ad (r0c4)

Duas alavancas de demanda **diferentes, não substitutas**:

| | `ad_campaign` (r1c1) | `set_budget(category="ad")` (r0c4) |
|---|---|---|
| Tipo de gasto | Pontual, 1x por execução | Recorrente, todo trimestre |
| Custo medido | **-1.800K exatos** (Standard Expense) | 5 níveis MAXIMUM..STOP, valores NÃO recalibrados nesta sessão (ver r0c4 abaixo — retirado de `pilot.SUPPORTED` em 18/08 por calibração falsa anterior) |
| Pré-requisito | **Exige** 1 business venture cultural pronto (`open_venture` + 1 `end_turn`) — sem ele, recusa sempre, mesmo com orçamento de Ad no máximo | Nenhum — é um dial genérico da companhia inteira |
| Seleciona funcionário/cidade? | Sim (funcionário) | Não — aplica-se à companhia toda |
| Status no piloto | `pilot.SUPPORTED` (18/08) | Removido (§r0c4, aguarda recalibração) |

Ou seja `open_venture` é pré-requisito de `ad_campaign`, mas **não** de
`set_budget(ad=...)` — o orçamento recorrente de Ad é uma alavanca
independente que não depende de possuir nenhum business venture. Os dois
gastos são cumulativos, não mutuamente exclusivos: nada no fluxo medido
sugere que um substitui o outro.

## r1c2 — Reunião / Conselho (REINVESTIGADO A FUNDO 18/08 — LEITURA confirmada, não é decisão)

**Investigado pela primeira vez 17/08** (submenu de 4 tópicos hipotetizado,
não drilled down). **Reinvestigado a fundo 18/08** (ETAPA 11-Conselho) — os 4
tópicos foram todos abertos e o conteúdo lido; abaixo o veredito completo.

### Fluxo real (medido em 2 savestates: fresh `eval_single_2000_lv5.state` e
`probe_hub_open_sa.state` com 1 rota + hub SA já abertos)

1. `A` abre a cena da sala de reunião: "I call this meeting to order."
2. **Só na PRIMEIRA vez que a reunião é chamada na sessão**, roda uma
   sequência de ~8 dicas de tutorial genéricas (texto fixo, mesmo conteúdo já
   citado em 17/08: "Slots can be gained from negotiating with a city.",
   "Order aircraft from a manufacturer. Delivery is 3 months later.", etc.).
   **Medido**: reabrindo a reunião mais tarde na mesma sessão (com ou sem
   savestate carregado de novo), essas dicas são **puladas** — cai direto no
   passo 3. Isso é um portão de tutorial "vi uma vez", não uma dica por
   turno.
3. Prompt `(YES NO)`: **"Shall I conduct the meeting?"** — cursor em YES.
   Confirmado com `A` (YES) nos dois savestates testados.
4. **Tópico 1 — New Rtes.** Anúncio "First, let's discuss opening new
   routes." (o gráfico YES/NO do passo 3 aparece 1 frame a mais por cima
   deste texto — artefato de renderização, não é um segundo prompt; `cash`
   idêntico, sem interação de cursor possível ali). Depois vêm **3
   sugestões de rota concretas**, cada uma citando cidades por nome:
   - Sugestão 1: sempre **"Washington and New York"** nos dois savestates
     testados (fixa, ligada à base).
   - Sugestão 2: **muda com o estado do jogo** — no savestate fresh (só a
     base, sem hub extra) foi "Washington and Chicago"; no savestate com hub
     aberto na América do Sul (Havana) foi **"Havana and Mexico City"** —
     ou seja, o conselho puxa uma cidade-hub que o jogador de fato possui.
   - Sugestão 3: sempre **"Washington and Southeast Asia... How about
     Tokyo?"** nos dois savestates (fixa).
5. Prompt `(YES NO)`: **"Next, let's discuss adjusting existing routes."**
   → confirmar YES. **Tópico 2 — Adjust Rtes.**
   - No savestate **sem nenhuma rota aberta**: o conteúdo colapsa para um
     comentário genérico de frota — "We have 6 planes in reserve." / "We
     have enough planes." — e a transição seguinte pula direto para
     Businesses (a transição textual "Next, let's discuss our plane
     holdings" **não apareceu** nesse caso — o tópico Planes foi
     absorvido/pulado quando não há rota para ajustar).
   - No savestate **com 1 rota real aberta** (Washington–Havana): o
     conteúdo é especificamente sobre a rota — "All of our flights are new
     routes." / "I'm sure we'll carry lots of passengers." — texto
     diferente do caso sem rota, confirmando que o tópico É sensível ao
     estado real das rotas (não é texto fixo).
6. (só no savestate com rota) Prompt `(YES NO)`: **"Next, let's discuss our
   plane holdings."** → YES. **Tópico 3 — Planes.** Conteúdo: **"Our
   company has 6 total aircraft, with 1 plane in service."** — número real
   da frota (batendo com o savestate: 6 aviões possuídos, 1 em uso na rota
   aberta) seguido de "We have enough planes." Confirma leitura ao vivo da
   contagem de frota (mesmo dado de `Info→fleet`, aqui narrado).
7. Prompt `(YES NO)`: **"Next, let's discuss business ventures."** → YES.
   **Tópico 4 — Businesses.** Nos dois savestates testados (nenhum tinha
   venture comprado): **"Our company currently does not have any business
   ventures."** — hipótese não testada: com 1+ venture comprado o conselho
   provavelmente citaria o tipo/cidade, por analogia ao padrão dos outros 3
   tópicos (não confirmado — nenhum savestate com venture ativo foi usado
   neste probe).
8. **"Meeting is adjourned."** → volta sozinho ao menu principal. Não
   apareceu o prompt separado "Shall we adjourn and meet again later?"
   citado no mapeamento de 17/08 nos 2 fluxos completos rodados agora — ele
   deve ser um caminho alternativo de SAIR CEDO (via `B`), não o fim natural
   depois dos 4 tópicos.

### Veredito por tópico

| Tópico | Decisão executável? | Conteúdo é sensível ao estado? |
|---|---|---|
| New Rtes | ❌ NÃO — sugestões são só texto, sem cursor/seleção sobre as cidades citadas | ✅ parcial — sugestão 2/3 muda com hubs possuídos, sugestões 1/3 fixas nos 2 testes |
| Adjust Rtes | ❌ NÃO | ✅ sim — muda completamente entre "0 rotas" e "1 rota real" |
| Planes | ❌ NÃO | ✅ sim — cita a contagem real de aviões (6 total / 1 em uso, batendo com o savestate) |
| Businesses | ❌ NÃO | ⚠️ não testado com venture ativo (só "sem ventures" nos 2 casos) |

**Nenhum dos 4 tópicos abre um cursor, uma lista selecionável ou uma
confirmação ligada a uma ação específica.** Cada `(YES NO)` visto no fluxo é
sempre da forma "quer ouvir o próximo tópico?" (avançar vs. pular/encerrar) —
nunca "aprovar esta rota/compra?". `B` durante o conteúdo provavelmente pula
para a próxima transição (não testado a fundo; não foi necessário porque o
fluxo natural via `A`+YES já percorre os 4 tópicos).

**Custo: nenhum em nenhum dos ~35 passos testados** (2 corridas completas,
16 savestates de calibração intactos, caixa idêntica do início ao fim em
ambas: $1.220.000K e $1.138.020K). Confirmado 📖 **leitura pura**, não
consome turno nem recurso, **não é candidato a ação executável** no espaço de
decisão do modelo.

### Ligação ao estado do modelo (o conteúdo é o produto, não a decisão)

Como o usuário apontou, o conselho **é um conselheiro embutido que o jogador
humano usaria** — mesmo sem decisão executável ali, o CONTEÚDO é sinal real
de jogo que vale a pena expor ao prompt do LLM, porque é a única tela que
narra em linguagem natural (sem precisar OCR de tabela) fatos que já existem
em outro lugar do jogo, cross-referenciados:
- **contagem de frota** (bate com `Info→fleet`, aqui em frase: "N total
  aircraft, M in service") — sinal de sobra/falta de aviões sem precisar ler
  a tabela pixel a pixel;
- **status "há rotas para ajustar ou não"** — proxy textual de "a rede tem
  rotas abertas";
- **sugestões de cidades-alvo para nova rota**, parcialmente ancoradas nos
  hubs já possuídos pelo jogador — pode servir como prior/sugestão de ação
  para o modelo, mas **NÃO deve ser tratado como uma recomendação
  otimizada**: as sugestões 1 e 3 são fixas independente do estado
  (Washington-NewYork, Washington-Tóquio), então é tutorial-flavored, não um
  motor de recomendação real.

**Recomendação para o harness**: não implementar `r1c2` como ação no
`pilot.SUPPORTED` (não há efeito a calibrar — não muda nada no jogo). Se o
eval quiser dar ao LLM acesso a esse "conselheiro", expor como uma
leitura opcional de baixo custo (poucos `A`s, sem risco) equivalente a
`Info`, não como uma ação de turno.

**Evidência 18/08**: `logs/action_space_map/cons_step_00..21.png` (corrida
completa a partir de `eval_single_2000_lv5.state`, savestate `_conselho_guard.state`)
e `logs/action_space_map/cons2_step_00..15.png` (corrida completa a partir de
`probe_hub_open_sa.state`, savestate `_conselho_guard2.state`). Script:
`harness/probe_conselho.py` (rascunho inicial; as corridas efetivas foram
feitas via one-liners registrados nesta seção para poder abortar
step-a-step ao ver `yesno_prompt`).

## r1c3 — Info (LEITURA — 6 relatórios)

| Relatório | Conteúdo medido | Status |
|---|---|---|
| **map** (índice 0) | mapa da região atual | 📖 já usado para navegação |
| **staff** (1) | funcionários (crachás/base/missão) | ✅ parcialmente lido (usado no gate de r0c2/r1c0), não vai ao prompt por cidade |
| **fleet** (2) | `Plane \| In Use \| Avail \| Order` | 🔶 CALIBRATION §13 usa para `aircraft_index`, falta expor ao prompt |
| **finance** (3) | **CORRIGIDO 17/08 (ETAPA 8-LerRanking)**: cai primeiro no "Quarterly Report \<mês\>\<ano\>" (P&L em barras por companhia); só depois de **mais um `A`** abre "Regional Rankings \<ano\>": mapa-mundi com 1 caixa por região (Europe/N America/SE Asia/Mid East/Oceania/Africa/S America) e as 4 companhias listadas (Federal/MetLink/AirRoma/Aussie), coloridas por colocação — ordem da legenda muda de fato entre trimestres, confirmado ao vivo (Apr2000 vs Jul2000, ver CALIBRATION.md) | ✅ tela + navegação calibradas (`world.on_regional_rankings_img`/`on_quarterly_report_img`); ✅ **18/08**: número do líder por região OCR'ado sem drill-down (`world.read_regional_rankings`, catálogo de glifos por hash — CALIBRATION.md §ETAPA 8-LerRanking), validado nos 2 momentos já capturados (N America 17280→34560, Oceania 1848→9048); ⚠️ offset de linha das outras 5 regiões (sem dado no savestate testado) e cor→companhia **RESOLVIDO 19/08** (`world.read_regional_leaders`/`read_rivals`, CALIBRATION.md §29: faixa de cabeçalho da caixa 64x32 preenchida com a cor do líder, casada com a legenda LIDA DO FRAME — sem paleta chumbada); offset das outras 5 regiões continua pendente só no catálogo de glifos; drill-down por caixa continua não testado (risco de $276.000K). **CORREÇÃO 19/08:** o `A` que leva do Quarterly Report ao Regional Rankings é o da CADEIA DE FIM DE TURNO — por `Info→finance` o `A` não muda a tela (medido, §29.2). E os detectores por pixel (`on_regional_rankings_img`/`on_quarterly_report_img`) foram substituídos por estruturais (`rankings_cells_ok`/`on_quarterly_report_img2`, §29.1/§29.3) |
| **facilities** (4) | "Cultural Facilities" por região, 3 ícones ×0 — ligado a r0c5 (ver acima) | ✅ mapeado 17/08 |
| **victory** (5) | **Texto exato das condições de vitória** (é o placar do eval): <br>"VICTORY CONDITIONS: have a hub in every region · be #1 in passengers for the year in North America · be #1 in passengers in all regions · have a profit for the year" <br> + status por região (Europe/Africa/Middle East/Southeast Asia/Oceania/North America/South America), todos `N/A` no turno 1 <br> + rótulo do cenário "SUPERSONIC 2000-2020" | ✅ mapeado 17/08, `logs/action_space_map/info_victory.png` |

**Nota importante para o eval**: a condição "be #1 in passengers" é **por
ANO**, não por trimestre — o P&L/ranking anual só deve existir em relatórios
específicos (Regional Rankings, ainda não drilled). O texto de vitória bate
exatamente com a leitura já feita do jogo por fora (STATUS.md).

## r1c4 — Sistema (LEITURA/META, não é decisão de jogo)

**Investigado pela primeira vez 17/08**. Menu: `Save / Animation [On] / Sound
/ Message [Medium] / End Game`. "What shall we do?" — são preferências de
emulação/UI (velocidade de animação, volume, velocidade do texto) e duas ações
de meta-jogo (Save = salvar dentro do jogo, End Game = encerrar a partida).
**Nenhuma opção foi executada** (Save e End Game são irreversíveis/arriscadas
para a sessão do harness). Saída seca: 1x `B` volta directo ao menu principal
sem diálogo de confirmação — não há armadilha de "tela trava" aqui.

Não entra no action space do modelo (não afeta economia/rede).

## r1c5 — Passar o turno (DECISÃO) / esperar — ✅ CONFIÁVEL (ETAPA 1, 17-18/08)

| # | Item | Status |
|---|---|---|
| F1 | Passar o trimestre | ✅ implementado, **detector = contador de trimestres da RAM** (`world.QUARTER_ADDR = 0x259F`, +1 por trimestre) |
| F2 | Não fazer nada (esperar) | ✅ implementado |

**Correção do detector.** O sinal era "o caixa mudou" — e ele mede tarde: nem
caixa nem contador se atualizam antes de a cadeia de relatórios ser
atravessada (MEDIDO em 3 turnos, CALIBRATION §24). Quem lia cedo concluía "o
turno não passou", redisparava o r1c5 e passava um trimestre extra sem contar.
O contador ainda distingue **virou 1** de **virou 2** — pulo agora é falha
explícita.

**Aceite:** 6 chamadas → 6 trimestres a partir de `eval_single_2000_lv5.state`
(181 → 187, APR.2000 → OCT.2001), com a data confirmada **pelos pixels** da
barra do menu em 6/6 e 1 disparo de r1c5 por chamada. Repetido em
`probe_hub_open_sa.state`: 6/6 (186 → 192). Logs em `logs/etapa1/`.

**Armadilha cara mapeada aqui (CALIBRATION §25):** a cadeia de fim de turno
pode parar numa caixa de decisão **(YES NO)** de patrocínio — "Rep. of EC …
$372000K is requested. Will you back this Project?", cursor em YES. Medido:
`A` = **−372.000K**; `B` e `Right`+`A` = 0. `world.yesno_prompt` detecta a
caixa e `Executor.dismiss_to_menu` **proíbe o A** enquanto ela estiver na
tela. Aceitar patrocínio é decisão de modelo e só entra como ação depois de
calibrado o que o dinheiro compra — **não medido**.

**Comprimento da cadeia (só B, savestate com rota+hub):** 35, 38 e uma
> 51 toques. O teto de `dismiss_to_menu` subiu de 48 para 96 — era o teto que
derrubava 1 chamada em 6.

---

## 18/08 — ETAPA 9-Validar: resultado da eval real (ACEITE NAO ATINGIDO)

Objetivo: validar `pilot.SUPPORTED` (10 ações) numa partida real de 8 turnos,
aceite = "pelo menos 6 TIPOS diferentes de ação executados com efeito
verificado". Rodado `laguna-s-2.1-free` (unico modelo -free saudável no
health-check do dia — `longcat`, `nemotron`, ambos `ling` falharam o PING),
savestate `eval_single_2000_lv5.state`, `--fresh --no-fallback`.

**Bloqueio operacional prévio**: `launch.ps1` tinha um bug de path (ROM
relativa resolvida contra `-WorkingDirectory` do BizHawk, não do harness —
EmuHawk abria sem ROM, `--lua` nunca rodava, bridge nunca respondia). Fix
aplicado no próprio `launch.ps1` (ver CALIBRATION.md). Regra nova: **sempre
conferir `(Get-Process EmuHawk).MainWindowTitle` não-vazio logo após o
launch, antes de qualquer chamada de bridge** — título vazio = ROM não
carregou, esperar mais não resolve.

**Resultado**: 5 de 8 turnos decididos (processo encerrado pelo host de
execução aos ~60min, no meio da execução do turno 5 — não foi crash nem
exceção). Dos 4 turnos com execução completa, **8/8 ações executadas OK, 0
falhas** — mas o modelo só escolheu **3 tipos distintos** em 5 decisões:
`negotiate_slots` (8x), `wait` (5x), `open_route` (2x). Ficou com **0 ações**
nos turnos 2 e 3 (gastou os 4 negociadores já no turno 1; no turno 3 já
tinha 2 negociadores livres de novo e mesmo assim escolheu não agir).
`open_venture`, `open_hub`, `close_hub`, `ad_campaign`, `adjust_route`,
`return_slots` — nunca ESCOLHIDOS, então não há recusa do harness a
reportar para eles, só ausência de tentativa.

**Tipos com efeito VERIFICADO (testemunha na string de detalhe do
Executor, não só `ok:true`)**:
1. `negotiate_slots` — 7/7 OK, testemunha `funcionarios livres N -> N-1`.
2. `open_route` — 1 OK (testemunha `caixa 1212340K -> 1184130K (-28210K)`)
   + 1 FALHA correta (harness recusou 2 voos/sem para um destino com 1 slot
   livre só — não é bug).

`wait` teve 4/4 OK mas SEM efeito por definição — não conta como "tipo com
efeito verificado" (seria reproduzir a armadilha da Regra 2: taxa alta com
o jogo intocado = falha).

**Total: 2 tipos verificados, abaixo do aceite (>= 6).** Ver detalhe
completo, evidência linha-a-linha e achados secundários (parse_error 3/5,
banner MD5 não catalogado, timing por turno) em CALIBRATION.md ("ETAPA
9-Validar: resultado da validação em partida real").

**Veredito**: o gargalo não é o action space (as 10 ações em `SUPPORTED`
continuam calibradas e prontas — nada foi invalidado aqui) nem a execução do
Executor (8/8 sem falha nas ações tentadas). É a **diversidade de decisão do
modelo dentro do orçamento de turnos** combinada com o **limite de duração
de execução em background** (~60min não bastou para 8 turnos com
`laguna-s-2.1-free`, cuja latência variou 7s–190s por chamada e pediu
reparo de JSON em 60% dos turnos). Próxima tentativa: (a) rodar em pedaços
menores encadeados via `--run` no mesmo diretório verificando
`next_turn_number()` continua consistente, OU (b) partir de um savestate
mais avançado (`probe_hub_open_sa.state`: rota+hub já abertos) para tornar
`adjust_route`/`close_hub`/`open_venture` legais desde o turno 1, testando
a EXECUTABILIDADE dessas ações sem depender da diversidade de escolha do
modelo.

---

## Consolidado — o que ainda falta (sem marcar como "não investigado", só como pendência de execução)

1. **r0c4**: medir o efeito numérico de cada um dos 5 níveis (RAISE/MAXIMUM/
   MAINTAIN/REDUCE/STOP) por categoria — hoje só a navegação e os nomes estão
   confirmados.
2. ~~**r0c5**: executar 1 compra de verdade...~~ **FEITO 17/08** (2 compras
   reais, CALIBRATION.md §21). Achado: Info→facilities **não** incrementa na
   hora (venture fica em negociação por meses) — falta medir o momento em que
   incrementa, e falta mapear o catálogo de mais cidades além de Washington/
   Denver/Philadelphia.
3. **r1c1**: medir o fluxo de SUCESSO (precisa: 1 venture comprado na região
   + nenhuma guerra em curso) — hoje só as duas recusas estão medidas.
4. ~~**r1c3→finance**: navegar até uma caixa de região...~~ **PARCIAL 17/08**
   (ETAPA 8-LerRanking): tela "Regional Rankings" alcançada e detectores
   calibrados (ver CALIBRATION.md); falta OCR do número/marcador por região —
   drill-down para dentro de uma caixa não foi tentado (risco de confirmar
   compra às cegas na mesma cadeia de menus).
5. **r0c1**: executar de fato Susp/Model/Planes/Flts/Fare num savestate
   descartável para medir efeito (hoje só a navegação pelas abas está
   confirmada); Close não deve ser testado sem plano de recuperação (é
   destrutivo).
6. **B2/B3**: nº de slots no lance e efeito de Area/Type/Wait no prazo de
   negociação — pendência antiga (CALIBRATION §16), não deste rewrite.
7. **Venda de aeronave (World Lease, dentro de r0c3)**: virar macro
   executável (CALIBRATION §16).

## Evidência (arquivos desta sessão, 17/08)

`logs/action_space_map/` — screenshots de r0c5 (business venture, 4 tipos),
r1c0 (hub: mensagem de sucesso "preparations... underway in Havana"), r1c1
(2 recusas), r1c2 (reunião completa), r1c4 (menu sistema), r0c1 (abas de
edição), Info→victory, Info→finance(rankings), Info→facilities.
Savestates novos: `states/probe_route_sa01.state` (negociação SA01 em
andamento), `states/probe_hub_open_sa.state` (rota + hub abertos na América
do Sul, caixa $1.138.020K, Jul/2001 — reutilizável para medir r0c1/r1c1 de
sucesso sem repetir a espera).
