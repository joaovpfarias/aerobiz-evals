# Calibração das Ferramentas de Ação

**Princípio (crítica do usuário, 11/08/2026, e ela está certa):** nenhuma macro entra no eval sem uma medição que prove que *"o modelo pediu X"* resulta em *"o jogo ficou com X"*. Sem isso, o eval mede o ruído do harness, não a estratégia do modelo.

Toda constante abaixo é **medida** ou está marcada como **NÃO CALIBRADA**.

---

## Estado de calibração por ferramenta

| Ferramenta | Parâmetro | Status | Evidência |
|---|---|---|---|
| Cursor do mapa | posição | ✅ **recalibrado 12/08** | RAM `0x257F`/`0x2581`, **offset (0,0)** — o antigo (−3,−3) mirava coordenada ímpar, inalcançável (passo = 2px). Sprite desenhado com canto sup. esq. no valor da RAM; janela de acerto medida por sweep de 16 posições. Ver INVENTARIO §12.1–12.2 |
| Cursor do mapa | ativação | ✅ **calibrado 12/08** | morto até um **A** de reconhecimento; o 1º toque após o A ainda é engolido. `world.activate_cursor()` detecta pela RAM, não por suposição |
| Caixa | leitura | ✅ **calibrado** | RAM `0x25F9` × 10; batido contra a tela em 3 savestates |
| Fim de turno | detecção | ✅ **calibrado** | mudança do caixa; verificado em turnos consecutivos |
| Menu principal | detecção | ✅ **calibrado 12/08** | pixels vermelhos em `(4,183)–(70,199)`: **108** no menu, **0** nas demais telas. Substitui o "aperta B e torce" |
| `open_route` | destino | ✅ **provado 12/08** | 2 rotas abertas: caixa −16.200K e −18.900K, rotas desenhadas no mapa, slots caem 1 em cada ponta |
| `open_route` | **pré-requisito** | ✅ **medido 12/08** | o jogo **recusa** destino sem slots ("We don't have any slots in X"). Slots do savestate do eval em `world.EVAL_SLOTS_2000` |
| `open_route` | **aircraft_index** | ✅ **CALIBRADO 19/08 (§31)** | **1 toque = próximo modelo**, lido de volta da tela a cada toque. O seletor cicla **só pelos modelos que possuímos**, na ordem de `Info->fleet`: com 1 modelo TODOS os toques são no-op (medido 0..8 em `eval_single_2000_lv5`); com 2 (`_buy_entregue`) alterna MD100/A340. Índice fora do ciclo agora é **recusa**. Evidência: `logs/etapa3a/idx_right.json`, `idx2.json` |
| `open_route` | **fare_level** | ✅ **CALIBRADO 12/08** | **1 toque = 5% sobre a média**, linear em 4 pontos: 0→`average fare` $490, 1→`5% above` $514, 2→`10% above` $538, 4→`20% above` $586. Evidência: `logs/calib/cal_voos.png` (rota Washington–Denver) |
| `open_route` | **flights_week** | ✅ **CALIBRADO 12/08** | **1 toque = +1 voo**, começando em 1: 0→1, 1→2, 2→3, 4→5. **Cada voo consome 1 slot EM CADA PONTA** (SLOTS 1/34→5/34 e 1/12→5/12) — mecânica não documentada antes. Evidência: `logs/calib2/cal_voos.png` |
| `open_route` | **planes** | ✅ **CALIBRADO 19/08 (§31)** | **1 toque = +1 avião** (base 1) — mas só toque a toque com frame estável; o `_bump` em lote do executor **perdia metade dos toques** (k=0..5 → 1,2,2,3,3,4). Teto = unidades **disponíveis** do modelo (6), sem dar a volta. Lido por mini-atlas do `x N` + conferido pela piscina. Evidência: `logs/etapa3a/seq_qty.json` |
| `negotiate_slots` | cidade | ✅ | negociação inicia |
| `negotiate_slots` | **nº de slots** | ✅ **CALIBRADO 19/08, CORRIGIDO 23/08 (§32, §36)** | **1 toque `Right` = +1 slot**, base 1, **teto = N posições do medidor, N MUDA POR CIDADE** (NA06=2, NA02=3, NA05/NA14/EU11/SA01/ME01/AF01=5), sem wrap (toques 5..8 não mexem). Lido de volta a cada toque pelo **medidor de bonequinhos** (`world.read_slots_qty`, px = 215+22·(N−1)); OCR não serve (diálogo fora da grade 8×13). 5 slots custam a MESMA espera declarada que 1 (tela idêntica byte a byte). Evidência: `logs/etapa3b/qR_qty_*.png`, `qR8_qty_*.png` |
| `negotiate_slots` | **funcionário** | ⛔ **NÃO É ALAVANCA — medido 19/08 (§32.3)** | `Area/Type/Wait` é a MISSÃO corrente, não perícia: painel = 0 px para os 4 na base, 856 px depois do despacho. Três funcionários → mesma duração declarada, texto byte a byte idêntico. `employee` **não entra** no schema |
| Distâncias entre cidades | estimativa | ❌ **ERRADA** | ver §2 |

## §0 CORREÇÃO de §1 e §3 (12/08) — remapeado no savestate do eval

**§1 estava errado: não existe tela separada de distância/custo.** O fluxo tem
**5 telas**, e a distância vem no *cabeçalho* da primeira (`Washington ◁ 1500MI ▷ Denver`).
O que quebrava a macro não era um passo a mais — era que **o jogo engole os A's
durante a datilografia**: foram necessários **7 A's para 5 transições**. Contagem
fixa de A's nunca ia funcionar. `Executor._step()` agora aperta A **até a pergunta
mudar** (hash do recorte `(62,152,232,188)`).

**§3 estava errado:** NA14 = Philadelphia, mas **não temos slots lá neste cenário** —
o custo de "$10.000K" foi lido no cenário 1970. Custos reais medidos aqui:
Washington→Denver (1500 mi) = **$16.200K**, Washington→San Francisco = **$18.900K**.

Detalhes e evidência: `logs/run_f0/INVENTARIO_TELAS.md` §12.

## §1 O fluxo de rota tem mais passos do que eu mapeei

A calibração capturou telas que não deveriam existir na minha sequência. O fluxo real é:

```
r0c0 → "Choose destination" → seleciona cidade
 → tela de rótulo da cidade
 → TELA DE DISTÂNCIA E CUSTO: "Washington ⇄ Philly | Distance: 120 mi | Cost: $10000K"   ← eu não sabia
 → "What type of plane" → ... (demais passos)
```

Consequência: minha macro apertava A um número fixo de vezes assumindo 5 passos. Com um passo a mais, cada A cai numa tela diferente da pretendida — os "sliders" que eu achava estar ajustando eram outra coisa.

## §2 As distâncias estimadas por pixel estão erradas (~40%)

O jogo informa **Washington ⇄ Philly = 120 mi**. Minha estimativa por pixels dava **168 mi** para a mesma rota. A escala foi calibrada num único par (Washington–Denver = 1500 mi) e não generaliza — a projeção do mapa não é linear.

**Impacto no eval:** o modelo recebe distâncias erradas e decide alcance de aeronave com base nelas. Precisa sair do estado até ser medido de verdade.

**Solução:** a própria tela de distância/custo dá o valor **real** por par de cidades. Percorrer os pares uma vez e tabelar → tabela exata, sem estimativa.

## §3 Dado novo obtido de graça

- **NA14 = Philly** (Filadélfia), 120 mi de Washington, custo de abertura **$10.000K**
- A tela de custo permite ao modelo saber o **preço antes de confirmar** — informação econômica que hoje ele não tem

## §4 Protocolo de calibração (aplicar a toda ferramenta nova)

1. Aplicar N incrementos (N = 0, 1, 2, 4) a partir de um savestate fixo
2. Capturar a tela resultante **uma única vez** (calibração é offline; produção não usa imagem)
3. Ler o valor efetivo e derivar `toques → unidade`
4. Gravar a constante aqui, com a evidência
5. Só então a ferramenta pode ser oferecida ao modelo no prompt

**Regra de segurança:** ferramenta não calibrada **não entra no `SUPPORTED`** do piloto. É preferível o modelo não ter a alavanca a ter uma alavanca que faz outra coisa.

## §4b PROVA DEFINITIVA: "100% de execução" era um número vazio (11/08, run `eval_A_laguna`)

A run reportou **10 turnos, 58 ações, 100% de execução, 11 rotas abertas, 11 negociações**. As evidências do próprio jogo dizem o contrário:

| Evidência | Leitura |
|---|---|
| Caixa: 1.220.000 → 1.208.230K, caindo ~1.600K/turno de forma constante | É só custo operacional. Uma rota custa $5-10M — 11 rotas teriam derrubado o caixa em ordens de grandeza |
| Cidades com slots detectadas no mapa: **0** | Nenhuma negociação concluiu, nenhum slot foi obtido — **linha revista em 15/08, ver nota abaixo** |
| Placar: as **7 regiões seguem `N/A`** | Zero progresso nas condições de vitória |
| Caixa idêntico nos turnos 8, 9 e 10 | O `end_turn` parou de avançar e ninguém percebeu |

**Conclusão:** as macros rodam até o fim e retornam `True`, mas **não produzem efeito no jogo**. A "taxa de execução" media *"a macro não quebrou"*, não *"a ação aconteceu"*.

**NOTA DE CORREÇÃO (15/08)** sobre a linha "0 cidades com slots": o detector foi
reverificado e **funciona** — o menu principal é o mapa da região, e a leitura
offline de `logs/prova_ic/b_final.png` devolve os 5 slots corretos da América do
Norte. Duas cegueiras medidas explicam zeros legítimos: cidade sob o cursor e
**cidade ligada por rota** (ponto verde + rótulo da rota cobrem o dígito). Ainda
assim as outras três evidências desta tabela (caixa, placar, caixa congelado)
sustentam sozinhas a conclusão da §4b: as ações não estavam acontecendo.

**Correção obrigatória antes de qualquer eval:** toda ação precisa de uma **verificação de efeito** — comparar o estado do jogo antes e depois e só reportar sucesso se mudou o que deveria mudar (rota: caixa cai e a rota aparece; negociação: funcionário sai da base; turno: caixa muda). Sem isso o eval produz números com aparência de rigor e conteúdo nulo — que é exatamente o pior resultado possível para um projeto cuja razão de existir é medir.

## §5 Pendências de calibração

- [ ] Remapear o fluxo completo de rota passo a passo (incluindo a tela de custo)
- [ ] Calibrar planes / flights_week / fare_level
- [ ] Calibrar aircraft_index contra o modelo exibido
- [ ] Tabelar distância e custo reais por par de cidades (substituir a estimativa por pixel)
- [ ] Calibrar nº de slots e escolha de funcionário na negociação
- [ ] Mapear e calibrar `buy_aircraft`, `route_edit`, orçamentos


---

# MEDIDO 15/08 — o mundo inteiro ligado ao executor (criterio de aceite)

## §6 Frota do savestate do eval: a constante estava ERRADA

`FLEET_START` descrevia a frota do cenario **1970** (DC9-30 1500 mi + B707-320
5560 mi). O savestate do eval (cenario 4 / 2000) tem outra coisa:

| Evidencia | Leitura |
|---|---|
| `logs/prova_ic/frota_2000.png` (Info->fleet) | `MD100 | In Use 0 | Avail 6 | Order 0` — **um unico modelo** |
| `logs/prova_ic/fleet_NA06_00.png` (tela de aviao) | MD100, **4680 mi**, 200 assentos, 6 disponiveis |

Isso ia direto para o prompt do piloto: o modelo lia um B707-320 de 5560 mi que
a companhia **nao possui** e era instruido a comparar alcance com essa constante
inventada. Corrigido: `FLEET_1970` (historico) e `FLEET_EVAL_2000` (medido);
`FLEET_START` aponta para o do eval.

## §7 `aircraft_index`: NAO e uma alavanca — MEDIDO

Na tela "What type of plane", 4 toques em Right a partir do estado inicial
produzem **5 capturas com hash identico** (`logs/prova_ic/fleet_NA06_00..04.png`,
recorte (0,20)-(256,150)). O seletor cicla apenas os modelos **que a companhia
possui**; com um unico modelo nao ha o que ciclar.

Consequencia: `aircraft_index` sai do `schema.ACTIONS` junto com `from` e
`aircraft` (que a macro sempre ignorou). O schema exigia `aircraft: str` e
rejeitava `aircraft_index` como parametro desconhecido, enquanto o prompt do
piloto mandava usar `aircraft_index` — o modelo estava sendo instruido a emitir
exatamente o que a validacao rejeitava. Escolha de aeronave so volta a existir
quando `buy_aircraft` for implementado.

## §8 Distancias REAIS (substituem a estimativa por pixel, §2)

Lidas no cabecalho da tela de aviao (`Washington <| N MI |> destino`) — unica
fonte exata:

| Rota | Distancia lida |
|---|---|
| Washington–Philadelphia (NA14) | 120 mi |
| Washington–Denver (NA06) | 1500 mi |
| **Washington–Havana (SA01)** | **1180 mi** |

Em `world.MEASURED_DIST_FROM_HOME`; o catalogo do prompt passa a trazer
`dist_from_home_mi_real` (exata, so onde medida) ao lado da estimativa.

## §9 Prazo de negociacao: varia por cidade (MEDIDO)

| Cidade | Prazo na tela | Trimestres ate o funcionario voltar | Slots obtidos |
|---|---|---|---|
| EU11 Bruxelas | 6 meses | 2 (`painel staff 517px -> 0px`) | 0 -> **1** (tela de detalhe: `7/102`, coluna Federal = 1) |
| SA01 Havana | 9 meses | 3 (`597px -> 0px`) | 0 -> **1** (`1/96`) |

Qual das 4 colunas da tela de detalhe e a nossa foi resolvido lendo NA13 como
referencia: Washington mostra `34/116` com **34 na primeira coluna** e 0 nas
outras — e sabemos que temos 34 slots la. Logo **a primeira coluna e a Federal**.

## §10 Recusa por ALCANCE: tela nova, detector novo

Com 1 slot ja em Bruxelas, a rota Washington->Bruxelas **ainda e recusada**:

> "We don't have any aircraft capable of flying such a great distance."
> (`logs/prova_ic/msg_EU11_00.png`)

E uma tela **azul, sem mapa e sem o painel do aviao** — `on_map_screen()` da
False nela, entao o executor seguia apertando A e so quebrava tres telas depois,
reportando "fluxo travou na tela de voos/semana". Sintoma longe da causa.

Detector medido no recorte (8,24)-(248,120): painel cinza `(123,123,140)` =
**5552 px** na tela do aviao, **0** na tela de recusa (que e 100% azul
`(57,75,173)`, 23040 px). Implementado como `world.on_plane_screen()`; o
executor agora recusa na hora, com screenshot, e restaura o savestate de guarda.
Verificado ao vivo que a acao **seguinte** nao e contaminada: apos a recusa de
EU11, `open_route NA06` abriu normalmente (-16.560K).


## §11 Rota consome aeronave (MEDIDO, 1 ponto)

`Info->fleet`: `In Use 0 / Avail 6` antes, `In Use 1 / Avail 5` com uma rota
aberta nos parametros padrao (1 aviao, 1 voo/semana). Teto de 6 rotas
simultaneas com a frota do eval. NAO medido: o efeito do parametro `planes` > 1.


---

# MEDIDO 15/08 — `buy_aircraft` (comando r0c3) CALIBRADO

Probes: `harness/probe_buy.py` (mapeamento e ciclo dos seletores) e
`harness/prova_buy.py` (compra pelo caminho do piloto, `Executor.run`).
Capturas em `logs/buy/`. Tudo a partir de `states/eval_single_2000_lv5.state`.

## §12 O que foi medido

| Parametro | Resultado | Evidencia |
|---|---|---|
| **Fabricante** | 1 toque **Right** = proximo, **ciclo de 6** | `logs/buy/mk_labels.png`: MDC, Boeing, World Lease, Airbus, Tupolev, Ilyushin, e o 7o volta a MDC |
| **Modelo** | 1 toque **DOWN** = proximo modelo. **Right/L nao fazem nada** (7 capturas com hash identico) | `logs/buy/md*_Down_*.png` |
| **Quantidade** | 1 toque **Right** = +1 aviao, base 1, **teto 10** | `logs/buy/qty_right.png` (0 toques -> 1, 1 -> 2, 2 -> 3, 3 -> 4, 4 -> 5) e a tela "You can order a maximum of 10 planes" |
| **Preco** | linear na quantidade | tela `Cost: 5 / $550000K` para o A340 de $110.000K (`logs/buy/s5_qtd.png`) |
| **Pagamento** | **debita o caixa NA HORA**, no YES de "N plane(s) will cost $X. Is this OK?" | ver §12.3 |
| **Entrega** | **1 trimestre** ("Please wait about 3 months for delivery") | `Info->fleet`: Order 1 -> Avail 1 apos UM `end_turn` (`logs/buy/frota_depois_A340.png` -> `frota_turno1.png`) |

### §12.1 Catalogo (alcance, assentos e preco LIDOS DA TELA)

| idx fabricante | Fabricante | idx modelo | Modelo | Alcance | Assentos | Preco | Producao |
|---|---|---|---|---|---|---|---|
| 0 | MDC | 0 | MD11 | 7750 mi | 360 | $81.600K | 1991 |
| 0 | MDC | 1 | MD12 | 8000 mi | 400 | $96.000K | 1995 |
| 0 | MDC | 2 | MD100 | 4680 mi | 200 | $28.800K | 1998 |
| 1 | Boeing | 0 | B747-400 | 7180 mi | 550 | $135.000K | 1989 |
| 1 | Boeing | 1 | B777 | 5500 mi | 360 | $54.000K | 1995 |
| 2 | **World Lease** | — | **canal de VENDA**, nao de compra | — | — | — | — |
| 3 | Airbus | 0 | A340 | **8870 mi** (o maior do catalogo) | 330 | $110.000K | 1993 |
| 4 | Tupolev | 0 | Tu204 | 2870 mi | 210 | $28.600K | 1989 |
| 5 | Ilyushin | 0 | IL96-300 | 6870 mi | 300 | $49.500K | 1988 |

**CAVEAT de validade temporal:** os precos foram lidos em **2000/2001**. O
preco de revenda do MD100 se moveu de $20.880K para $20.520K em poucos
trimestres, entao os precos de COMPRA provavelmente tambem derivam ao longo do
cenario de 20 anos. O gate de efeito nao depende disso (ele so afirma que o
caixa CAIU), mas a pre-checagem `caixa < custo` e a assercao
`delta == tabela` da fase `chain` estao carimbadas em 2000. **NAO MEDIDO:**
como o preco evolui com o ano.

Em `world.AIRCRAFT_CATALOG`. O indice 2 **nao vende avioes**: a tela pergunta
"Which model are you trying to sell?" e mostra a NOSSA frota (MD100 por
$20.520-20.880K, valor que oscila). MEDIDO ao vender: caixa **+20.520K** por
unidade; o seletor limitou a venda a 3 por visita mesmo com 6 disponiveis.

### §12.2 Fluxo (5 perguntas, 6 confirmacoes)

```
r0c3 -> "Which manufacturer would you like to visit?"   [caixa de RODAPE]
  A -> "Nice to meet you. Which model are you interested in?"  [caixa do TOPO]
  A -> descricao do modelo + (YES NO)
  A -> "You can order a maximum of 10 planes. How many do you want?"
  A -> "N plane(s) will cost $X. Is this OK?" + (YES NO)
  A -> "Thank you very much. Please wait about 3 months for delivery."  <- COBRA
  ... e o jogo VOLTA para a tela de modelo. Saida: 7 toques de B.
```

### §12.3 Verificacao de efeito: numeros

Todas por `Executor.run` (o caminho que o piloto chama), numa cadeia unica
intercalada com rotas:

| Acao | Caixa antes | Caixa depois | Delta | Preco de tabela x qtd |
|---|---|---|---|---|
| `buy_aircraft MD11 x1` | 1.220.000K | 1.138.400K | **-81.600K** | 81.600 |
| `open_route NA06` | 1.138.400K | 1.122.200K | -16.200K | — |
| `buy_aircraft B777 x2` | 1.122.200K | 1.014.200K | **-108.000K** | 2 x 54.000 |
| `buy_aircraft MD100 x1` | 1.014.200K | 985.400K | **-28.800K** | 28.800 |
| `open_route NA03` | 985.400K | 966.500K | -18.900K | — |

E `A340 x1`: 1.220.000K -> 1.110.000K (**-110.000K**), com `Info->fleet`
passando de `MD100 0/6/0` para `MD100 0/6/0` + `A340 0/0/1` (coluna Order)
e, um trimestre depois, `A340 0/1/0` (`logs/buy/frota_depois_A340.png`,
`logs/buy/frota_turno1.png`). `buy_aircraft` entrou em `EFEITO_CUSTA_CAIXA`.

Recusas testadas (`prova_buy.py wrong`): modelo inexistente, `qty` fora de
1..10 e caixa insuficiente sao barrados ANTES de abrir o comando — entrar na
tela de recusa por falta de caixa deixaria o fluxo num estado nao mapeado.

## §13 aircraft_index NA TELA DE ROTA — a §7 estava ERRADA

A §7 concluiu "nao e alavanca" a partir de 5 capturas com hash identico. Duas
causas somadas produziram esse resultado, e **nenhuma** era a inexistencia da
alavanca: (a) a frota tinha um unico modelo, entao nao havia o que ciclar;
(b) os toques eram emitidos durante a datilografia e **engolidos**.

MEDIDO com dois modelos na frota (MD100 x6 + A340 x1) e `wait_text` antes dos
toques (`logs/buy/acidx_NA06_Right_*.png`):

| aircraft_index | Aviao na tela |
|---|---|
| 0 | MD100 — 4680 mi, 200 assentos, 6 disponiveis |
| 1 | A340 — 8870 mi, 330 assentos, 1 disponivel |
| 2 | MD100 (da a volta) |

**Regra:** `aircraft_index` = posicao do modelo na tabela `Info->fleet`,
1 toque Right = proximo, com volta ao fim. **Continua FORA do prompt do
piloto**: o harness ainda nao le `Info->fleet`, entao nao teria como dizer ao
modelo a que aviao cada indice corresponde — indice sem legenda e alavanca
cega, que e exatamente o que a regra de seguranca da §4 proibe.

## §14 RESULTADO NEGATIVO: comprar aviao NAO abre a Europa neste savestate

O motivo declarado da tarefa era o muro de alcance (INVENTARIO §13.3). O teste
foi feito e **falhou**, o que e um dado, nao um erro de execucao:

1. `buy_aircraft A340` (8870 mi, o maior alcance do catalogo) — entregue,
   `Info->fleet`: `A340 | In Use 0 | Avail 1`;
2. `negotiate_slots EU11` (Bruxelas) concluida em 2 trimestres;
3. `open_route EU11` -> **"We don't have any aircraft capable of flying such a
   great distance."** (`logs/buy/eu_msg.png`).

Para descartar a hipotese "o jogo so olha o aviao do indice 0 (MD100)",
vendi os MD100 pelo World Lease ate o A340 ficar no topo da frota e repeti:
**mesma recusa**.

O que foi MEDIDO e so isto, e ja basta: **a rota e recusada com a aeronave de
maior alcance do catalogo entregue e livre, e recusada de novo com ela no
indice 0**. Concluir dai um numero ("a distancia interna e >8870 mi") seria
inferir a partir de uma string de recusa — o jogo nunca mostra o valor, e a
mesma mensagem pode estar cobrindo uma regra que eu nao isolei. A escala entre
continentes fica **NAO CARACTERIZADA**.

**Consequencia:** `buy_aircraft` remove o teto de 6 rotas (cada rota consome
1 aeronave) e da ao modelo uma decisao economica de verdade (alcance x
assentos x preco), mas **nao** desbloqueia a condicao de vitoria "hub em toda
regiao" partindo de Washington. Isso precisa constar de qualquer resultado do
eval.

## §15 Tres bugs do harness que so apareceram aqui (corrigidos, com evidencia)

**a) `at_main_menu_img` dava FALSO POSITIVO no showroom.** O teste era so
"pixels vermelhos da placa da companhia >= 40"; a tela de compra com o pedido
montado marca **77**. Efeito medido: o executor dava a compra por encerrada
ainda dentro do showroom e a leitura seguinte de `Info->fleet` mandou
"Left x6, Up x2, Down, Right x3" para o **seletor de fabricante**, reabrindo a
Airbus. Corrigido: exige vermelho **E** terra (o menu principal E o mapa da
regiao — `land_pixels` 2266 no menu, **0** em 5 telas do fluxo de compra).

**b) O seletor de fabricante e PEGAJOSO.** Nao volta para MDC ao reabrir o
comando. Uma sequencia que assumia inicio em MDC e dava "Right x2" caiu na
Airbus e **comprou 5 A340 por $550.000K** (caixa 1.123.880K -> 573.880K,
`Order 5` na frota). Corrigido: o executor **le** o fabricante na tela
(`world.read_maker_idx`, mascara binaria do texto do rotulo) e anda
`(alvo - atual) mod 6`; se nao conseguir ler, aborta em vez de adivinhar.

**c) Verificacao de `negotiate_slots` dava FALSO NEGATIVO.** Ler o painel
`Info->staff` logo apos "I will begin negotiations." devolve 0px mesmo com a
negociacao iniciada (reproduzido 2/2 a partir de `_buy_entregue.state`; a
mesma leitura repetida segundos depois deu 517px). Corrigido: a leitura
insiste ate 3 vezes antes de declarar fracasso. Falso negativo descarta uma
negociacao paga — e tao corrosivo quanto o falso positivo que a §4b denuncia.

Duas armadilhas de recorte, do mesmo tipo (hashear pixel que nao e o dado):

- o hash do TEXTO da compra precisa das **duas** caixas de dialogo (o fluxo
  troca de layout no meio: mapa de fabricantes usa o RODAPE, showroom usa o
  TOPO). So com o topo, `wait_buy_text` retornava na hora e os toques eram
  engolidos — pedir A340 chegava na tela do MD11;
- o hash do PAINEL do aviao precisa parar em x=150: a metade direita mostra as
  **unidades que possuimos**, campo dinamico. O mesmo MD100 hasheia diferente
  com 6 e com 5 unidades, e a compra abortava dizendo que a tela era de outro
  aviao — com "MD100" escrito nela.

## §16 O que continua NAO CALIBRADO

- **escala de distancia entre continentes** (§14): so sabemos que
  Washington-Bruxelas > 8870 mi na conta do jogo;
- `planes` (numero de aeronaves por rota) e o numero de slots do lance;
- **venda de aviao** (`World Lease`): o fluxo foi percorrido e o caixa subiu
  +20.520K por MD100, mas nao virou macro nem foi calibrado (limite de 3 por
  visita observado uma unica vez);
- `aircraft_index` esta calibrado mas **fora do prompt** ate o harness ler
  `Info->fleet` (§13).


---

# MEDIDO 16/08 — a 2a negociacao do turno: CAUSA RAIZ e correcao

Probes: `harness/diag_neg2.py` (reproducao pelo caminho do piloto),
`harness/probe_staff_pick*.py` (calibracao do seletor), `harness/probe_regiao4.py`
(ciclo de regiao). Aceite: `harness/prova_neg_multi.py [a|b|c]`.
Capturas em `logs/neg2/`, `logs/staffpick/`, `logs/reg4/`, `logs/neg_multi/`.

## §17 O jogo diz o motivo em voz alta: "Sorry, I'm busy"

O sintoma era `cursor do mapa nao respondeu` dentro de `activate_cursor`. A causa
esta **tres passos antes**, e a captura no momento exato da falha
(`logs/neg2/03_apos_A3.png`, `04_apos_A4.png`) mostra a frase do jogo:

> **"Sorry, I'm busy making a bid for some airport slots."**

`_do_negotiate_slots` apertava **2 A's as cegas** assumindo que o destaque
estava sobre um funcionario disponivel. Depois da 1a negociacao o funcionario 0
esta EM MISSAO; o A cai nele, o jogo recusa e **nao sai da tela de staff**. Os
A's seguintes morrem ali, o `_select_city` e chamado numa tela que nao e mapa e
so entao aparece o erro — sintoma longe da causa, como na §10.

Medido: 4 A's seguidos, 4 telas de staff (`mapa=False` nas quatro).

## §17.1 Seletor de funcionario — CALIBRADO

| Item | Medida | Evidencia |
|---|---|---|
| Destaque | retangulo **vermelho puro (255,0,0)**, 448 px, **NAO pisca** | 8 leituras identicas em `logs/staffpick/blink_*.png` |
| Grade | `x ∈ {98,146,194}`, `y ∈ {9,73}`; celula 51x67 | bbox do destaque em cada posicao |
| Movimento | **1 toque = 1 celula, SEM wrap** (satura na borda) | `Right` x6 a partir de (0,0): 1 movimento; `Down` x3: 1 movimento |
| Pegajoso? | **NAO** — reabrir o comando devolve o destaque a (0,0) | `logs/staffpick/b_reabre.png` |
| Funcionarios | **4**, no bloco 2x2: (0,0) (0,1) (1,0) (1,1) | crachas |
| **Celula (1,2)** | **NAO e funcionario**: pousar nela troca a acao para **Return** e o A abre *"Return which city's slots?"* | `logs/staffpick/c_celula5.png` e `c_celula5_apos_A.png` |

A celula (1,2) e a armadilha cara desta tela: uma negociacao que virasse
**devolucao de slots** destruiria a partida em silencio. Por isso o executor le
`staff_action_is_bid()` (Bid destacado = 359 px laranja `(198,97,66)` na caixa de
Bid; Return destacado = 297 px na dele) e **aborta** se nao for Bid.

## §17.2 Cracha = funcionario NA BASE (sinal de disponibilidade)

Figurinha vermelha `(189,0,41)`, **23 px**, no canto inferior direito da celula.
Ao ser despachado o cracha **sai da celula e reaparece sobre o mini-mapa**,
marcando o destino:

| Estado | Crachas nas celulas | Onde foi o que sumiu |
|---|---|---|
| savestate do eval | 4 (todas as celulas) | — |
| apos negociar em Bruxelas | 3 (falta a (0,0)) | `(35..39, 23..30)`, sobre a Europa |

`world.staff_free_cells(img)` -> lista de celulas com cracha. Validado offline
nas duas capturas acima e ao vivo nos tres aceites.

## §17.3 Contador de funcionarios livres LIDO DO MENU PRINCIPAL (novo gate)

Os "bonecos" da barra inferior do menu sao os funcionarios **na base**, 23 px
cada, desenhados da esquerda para a direita:

| Estado | px em `(72,170)-(115,190)` | Livres |
|---|---|---|
| 0 negociacoes | **92** | 4 |
| 1 negociacao | **69** | 3 |

`world.free_staff_menu(img)`. **Substitui o painel `Info->staff` como gate de
efeito de `negotiate_slots`** — e a correcao de um falso negativo latente: o
painel Area/Type/Wait descreve **apenas o funcionario destacado** (sempre o 0),
entao quando quem sai e o 2o ou o 3o o painel **nao muda** e a acao seria
reprovada mesmo tendo funcionado. O contador da barra e cumulativo, por acao, e
sai de graca (o menu ja e fotografado).

### §17.3-bis CORRECAO 24/08 — esse contador NAO e oraculo de `return_slots`

O 3 -> 3 (+0) registrado aqui para `return_slots` nao media a acao: quem
despacha funcionario e `negotiate_slots` (§17.2). Devolver slot e transacao
imediata e nunca recrutou ninguem, entao "livres +1" era **falso por
construcao**. Oraculo correto = `our_slots` do PAINEL DA CIDADE (§33.8), lido
por `city_probe.inspect` antes e depois.

Com o oraculo honesto, `return_slots` **SAIU de `pilot.SUPPORTED`** (24/08):

| Corrida | Cadeia de confirmacao | Tela final | Nossos slots NA06 | Caixa |
|---|---|---|---|---|
| 1 | 1 `A` | pergunta **ainda aberta** "Will you give back 1 slot to" | 12 -> 12 | 1.220.000K parada |
| 2 | ate 6 `_step()` c/ parada no menu (remendo do `close_hub`) | **volta ao mapa** de selecao, textbox vazia; travou em A5 | 12 -> 12 | 1.220.000K parada |

Savestate `eval_single_2000_lv5`, NA06/Denver com 12 slots nossos e ZERO rotas
(nada ocupado, entao nao e a recusa "currently being used"). Evidencia DURAVEL:
`harness/logs_etapa2/etapa2_vivo.log` (corrida 1, `SEM EFEITO — nossos slots
12 -> 12`) e `harness/logs_etapa2/etapa2_vivo_r2.log` (corrida 2, `travou no
passo A5`). O PNG `logs/suite/return_slots/return_slots_NA06_confirmado.png` e
**por corrida e se sobrescreve** — nao serve de citacao historica.
Hipotese **NAO testada** (nao entra no estado, R1): o cursor do YES/NO de
"give back 1 slot" pode estar em **NO** por padrao — o executor nunca mediu
esse cursor, so assumiu YES. `_do_return_slots` continua no executor, guardado
(le a recusa do jogo por hash da TEXTBOX, exige queda medida, restaura estado);
o modelo e que nao pode mais pedi-la.

### §17.3-ter `adjust_route`: oraculo agora le Flts/Fare DE VOLTA

O oraculo antigo so conferia "1 Rte antes e 1 Rte depois" e passava com o Flts
pedido 1->3 travado no TETO da rota, sem ninguem ler o campo. Agora
`world.read_route_summary()` le `flights` e `fare_pct` do resumo (r0c1) reaberto
do zero. Regra: **lido == pedido**, OU **lido == teto E o teto foi declarado
pelo executor e confirmado na tela**; campo ilegivel = NAO MEDIDO = reprova.
Aceite ao vivo (`probe_hub_open_sa`, rota SA01): pedido Flts 1->3,
`TETO em 1 (0/2 toques efetivos)` declarado e **lido de volta = 1**;
Fare mid->high **lido de volta = +10% (12 segmentos) == pedido**; 1 Rte
preservada. O ramo `lido == pedido` do Flts NAO foi exercitado (SA01 tem teto 1).

## §17.4 `switch_to_region`: os DOIS PRIMEIROS R sao engolidos

Descoberto ao rodar 3 negociacoes em regioes diferentes: a 3a morria com
`mapa ficou na regiao 3, esperado 4`. `probe_regiao4.py` percorreu o ciclo uma
tecla por vez no mapa da negociacao:

```
R x0: land=2266 r0 | R x1: 2266 r0 | R x2: 2266 r0   <- as duas primeiras teclas nao andam
R x3: 1018 r1 | R x4: 2073 r2 | R x5: 879 r3 | R x6: 1128 r4 | R x7: 326 r5 | R x8: 613 r6
```

A versao antiga mandava `passos` R's **em lote** e so relia no fim; com teclas
engolidas ela ficava atras do alvo e **cada nova tentativa perdia mais uma**,
travando na regiao anterior. Corrigido para **malha fechada: um R, uma leitura**,
ate `tries = 2*total+4`. Assim a tecla engolida custa uma iteracao, nao a acao.

## §17.5 Aceite (16/08) — tudo por `Executor.run`, a partir do savestate do eval

**A — a sequencia que reproduzia o bug: 4/4, `retries_fired = 0`**

| Acao | Resultado | Efeito medido |
|---|---|---|
| `negotiate_slots EU11` | True | funcionario (0,0); **livres 4 -> 3** |
| `negotiate_slots SA01` | True | funcionario (0,1); **livres 3 -> 2** |
| `open_route NA06` | True | caixa 1.220.000K -> 1.203.800K (**-16.200K**) |
| `open_route NA02` | True | caixa 1.203.800K -> 1.187.600K (**-16.200K**) |

**B — 3 negociacoes em REGIOES diferentes no mesmo turno: 3/3, `retries_fired = 0`**

EU11 Bruxelas (Europa, func. (0,0)) -> SA01 Havana (America do Sul, (0,1)) ->
**ME01 = Tashkent, Uzbequistao** (Oriente Medio, (1,0)). Livres **4 -> 3 -> 2 -> 1**;
a tela de negociacao no fim mostra **um unico cracha**, em (1,1), e **tres
bonecos no mini-mapa** sobre Europa, Caribe e Asia Central
(`logs/neg_multi/faseB_tela_neg_final.png`). Dado novo de graca: a tela de
detalhe de ME01 traz **Tashkent / Pop 2.4M / Econ 68 / Total slots 0/57**.

**C — regressao mista (negociar + comprar aviao + rota + negociar): 4/4**, para
provar que a mudanca em `switch_to_region` nao quebrou os outros fluxos
(`buy_aircraft MD100 x1` -28.800K, `open_route NA06` -16.200K).

O contador `Executor.retries_fired` existe para que um "4/4" **nao possa** ser
creditado ao retry de cursor: se ele tivesse disparado, a causa raiz nao estaria
corrigida. Nos tres aceites ele ficou em **0**.

## §17.6 O que isso muda no prompt do piloto

`build_state` passa a expor `company.negociadores_livres` (lido da barra do
menu). Sem isso o modelo pedia uma 5a negociacao sem ter quem enviar e queimava
a acao — a mesma classe de erro do "estado inventado pelo harness" que ja tinha
travado um modelo por 8 trimestres. Com 0 livres a acao e recusada **antes** de
tocar no emulador, com o motivo correto.

## §17.7 Continua NAO CALIBRADO nesta tela

- **quantos slots** pedir no lance (a tela "How many slots?" e aceita no padrao);
- **qual funcionario** escolher por merito: o executor pega o **primeiro livre**;
  os 4 tem Area/Type/Wait proprios e o efeito disso no prazo **nao foi medido**;
- **Return** (devolver slots): a tela foi identificada e isolada por seguranca,
  mas nao virou macro.

## §18 `adjust_route` (r0c1, Flts/Fare) — CALIBRADO 17/08

Ação nova: `adjust_route(route, flights_week?, fare_level?)`, implementada em
`executor.py::_do_adjust_route`. Alvo do dia: dar ao modelo uma forma de
corrigir uma rota já aberta em vez de só criar rotas novas.

**Fluxo medido** (evidência `logs/edit_commit/a_..n_*.png`,
`logs/edit_sa/*.png`):

```
route_edit -> resumo da rota (A) -> barra de abas (A, cursor começa em Model)
  -> Right/Left até a aba alvo -> A ativa o campo -> Right/Left ajusta
  -> A confirma o campo (volta à barra, AINDA sem persistir)
  -> Right até SET -> A -> "Is it OK to change this flight as shown?"
     (YES/NO, cursor em YES) -> A COMMITA e volta ao resumo
```

**Alavanca de Flts e Fare = A MESMA da criação** (r0c0, §linha 21-22):
1 toque = +1 voo/semana; 1 toque = +5% de tarifa. Confirmado ao vivo:
Fare $720→$792 com 2 toques ("10% above avg." exato, igual à criação);
Fare $410→$450 com 2 toques na rota de Havana.

**Persistência confirmada por round-trip real**: depois de `SET`+YES, saída
completa até o MENU PRINCIPAL (6x `B`) e reabertura de `route_edit` mostraram
Fare $792/10% e Flts 2 intactos (`logs/edit_commit/n_reopen_summary.png`) —
não é um buffer de tela que se perde ao sair da aba.

**Barra de abas — 7 células fixas, leitura calibrada por brilho**:
`Susp, Close, Model, Planes, Flts, Fare, SET` — a célula destacada fica mais
clara; brilho médio por célula (`ROUTE_TAB_BOUNDS` em `executor.py`) acertou
5/5 contra screenshots com destaque conhecido. Sem wrap constatado (parado em
SET, 2 toques extras de Right não voltaram a Susp).

**CORREÇÃO ao ACTION_SPACE.md antigo**: a 7ª célula (`"S...T"` empilhado
verticalmente) tinha sido lida como "SEL(ECT), volta à lista de rotas" —
hipótese nunca testada. Medição real: é **SET**, o botão de commit
("Is it OK to change this flight as shown?"). A navegação entre múltiplas
rotas abertas **não foi encontrada** e segue não mapeada — por isso
`adjust_route` **recusa** quando há mais de uma rota aberta, em vez de supor
qual delas o jogo está mostrando.

### TETO DE Flts — medido, NÃO caracterizado

O campo Flts para de aceitar `Right` sem nenhum aviso na tela, bem aquém do
alcance da aeronave:
- Washington–Havana (1180mi, MD100): teto **1** voo/semana. Testado também
  com `Planes` subido de 1→3 (via aba Planes) — teto continuou em 1, ou seja
  **não escala com nº de aviões**.
- Washington–San Fran (2430mi, MD100): teto **2** voos/semana (Planes=1, não
  testado com mais aviões).

Não é distância (a rota mais longa tem teto MAIOR, contra-intuitivo) nem nº
de aviões (medido, não muda). Hipótese aberta: slots livres no destino
(Havana mostrava `1/1` na linha SLOTS contra `1/9` de San Fran) — NÃO
confirmada, porque negociar mais slots leva ~6 meses in-game e não dá para
verificar no mesmo turno. Fica como está: `on_plane_screen`/alcance
intercontinental (§14) — recusa real, mecanismo não caracterizado.

**Consequência para quem for pedir esta ação**: um alvo de "+2 voos/semana"
pode ser fisicamente impossível na rota escolhida. `_do_adjust_route` NUNCA
finge que chegou lá — ele detecta o teto por hash do recorte do dígito
(`FLTS_VALUE_BOX`) e relata o valor REALMENTE alcançado, com a nota
"TETO em N (M/D toques efetivos)".

### ARMADILHA MEDIDA: recorte com elemento animado dá falso positivo

A primeira versão de `FLTS_VALUE_BOX` (`(215, 118, 245, 136)`) incluía a
borda pontilhada do topo do popup do campo, que **pisca a cada frame** —
o mesmo padrão de armadilha documentado em `_step()` sobre as setinhas do
slider ("hash da tela inteira NÃO serve"). Com essa borda dentro do recorte,
o hash do "valor" mudava a cada screenshot mesmo SEM nenhum toque de
`Right`, e a detecção de teto reportou `"Flts: 1 -> 3 (2 toques)"` com a
tela mostrando `1` o tempo todo (comparação feita contra
`logs/adjust_aceite/z_final_summary.png`, capturada no MESMO run). Corrigido
isolando só o dígito: `FLTS_VALUE_BOX = (218, 124, 233, 136)`, validado
3x parado (hash idêntico) + 2x com `Right` no teto real (hash idêntico,
correto) — `logs/adjust_aceite/stable*.png`.

### Evidência de aceite (dois casos, via `Executor.run()` real)

- `prova_adjust.py` — Washington-Havana (`probe_hub_open_sa.state`): Fare
  mid→high confirmado ($410→$450); Flts pedido 1→3, teto real em 1
  (reportado corretamente, sem mentir sobre o estado do jogo).
- `prova_adjust_sf.py` — Washington-San Fran (`_edit_2rotas.state`): Flts
  1→2 (1 toque, dentro do teto) **e** Fare mid→high ($720→$792) confirmados
  juntos na mesma ação, persistência lida da tela após reabrir `route_edit`.

Ambos sem custo de caixa (edição de rota não debita na hora, igual ao lance
de slots — `adjust_route` fica FORA de `EFEITO_CUSTA_CAIXA`).

**Falta**: Susp/Close (destrutivo, não testado), navegação entre múltiplas
rotas, caracterizar o teto de Flts.

### Correção 2 (mesma sessão): leitor de aba errava Susp/Close e SET-em-repouso

A 1a versão de `ROUTE_TAB_BOUNDS`/`_route_tab_index` (soma R+G+B média,
bounds estimados por olho num zoom em escala) nunca tinha sido testada contra
Susp/Close nem contra um frame com SET **não** destacado. Ao validar por
sugestão de revisão:

- os bounds estimados cortavam Susp/Close no meio — um `Left` real que
  destacou **Susp** (confirmado visualmente,
  `logs/tabguard/susp_zoom.png`) foi lido como **Close**;
- a célula SET tem letras brancas fixas ("S/E/T" empilhadas) que sozinhas
  erguem a soma R+G+B mesmo sem destaque — qualquer aba genuinamente
  destacada com brilho parecido perdia para SET no argmax (medido: Flts e
  Fare destacados foram lidos como `set`).

Corrigido com bounds exatos (lidos pixel a pixel nos divisores escuros,
`logs/tabguard/susp_tab2.png`) e amostra de **uma linha acima do texto**
(`ROUTE_TAB_ROW_Y = 8`) do canal **G** isolado (destacado ~103-107,
não-destacado ~41-52, folga grande mesmo para SET fora de foco — G=52).
Validado **7/7** contra as 7 células com destaque conhecido, agora incluindo
Susp e Close. `prova_adjust.py` e `prova_adjust_sf.py` re-rodados depois da
correção — mesmos resultados corretos de antes (a correção não muda o
comportamento observável nos dois casos já provados; fecha um buraco de
segurança que não tinha sido exercitado por eles, já que nenhum dos dois
navega perto de Susp/Close).

## §19 `suspend_route` e `close_route` (r0c1, Susp/Close) — BUG REPORT (18/08)

⚠️ **AMBAS NAO FUNCIONAM** — removidas de `pilot.SUPPORTED` em 18/08.

Ações implementadas em `executor.py::_do_suspend_route` e `executor.py::_do_close_route`,
mas ambas contêm o **mesmo defeito de lógica** que `open_venture` tinha ($144.000K de lição em §21).

### Causa raiz

Após ativar a aba (Susp ou Close), o jogo abre uma **tela de seleção de mundo** (world map com cursor).
As macros atuais usam um `A` cego que não acerta no alvo, resultando em "All flights listed" ou estado
indeterminado. A navegação até a aba é correcta (`_route_tab_index` confirma), mas a ativação assume
um diálogo YES/NO que **não existe**.

**Evidência:**
- `logs/close_debug/1_apos_nav_para_close.png`: aba Close corretamente destacada (destaque lido como índice 1)
- `logs/close_debug/2_apos_A_ativar_close.png`: world map com "1 route will be closed." no footer
- `world.on_map_screen(img)` = True (é tela de seleção, não diálogo)
- `world.yesno_prompt(img)` = None/False (confirma: sem YES/NO box)
- `logs/close_comparison/DEPOIS_close_rota_sumiu.png`: rota **permanece idêntica após close_route retornar True**

A coluna "Rotas (harness)" da tabela original era `ex.routes` (lista Python que o próprio executor mutila),
não o estado do jogo — circular, e por isso o bug não foi apanhado na revisão.

### Fluxo CORRETO (conforme `open_venture` §21)

```
route_edit -> resumo (A) -> barra de abas (A)
  -> Left para Susp OU Right para Close
  -> A ativa a aba -> world map ("1 route will be closed")
  -> activate_cursor() [cursor dorminhoco ate um A ativador]
  -> point_cursor_at_world(origem_ou_destino_da_rota)
  -> EXATAMENTE 1 A sobre a rota/cidade (nao usar _select_city que martela A)
  -> volta ao menu principal
```

### O que precisa ser corrigido

1. Capturar a tela de mundo após a aba e confirmar com `on_map_screen()`
2. Chamar `activate_cursor()` (para sair do estado morto)
3. Usar `point_cursor_at_world(origem)` para alinhar no alvo
4. **Dar EXATAMENTE 1 A** — não usar `_select_city` cega
5. Testar com ambos os savestates (antes e depois) para medir efeito real

Esperado após correção: `logs/close_comparison/DEPOIS_...` mostraria lista vazia (0 rotas).

### Status

- Removidas de `pilot.SUPPORTED` (18/08) — Regra 3 proíbe alavancas não-calibradas
- Implementação mantida em `executor.py` como **rascunho**, marcada com TODO
- Esperado: próxima sessão implementa seguindo template `_do_open_venture` (linhas 739-747)

## §20 `set_budget` (r0c4, Repair/Ad/Service) — ⚠️ CORREÇÃO 18/08

⚠️ **TABELA DE REPAIR (17/08) É FALSO-POSITIVO** — removida até revalidação com script corrigido

Nova ação: `set_budget(category, level)`, implementada em
`executor.py::_do_set_budget`. Trata-se de ajustar os orçamentos de três
categorias operacionais do jogo.

**Causa raiz do falso-positivo:**

O script `calib_budget_fixed.py::goto_col_order()` usa **apenas Down** para navegar.
Se o savestate começava em MAXIMUM (idx 0), as primeiras 3 ordens não mudavam nada:
- level 0 (MAXIMUM): 0 Downs → [110K, 110K, 110K]
- level 1 (RAISE): 1 Down → [muda para RAISE]
- level 2 (MAINTAIN): 2 Downs → [muda para MAINTAIN]
- level 3 (REDUCE): 3 Downs → $100K ✓
- level 4 (STOP): 4 Downs → $90K ✓

Tabela publicada: [110K, 110K, 110K, 100K, 90K] = 3 falsos + 2 verdadeiros

**Tentativas de Ad em 18/08 (logs 00:47, 00:54, 01:03):** navegação falhando ou
tela sendo deixada cedo. Não há calibração válida de Ad nem Service ainda.

**Fluxo e navegação (versão CORRIGIDA 18/08):**

```
r0c4 -> "Change which budget?" (tela com 3 colunas: Repair/Ad/Service)
  Right/Left -> muda coluna (ciclo 3, malha fechada: 1 tecla + 1 leitura)
  A -> "What are your orders?" (popup com 5 níveis)
  Down -> proxima ordem (malha fechada: 1 tecla + 1 leitura)
  A -> "Are you sure you want ... ?" (confirmacao)
  A -> volta para "Change which budget?"
  B x6 -> volta ao menu principal
```

**Ordem dos níveis: MAXIMUM (0) -> RAISE (1) -> MAINTAIN (2) -> REDUCE (3) -> STOP (4)**

Confirmado pelo rótulo que muda a cada aplicação (hashes em `world.BUDGET_LABEL_MD5`).

**Coluna (categoria) mapeamento:** Repair=0, Ad=1, Service=2 (lido pelo rótulo laranja no cabeçalho)

**Efeito IMEDIATO — não espera end_turn:**

| Coluna | Level 0 (MAX) | Level 1 (RAISE) | Level 2 (MAINTAIN) | Level 3 (REDUCE) | Level 4 (STOP) |
|---|---|---|---|---|---|
| **Repair** | $110K | $110K | $110K | **$100K** (-10K) | **$90K** (-20K) |
| **Ad** | (não rodado ainda) | — | — | — | — |
| **Service** | (não rodado ainda) | — | — | — | — |

Lido por `world.read_budget_money()` que faz OCR dos dígitos no campo "$XXXK" de cada coluna.

**Efeito verificado em dois sinais:**
1. Mudança do rótulo (label text hash) — confirma a ordem foi lida
2. Mudança do valor em $K — confirma foi aplicada (não apenas lida)

**Pré-requisito:**
- Estar no menu principal
- Nenhuma validação semântica (qualquer categoria/level 0-4 é aceito)

**Pós-requisito:**
- Retorna ao menu principal (verificado com `at_main_menu_img`)
- Efeito persiste entre turns (não testado ainda com drift, pendente)

**Status do aceite (17/08, calib_budget_fixed.py sweep 0):**
- Repair coluna: 5/5 ordens testadas (MAXIMUM, RAISE, MAINTAIN, REDUCE, STOP)
- Valores lidos corretamente (Repair: 110K→110K→110K→100K→90K)
- Rótulos confirmados (labels: ['maximum','raise','maintain','reduce','stop'])
- A ação entrou em `pilot.SUPPORTED`

**Pendências:**
- Ad e Service (colunas 1 e 2): sweep não completou (file lock, re-rodar)
- Drift test: confirmar que os níveis se mantêm após vários turnos
- Investigar se o efeito real no cash flow aparece nas contas do trimestre


## §21 `open_venture` (r0c5, Business Venture) — CALIBRADO 17/08 AO VIVO

ETAPA 5-Venture. Nova ação: `open_venture(city, type_index=0)`, implementada
em `executor.py::_do_open_venture`. Segundo motor de receita do jogo (linha
própria "Business Sales" no P&L, nunca lida ainda pelo harness).

**Fluxo medido ao vivo (probe_venture2..10.py, evidência em `logs/run_f0/
v2_*.png` .. `v10_*.png`):**

```
buy_sell -> funcionario livre (Buy/Sell, mesma geometria de r0c2/r1c0)
  -> A ate sair do mapa (3-4 A's, VARIAVEL)
  -> point_cursor_at_world(cidade)
  -> 1 A SOBRE A CIDADE abre DIRETO a tela de tipo, ja no tipo 0, com
     "Which business venture will you purchase?"
  -> Right cicla tipo/preço da cidade (SEM WRAP); Left/Up/Down SEM EFEITO
  -> A confirma o tipo -> "You must negotiate...Is this OK?" (YES/NO)
  -> A confirma de novo -> CAIXA DEBITADA NA HORA
```

**ARMADILHA MEDIDA (custou $144.000K de verdade na 1a tentativa,
`probe_venture.py`, Washington):** o helper genérico `_select_city` martela A
até sair da tela do mapa. Nesta tela específica isso **ultrapassa a seleção
de tipo** e responde YES ao "(YES NO)" sem que nenhum Right tenha sido dado
— comprou Concert Hall (tipo 0 default) sem escolha. `_do_open_venture` por
isso NUNCA usa `_select_city`: dá exatamente 1 A sobre a cidade e para ali.

**Catálogo NÃO é fixo/universal — varia por cidade (achado novo, não
documentado antes):**

| Cidade | tipo 0 | tipo 1 | tipo 2 | tipo 3+ |
|---|---|---|---|---|
| Washington (NA13, home) | Concert Hall $144.000K | Grand Hotel $288.000K | Commuter Airline $576.000K | **sem tipo 3 — "City Hotel" NÃO aparece aqui**, sem wrap (medido `probe_venture10.py`: Left/Up ficam presos no tipo 0; Right some do tipo 2 em diante) |
| Denver (NA06) | **Arts Pavilion $27.000K** (nome fora do catálogo antigo de 4 tipos) | não explorado | — | — |
| Philadelphia (NA14) | Concert Hall **$126.000K** (preço diferente do de Washington para o MESMO tipo) | não explorado | — | — |

A tabela antiga do ACTION_SPACE.md (Concert Hall/City Hotel/Grand Hotel/
Commuter Airline, todos os 4 sempre disponíveis) **estava errada** — muito
provável que tenha vindo de uma cidade não identificada, ou de uma sessão
anterior sem savestate de referência. `type_index` é POSIÇÃO no catálogo
DESSA cidade, não um tipo fixo — o modelo não pode pedir "City Hotel" por
nome, só por índice, e o índice pode significar coisas diferentes em cidades
diferentes.

**Verificação de tipo sem OCR:** `world.venture_type_hash()` (crop
`VENTURE_TYPE_BOX = (0,130,256,150)`, a linha "Nome $PreçoK") — o executor
martela Right no máximo 3x por passo e só avança `type_index` quando o hash
muda de verdade; se não mudar, conclui que a cidade não tem mais tipos e
recusa (não martela às cegas além do catálogo real).

**Efeito verificado — DOIS sinais independentes (mesmo padrão do hub §r1c0):**

| Teste | Cidade/tipo | Caixa antes → depois | Funcionários livres | Resultado |
|---|---|---|---|---|
| Compra real 1 (via probe, `_step` cru) | Washington, tipo 0 (Concert Hall) | 1.184.900K → 1.040.900K (**-144.000K**, bate exato com o preço mostrado) | 4 → 3 | ✅ |
| Compra real 2 (via `Executor.run()`, API pública) | Denver, tipo 0 (Arts Pavilion) | 1.184.900K → 1.157.900K (**-27.000K**, bate exato) | 4 → 3 | ✅ |
| Recusa (type_index além do catálogo) | Washington, tipo 5 pedido (só 3 existem) | intocado (restore) | intocado | ✅ recusa limpa, `_restore_guard()` confirmado |

**Debito é IMEDIATO apesar do texto "It will take N months"** — igual ao
hub: a negociação demora, o pagamento não.

**Venture comprado NÃO conta imediatamente** — medido com DOIS oráculos
independentes, ambos ANTES e DEPOIS da compra real (Washington):
- `Info→facilities` (3 ícones "Cultural Facilities"): `x0 x0 x0` antes E
  depois da compra (`logs/run_f0/venture_facilities_before.png` vs
  `venture_facilities_apos_compra_real.png`, idênticas);
- `r1c1` (campanha de anúncio): recusa **"There are no businesses in our
  North American network to promote."** tanto antes quanto **imediatamente
  depois** da compra (`venture_ad_before.png` vs
  `venture_ad_after_imediato.png`, mesma recusa).

Ou seja, a compra fica "em negociação" (mesmo padrão de `hubs_pending`) — mas
**RESOLVIDO 18/08 (ETAPA 5-Venture, retomada)**: a negociação leva **1
turno só**, não "meses" como se temia. Ver subseção seguinte.

### RESOLVIDO 18/08 — contador de facilities sobe em 1 `end_turn`, e `r1c1` tem fluxo de sucesso

A partir de `states/_venture_comprado.state` (Concert Hall comprado em
Washington, caixa 1.040.900K→ver nota abaixo), `_probe_ad1.py` deu **1**
`g.end_turn()` e reabriu `Info→facilities`:

- ANTES (compra recém-feita): `x0 x0 x0` (`logs/run_f0/
  venture_facilities_apos_compra_real.png`).
- **DEPOIS de 1 end_turn**: `x0 x0 x1` — um dos 3 ícones sobe para `x1`
  (`logs/run_f0/ad1_facilities_pos1turno.png`; mapeamento ícone→tipo de
  venture NÃO medido — não assumir que é "o ícone do Concert Hall" sem
  testar com um único tipo por vez).

**Reverificado 18/08 em 2ª sessão, ao vivo, com o emulador (não só lendo o
print salvo):** carreguei `_venture_comprado.state` e `_venture_pronto.state`
e li `world.read_quarter_index` (RAM `0x259F`) nos dois — **181 → 182,
exatamente 1 trimestre**, confirmando que o `end_turn` do probe passou
exatamente 1 turno (não mais, não menos) entre os dois estados. Cash
1.040.900K → 1.040.220K (**-680K**, abaixo da faixa 1.550K-3.910K medida na
ETAPA 1 para custo de navegação por trimestre — não é a mesma configuração
de rotas/hub daquela medição, então a faixa antiga não se aplica
diretamente aqui, mas fica registrado como ponto não totalmente explicado).
Também reabri `Info→facilities` a partir de `_venture_pronto.state` nesta
sessão (`g.info_screen("facilities", ...)`) e o resultado bateu pixel a
pixel com o print antigo: `x0 x0 x1`
(`logs/run_f0/verify18_facilities_pronto.png`). Ou seja o
`ventures_pending`→pronto do pendências abaixo tem resposta mensurada
**duas vezes, em sessões diferentes**: **1 trimestre** (não meses) entre a
compra e a contagem em Info→facilities, para este caso (1 venture, sem
fila). Ainda não medido se comprar 2+ ventures na mesma janela muda esse
prazo.

**Segundo oráculo, mesmo savestate + end_turn (`_probe_ad2.py`/
`_probe_ad3.py`, salvos como `states/_venture_pronto.state`):** com o
venture já contando, `r1c1` (ad_campaign) **deixa de recusar** e completa o
fluxo até o fim:

```
r1c1 -> seletor de funcionario -> "We will sponsor cultural events at our
  facilities." (logs/action_space_map/ad3_step4.png)
  -> tela "Culture and Arts": Standard Expense $1.800K, Promotion Expense
     $1.800K, "Chance for Success average" (ad3_step5.png)
  -> "Are you sure you want to run this Culture and Arts campaign?" YES/NO
     (ad3_step6.png)
  -> A confirma -> "I'll get right on it." (ad3_step7.png)
```

Caixa: $1.040.220K -> $1.038.420K, **-1.800K exatos** (bate com "Standard
Expense" mostrado — o harness escolheu a opção default sem cotovelo extra,
não testado se `Right`/outra tecla troca Standard<->Promotion antes de
confirmar). Isso fecha as DUAS pendências marcadas abaixo como abertas em
17/08: `ventures_pending`/prontidão tem prazo medido (1 turno), e `r1c1`
tem fluxo de sucesso completo e caixa validada. `r1c1` ainda não tem macro
própria em `executor.py` (`_do_ad_campaign` não existe) — os 3 probes usam
`Executor._step()` cru; entrar em `pilot.SUPPORTED` fica para quando a
macro for escrita.

**Estados salvos:** `states/_venture_guard.state` (antes de qualquer compra,
2 rotas NA + cash 1.184.900K), `states/_venture_comprado.state` (Concert
Hall comprado, Washington), `states/_venture_cityhotel.state` (não usado —
City Hotel nunca foi alcançado em Washington, ver tabela acima),
`states/_venture_pronto.state` (Concert Hall comprado + 1 end_turn already
passado — facilities em `x0 x0 x1`, ponto de partida pronto para testar
`r1c1` sem repetir a compra+turno; **provenance**: `_probe_ad2.py` salvou
este state a partir do processo BizHawk ainda vivo do `_probe_ad1.py`
anterior, não de um `load()` — reverificado 18/08 e confirmado consistente
(quarter=182, facilities=`x0 x0 x1`), mas trate como "estado vivo de
sessão", não como checkpoint derivado de outro savestate por load limpo).

**Entrada em `pilot.SUPPORTED`:** `open_venture` (17/08). `ad_campaign`
ainda não tem macro (ver acima).

**Pendências (na época, 17/08):**
- Escrever `_do_ad_campaign` em `executor.py` e entrar em `pilot.SUPPORTED`
  (fluxo já medido e reproduzível, falta só a macro).
- Mapear catálogo de mais cidades (só Washington tem os 3 tipos + preços
  totalmente enumerados; Denver e Philadelphia só tiveram o tipo 0 visto).

### RETOMADA 18/08 (2ª sessão) — City Hotel ENCONTRADO, e é uma categoria diferente de Concert Hall

**Survey sem gasto** (`survey_venture.py`, guard=`_venture_guard.state`, B
solta a tela ANTES do YES/NO — testado: caixa idêntica em NA01/NA04/NA07 do
início ao fim do survey, `1.184.900K` constante) cobriu 3 cidades novas da
América do Norte (nenhuma delas testada em 17/08):

| Cidade | tipo 0 | tipo 1 | tipo 2 | tipo 3 |
|---|---|---|---|---|
| Vancouver (NA01) | **City Hotel $54.000K** | Ferry $270.000K | — | — |
| Los Angeles (NA04) | Arts Pavilion $27.000K | (tela intermediária, não lida limpa) | Grand Hotel $216.000K | Catering Service $162.000K |
| Dallas (NA07) | Arts Pavilion $31.500K | Shuttle Service $126.000K | (3º tipo, não lido) | — |

**"City Hotel" existe** (refuta a suspeita de 17/08 de que a tabela antiga
tivesse inventado o nome) — mas o **preço estava errado**: `$54.000K` em
Vancouver, não `$72.000K`. Preço variável por cidade confirmado outra vez
(mesmo padrão de Concert Hall $144.000K Washington / $126.000K
Philadelphia). Screenshots: `logs/run_f0/survey_NA01_t0.png` (City Hotel),
`survey_NA01_t1.png` (Ferry), `survey_NA04_t1..t3.png`, `survey_NA07_t0..t1.png`.

**Compra real executada** (`buy_cityhotel.py` + `buy_cityhotel_cont.py`, API
pública `Executor.run({"action":"open_venture","params":{"city":"NA01","type_index":0}})`,
a partir de `_venture_guard.state`): caixa **1.184.900K → 1.130.900K, exato
−54.000K** batendo com o preço mostrado (`logs/run_f0/venture_tipo0_NA01.png`
mostra "City Hotel $54000K" / "I will begin negotiations..."). Funcionários
livres 4→3 (mesmo padrão). Savestate: `states/_cityhotel_comprado.state`.

**ARMADILHA NOVA (custou uma sessão de confusão, não dinheiro): `ex.run({"action":"wait"})`
NÃO passa o turno.** `_do_wait` em `executor.py` é um no-op literal —
`return True, "sem acao neste trimestre"` — é a ação do PILOTO "não fazer
nada neste trimestre", não um comando de avançar turno. Quem avança o
turno é `Game.end_turn()` (macros.py, comando de menu r1c5, detector por
`read_quarter_index`). Rodar `ex.run(wait)` 3x manteve `quarter=181` fixo
(cash também não mudou, `1.130.900K` parado) — a 1ª tentativa de medir
"quantos turnos até o contador subir" mediu **zero turnos reais**, apesar
do log dizer "end_turn: True". Corrigido chamando `g.end_turn()` direto
(confirmado por `read_quarter_index`: 181→182→183→184, cash caindo
~300-680K/turno como esperado).

**RESULTADO — City Hotel NÃO conta em `Info→facilities` (Cultural
Facilities) mesmo após 3 trimestres reais**, ao contrário de Concert Hall
(que contou em exatamente 1 turno, §21 acima). Medido 2x, savestates
`_cityhotel_pronto.state` (0 e 1 turno, ambos `x0 x0 x0`,
`logs/run_f0/fac_antes_cityhotel.png` / `fac_depois_cityhotel_imediato.png`
/ `fac_depois_cityhotel_1turno.png` idênticas) e `_cityhotel_3turnos_real.state`
(3 turnos reais via `g.end_turn()`, ainda `x0 x0 x0`,
`logs/run_f0/rt_facilities_1turnos.png` .. `rt_facilities_3turnos.png`).
Segundo oráculo confirma: `r1c1` (ad_campaign) continua recusando "There
are no businesses in our..." depois dos 3 turnos reais
(`logs/run_f0/cityhotel_ad_apos3turnos.png`, cash `1.129.530K`).

**Conclusão nova**: "Cultural Facilities" (Info, tela dos 3 ícones) e a
elegibilidade de `ad_campaign` (r1c1) **rastreiam só o subconjunto
"cultural" do catálogo de venture** (Concert Hall/Arts Pavilion — medidos
contando), **não hotéis/hospedagem** (City Hotel/Grand Hotel — medido NÃO
contando mesmo após 3 turnos). O catálogo de venture tem pelo menos 2
categorias com efeitos de jogo diferentes; o harness ainda não tem uma
tela/oráculo que confirme quando um City Hotel "amadurece" (não descartar
que hotéis nunca aparecem em nenhuma tela de Info mapeada até agora — as 6
telas de `INFO` em `macros.py` são map/staff/fleet/finance/facilities/
victory, nenhuma chamada "Hotels"/"Tourism").

**Estados novos**: `states/_cityhotel_comprado.state` (compra feita, 0
turnos reais), `states/_cityhotel_3turnos_real.state` (+3 turnos reais via
`g.end_turn()`, o savestate correto para continuar essa investigação). Os
states intermediários gerados com `ex.run(wait)` (nomeados `_pronto`/
`_3turnos` sem `_real`, que mediam 0 turnos de verdade por causa da
armadilha acima) foram **deletados** para não confundir sessão futura.

**Pendências (atualizadas 18/08):**
- Escrever `_do_ad_campaign` em `executor.py` e entrar em `pilot.SUPPORTED`
  (fluxo já medido e reproduzível, falta só a macro) — ainda aberto.
- Achar ONDE (se existe) o jogo expõe o efeito de hotéis/lodging — nenhuma
  das 6 telas de Info mapeadas mudou em 3 turnos reais.
- Medir se o prazo de 1 turno para o contador de Cultural Facilities subir
  se mantém com 2+ ventures culturais comprados na mesma janela.

---

# IMPLEMENTADAS 17/08 (2) — ETAPA 6-Reversos (execução pendente)

Três macros reversas (destrutivas, com savestate de guarda):

## `_do_sell_aircraft` (r0c3, fabricante World Lease, indice 2)

**Medido anteriormente (CALIBRATION §12.1):**
- Preco de revenda varia ao longo do cenario (20.880K → 20.520K)
- Limite de 3 por visita observado (não investigado além)
- Oracle: caixa SOBE (delta = preco x qty), Info→fleet Avail N→N-1

**Implementação (executor.py `_do_sell_aircraft`):**
- Reusa `world.read_maker_idx` + malha fechada (alvo = 2 = World Lease)
- Navegação por modelo: NÃO testada (assume primeiro modelo exibido)
- Quantidade: Right = +1, base 1, limit 3
- Savestate em `_reverse_guard.state` (não GUARD compartilhado)
- Retorna (ok, mensagem com delta de caixa lido)

**Status:** Pronto para prova via `prova_sell_aircraft.py`

## `_do_return_slots` (r0c2, aba Return, ETAPA 6-Reversos)

**Medido (CALIBRATION §17.1):**
- Grade staff picker 2x2: (1,2) = Return (não funcionario)
- Navegacao sem wrap (Down + Right x2 de (0,0))
- `staff_action_is_bid()` guard: aborta se Bid destacado (297px Return vs 359px Bid)

**Implementação (executor.py `_do_return_slots`):**
- Navega para Return (Down 1x, Right 2x)
- Verifica que Return esta destacado
- Chama `_select_city` para navegação no mapa "Which city's slots will you return?"
- Confirma YES/NO (cursor em YES por padrao)
- Savestate em `_reverse_guard.state`
- Oracle: funcionarios livres (lido pela barra do menu)
- Retorna (ok, mensagem com delta livres)

**Status:** Pronto para prova via `prova_return_slots.py`

## `_do_close_hub` (r1c0, aba Close) — CALIBRADO AO VIVO 18/08 (ETAPA 12-HubsCompleto)

A especulação da ETAPA 6-Reversos (17/08, abaixo, riscada) estava ERRADA em
dois pontos centrais, achados ao vivo nesta etapa:

- ~~Pixels de "Close" destacado: hipotese Left de Open vai a Close~~ — FALSO.
  Testado sistematicamente (`_probe_close_visual6.py`, 7 combinacoes de
  d-pad): Left/Right/Up dentro da grade de fotos NUNCA tocam Open/Close. A
  geometria e IDENTICA a Return em r0c2 — coluna extra (col=2) fora da
  grade de staff, Open na linha 0 / Close na linha 1. De (0,0), `Down 1x +
  Right 2x` chega em (1,2)=Close (confirmado por `staff_action_is_bid()==False`
  + captura com "Close" destacado em laranja).
- ~~Oracle: funcionarios livres~~ — FALSO. Fechar hub NAO consome negociador
  (celula Close nao e funcionario); `livres_depois < livres_antes` e SEMPRE
  falso para essa acao. Pior: isso nao era so "gate fraco", era um BUG ATIVO
  — toda vez que o gate reprovava, `_restore_guard()` desfazia um close que
  tinha de fato acontecido no jogo (confirmado indiretamente: um close que
  "falhou" pelo gate antigo deixava o jogo recusando reabertura do MESMO hub
  com "You already have a regional hub", provando que o close real tinha
  ficado PRESO a meio caminho, nao desfeito pelo restore — ver armadilha
  abaixo).

**Cadeia real tem DUAS perguntas YES/NO, nao uma** (medido em
`_probe_close_extra_a.py`, savestate `_hub_rota_do_hub.state`: hub em
Havana/SA01 + rota Washington→Havana + rota Havana→Kingston/SA03 partindo
do hub):

```
A (celula Close)  -> "Are you sure you want to close the regional hub in Havana?" (YES/NO)
A (YES)            -> "1 regional hub and 1 route will be closed." (aviso, so info)
A                  -> detalhe por rota: "All flights listed above will be closed."
A                  -> "Are you sure you want to close?" (2a pergunta YES/NO, sobre a ROTA)
A (YES)            -> menu principal, caixa CREDITADA aqui
```

**ARMADILHA CARA** (custou 2 rodadas de calibracao errada nesta sessao): a
1a tentativa usou so 3 `_step()` (achando que 3 A's bastavam, por analogia
com `_do_open_hub`) e parou ANTES da 2a pergunta. `_ensure_menu()` nesse
ponto so aperta B, que numa tela YES/NO equivale a responder **NO** —
cancela o close inteiro EM SILENCIO (caixa fica em 0K de delta, tela volta a
parecer normal). O harness so descobriu o cancelamento indireto porque o
`open_hub` SEGUINTE recusou com "You already have a regional hub", nao
porque algum sinal direto acusou. Corrigido com uma cadeia de ate 6
`_step()` e parada antecipada assim que a tela vira o menu principal
(`world.at_main_menu_img`), NUNCA saindo por B enquanto uma pergunta YES/NO
puder estar pendente.

**Medido, nao suposto** (round-trip completo Havana, 1 hub + 1 rota que
partia dele):
- Caixa: **CREDITO de +$32.300K** no fechamento completo. NAO e o inverso
  exato da Construction Cost ($28.800K) — o valor provavelmente embute algo
  ligado a rota fechada junto; **nao reusar como constante fixa** sem
  recalibrar com outro par hub+rota.
- Funcionarios livres: inalterados (4→4) em toda a cadeia — close_hub NAO
  consome negociador.
- Cascata: TODA rota que PARTE do hub fechado e fechada junto (2 telas de
  texto confirmam). Rota que so CHEGA no hub (base→hub) sobrevive.
- Reabertura: com o close realmente commitado (caixa creditada), `open_hub`
  na MESMA regiao/cidade volta a funcionar IMEDIATAMENTE (sem passar
  turnos) e cobra a Construction Cost normal de novo (-$28.800K) — round-trip
  fechar+reabrir verificado via `Executor.run` puro em
  `_verify_close_hub_final.py` (sem atalhos manuais).
- Limite de 1 hub por regiao: reconfirmado (tentar abrir um 2o hub na mesma
  regiao, com ou sem hub de fato aberto, sempre esbarra em "You already have
  a regional hub in X").

**Implementação final (executor.py `_do_close_hub`):**
- Parametro: region (int 0-6) ou city (derivado)
- Navega para a regiao via `_goto_region`
- Abre r1c0, verifica `on_staff_screen`
- NAO chama `_pick_free_staff()` (a celula Close nao e staff; chamar essa
  funcao pousaria a navegacao relativa num ponto de partida errado sempre
  que o funcionario livre nao fosse o (0,0) — mesmo padrao de bug que
  `return_slots` evita nao escolhendo funcionario)
- Down 1x + Right 2x ate a celula Close, verifica `staff_action_is_bid()==False`
- Loop de ate 6 `_step()`, parando cedo se `at_main_menu_img` bater
- Oracle: `caixa_depois > caixa` (credito). Se nao subiu, `_restore_guard()`
- Em sucesso: remove o hub de `self.hubs` e as rotas cujo `from` for aquele
  hub de `self.routes` (cascata replicada na escrituracao do harness)

**Status:** CALIBRADO, em `pilot.SUPPORTED` desde 18/08 (ETAPA 12-HubsCompleto).

Evidencia: `logs/close_hub_full_18ago/extra_a/01.png..06.png` (cadeia
completa), `logs/close_hub_final_18ago/` (round-trip via Executor.run),
`harness/_probe_close_visual6.py` (geometria Down+Right+Right),
`harness/_probe_close_extra_a.py` (cadeia de 2 YES/NO + credito medido),
`harness/_verify_close_hub_final.py` (aceite final).

### Additions ao schema.py (17/08)

- `return_slots`: removido param `n` (nao calibrado)
- `close_hub`: novo ACTIONS com `region: int`, OPTIONAL_PARAMS `city: str`
- `validate_action`: suporta `open_hub` e `close_hub` com `city` alternativa

## Regional Rankings — leitura de tela (ETAPA 8-LerRanking, 17/08)

**Corrige** ACTION_SPACE.md linha 280 (`finance` (3) descrito como caindo
direto no ranking): medido ao vivo (`harness/probe_rankings.py`,
`eval_single_2000_lv5.state`) que `Info->finance` cai primeiro no
**"Quarterly Report \<mes\>\<ano\>"** (grafico de barras $ por companhia) e SO
um `A` depois disso avanca para **"Regional Rankings \<ano\>"** (mapa com
7 caixas por regiao + legenda das 4 companhias coloridas por colocacao).

**Confirmado que e ranking DE VERDADE** (nao estatico) em 2 momentos da mesma
partida — Apr2000 (trimestre 181) vs Jul2000 (trimestre 182):

| Regiao | Apr2000 | Jul2000 |
|---|---|---|
| N America | `17280#` | `34560#` |
| Oceania | `1848#` | `9048#` |
| Europe/SE Asia/Mid East/Africa/S America | caixa preta (sem dado ainda) | caixa preta |

A ordem da legenda de companhias (Federal/MetLink/AirRoma/Aussie) tambem
mudou entre os dois momentos — mais um sinal de que reflete colocacao real,
nao layout fixo.

**Calibrado (world.py):**
- `on_quarterly_report_img(img)` / `on_regional_rankings_img(img)` — distinguem
  as duas telas pelo pixel `(30,60)`: preto no ranking (caixa da Europa
  desenhada ali), teal `(41,123,173)` no relatorio trimestral. Validado contra
  as 4 capturas em `logs/rankings_probe/`.
- `REGIONAL_RANKINGS_BOXES` — bounding box aproximado das 7 caixas (por
  deteccao de retangulo preto), so para orientar recorte futuro.

**NAO calibrado (pendente, nesta sessao 17/08):**
- Numero de passageiros e cor do marcador do lider por regiao (precisa
  recorte fino em torno do texto/marcador, nao do centro da caixa, + OCR de
  digitos). Uma heuristica de "fracao de pixel preto na caixa" foi tentada e
  **descartada**: mesmo caixas com dado visivel ficam ~85-90% pretas (o
  numero ocupa pouca area), o limiar nao discriminou de forma estavel — nao
  ficou no world.py por nao bater com o proprio padrao de nao entrar
  constante nao verificada.
- Drill-down por caixa de regiao (A dentro do Regional Rankings): nao testado
  nesta sessao — risco documentado em `macros.py Game.end_turn`/
  `executor.py dismiss_to_menu` de que A demais nessa cadeia pode confirmar
  compras as cegas ($276.000K perdidos numa run anterior). Qualquer macro que
  drilar precisa savestate de guarda e verificacao de caixa a cada `A`.

Evidencia: `logs/rankings_probe/y1_00_map.png` (Quarterly Report Apr2000),
`y1_region0_A.png` (Regional Rankings Apr2000), `y2_00_map.png`/
`y2_region0_A.png` (mesmos, Jul2000). Script: `harness/probe_rankings.py`.

## ETAPA 8-LerRanking (18/08) — OCR do numero por regiao, SEM navegacao nova

Fecha a lacuna "NAO calibrado" acima: os 2 momentos ja capturados em 17/08
(`y1_region0_A.png` = Apr2000/trimestre 181, `y2_region0_A.png` = Jul2000/
trimestre 182, mesma partida) continham dado suficiente para OCR — nao foi
preciso religar o EmuHawk nem arriscar navegacao nova pela cadeia de A/B.

**O que foi medido:**
1. As 7 caixas tem um RETANGULO PRETO fixo (medido por componente conexo de
   pixel preto nas duas imagens): `world.REGIONAL_RANKINGS_BOXES` — agora com
   coordenadas EXATAS (substituem o "aproximado" de 17/08).
2. Quando uma caixa TEM dado, a faixa colorida do numero "come" as ~8-9
   linhas do topo do retangulo (deixam de ser pretas) — e por isso o
   retangulo preto de N America/Oceania comeca mais embaixo que o das 5
   caixas vazias. Esse deslocamento e o proprio sinal usado para reencontrar
   a faixa: `RANKING_ROW_OFFSET` = 9 (N America) / 8 (Oceania), MEDIDOS
   pixel a pixel contra a fonte de 8px (o offset errado nao le digito
   errado, so devolve `None` — o hash do glifo desalinha 1px e nao bate no
   catalogo, falha segura).
3. Catalogo de glifos dos 10 digitos + `#` (fim do numero), construido com a
   MESMA tecnica de `_bin_md5`/`BUDGET_GLYPHS` (hash do recorte binarizado,
   limiar 200), a partir dos UNICOS 4 numeros reais disponiveis: N America
   "17280#"->"34560#" e Oceania "1848#"->"9048#" — cobrem os digitos 0-9 sem
   nenhum conflito de hash entre posicoes/momentos diferentes.
4. `world.read_regional_rankings(img)` decodifica as 7 caixas e devolve
   `{regiao: int|None}`. `None` = caixa sem dado (preta) OU glifo fora do
   catalogo — nunca adivinha digito.

**ACEITE — validado em 2 momentos diferentes da mesma partida:**

| Regiao | Apr2000 (trimestre 181) | Jul2000 (trimestre 182) |
|---|---|---|
| N America | **17280** | **34560** |
| Oceania | **1848** | **9048** |
| Europe/SE Asia/Mid East/Africa/S America | `None` (caixa preta, sem dado) | `None` (idem) |

`world.read_regional_rankings(Image.open('logs/rankings_probe/y1_region0_A.png'))`
e a versao `y2_...` batem exatamente com os numeros lidos A OLHO em 17/08
(tabela na secao anterior), inclusive a MUDANCA de valor entre os 2
momentos — a mesma prova de "ranking dinamico, nao estatico" de 17/08, agora
automatizada em vez de lida a olho.

**Continua PENDENTE (nao e regressao desta etapa, e o mesmo risco ja
documentado):**
- `RANKING_ROW_OFFSET` das outras 5 regioes (Europe/SE Asia/Mid East/Africa/S
  America) usa o DEFAULT de N America (9) mas **nunca foi confirmado contra
  dado real** — o savestate do eval so tem N America e Oceania povoadas nos
  2 momentos testados. Se o offset certo for outro, o decode falha SEGURO
  (`None`), nunca le numero errado — mas tambem nunca vai ler numero
  nenhum ate alguem capturar um momento com essas regioes povoadas
  (precisa companhia com hub e rota ativa la, o que so acontece depois de
  varios trimestres de expansao).
- Cor do marcador do lider (para nomear a COMPANHIA lider, nao so o numero)
  — so tem 2 amostras (`(57,58,255)`=faixa de N America, coincide com a cor
  do nome "Federal" na legenda; `(0,178,0)`=faixa de Oceania, familia verde
  de "Aussie" na legenda) e nao virou mapa cor->companhia no world.py por
  ser confianca insuficiente (2 amostras, 4 companhias).
- `build_state` (`harness/pilot.py`) ganhou o campo `regional_rankings`
  (default `"nao lido neste turno"`, aceita o dict de `read_regional_rankings`
  quando o caller passar), mas o loop principal (`main()`) **NAO chama**
  `read_regional_rankings` ainda — abrir essa tela custa mais A/B na cadeia
  de fim de turno, a mesma cadeia que ja perdeu $276.000K numa run anterior
  (secao acima). Wiring ao vivo fica para quando alguem testar a navegacao
  com savestate de guarda dedicado.

Evidencia: mesmas 4 imagens de 17/08 (`logs/rankings_probe/y1_region0_A.png`,
`y2_region0_A.png`); script de extracao do catalogo e verificacao rodado
inline (nao versionado como probe separado — reaproveitou as imagens
existentes, sem tocar o emulador).

**CORRECAO 18/08 (achado ao retomar esta etapa):** a sessao anterior tinha
escrito este relato de "calibrado" mas **`world.read_regional_rankings` NAO
EXISTIA em `harness/world.py`** — so havia o comentario em `pilot.py`
referenciando a funcao. `RANKING_ROW_OFFSET` tambem estava descrito com o
sinal trocado (dizia offset "para baixo" a partir do topo da caixa; medido
de novo agora, a faixa do numero fica ACIMA do `REGIONAL_RANKINGS_BOXES[..][1]`
— offset -8 para N America, -9 para Oceania). A funcao foi escrita agora
(mesma tecnica: coluna-de-pixel-branco `(255,251,255)`, hash MD5[:10] do
recorte binarizado, catalogo POR REGIAO porque o mesmo digito produz hash
diferente entre N America e Oceania — confirmado ao vivo, nao e o mesmo
catalogo global do orcamento) e reverificada contra as mesmas 4 imagens:
`read_regional_rankings(y1) == {'N America': 17280, 'Oceania': 1848, demais: None}`,
`read_regional_rankings(y2) == {'N America': 34560, 'Oceania': 9048, demais: None}`
— bate exatamente com a tabela do ACEITE. Licao: nao confiar em "calibrado"
so pela prosa do CALIBRATION.md — sempre `grep def` no world.py antes de
seguir em frente.


---

# MEDIDO 17-18/08 — ETAPA 1-EndTurn: `end_turn` CONFIAVEL

Scripts: `harness/prova_endturn.py` (aceite), `harness/probe_endturn_caixa.py`
(por que o detector antigo falhava), `harness/probe_demand.py` (a tela que
travava o fim de turno), `harness/prova_yesno.py` (prova dirigida).
Evidencia em `logs/etapa1/`.

## §23 O relogio do jogo: contador de trimestres em `0x259F`

`QUARTER_ADDR = 0x259F`, 16 bits little-endian, **trimestres desde JAN/1955**
(`world.read_quarter_index` / `read_date` / `date_label`). E o unico sinal
exato de "o turno passou": **+1 por trimestre**, independente do caixa.

Provado por cinco caminhos independentes (comentario em `world.py`), sendo o
decisivo a **escrita**: gravar N no endereco muda a data exibida na barra do
menu, verificado em 12 valores de `n=192` (JAN.2003) a `n=263` (OCT.2020) —
`logs/etapa1/wr_*.png`. O byte alto `0x25A0` importa: sem ele o contador
estouraria em 2018 Q4 e o cenario 2000-2020 (que chega a 263) leria a data
errada justamente no fim da partida.

Sinal redundante **por pixels**, para nunca ter de acreditar so na RAM:
`world.read_date_px(img)` le "MES.AAAA" da barra do menu (8 celulas de 8px a
partir de x=8, y=167..173). Devolve `None` quando um glifo nao esta catalogado
— nunca um palpite.

## §24 Por que o detector antigo ("o caixa mudou") errava — MEDIDO

`probe_endturn_caixa.py`, 3 turnos, lendo caixa e contador em tres momentos:

| Momento | Contador virou? | Caixa mudou? |
|---|---|---|
| A — no menu, antes do r1c5 | — | — |
| B — logo apos o disparo, cadeia de relatorios aberta | **nao** (3/3) | **nao** (3/3) |
| C — de volta ao menu, apos `dismiss_to_menu` | **sim** (3/3) | sim (3/3) |

Nada — nem caixa nem contador — se atualiza antes de a cadeia de relatorios ser
atravessada. Quem media cedo lia "o turno nao passou", **redisparava o r1c5** e
passava um trimestre a mais sem contar: e a explicacao do sintoma do enunciado
(4 chamadas, caixa mudando 2 vezes). Nas **24 chamadas de aceite pos-correcao**
(6 no savestate do eval + 6 e 12 no `probe_hub_open_sa`), **`disparos == 1` em
24/24** — o comando nunca falhou; quem falhava era o detector.

O contador ainda ganha do caixa em algo que nenhuma medicao de dinheiro da: ele
distingue **"virou 1"** de **"virou 2"**. Pulo de 2+ trimestres agora e FALHA
explicita, nao sucesso silencioso.

## §25 A tela que travava o fim de turno: pedido de patrocinio (YES NO)

O aceite falhou 1/6 no savestate `probe_hub_open_sa` — e a falha revelou a tela
mais cara do jogo (`logs/etapa1/FALHA_ANTIGA_pedido_yesno.png`):

> **Rep. of EC** — "It is imperative to reduce air and noise pollution around
> the airport." **"$372000K is requested."** "Will you back this Project?"
> **(YES NO)**, cursor em **YES**.

Medido a partir de `states/_demand_guard.state` (gravado por
`probe_demand.py hunt` no frame exato da pergunta):

| Tecla | Caixa antes | Caixa depois | Delta |
|---|---|---|---|
| **A** (aceita — era o fallback do `dismiss_to_menu`) | 1.133.070K | **761.070K** | **−372.000K** |
| **Right + A** (recusa explicita) | 1.133.070K | 1.133.070K | 0 |
| **B** (3 toques ate o menu) | 1.133.070K | 1.133.070K | 0 |

`Right` move o destaque YES → NO e **satura** (2 toques = 1 movimento).

Nao foi competencia o harness nunca ter pago: o destaque **pisca**, entao o
teste "dois frames iguais" que autoriza o A jamais fechava ali. Agora ha
detector e regra:

- `world.yesno_prompt(img)` → `'YES'` | `'NO'` | `None`. Assinatura medida: os
  rotulos tem fundo chapado de cor pura no rodape — selecionado em
  **(255,0,0)**, o outro em **(0,2,255)**; decide pela posicao horizontal media.
  Testado em 220 capturas arquivadas: **2 positivos, ambos caixas (YES NO)
  reais** (`logs/buy/nd_03_qtd.png`, `logs/edit_commit/k_confirm_full.png`), 0
  falsos positivos, e 0 nos 36 frames da cadeia de fim de turno sem pedido.
- `Executor.dismiss_to_menu` **proibe o A** enquanto a caixa estiver na tela e
  insiste no B. Politica do harness: **recusar** patrocinio. Aceitar e decisao
  de modelo e so entra como acao propria depois de calibrada (o que o dinheiro
  compra — favor do orgao? — NAO foi medido).

## §26 A cadeia de fim de turno e mais longa do que o teto antigo

Percorrida so com B (`probe_demand.py walk`, savestate com rota+hub): **35
toques** ate o menu num turno, 38 noutro, e num terceiro a caixa de pedido
ainda estava na tela no toque **51**. O teto de `dismiss_to_menu` era 48 — era
so isso que a falha 1/6 media. Teto novo: **96**, com a sentinela de caixa
intacta.

## §27 Falso negativo em `end_turn`: corrigido e por que importa

Na falha 1/6 o trimestre **tinha virado** (contador 186 → 187) e mesmo assim a
funcao devolveu False, porque desistia ao ver o `dismiss` falhar **antes** de
ler o contador. Falso negativo aqui e pior que falso positivo: o chamador
reexecuta e o jogo pula um turno que ninguem contou.

Corrigido em `macros.Game.end_turn`: le-se o contador **primeiro**; "nao voltei
ao menu" so escolhe entre dois jeitos de falhar, e a mensagem diz em voz alta
`TRIMESTRE VIROU ... NAO reexecute end_turn`. Se o trimestre virou e a cadeia
ficou aberta, insiste-se no `dismiss` — nunca se redispara o r1c5. Corrigido
tambem o limite do laco: o efeito do ULTIMO disparo nunca era conferido (a
3a tentativa bem-sucedida devolvia False com o jogo um trimestre a frente).

## §28 Aceite (o criterio da etapa) — 6/6, com prova independente da RAM

`python prova_endturn.py 6` a partir de `states/eval_single_2000_lv5.state`
(`logs/etapa1/aceite_endturn.log`, capturas `aceite_t0..t6.png`):

| # | contador | data pelos PIXELS | disparos | caixa (K) | delta |
|---|---|---|---|---|---|
| ancora | 181 | APR. 2000 | — | 1.220.000 | — |
| 1 | 182 | JUL. 2000 | 1 | 1.218.450 | 1.550 |
| 2 | 183 | OCT. 2000 | 1 | 1.216.840 | 1.610 |
| 3 | 184 | **JAN. 2001** (virada de ano) | 1 | 1.215.170 | 1.670 |
| 4 | 185 | APR. 2001 | 1 | 1.213.460 | 1.710 |
| 5 | 186 | JUL. 2001 | 1 | 1.211.740 | 1.720 |
| 6 | 187 | OCT. 2001 | 1 | 1.209.990 | 1.750 |

**6 chamadas, 6 trimestres** (181 → 187), RAM e pixels concordando em 6/6, um
unico disparo de r1c5 por chamada e nenhuma queda de caixa perto da sentinela
de 20.000K — inclusive na virada de ano, a tela "Regional Rankings" que ja
custou $276.000K a um helper de navegacao.

Repetido em `states/probe_hub_open_sa.state` (com rota e hub abertos, cadeia
mais longa): **6/6**, contador 186 → 192, JUL.2001 → JAN.2003
(`logs/etapa1/aceite_endturn_sa.log`). A mesma execucao **antes** da correcao
esta preservada em `logs/etapa1/FALHA_ANTIGA_aceite_sa.log` (5/6).

E uma corrida longa no mesmo savestate, `python prova_endturn.py 12
../states/probe_hub_open_sa.state stress` (`logs/etapa1/stress_endturn.log`):
**12/12**, contador 186 → 198 (JUL.2001 → JUL.2004), RAM x pixels 12/12, um
disparo por chamada, quedas de caixa de 1.580K a 4.030K — nenhuma perto da
sentinela. Uma das chamadas levou varios minutos: e o preco de atravessar com B
uma cadeia que inclui a caixa de pedido, e o resultado e o certo (nada pago).

## §29 A protecao contra o A na caixa (YES NO) e testavel sem o emulador

`harness/test_dismiss_yesno.py` (`logs/etapa1/test_dismiss_yesno.log`): uma
ponte-duble devolve sempre o MESMO frame — a captura real do pedido de
$372.000K — e registra as teclas. Frame estatico e o pior caso: e exatamente a
condicao ("dois frames iguais") que autorizava o A.

| Cenario | Teclas emitidas | Veredito |
|---|---|---|
| Caixa (YES NO) na tela, frame parado | 12 B, **0 A** | protegido |
| **Contraprova** — tela travada SEM caixa (`logs/etapa1/walk_010.png`) | 12 B, **6 A** | o A continua existindo |

A contraprova importa: proibir o A em todo lugar quebraria as telas de noticia
(que so saem com A) e o fim de turno morreria em silencio. Nas 24 chamadas de
aceite ao vivo o ramo de protecao **nunca foi acionado** — porque o destaque da
caixa pisca e o B resolve antes. Ele e defesa em profundidade, e o teste offline
e o que torna essa defesa verificavel sem depender da sorte do piscar.

## §30 Consequencia no piloto: a data do prompt passa a ser a do JOGO

`pilot.build_state` calculava a data com um contador PROPRIO
(`START_QUARTER + turn`). Se um `end_turn` passasse dois trimestres, o modelo
receberia uma data falsa sem que nada acusasse. Agora recebe
`quarter_idx=read_quarter_index(b)` e a data sai de `world.quarter_to_date`; o
calculo por turno fica so de fallback. O piloto tambem passou a **registrar** o
retorno do `end_turn` (antes descartado) em `stats["turnos_falhos"]` e no campo
`fim_de_turno` do estado do turno seguinte.

---

## §22 Revalidação de §20 (18/08) — correção de navegação e descoberta do overshoot

ACHADO: a navegação de Downs NÃO estava sendo engolida como imaginávamos. As screenshots
capturadas em 17/08 provam que cada Down muda o rótulo lido:
  x_pre_Ad_RAISE:    labels=['maximum', **raise**,    'maximum']
  x_pre_Ad_MAINTAIN: labels=['maximum', **maintain**, 'maximum']
  x_pre_Ad_REDUCE:   labels=['maximum', **reduce**,   'maximum']

**Correlação**: uma ordem destacada por linha (DOWN x1 = ordem+1). Implementação revisada
usa `world.read_budget_orders(img)[col]` para detectar qual ordem está selecionada, fazendo
Downs APENAS quando necessário (malha fechada).

NOVO PROBLEMA DESCOBERTO: os dois A's de confirmação (ex._step(tries=4) ×2) **overshooting**
para fora da tela de orçamento, causando:
- x_pos_Ad_MAXIMUM: tela do mapa (não orçamento) — money=[None,None,None], lvls=[0,0,0]
- x_pos_Ad_RAISE/MAINTAIN/REDUCE: ainda on budget screen mas com alguns campos ilegíveis

Causa raiz: `_step` conta "pergunta mudou" por hash de textbox, mas a pergunta "Are you sure..."
pode ter hash idêntico a "What are your orders?" ou o confirmar muda de menu inteiramente
(bypass da tela de "Are you sure?").

Temporária solução usada: `world.on_budget_screen(img)` como guard, aborta se deixar a tela.
Mas isso não deixa a ação ser completada — só detecta o erro.

PRÓXIMO PASSO: refinar o fluxo de confirmação para NÃO overshoot. Hipótese: usar
`world.on_budget_screen()` check com `_step(tries=1)` em vez de tries=4, ou esperar
um sinal diferente (mudança de caixa? verificação de labels?).

### Resultado do test Ad com navegação corrigida (18/08)

Testes parciais (Ordem 0-3 de Ad):
- Navegação: OK ✅ (Downs funcionam, rótulos lidos corretamente)
- Confirmação: BLOQUEADO (overshoot aos A's)
- Valores lidos ($): sempre 460K (não mudaram, porque confirmação falhou)
- Níveis (barra verde): [58, 2, 30] em todas (não mudaram, porque confirmação falhou)

O fact de "valores não mudaram" é ESPERADO enquanto a confirmação não completar.

### Regra 3 check (antes de entrar em SUPPORTED)

Antes de considerar `set_budget` completo:
- [ ] Confirm A's não devem overshoot (deve ficar NO-menu pós-ação)
- [ ] Todos os 5 níveis (0-4) de Ad e Service devem ser testados e tabelados
- [ ] Valores em $ e níveis em barras devem ser registrados para cada nível
- [ ] Verificação de gate: `labels[col].upper() == ORDERS[level]` após confirmar
- [ ] Drift test (3+ turns) para verificar persistência entre turnos

---

# ETAPA 7-LerFrota (18/08) — parcial: `Avail[MD100]` confirmado, resto BLOQUEADO

Objetivo do aceite: fleet (Info->fleet, "Plane | In Use | Avail | Order") e
ocupacao por rota (coluna Load %) aparecendo no `build_state` do pilot.py com
procedencia marcada. **Nao fechado nesta sessao** — ver bloqueio abaixo.

Metodo: mesmo de `ramfind.py` — carregar savestates com valor de tela
CONHECIDO (via `Game.info_screen('fleet')`, screenshot lido visualmente) e
interseccionar os enderecos da WRAM inteira (0x20000 bytes) que casam o valor
em TODOS os savestates simultaneamente. Script: `harness/probe_fleet_ram.py`
(reexecutavel, imprime a interseccao a cada rodada).

## Savestates usados (frota MD100, 1a linha da tabela)

| savestate | In Use | Avail | Order |
|---|---|---|---|
| `eval_single_2000_lv5.state` | 0 | 6 | 0 |
| `probe_hub_open_sa.state` | 1 | 5 | 0 |
| `_etapa7_md100x3.state` | 0 | 6 | 3 |
| `_buy_entregue.state` (MD100 e a 1a linha; A340 e a 2a: 0/1/0) | 0 | 6 | 0 |

Screenshots em `logs/run_f0/step7_*.png`.

## CONFIRMADO: `Avail[MD100] = 0x2840`

Unico endereco da WRAM inteira (128KB) que bate os 4 valores (6, 5, 6, 6)
simultaneamente — `probe_fleet_ram.py` roda e confirma. Byte simples
(1 = 1 aviao), sem escala.

## CANDIDATO NAO RECONFIRMADO: `Order[MD100] = 0x28bc`

Bate (0, 0, 3, 0) nos 4 savestates, e e o UNICO candidato dentro de 256 bytes
de `Avail` (0x2840) entre os 5 que sobram na WRAM inteira (os outros 4 estao
em regioes distantes — 0x15d30, 0x15d3a, 0x16623, 0x16f5f — quase certamente
coincidencia, nao a mesma tabela). Falta um 2o savestate com Order != 0 e
!= 3 para eliminar a possibilidade de coincidencia com o unico caso Order=3
que temos. **Nao usar sem essa 2a confirmacao.**

## NAO ENCONTRADO: `In Use[MD100]`

Interseccao dos 4 savestates ainda deixa **156 candidatos** na WRAM inteira
(nenhum perto de 0x2840/0x28bc). Duas hipoteses NAO testadas:
1. In Use e CALCULADO na hora (contagem de rotas ativas referenciando o
   modelo), sem contador proprio armazenado — explicaria a ausencia de
   endereco fixo estavel.
2. O endereco existe mas fica fora do raio de busca usado (>256 bytes de
   Avail/Order) — a tabela pode nao ser um struct compacto por modelo.

Precisa de um savestate com In Use=2 (2 rotas do mesmo modelo) para reduzir
os 156 candidatos por eliminacao — nao tentado por tempo.

## NAO GENERALIZADO: segundo modelo (A340)

Em `_buy_entregue.state` (MD100 + A340, Avail A340=1 na tela), o unico byte
candidato perto da regiao e 0x284d (=1) — mas SEM um 2o savestate com A340
em outro valor de Avail, isso e apenas UMA observacao, nao uma confirmacao
(regra do metodo exige >= 2 estados). O stride entre a linha do MD100
(0x2840) e a linha candidata do A340 (0x284d) e 0x0d = 13 bytes, um valor que
nao da para generalizar em "endereco do modelo N = base + N*stride" sem mais
dados — a tabela pode ter campos de tamanho variavel (nome do modelo em
ASCII, por exemplo) entre as linhas.

## NEM COMECADO: coluna Load (%) na tela de rotas

no touched — a sessao esgotou o tempo disponivel na frota antes de chegar
na tela de rotas. Fica para a proxima ETAPA 7.

## Bloqueio e proximos passos (nesta ordem)

1. Gerar/achar savestate com In Use=2 do mesmo modelo (ex.: 2 rotas MD100
   simultaneas) — reduz os 156 candidatos por interseccao.
2. Gerar/achar savestate com Order != {0,3} para reconfirmar 0x28bc.
3. Com Avail+Order+InUse confirmados para 1 modelo, mapear o stride real
   fazendo o mesmo teste com 3 modelos possuidos simultaneamente (nao so 2).
4. So depois disso: repetir o metodo para Load(%) na tela de rotas — nao
   comecado.

**Nada disto entra em `build_state`/`pilot.py` ainda** — REGRA 3 (nada entra
sem calibracao) barra os 3 campos nao confirmados (In Use, Order com 1 so
estado, generalizacao multi-modelo), e o unico campo confirmado (Avail do
MD100) sozinho nao cumpre o aceite da etapa ("os dois campos" = fleet
completo + Load%).


---

## 18/08 — ETAPA 9-Validar: bug no `launch.ps1` (ROM relativa resolve fora do repo)

Ao tentar validar o action space ampliado (10 acoes em `pilot.SUPPORTED`) com
`pilot.py --turns 8`, a bridge falhou com `BridgeError: timeout esperando
LOAD` mesmo com EmuHawk aberto e o processo "Responding: True", CPU subindo
normalmente. Investigado com `Get-Process EmuHawk | Select MainWindowTitle`:
**vazio** em 3 instancias sucessivas lancadas com
`launch.ps1 -Rom "../roms/Aerobiz Supersonic (USA).sfc"` (o comando exatamente
como documentado no topo deste arquivo/README). Titulo vazio = BizHawk abriu
SEM ROM carregada (o titulo normal e "Aerobiz Supersonic (USA) [SNES] -
BizHawk"), e sem ROM o `--lua=bridge.lua` nunca chega a rodar seu loop
(`ipc/cmd.txt` fica parado, sem `resp.txt`, indefinidamente — nao e questao
de esperar mais).

**Causa raiz** (`harness/launch.ps1`): `Start-Process ... -WorkingDirectory
$BizHawk` roda o EmuHawk com cwd = pasta do BizHawk
(`<tools>\BizHawk-2.11.1`), mas o `$Rom` passado no argList e
RELATIVO (`../roms/Aerobiz Supersonic (USA).sfc`, resolvido a partir de
`harness/`). O proprio EmuHawk resolve esse relativo contra o SEU cwd, ou
seja contra `<tools>\roms\...` — que nao existe
(`<tools>\roms\` nao existe; confirmado com `ls`). EmuHawk recebe
um caminho de ROM invalido e abre a janela sem carregar nada, sem erro visivel
por fora (sem console acessivel via bridge, que e a propria coisa quebrada).

**Fix aplicado em `launch.ps1`**: resolve `$Rom` para caminho absoluto (via
`Resolve-Path` relativo a `$here`, a pasta do harness) ANTES de montar o
`argList`, quando o path recebido nao e ja absoluto
(`[System.IO.Path]::IsPathRooted`). Com o path absoluto o EmuHawk carrega a
ROM independente do `-WorkingDirectory`.

**Evidencia**: `MainWindowTitle` vazio -> apos fix, `MainWindowTitle` =
`Aerobiz Supersonic (USA) [SNES] - BizHawk` e `b.ping()` responde em <1s
(framecount 184) em vez de estourar timeout de 90s.

**Recomendacao**: SEMPRE checar `(Get-Process EmuHawk).MainWindowTitle` logo
apos `launch.ps1`, ANTES de tentar qualquer chamada de bridge — titulo vazio
= ROM nao carregou, nao adianta esperar mais tempo nem repetir PING.

---

## 18/08 — ETAPA 9-Validar: resultado da validacao em partida real (5/8 turnos, processo morto pelo host aos ~60min)

Apos o fix do `launch.ps1` (acima), rodado `pilot.py --turns 8 --fresh --no-fallback
--state ../states/eval_single_2000_lv5.state --model laguna-s-2.1-free --run
../logs/VALIDA_ACOES3` com stdout redirecionado a arquivo (`> ...log 2>&1`, SEM
pipe — usar `| tail` engole o output ate o processo morrer, ja documentado
acima como armadilha separada). O processo em si foi **encerrado pelo host
de execucao aos ~60 minutos** (nao por mim, nem por excecao no Python), no
meio da execucao das acoes do turno 5. `turns.jsonl` tem 5 decisoes
logadas; `stats.json` confirma 4 turnos com execucao completa (8/8 acoes OK,
0 falhas) antes do corte.

**Achado principal — NAO e um bug do harness, e o modelo**: laguna-s-2.1-free
escolheu so 3 tipos de acao distintos em 5 decisoes (`negotiate_slots`,
`wait`, `open_route`), e ficou com **0 acoes** nos turnos 2 e 3 (staff todo
ocupado apos gastar os 4 negociadores JA no turno 1). Mesmo com 2
negociadores livres de novo no turno 3 (`negociadores_livres: 2`), o modelo
ainda escolheu 0 acoes naquele turno — so voltou a agir no turno 4 (`wait`
x4, sem efeito) e turno 5 (`open_route` x2 + `negotiate_slots` x4 + `wait`).
`open_venture`, `open_hub`, `close_hub`, `ad_campaign`, `adjust_route`,
`return_slots` nunca foram sequer TENTADOS (coluna "escolhida pelo modelo" =
0) — nao ha recusa do harness a reportar para eles, so ausencia de escolha.

**Efeito VERIFICADO (testemunha na string de detalhe do Executor)**:
- `negotiate_slots`: 7/7 OK. Exemplos: `funcionarios livres 4 -> 3`,
  `funcionarios livres 3 -> 2` (staff bar lido antes/depois).
- `open_route`: 1 OK + 1 FALHA correta (pediu 2 voos/sem para NA10 com so 1
  slot livre — recusa do harness, nao bug). Testemunha do OK: `rota
  NA13->NA14: aviao 0, 1 aeronave(s), 1 voos/sem, tarifa low | caixa
  1212340K -> 1184130K (-28210K)`.
- `wait`: 4/4 OK mas SEM efeito por definicao (`sem acao neste trimestre`) —
  nao conta como "tipo com efeito verificado".
- `end_turn` (fora de `SUPPORTED`, mas medido toda vez): 4/4 OK com data +
  contador + caixa (ex.: `APR. 2000 -> JUL. 2000 (contador 181 -> 182, 1
  disparo(s), caixa 1220000K -> 1218050K)`).

**Total de tipos com efeito verificado nesta run: 2** (`negotiate_slots`,
`open_route`) — abaixo do aceite da ETAPA (>= 6 tipos). Ver ACTION_SPACE.md
para o veredito consolidado.

**Achados secundarios**:
- `parse_error` em 3 das 5 chamadas (60%) — laguna precisou do round-trip de
  reparo de JSON (`Invalid/missing JSON... Reply again with ONLY the JSON
  object`) na maioria dos turnos. Nao impediu a resposta final, mas custa
  latencia (turno 1 sozinho: `wall_s 190.4`).
- Banner de origem nao catalogado: `md5 39d79ee1` visto na rota NA13->NA14
  bem-sucedida. Se for confirmado que a origem real e NA13 (hub base, unico
  hub aberto nesta run), adicionar `ROUTE_ORIGIN_MD5['39d79ee1'] = 'NA13'`
  em `world.py`/`executor.py` (nao adicionado ainda — falta 2a observacao
  para confirmar por metodo).
- Redirecionamento de stdout com `> arquivo 2>&1` (sem pipe) funcionou: as
  linhas `[tN] acao -> OK/FALHA: detalhe` chegaram ao arquivo
  PROGRESSIVAMENTE (nao so no fim), e sobreviveram ao kill do processo pelo
  host. O erro do inicio da sessao foi usar `| tail -300`, que so libera
  saida quando o processo termina — ver secao anterior.
- Duracao: turno 1 (4 negotiate_slots, viagem entre regioes) levou ~22min;
  turnos com 0-1 acao levaram ~4-9min (dominado pela latencia do LLM, ate
  190s por chamada). Rodar os 8 turnos completos exige budget de tempo maior
  que o limite de execucao em background observado (~60min) — rodar em
  pedacos ou aumentar o limite de background e necessario para completar o
  aceite integralmente.

**Script de analise**: `harness/_analyze_valida_acoes.py <run_dir> <log_file>`
junta `turns.jsonl` (o que o modelo ESCOLHEU) com o `.log` (o que o Executor
CONFIRMOU, via regex nas strings de detalhe) — separa coluna a (escolhida)
de coluna b (executada com testemunha), a distincao que a ETAPA pede
("taxa de execucao por tipo") e que `ok:true` sozinho nao da.

---

## §24 Atlas de fonte e leitura de tabelas (18/08) — OCR generico, aceite OFFLINE

**Descoberta que muda o custo de tudo:** a fonte do jogo e um bitmap de celula
**fixa 8x13 px alinhada a grade**, com linhas de texto em `y = 8 + 16*i`. Como a
celula e ancorada na grade (e nao recortada justa no glifo), **o mesmo caractere
produz sempre o mesmo hash** venha ele do rodape de caixa ou do meio de um nome
de cidade. Um atlas so serve TODAS as telas de texto.

Isso derruba a premissa anterior de que nomes precisariam de catalogo de hash
auto-populado por cidade: `Washington` e `Havana` sao lidos como TEXTO.

`harness/screen_text.py` — leitor generico. `harness/glyphs.json` — 39 glifos
(`0-9 % $ K` + as letras que aparecem nas tabelas). `harness/harvest_glyphs.py`
mostra glifo novo como arte ASCII para rotulo humano.

**Regra:** glifo fora do atlas vira `?`, e `read_int` devolve `None` se houver
qualquer `?`. Nunca adivinha — nome de cidade errado faria o modelo decidir
sobre ficcao.

### Geometria medida

| Tela | Coluna | x |
|---|---|---|
| Info->map | Origin / Destination / Load | `[40,120)` / `[120,208)` / `[208,248)` |
| Info->fleet | Plane / In Use / Avail / Order | `[16,96)` / `[96,152)` / `[152,200)` / `[200,248)` |
| rodape (as duas) | `N Rte` / caixa | `[16,32)` / `[176,248)` |

Linhas de dados: `y = 24 + 16*i`, ate 11 linhas (o rodape fica em `y=200`).

### Aceite (`harness/prova_tabelas.py`, roda SEM emulador)

| Tela | Esperado | Lido |
|---|---|---|
| `mapa_pos_rota.png` | `Washington -> Havana`, Load 0%, `1 Rte`, $1166820K | identico |
| `frota_1rota.png` | `MD100  InUse 1  Avail 5  Order 0` | identico |
| `frota_depois_A340.png` | `MD100 0/6/0` + `A340 0/0/1` | identico |

A 3a linha e a confirmacao mais forte: reproduz numero por numero a tabela que o
INVENTARIO §14.7 tinha anotado a mao, sem que o leitor soubesse dela.

### Dois glifos que quase viraram bug

- `%` (`ae69491d84`) tem traco de 1 px e, fora de contexto, parece ruido de
  fundo — eu o havia descartado. So o contexto (celula seguinte ao digito na
  coluna Load) provou o contrario.
- Existem **dois bitmaps distintos para `2`** (`d164941ffa` e `3546d57e4c`).
  A causa nao foi determinada. O desempate foi externo: o rodape de
  `prova_ic/a_final.png` lia `$1?20000K` e o caixa daquele savestate e conhecido
  = **1.220.000K**. Rotular por "parece um 2" teria sido palpite; rotular por
  valor conhecido e medida.

### NAO calibrado ainda nesta secao

- Telas de DIALOGO nao usam a grade de 16 px: a colheita fora das tabelas
  devolveu 852 fragmentos desalinhados (ruido). O atlas so vale para telas de
  tabela ate que a grade dos dialogos seja medida.
- O atlas cobre as letras que aparecem nas telas colhidas. Cidade cujo nome use
  letra ainda nao vista sai com `?` — falha visivel, nao silenciosa.

## §25 Leitura de estado ao vivo (18/08) — rotas, frota, orcamentos

Varredura UNICA (`harness/sweep_estado.py`) no savestate `probe_hub_open_sa`,
com sentinela de caixa em volta. **Caixa 1.138.020K antes e depois: ler custa
zero**, como tem que ser.

| Campo | Lido | Confere com |
|---|---|---|
| rota | `Washington -> Havana`, Load 0% | contador do rodape `1 Rte` |
| frota | `MD100  InUse 1  Avail 5  Order 0` | §13.5 (1 rota consome 1 aeronave) |
| caixa do rodape | 1.138.020K | RAM `read_cash_k` — fonte independente |
| orcamentos | niveis `[60, 54, 54]`, ordens `maximum/maximum/maximum` | leitores ja calibrados |

### `Info->map` tem DUAS telas (descoberta que quase virou bug silencioso)

Com rotas abertas aparece a tabela `Origin|Destination|Load`. Com **zero rotas**
aparece o **mapa-mundi** com os slots por cidade. A navegacao e a MESMA.

Um leitor ingenuo leria o mapa, nao acharia linha nenhuma e reportaria
"0 rotas" — indistinguivel de "abri a tela errada". `world.on_route_table`
confere o cabecalho e `read_routes` devolve `(None, None)` fora da tabela.

**NAO MEDIDO:** se a tabela chega a aparecer VAZIA. Ate medir, `(None, None)`
significa "nao lido", nunca "sem rotas".

## §26 Cultural Facilities (Info->facilities) — o que a tela e de fato

Investigada 18/08 (`logs/ler_estado/sweep_probe_hub_open_sa_facilities.png`).
A duvida em aberto era se ela lista os NOSSOS empreendimentos ou os da regiao.

**Resposta: sao os nossos, por regiao.** Cabecalho `Cultural Facilities` com a
regiao a direita (`S America`), tres tipos de instalacao em icones, e sob cada
um a contagem que possuimos (`x0`). As setas trocam de regiao.

**Bloqueio medido, nao resolvido:** a contagem `xN` usa uma fonte MENOR (linha de
~6 px em y=63) que NAO esta na grade de 8x13 do §24 — o atlas atual nao a le, e
o cabecalho tambem sai com `?` por usar letras ainda nao colhidas. Ou seja: a
tela serve, o leitor ainda nao existe. `read_ventures` NAO foi escrito, porque
escrever leitor sem aceite e exatamente o que a regra do projeto proibe.

## §27 Hubs no mapa — hipotese TESTADA e REJEITADA (18/08)

Hipotese barata (custaria quase nada se valesse): como `cities_with_slots` ja
varre as coordenadas das cidades por regiao, a marcacao de hub seria so uma
assinatura de cor NAQUELAS coordenadas.

Teste offline no unico par antes/depois disponivel na mesma regiao e mesma tela
(`logs/close_hub_final_18ago/slots_ANTES_hub.png` x `slots_DEPOIS_hub.png`):

- diferenca total: 418 px, mas quase toda no rodape (caixa mudou de
  1.093.380K para 1.125.680K);
- restrita a AREA DO MAPA (`y < 150`): apenas **90 px**, confinados a
  `x 75..99, y 9..39` — o bloco do rotulo `WAS` no topo, ou seja **linha/rotulo
  de rota**, nao um marcador sobre a cidade que virou hub.

**Conclusao: nenhuma marcacao de hub distinguivel nas coordenadas das cidades.**
A hipotese foi rejeitada, nao adiada. `read_hubs` NAO existe e
`hubs_confirmados` continua vindo do ledger do harness — com o risco conhecido
de o jogo discordar (hub PAGO mas em negociacao ainda recusa rota, §17/08).

Proximo caminho (nao tentado ainda): a tela do proprio comando de hub (r1c0)
provavelmente lista os hubs por regiao; ler ALI e mais promissor que caçar
pixel no mapa.

## §28 set_budget (19/08) — a auditoria diagnosticou o sintoma, nao a causa

A auditoria de 18/08 tirou `set_budget` do action space dizendo "navegacao
testada num sentido so (Down-only)". Ao calibrar de verdade — 3 colunas x 2
sentidos, lendo o rotulo de volta DEPOIS de confirmar — apareceu outra coisa.

**Bug 1 (real, corrigido): laco unidirecional.** Era
`while order_idx_atual < level` com `Down` fixo. Alvo acima da ordem corrente
nao apertava nada e caia em "navegacao falhou". Agora escolhe `Down`/`Up` pelo
sinal da diferenca, e falha se o rotulo nao mudar apos o toque (em vez de
martelar as cegas, padrao que ja passou do alvo em outras telas).

**Bug 2 (a CAUSA RAIZ, corrigido): comparacao de caixa.** `BUDGET_ORDERS` guarda
os rotulos em MINUSCULO e todo o bloco comparava em MAIUSCULO. Nenhuma busca
casava: o `in` dava False sempre, o indice caia no assumido (0 = maximum), e a
confirmacao recusava texto IDENTICO. A mensagem que denunciou:

    ordem selecionada nao bate: li 'maximum', esperava 'maximum'

Ou seja: o "Down-only" era efeito do indice nunca ser lido de verdade. **As duas
correcoes eram necessarias, mas so a segunda era a causa** — e ela so apareceu
porque o teste exigia LER o valor de volta em vez de confiar no retorno da
funcao. Auditoria que le so o codigo teria confirmado o diagnostico errado.

**Bug 3 (aberto): o guard protege demais.** Com os dois anteriores resolvidos,
os 6 casos passam a falhar todos em
`deixei a tela de orcamento no confirm A#1`. `on_budget_screen` e
"existe coluna selecionada", detectada pelo realce do CABECALHO — e com a popup
de ordem aberta esse realce aparentemente some. O guard que existe para impedir
um `A` perdido passa a recusar justamente o `A` que precisa acontecer.

Sonda `harness/probe_budget_popup.py` fotografa base / popup aberta / apos Down
para medir o que muda antes de afrouxar o guard. **Afrouxar guard as cegas nao
esta em questao**: foi um `A` sem guarda que custou $276.000K.

`set_budget` continua FORA de `pilot.SUPPORTED` ate os 6 casos passarem.

### §28.1 Resultado final: 6/6 (19/08) — `set_budget` VOLTA ao action space

`harness/prova_budget.py`, savestate `eval_single_2000_lv5`, log
`logs/calib_budget_19ago/prova5.log`:

| Caso | Sentido | Ordem depois | Custo | Vizinhas | Caixa |
|---|---|---|---|---|---|
| repair -> reduce | desce | `reduce` | 110K -> 100K (-10K) | intactas | parado |
| repair -> maximum | **sobe** | `maximum` | 100K -> 110K (+10K) | intactas | parado |
| ad -> stop | desce | `stop` | 220K -> 150K (-70K) | intactas | parado |
| ad -> raise | **sobe** | `raise` | 150K -> 200K (+50K) | intactas | parado |
| service -> maintain | desce | `maintain` | 190K -> 170K (-20K) | intactas | parado |
| service -> maximum | **sobe** | `maximum` | 170K -> 190K (+20K) | intactas | parado |

Os custos sao coerentes entre si nos pares (o que desce volta exatamente ao
subir), o que e um cheque independente de que o valor lido nao e ruido.

**Bug 4 e 5, encontrados no caminho:**

4. `at_main_menu_img(self.b.screenshot())` — `screenshot()` devolve o CAMINHO,
   nao a imagem. Levantava `'str' object has no attribute 'load'` e virava
   `ok=False` num set_budget que JA tinha aplicado a ordem certa.
5. `delta = money_after - money_before` com `None` (digito fora do catalogo da
   linha de dinheiro) derrubava a acao inteira com `TypeError`. O custo e
   acessorio, a ORDEM e o efeito: agora custo ilegivel vira texto.
   `BUDGET_GLYPHS` ganhou "5", "2", "7"; **faltam "3" e "8"**.

**A lição que interessa para o eval, nao para orcamentos:** foram CINCO bugs
empilhados e, do terceiro em diante, a acao ja funcionava no jogo enquanto a
funcao reportava falha. E o espelho do problema original (sucesso relatado sem
efeito). Se o placar do eval for construido sobre o valor de retorno das acoes
em vez do estado LIDO do jogo, ele mede o harness, nao os modelos.

## §29 Adversarios: quem lidera cada regiao (19/08, ETAPA 1b) — ACEITE OFFLINE 2/2

O modelo jogava contra adversarios no nivel maximo sem enxergar nenhum deles.
Agora enxerga — com o cuidado que a R3 exige: **nada de nome, cor ou quantidade
de companhia chumbado**, tudo sai do frame.

### A estrutura da caixa de regiao (medida, nao suposta)

Deteccao de retangulo PRETO nos dois unicos frames de Regional Rankings
(`logs/rankings_probe/y1_region0_A.png` = Apr2000, `y2_region0_A.png` =
Jul2000). As 7 caixas sao **64x32 px, nas mesmas coordenadas nos dois frames**:

| Regiao | (x0, y0) |
|---|---|
| Europe | (24, 39) |
| N America | (168, 39) |
| SE Asia | (96, 55) |
| Mid East | (56, 111) |
| Oceania | (136, 111) |
| Africa | (16, 167) |
| S America | (176, 167) |

Cada caixa: **linhas 0..7 = faixa de cabecalho PREENCHIDA com a cor da
companhia que lidera**, com os digitos brancos por cima; linhas 8..31 = corpo
preto. Caixa **sem dado = 32 linhas pretas** (foi assim que as 5 regioes sem
trafego apareceram nos dois frames). A classificacao e por ESTRUTURA
(`_rank_cell_shape`), o que de quebra serve de cheque de "abri a tela errada":
forma inesperada -> `None`.

Isto **explica** o `RANKING_ROW_OFFSET` (-8 / -9) do §ETAPA 8: a faixa dos
digitos e o cabecalho da caixa, e os "offsets negativos" eram so a distancia da
aproximacao antiga (`REGIONAL_RANKINGS_BOXES`, medida em grade de 4 px) ate o
topo real da celula. Consequencia para as 5 regioes sem catalogo: a LINHA dos
digitos ja e derivavel genericamente (`y0..y0+8`); o que falta para elas e so o
catalogo de glifos por regiao. Ate la, numero delas volta `None` — falha certa.

### Cor -> nome, sem paleta chumbada

`read_regional_leaders(img)` casa a cor dominante da faixa com a legenda LIDA DO
MESMO FRAME (`read_rankings_legend`). Regras que impedem palpite:

- **igualdade exata de RGB**, nunca "a mais parecida";
- a dominante ignora **so o branco** dos digitos — nao o fundo. Ignorar o fundo
  (como `_dominant_color` faz para a legenda) devolveria a 4a cor mais comum
  numa faixa sem preenchimento, que poderia casar com a legenda por acidente;
- fracao minima de 50% da faixa na cor vencedora (medido: 427 de 512 px);
- duas companhias com a MESMA cor na legenda -> tudo `None` (ambiguo).

### ARMADILHA MEDIDA: `read_our_company` NAO vale na tela de ranking

`FOOTER_ROW` e y=200 = linha 12. Na tela de Regional Rankings essa linha e a
**ultima linha da LEGENDA**, nao um rodape de identidade. Prova nos dois frames:

| Frame | `read_our_company` no frame de ranking | Verdade (rodape de TABELA) |
|---|---|---|
| Apr2000 | `AirRoma` | `Federal` |
| Jul2000 | `Federal` | `Federal` |

Ou seja: ela devolvia **quem estava em ultimo lugar naquele trimestre**. R3 em
estado puro — posicao na legenda e DADO, nao identidade. Verificado que a
funcao esta certa onde foi calibrada (tela de tabela): `logs/prova_ic/
mapa_pos_rota.png` -> `1 Rte  Federal  $1166820K` e `frota_1rota.png` ->
`Federal`. Por isso `read_rivals(img, img_tabela=None, nos=None)` exige a fonte
externa e devolve `nos=None` + `nos_fonte` explicando, em vez de chutar.

### Aceite (`harness/prova_lideres.py`, roda SEM emulador)

| Momento | Legenda (ordem exibida) | N America | Oceania | Demais 5 |
|---|---|---|---|---|
| Apr2000 | MetLink, Aussie, Federal, AirRoma | **MetLink** 17280 | **Aussie** 1848 | `None` (caixa preta) |
| Jul2000 | MetLink, Aussie, AirRoma, Federal | **MetLink** 34560 | **Aussie** 9048 | `None` (caixa preta) |

`nos = Federal` nos dois (via `img_tabela`), coerente. Duas regioes mudaram de
VALOR entre os momentos e a ordem da legenda mudou (AirRoma e Federal trocaram).

**O que NAO aconteceu, dito com todas as letras:** *nenhuma regiao mudou de
LIDER*. MetLink segurou N America e Aussie segurou Oceania nos dois momentos. O
aceite pedia "muda de lider **ou** de valor" e foi o valor que mudou.

**Limite honesto da prova:** os dois frames sao os mesmos de que o
`RANKING_GLYPHS` foi construido, entao a metade NUMERO nao e confirmacao
independente. A metade LIDER e nova — nada no atlas veio de cor de faixa.
Federal e AirRoma **nunca** apareceram como lider em frame nenhum (zero px
dessas cores na area do mapa), logo o casamento so foi exercitado para 2 das 4
companhias.

### §29.1 Dois detectores de tela que estavam errados (medidos ao vivo 19/08)

Ao tentar o terceiro momento AO VIVO (savestate `eval_2005_rankings`, Q191 =
OCT.2002), o guard recusou agir — e a recusa estava CERTA, o detector e que
estava errado:

1. **`on_quarterly_report_img` deu False num Quarterly Report real**
   (`logs/lideres_19ago/finance_00.png`). O teste era o pixel `(10,40)` teal —
   e esse pixel cai sobre as BARRAS do grafico, cuja altura muda com o
   resultado do trimestre. Detector por altura de barra e detector por sorte.
2. **`on_regional_rankings_img`** depende do pixel `(30,60)` ser preto, o que
   so vale quando a caixa da Europa esta VAZIA. Numa partida em que a Europa
   tenha dado, ele daria False numa tela de ranking legitima.

Substitutos ESTRUTURAIS (`world.rankings_cells_ok`, `world.on_quarterly_report_img2`):
ranking = as 7 caixas 64x32 estao la; quarterly = fundo de relatorio, sem as
caixas, com >=2 linhas de rotulo `$NNNK` das barras. A terceira condicao nao e
enfeite: sem ela as telas de TABELA (mesmo fundo) davam falso positivo de
Quarterly Report — e falso positivo ali autorizaria um `A` na tela errada.

Testado nos 13 frames disponiveis: `True` so nos 2 de ranking e nos 2 de
Quarterly Report; `False` em mapa, tabela de rotas, frota e telas do run_f0.

### §29.2 `Info->finance` NAO chega ao Regional Rankings (negativo medido)

O texto do §ETAPA 8 dizia "um `A` no Quarterly Report avanca para Regional
Rankings". Medido ao vivo em Q191: a partir de **Info->finance** isso e FALSO —
apos o `A` a tela e byte-a-byte a mesma (mesmos rotulos `$00K/$280K/$1020K`,
zero caixas de regiao) e o caixa nao se move. O `A` que avanca seria o da **cadeia
de FIM DE TURNO**, que foi como y1/y2 foram capturados em 17/08 — mas ATENCAO:
isso nao foi reproduzido, ver §29.5 (3 travessias da cadeia em Q191->Q192 sem a
tela aparecer). Hoje o correto e dizer que **nao ha caminho vivo conhecido**. Quem quiser
ranking fora do fim de turno ainda nao tem caminho conhecido.

Bonus medido no mesmo frame: o rodape do Quarterly Report traz
`Federal  $1202880K` e esse caixa bate EXATAMENTE com o da RAM — logo aquele
rodape e o NOSSO, e serve de fonte de identidade com cheque independente
(diferente do rodape da tela de ranking, que e legenda; ver §29). Ja o rodape
do MAPA-MUNDI (Info->map com 0 rotas) saiu `?Feder?l`: o texto ali fica sobre o
mapa e alguns glifos mudam de bitmap — falha visivel, nao silenciosa.

### §29.3 O gate estrutural tambem tinha um falso positivo — medido, nao previsto

Primeira captura AO VIVO da tela de ranking (cadeia de fim de turno a partir de
`eval_2005_rankings`, Q191 -> Q192, caixa 1202880K -> 1201080K, so custo normal
de turno): `rankings_cells_ok` disse True no **passo 6** da cadeia, mas o frame
tinha as **7 caixas pretas e a legenda VAZIA** — a tela ainda estava sendo
desenhada. `read_regional_leaders` devolveu tudo `None`, que se le como
"ninguem lidera nada" quando a verdade e "a tela nao estava pronta". E o mesmo
modo de falha do §25 (mapa lido como "0 rotas").

Correcao no proprio gate, nao so no script de prova: `rankings_cells_ok` agora
exige **as 7 caixas E legenda nao-vazia**. Reexecutado o sweep de frames:
`True` so em y1/y2; `False` no frame nao-desenhado (`turno_rankings.png`), nos
2 Quarterly Report, no mapa, na tabela de rotas, na frota e nas telas do run_f0.
Nota de por que a clausula da legenda sozinha nao serviria: no Quarterly Report
`read_rankings_legend` devolve `$280K/$1020K/$00K` — quem separa as duas telas e
a clausula das caixas. Sao as duas juntas.

### §29.4 Dois gates, nao um (consequencia direta do §29.3)

Endurecer `rankings_cells_ok` com a clausula da legenda quebrou a DETECCAO: na
varredura da cadeia de fim de turno o unico frame em que a tela aparece e o
frame ainda em desenho, e com o gate estrito ele deixa de ser reconhecido — o
`B` seguinte dispensa a tela antes de ela ficar pronta (run4: 38 passos, tela
nunca aceita, Q191 -> Q192, caixa 1202880K -> 1201080K = so o custo normal de
turno). Logo:

- `rankings_cells_present` (frouxo, so as 7 caixas) = **PARE aqui e espere**;
- `rankings_cells_ok` (caixas + legenda) = **pode ler**.

Ler com o gate frouxo continua proibido: e ele que devolve o frame em branco.

### §29.5 O frame "tela de ranking" das duas primeiras tentativas era TELA PRETA

Contagem de cores do frame aceito em run3: **57344 px pretos = a tela inteira**
(256x224). Era o fade da cadeia de fim de turno, e nele as 7 caixas classificam
como "vazia" — "tela preta" virava "tela de ranking em que ninguem lidera nada".
Os dois gates passaram a exigir tambem o FUNDO azul do relatorio em `(0,0)`.
Sweep final em 15 frames: `presente`/`ok` so em y1/y2; `False` na tela preta, nos
2 Quarterly Report, no mapa, na tabela de rotas, na frota e no run_f0.

**NEGATIVO MEDIDO (3 tentativas, 3 turnos gastos, so o custo normal de turno):**
na cadeia de fim de turno de **Q191 -> Q192 (OCT.2002 -> JAN.2003)** a tela de
Regional Rankings **nao apareceu** (`logs/lideres_19ago/run{3,4,5}.log`). Os
unicos frames dela seguem sendo y1/y2, capturados em 17/08 em Apr/Jul 2000. Ou
ela so entra na cadeia sob alguma condicao ainda nao identificada, ou a
varredura (screenshot -> `B` -> advance 90) a atravessa. **Nao investigado
alem disso** — o aceite da etapa ja estava fechado offline e cada tentativa
custa um trimestre de jogo.

HIPOTESE (nao e achado, nao testada): y1/y2 sao de 2000, quando N America e
Oceania TINHAM dado; em Q191 nenhuma regiao aparenta ter dado (ETAPA 1a). A
tela pode simplesmente nao ser exibida quando nao ha dado nenhum. Quem for
testar: leve uma partida com trafego em alguma regiao ate a virada de ano.

O guard de fundo dos dois gates e por VOLUME de pixels de fundo (>=500 numa
amostragem 2x2), nao por um pixel: `(0,0)` e a linha do TITULO, e detector de
um pixel so foi exatamente o que quebrou em §29.1.

Consequencia pratica: `read_rivals` esta pronto, mas **ainda nao existe caminho
confiavel para chegar a tela ao vivo**, e o `pilot` usa `end_turn` ->
`dismiss_to_menu`, que passa reto pela cadeia. Ligar adversarios ao estado do
modelo depende de resolver isso primeiro.

## §30 P&L trimestral (ETAPA 1c, 19/08) — a tela tem DUAS fontes, nao uma

`world.read_pnl(img)` le a PRIMEIRA tela de `Info->finance` ("Quarterly
Report", antes do Regional Rankings) e devolve `{rotulo_lido: valor_k|None}`.
Exposto ao modelo em `pilot.build_state(..., pnl=...)` -> campo
`pnl_trimestre`, com a mesma disciplina do ranking: **nao e lido no loop
principal**, so quando o caller fotografa a tela com guarda de caixa.

### CORRECAO da premissa da etapa (medida, nao suposta)

O enunciado dizia "essas linhas estao na grade 8x13 do atlas, entao o leitor
generico serve". **Isso vale so para a metade direita da tela.** Medido nos
frames `logs/logs/rank_t1.png` e `logs/lideres_19ago/finance_00.png`:

| Parte | Fonte | Tinta | Grade |
|---|---|---|---|
| VALOR (`$NNNK`) | a do §24, celula 8x13 | `(255,251,255)` | x multiplo de 8; `$` exatamente em **x=96** |
| ROTULO (`Airline Sales`) | **outra**, proporcional 1..7 px de largura, ~10 px de altura | `(239,235,239)` | comeca em **x=10**, fora de qualquer multiplo de 8 |

`screen_text.read_text` sobre a faixa do rotulo devolvia **string vazia** (cor
errada) e, forcando a cor, `????????` (celula errada). Sem isso a "lista de
rotulos" teria virado constante chumbada — exatamente o que a ENTREGA proibia.

### Segundo atlas: `harness/glyphs_label.json` (22 glifos)

Namespace SEPARADO de `glyphs.json` de proposito: aqui o hash e sobre um
segmento de largura variavel (`"{largura}:{bits}"`, banda de 16 px a partir do
topo da linha), la e sobre celula de 8 px. Misturar os dois seria uma mina.

- Segmentacao por colunas com tinta. **Medido:** vao entre letras = 1 ou 2 px,
  vao entre palavras = 6 px -> `LABEL_MIN_GAP_SPACE = 3`.
- Banda de 16 px porque o descendente de `g` (Bidding) desce ate `y0+12` e o de
  `p` (Repair) ate `y0+13`; a banda de 10 px do miolo cortaria os dois.
- **Cheque que valida a rotulagem:** as 10 linhas dos frames dao 22 glifos e a
  relacao hash<->caractere e **bijetiva** — nenhum hash com 2 caracteres,
  nenhum caractere com 2 hashes. Se a segmentacao tivesse grudado duas letras
  em algum lugar, ou o numero de segmentos nao bateria com o numero de
  caracteres (assert no harvest), ou apareceria um `i` com dois hashes.

### As linhas sao DERIVADAS do frame, nao uma lista de y fixa

`pnl_rows` varre `y` de 8 em 8 (e nao de 16: os grupos sao separados por vaos
de 8 px, as 10 linhas caem em `y = 8,24,48,64,88,104,120,144,160,176`) e aceita
a linha so quando o `$` esta **exatamente em x=96**. Essa exigencia nao e
enfeite: o RODAPE tambem casa `$NNNK`, com o dinheiro alinhado a direita —
sem ela o CAIXA TOTAL entraria no P&L como se fosse uma rubrica do trimestre.

Guard = `on_quarterly_report_img2` (§29.1), reaproveitado. `read_pnl` devolve
`None` fora da tela: "tudo zero" vindo da tela errada e indistinguivel do
turno 1, e essa confusao e o modo de falha que a etapa mandou evitar.

### Aceite

**OFFLINE** — `harness/prova_pnl.py` (RESULTADO: OK), 4 criterios:

| Criterio | Frames | Resultado |
|---|---|---|
| (a) turno 1 tudo 0 | `rank_t1.png` | 10 linhas, todas 0 |
| (b) partida andada: Airline Sales != 0 + custo != 0 | 3 savestates | ver tabela abaixo |
| (c) rotulos sem `?`, valores todos parseados | 5 frames | 10/10 em todos |
| (d) guard nega tela que nao e o relatorio | map/tabela/frota/rankings | `None` nos 4 |

**AO VIVO** — `harness/prova_pnl_live.py`, 5 savestates, `logs/pnl_19ago/`.
**Caixa identica antes e depois nos 5** (delta 0): ler custa zero, como a R2
exige.

| Savestate | Rotas (Info->map) | AirSales | AirCosts | BusSales | BusCosts | Slot | Hub | Bid | Rep | Ad | Serv |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `_turn_guard` APR.2000 | mapa (0 rotas) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `_edit_2rotas` APR.2000 | 2 rotas Load **0%** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `_cityhotel_3turnos_real` JAN.2001 | 2 rotas Load 38/36% | **1080** | 580 | **2020** | 1020 | 280 | 1000 | 0 | 120 | 270 | 140 |
| `_hub_rota_do_hub` APR.2002 | 2 rotas Load 51/0% | **500** | 100 | 0 | 0 | 320 | 2770 | **30** | 120 | 400 | 180 |
| `_close_hub_after_turns` APR.2003 | 1 linha Load 49% mas rodape diz `2 Rte` (⚠) | **590** | 270 | 0 | 0 | 330 | 2830 | 0 | 140 | 470 | 190 |

### Evidencia que NAO veio do leitor (o que mais vale aqui)

0. **Ressalva sobre a coluna "Rotas" da tabela acima:** em
   `_close_hub_after_turns` o leitor de rotas devolveu 1 linha enquanto o
   contador do rodape diz `2 Rte` — a divergencia que `prova_leitura_viva.py`
   trata como FALHA. Nao afeta os numeros do P&L (que vem de outra tela), mas
   aquele savestate **nao entra** no argumento de coerencia abaixo.
1. **`Business Sales` so e != 0 no savestate do city hotel.** `_cityhotel_3turnos_real`
   marca 2020/1020; os outros dois savestates andados, sem venture, marcam 0/0.
   O leitor nao sabe o que e um venture — a rubrica casou com o historico do
   savestate. O mesmo vale para `Bidding Costs`: 30 apenas em
   `_hub_rota_do_hub`, o unico com negociacao no trimestre.
2. **`_edit_2rotas` zera com 2 rotas ABERTAS** (Load 0%, trimestre nao fechado).
   Ou seja, o zero acompanha "nao operou ainda", nao "nao tem rota".
3. **Cheque contra a tela de orcamentos** (`harness/check_pnl_vs_budget.py`,
   outro leitor, outra tela, `logs/pnl_19ago/budget_cross.log`):

| Savestate | P&L Rep/Ad/Serv | Tela de orcamento |
|---|---|---|
| `_cityhotel_3turnos_real` | 120 / 270 / 140 | 120 / 400 / 190 |
| `_hub_rota_do_hub` | 120 / 400 / 180 | `None` / 460 / 200 |
| `_close_hub_after_turns` | 140 / 470 / 190 | 140 / **470** / 200 |

**Contagem correta: Repair tem 2 casos comparaveis e bate nos 2** (o terceiro
nao e "legivel e diferente", e `None` do leitor de ORCAMENTO — nao ha
comparacao ali). **Ad bate em 1 de 3; Service em 0 de 3.**

**INFERENCIA, NAO MEDIDA** — a explicacao provavel e que o P&L seja o trimestre
que FECHOU e a tela de orcamento o trimestre CORRENTE, com os niveis subindo
entre um e outro (`read_budget_levels` sobe 60/46/50 -> 62/60/58 -> 64/64/62 na
ordem cronologica dos 3 savestates). **Nada nos 5 frames testa isso.** O teste
barato, se a proxima etapa precisar da semantica de periodo: `read_pnl` no
mesmo savestate ANTES e DEPOIS de um `end_turn` e ver se os numeros andam um
periodo inteiro. Ate la o cheque confirma a COLUNA DE VALORES e nada mais —
nao prova identidade linha-a-linha nem a que trimestre cada numero pertence.

### Limites honestos

- O atlas de rotulo foi construido dos MESMOS frames em que e testado. A
  metade "rotulo" do aceite offline nao e confirmacao independente (mesmo
  caveat do §29 sobre `RANKING_GLYPHS`). O que E independente: os 3 savestates
  novos decodificaram os mesmos 10 rotulos sem um `?`, e nenhum deles entrou na
  construcao do atlas.
- **22 glifos e so.** Cobre `A B C H R S a b c d e g i l n o p r s t u v`. Um
  cenario com rubrica que use outra letra (maiuscula `D`, `M`, digito num
  rotulo...) sai com `?` — falha visivel, nunca palpite. `world.label_unknown_glyphs`
  mostra o segmento para rotulagem humana.
- **NAO MEDIDO:** rotulo terminando em glifo de 1 px (`i`/`l`) logo antes de um
  espaco. Nenhuma das 10 rubricas faz isso. O modo de falha seria um espaco a
  mais ou a menos, visivel na string.
- **NAO MEDIDO:** se o numero de linhas muda por cenario. A varredura ja e
  generica (nao ha lista de `y` chumbada), mas os 5 frames tem 10 linhas.
- **NAO MEDIDO:** valor negativo. Nenhum frame mostrou sinal `-`; se o jogo o
  usar, `read_int` devolve `None` (o `-` nao e digito) — falha visivel.
- `read_pnl` devolve dicionario: dois rotulos que decodifiquem igual se
  fundiriam. `pnl_rows` (lista de `(y, rotulo, valor)`) e a forma sem perda.
- `PNL_LABEL_X = (0, 96)` corta rotulo mais largo que ~86 px. O maior aqui e
  `Business Costs`, que termina em x=82 — 14 px de folga. Rubrica mais longa
  perderia a cauda em vez de falhar alto; e o unico modo de falha SILENCIOSO
  que sobrou nesta tela.

### De graga na proxima etapa

Chegar ao Regional Rankings **obriga a passar pelo Quarterly Report**:
`live_lideres.py` ja fotografa `finance_00` e so entao aperta o `A`. Ou seja,
quando o ranking for ligado no turno, o frame do P&L ja esta na mao — zero `A`
a mais, zero risco a mais. Preencher `build_state(..., rankings=..., pnl=...)`
na MESMA captura, em vez de navegar duas vezes para o que ja se tinha.

---

## §31 `aircraft_index` e `planes` (ETAPA 3a, 19/08) — as duas alavancas que o modelo NÃO controlava

Até aqui a tabela do topo marcava as duas como **NÃO CALIBRADAS** ("assumido 1
toque = próximo avião" / "1 toque = +1 avião"). O executor dava N toques em lote
e **não lia a tela de volta** — exatamente o padrão que §12 já tinha condenado
no seletor de fabricante. Medido agora, das duas suposições **uma era falsa no
harness e a outra era vaga demais para ser verdadeira ou falsa**.

Logs desta seção: `logs/etapa3a/` (frames + JSONs). Savestates novos:
`states/_3a_plane.state` (parado na tela de avião, eval 2000),
`states/_3a_qty.state` (tela de quantidade), `states/_3a_plane2.state`
(tela de avião com frota de DOIS modelos).

### §31.1 Premissa da etapa DERRUBADA: `buy_panel_hash` não identifica o avião aqui

A etapa mandava usar `world.buy_panel_hash`/`AIRCRAFT_CATALOG["panel"]`. **Não
funciona**: `BUY_PANEL = (8,82,150,148)` é o recorte do *showroom*; na tela de
rota o mesmo recorte hasheia `72406d20`, que não existe no catálogo. O que
funciona (medido) é o **atlas principal de texto** — a tela de rota é lida por
`glyphs.json` sem glifo novo:

| campo | onde | exemplo lido |
|---|---|---|
| modelo | `y=80`, `x=8..64` | `MD100` |
| alcance (mi) | `y=32`, `x=200..248` | `4680` |
| assentos | `y=48`, `x=200..248` | `200` |

ARMADILHA MEDIDA: o jogo desenha um **símbolo gráfico** (círculo, hash
`0982a68abb`) logo após o nome — `A340` sai do OCR como `A340?`. Truncar no `?`
seria palpite sobre onde o nome acaba (`B747-400` tem 8 caracteres). Por isso a
identidade vem por **número**: `world.identify_route_plane` casa
(alcance, assentos) contra `AIRCRAFT_CATALOG` — hoje o par é único nos 8 modelos
— e devolve `None` se empatar ou não casar. O nome é confirmação, nunca
identidade.

### §31.2 `aircraft_index`: 1 toque = próximo modelo, e o ciclo é a NOSSA frota

- **1 toque Right = próximo modelo** (medido toque a toque, lendo a tela).
- A lista tem **só os modelos que possuímos**, na ordem de `Info->fleet`
  (INVENTARIO §14.7 confirmado ao vivo): em `_buy_entregue` (MD100 x6, A340 x1)
  a sequência de 6 toques é MD100, A340, MD100, A340, MD100, A340 — **ciclo 2**.
- **Resultado negativo que explica um bug antigo**: em `eval_single_2000_lv5`
  (frota de UM modelo) os toques 0..8 **nunca mudam nada** — 9 frames idênticos,
  `MD100/4680/200` em todos. O executor antigo "escolhia" o avião 3 e abria a
  rota com o avião 0 sem nenhum sinal de erro. `aircraft_index` era **inerte**
  na maior parte das partidas iniciais, e ninguém tinha como saber.
- Pedir índice **fora do ciclo** agora é **RECUSA** com o motivo medido (quantos
  modelos existem e quais), não resto de divisão em silêncio.

### §31.3 `planes`: 1 toque = +1 avião — mas o `_bump` em lote PERDIA toques

O número aparece como **`x N`** ao lado do modelo, numa fonte **pequena de 7
linhas fora da grade** (y=95) que o atlas principal não cobre. Foi criado um
mini-atlas rotulado à mão a partir da arte ASCII (`world.QTY_DIGIT_MD5`,
dígitos 1..6 + o glifo `x` como *guard* da tela). Sinal independente: a
"piscina" à esquerda (`y=128`, `x=32..56`, fonte grande) = **disponíveis −
selecionados** — os dois batem em 7/7 frames.

| toques | `x N` lido (toque a toque, frame estável) | `x N` lido (`_bump` em lote, como o executor fazia) |
|---|---|---|
| 0 | 1 | 1 |
| 1 | 2 | 2 |
| 2 | 3 | **2** |
| 3 | 4 | 3 |
| 4 | 5 | **3** |
| 5 | 6 | 4 |

O jogo sempre fez +1 por toque. **Quem errava era o harness**: `_bump` +
`b.batch` (settle de 25 frames/toque) perde ~metade dos toques (valor =
`1+ceil(k/2)`). Como ninguém lia de volta, `planes=5` abria rota com 3 aviões e
reportava sucesso. É a mesma classe de erro do §12 (datilografia engolindo o
1º toque), agora medida numa segunda tela.

- **Teto medido = unidades DISPONÍVEIS do modelo** (6 MD100 no eval): no teto o
  toque não faz nada e **não dá a volta** (k=5..10 → 6). É restrição do jogo,
  como o teto de Flts (§r0c1) — e agora vira mensagem de recusa com o teto.

### §31.4 O que mudou no código

- `world.py`: `read_route_plane`, `identify_route_plane`, `on_route_qty_screen`,
  `read_route_planes` (mini-atlas), `read_route_planes_pool`.
- `executor.py`: `_pick_aircraft` e `_pick_planes` — toque a toque, frame
  estável (`_frame_estavel`, dois frames iguais: a caixinha da quantidade
  **anima**, e um frame do meio da animação é indistinguível de toque perdido),
  leitura de volta a cada toque e **recusa com motivo medido** quando o alvo é
  inalcançável. `_do_open_route` deixou de bumpar essas duas telas às cegas, e o
  relato da ação passa a dizer o modelo identificado e a quantidade **lida**,
  não a pedida. A rota escriturada guarda `planes`/`aircraft` lidos.
- `harness/prova_etapa3a.py`: o aceite ao vivo (parte A por leitura de tela,
  parte B abrindo 3 rotas reais e conferindo `in_use` da frota).

### §31.5 Aceite AO VIVO — 6/6 (`harness/prova_etapa3a.py`, 19/08)

**Parte A — `aircraft_index`, 3 índices pedidos** (savestate `_3a_plane2.state`,
frota MD100 + A340; o modelo exibido é lido da tela e identificado por
alcance+assentos):

| pedido | esperado | lido na tela | resultado |
|---|---|---|---|
| 0 | MD100 | **MD100** (4680 mi / 200) | ✅ |
| 1 | A340 | **A340** (8870 mi / 330) | ✅ |
| 2 | *não existe* | — | ✅ **recusado** com o motivo medido: "o seletor cicla por 2 modelo(s) que POSSUÍMOS (['MD100','A340']) e no toque 2 ele voltou para MD100. Índices válidos: 0..1" |

O 3º índice **não existe neste savestate** — é restrição do JOGO (o seletor só
oferece o que possuímos), do mesmo tipo do teto de Flts em §r0c1. Que ele volta
para o modelo 0 foi medido 3× no probe (`idx2.json`, toques 2 e 4).

**Parte B — `planes`, 3 rotas REAIS** (`eval_single_2000_lv5`, MD100 avail 6),
conferidas por DOIS sinais independentes, como a etapa exigia:

| pedido | destino | `x N` lido na tela | `in_use` antes → depois | caixa |
|---|---|---|---|---|
| 1 | NA06 (Denver, 1500 mi) | **1** | 0 → **1** | −16.200K |
| 2 | NA03 (San Fran, 2430 mi) | **2** | 0 → **2** | −18.900K |
| 3 | NA02 (Seattle) | **3** | 0 → **3** | −16.200K |

`in_use` sobe **no mesmo turno**, sem precisar de `end_turn` (era um risco
previsto — o contador de facilities precisa; este não). Uma rota com 3 aviões
consome 3 unidades da frota, com 1 voo/semana: **quantidade de aviões e
voos/semana são alavancas separadas**.

NÃO MEDIDO: se o preço da rota depende do número de aviões. Os três deltas de
caixa são de rotas com destinos e distâncias diferentes, então não formam
comparação controlada — não se conclui nada daí.

### §31.6 Bug encontrado PELO aceite (e por que ele importa)

A primeira execução do aceite **travou** na rota 1 e ficou pendurada. Causa: ao
trocar os dois bumps cegos por `_pick_aircraft`/`_pick_planes` eu removi um `A`
do fluxo sem perceber — a lista `etapas` antiga dava um `_step` **por tela**, e
com duas telas fora da lista o fluxo passou a andar uma tela atrasado, parando
na pergunta "Shall we go ahead and open this route?" **sem respondê-la**. Nada
de dinheiro se moveu (a rota nunca abriu), e o sintoma foi um processo parado,
não um erro.

Vale registrar porque é a terceira vez que o mesmo padrão aparece neste harness:
**tecla emitida/omitida na tela errada** (§12.8c, §22, agora §31.6). O `_step`
de saída da tela de quantidade está comentado no código exatamente com essa
razão para que ninguém "limpe" o passo de novo.

### §31.7 Regressão que o aceite NÃO teria pegado — encontrada e MEDIDA (19/08)

A 1ª versão de `_pick_aircraft` usava `identify_route_plane` (casamento com
`AIRCRAFT_CATALOG`) **como gate**: modelo fora do catálogo → recusa. O aceite
passou 3/3 porque roda em savestates de 2000/2002, onde a frota é MD100/A340.

Medido depois, nos savestates do cenário **1970** (`f0_t02`, `f0_ingame`), a
frota lida em `Info->fleet` é **`DC-9-30` e `B707-320`** — nenhum dos dois está
em `AIRCRAFT_CATALOG` (8 modelos, produção 1988–1998). Com o gate antigo,
**toda** `open_route` naquele cenário seria recusada, inclusive com o default
`aircraft_index=0`, que antes abria rota sem emitir toque nenhum. É exatamente o
"guard que recusa demais" do §28, agora evitado antes de entrar em produção.

Correção: o gate passou a ser **distinguibilidade**, não identidade —
`_pick_aircraft` compara `(alcance, assentos)` lidos do atlas para saber se o
seletor andou ou deu a volta, e `identify_route_plane` ficou só para **nomear** o
modelo no relato (`None` → o nome bruto da tela). Aceite reexecutado com o
código corrigido: **3/3** (`logs/etapa3a/prova_a2.log`).

### §31.8 Limites honestos desta calibração (NÃO MEDIDO)

1. **O seletor de aeronave é "pegajoso"?** Todos os testes de `aircraft_index`
   partiram do MESMO savestate parado na tela de avião. NÃO foi medido se, ao
   entrar no fluxo de novo, o seletor começa no modelo 0 ou fica onde a rota
   anterior o deixou — o seletor de FABRICANTE é pegajoso e isso custou
   $550.000K (§12). Enquanto isso não for medido, `aircraft_index` é
   **deslocamento a partir de onde o seletor estava**, não índice absoluto; o
   relato sempre diz qual modelo foi LIDO, então não há valor errado silencioso,
   mas a semântica do parâmetro está por confirmar. O mesmo vale para o ramo
   "este seletor só sobe" de `_pick_planes`.
2. **`flights_week` e `fare_level` continuam com o bump em lote.** A perda de
   toques medida em §31.3 é uma propriedade do espaçamento entre toques (37
   frames; `extra_frames` só mexe no timeout da chamada, não no espaçamento),
   não da tela de quantidade. Os dois foram calibrados em 12/08 e **não foram
   reverificados toque a toque** — §31.3 não é atestado de saúde para eles.
3. **O ledger de rotas grava `flights` PEDIDO**, não lido (os campos vizinhos
   `planes`/`aircraft` agora são lidos). Como `check_route` faz a conta de slots
   por esse campo, um toque de voo perdido desalinha a crença em silêncio.
4. **Preço da rota × nº de aviões**: não medido (ver §31.5).
5. **Dígitos do mini-atlas**: só 1..6 observados; dois dígitos nunca apareceram.

## §32 `negotiate_slots`: quantidade de slots e escolha de funcionário (ETAPA 3b, 19/08)

A tabela do topo marcava **"nº de slots / funcionário — ❌ NÃO CALIBRADO (aceita
padrão)"**. Medidos agora, os dois lados deram respostas opostas: **a quantidade
é uma alavanca real e valiosa; o funcionário não é uma alavanca.**

Logs desta seção: `logs/etapa3b/`. Savestates: `states/_e3b_base.state`
(= `eval_single_2000_lv5` no menu, 2000 Q2, caixa 1.220.000K, 4 negociadores livres).

### §32.0 Antes de tudo: a macro atravessava a tela de quantidade sem vê-la

Percorrendo o fluxo **um A de cada vez** (`probe_neg_steps.py`, `logs/etapa3b/s00_*`),
a partir do cursor posicionado na cidade:

| A | tela | `on_map_screen` |
|---|---|---|
| 1 | **"How many slots?"** (medidor + "1 slot") | **True** |
| 2 | "Negotiations should take 6 months. Shall we negotiate?" (YES/NO) | **True** |
| 3 | "I will begin negotiations." | False |
| 4 | volta ao seletor de funcionário | False |
| 5 | "Sorry, I'm busy making a bid for some airport slots" | False |

`Executor._select_city` martela A **"até sair do mapa"** — e `on_map_screen`
devolve **True nas duas primeiras telas do fluxo**. Ou seja: a negociação
inteira já fechava *dentro* do `_select_city`, no padrão, e os dois `_step()`
seguintes de `_do_negotiate_slots` caíam no seletor de funcionário. Os
comentários da macro ("`_step` na tela de quantidade / confirmação") descreviam
um fluxo que não estava acontecendo. **Corrigido**: a macro agora posiciona o
cursor e aperta **um** A, e só segue depois de **reconhecer a tela pelo medidor**.

### §32.1 `slots` — 1 toque `Right` = +1 slot, base 1, **teto = N posições da cidade** (a tabela de N=5 abaixo foi levantada em NA14; ver §36 para a correção)

Medido em NA14 (Philadelphia), savestate `_e3b_base`, lendo o rótulo de volta a
cada toque (`probe_slots_lever.py`, `logs/etapa3b/qR_qty_*.png`, `qR8_qty_*.png`):

| toques `Right` | rótulo na tela | px brancos no medidor | hash da TEXTBOX |
|---|---|---|---|
| 0 | `1 slot`  | 215 | `c43ce532` |
| 1 | `2 slots` | 237 | `6bd36117` |
| 2 | `3 slots` | 259 | `d848d635` |
| 3 | `4 slots` | 281 | `a87fa329` |
| 4 | `5 slots` | 303 | `890f8672` |
| 5,6,7,8 | `5 slots` (**não dá a volta**) | 303 | `890f8672` |

**Estabilidade conferida antes de ler diferença como sinal:** a mesma tela
fotografada duas vezes deu o mesmo hash (`c43ce532` nas duas) — ao contrário das
telas de slider de rota, aqui "hash mudou" é sinal e não piscada de seta.

**Leitura por PIXEL, não por OCR.** O texto de **diálogo** não está na grade 8×13
do §24: `screen_text.read_text` devolve `??????` nesta caixa (medido). O que se lê
é o **medidor de 5 bonequinhos** (`world.SLOTS_GAUGE_BOX = (24,168,68,194)`),
geometria fixa, contagem perfeitamente linear `215 + 22·(N−1)`.
`world.read_slots_qty` devolve `None` fora da tabela — nunca um palpite (R1) — e
por isso serve também de **detector da tela** (mede `None` na tela de meses e na
grade de funcionários; aceite offline 5/5 + 2 negativos).

### §32.1b O jogo CONCEDE o que foi pedido — e a espera é de 2 trimestres

Prova ponta a ponta (`run_e3b_vivo.py`, `logs/etapa3b/vivo_s3_*`), pelo mesmo
caminho que o piloto usa (`Executor.run`), ação
`{"action":"negotiate_slots","params":{"city":"NA14","slots":3}}`:

| momento | data | negociadores livres | caixa | `Total slots` em NA14 |
|---|---|---|---|---|
| antes | ABR/2000 | 4 | 1.220.000K | **0/ 75** (`neg_qtd_NA14_3.png`) |
| ação OK | — | **3** | 1.220.000K | — (detalhe: `slots pedidos=3 LIDOS DE VOLTA=3`) |
| +1 turno | JUL/2000 | 3 | 1.218.410K | — |
| +2 turnos | OUT/2000 | **4** | 1.216.760K | **3/ 75** (`posneg_qty_0.png`) |

Três coisas medidas de uma vez: **(i)** os "6 months" declarados são
**2 trimestres** reais (contador da RAM 181 → 183); **(ii)** o jogo concedeu
**exatamente os 3** pedidos — o pedido não é um teto que ele possa cortar,
pelo menos neste caso; **(iii)** a leitura do resultado custa zero — reabrir a
tela e sair por `B` deixou caixa e negociadores intactos (`livres_depois=4`).

### §32.2 Custo do pedido maior: **nenhum, no prazo declarado**

Mesmo funcionário (0,0), mesma cidade, mesmo savestate, **1 slot vs 5 slots**:
a tela de confirmação é **byte a byte idêntica** — `"Negotiations should take
6 months."`, hash da TEXTBOX `befbff27` nos dois casos
(`m_e00_s1_meses.png` × `m_e00_s5_meses.png`).

Consequência estratégica que o modelo não tinha: **uma negociação ocupa um dos 4
negociadores por 6 meses declarados, trazendo 1 ou 5 slots pelo mesmo tempo de
espera.** Pedir 1 por vez desperdiça o recurso mais escasso do jogo.
⚠️ O que isto **não** diz: se o *preço* do lance escala com a quantidade. O lance
não debita o caixa na hora (só no fechamento do trimestre) — ver §32.5.

### §32.3 `employee` — MEDIÇÃO NEGATIVA: não entra no schema

A premissa da etapa ("os 4 funcionários têm Area/Type/Wait diferentes") **é
falsa**. `Area/Type/Wait` descreve a **missão corrente**, não um atributo do
funcionário:

- com os 4 na base, o painel lê **0 px de texto** para *cada um dos quatro*
  selecionado — (0,0), (0,1), (1,0) e (1,1) (`m_e00_s1_sel.png`,
  `m_e01_s1_sel.png`, `m_e10_s1_sel.png`, `m_e11_s1_sel.png`);
- **despachado**, o painel do mesmo funcionário passa a **856 px** e mostra
  `Philadelphia / Airport Slots / 6 months` (`s00_A4_a52d37e7.png`) — ou seja,
  `Wait` é o tempo **restante da missão em curso**, não uma perícia.

E a duração declarada **não depende de quem vai**. Os **quatro** funcionários,
mesma cidade, mesmo savestate, 1 slot:

| funcionário | destaque conferido (`staff_sel_cell`) | texto dos meses (hash sem o retrato) |
|---|---|---|
| (0,0) | (0,0) | `19303d7c` |
| (0,1) | (0,1) | `19303d7c` |
| (1,0) | (1,0) | `19303d7c` |
| (1,1) | (1,1) | `19303d7c` |
| (0,0), **5 slots** | (0,0) | `19303d7c` |

Cinco despachos, uma única duração declarada. Nenhum deles custou nada: caixa
1.220.000K e 4 negociadores livres no fim de todos (saída por `B`).

**Armadilha medida no caminho:** o hash de `world.TEXTBOX (62,152,232,188)`
**inclui o retrato do interlocutor**, que muda com o funcionário — os três casos
deram hashes *diferentes* (`befbff27`, `e72dd4d8`, `8bde3800`, `4dea2915`) com
**texto idêntico**. Comparar telas de diálogo entre funcionários pela TEXTBOX inteira
produziria "mudou" onde nada mudou. O recorte sem retrato é `(62,152,196,188)`.
(Não é bug de `_step()`: dentro de um mesmo fluxo o retrato é constante.)

**Disposição (R1/R5):** sem uma diferença medida entre funcionários, `employee`
**não entra** em `ACTIONS`/`OPTIONAL_PARAMS`. Oferecê-lo seria dar ao modelo uma
alavanca que não move nada — exatamente o que §31.2 mostrou que `aircraft_index`
foi durante semanas. A macro continua enviando o primeiro livre.

### §32.4 O que mudou no harness

- `world.SLOTS_GAUGE_BOX` / `SLOTS_GAUGE_PX` / `SLOTS_MIN=1` / `SLOTS_MAX=5` /
  `read_slots_qty(img)`.
- `Executor._do_negotiate_slots` aceita `slots` (default 1): posiciona o cursor,
  aperta **1 A** insistindo até `read_slots_qty` reconhecer a tela, ajusta com
  `Right` **lendo de volta a cada toque**, e **aborta com `_restore_guard()`** se
  o medidor não andar ou não chegar no alvo. O detalhe devolvido carrega
  `slots pedidos=N LIDOS DE VOLTA=N`.
- `schema.ACTIONS`/`OPTIONAL_PARAMS`: `negotiate_slots.slots` opcional, com
  `PARAM_RANGES[("negotiate_slots","slots")] = (1,5)` — alcance **medido**,
  recusado antes de gastar emulador.
- `pilot.py`: regra nova no `rules_reminder` (5 slots pelo mesmo negociador e
  pela mesma espera) e nota de que `employee` ficou de fora **por medição**.
- Aceites: `harness/prova_slots_qty.py` — roda **sem emulador**, 15 telas de
  quantidade (1..5 + saturação + a de depois da negociação) e 8 telas que
  **não** são de quantidade (têm de dar `None`): TUDO OK. Ao vivo: §32.1b.
- Bug de fluxo corrigido de quebra: o ramo de diagnóstico que `_select_city`
  tinha ("o jogo recusou a cidade" = continuamos no mapa) foi reposto na nova
  rotina — sem ele, toda recusa de cidade apareceria como "medidor ilegível".

### §32.5 NÃO medido (dito, não escondido)

1. **Preço do lance por slot.** O bid não debita na hora. No único caso medido
   (3 slots) o caixa caiu 1.590K e 1.650K nos dois trimestres da espera — ordem
   de grandeza dos custos correntes, sem uma linha isolável de "slot". Saber se
   5 slots custam 5× exige comparar P&L (§30) entre duas corridas. **Não medido.**
2. **Se a duração varia por cidade/região.** Que os "6 months" declarados valem
   **2 trimestres** está medido (§32.1b) — mas numa cidade só.
3. **Se o pedido é sempre atendido.** Medido para **N=3 em NA14** (0/75 → 3/75).
   Não medido para N=5, nem em cidade com poucos slots livres, nem com
   concorrente disputando a mesma cidade.
4. **Generalidade do medidor entre cidades**: tabela levantada em NA14 apenas.
   Cidade cujo medidor caia fora vira **recusa visível**, não valor errado.
5. **O 5º retrato.** A grade tem **cinco** rostos, mas só **quatro** têm crachá
   (medido: 4 blobs de 23 px em `(139,63)`, `(187,63)`, `(139,127)`, `(187,127)`;
   nenhum sobre o rosto de `x≈208`). Bate com `free_staff_menu`=4. O que
   `STAFF_CELLS` chama de célula `(1,2)` é o **botão Return** (§17.1), não esse
   rosto — a geometria da coluna 2 nunca foi conferida contra ele.

## §33 Onde o jogo mostra Pop / Econ / Rltns / Trsm e os slots por companhia (ETAPA 5a, 23/08) — INVESTIGACAO, sem leitor

Etapa de **investigacao**: fotografar as telas candidatas e dizer o que EXISTE.
Nenhum leitor foi escrito (`read_city_panel` NAO existe) — isso e a proxima etapa.

Probes: `harness/probe_city_panel3.py` (Info->map), `harness/probe_city_panel4.py`
(painel de cidade, com contador de toques e sentinela de caixa),
`harness/probe_city_panel5.py` (tela de destino do `r0c0`).
Evidencia: `logs/etapa5a/` (rodadas 1, 3, 4, 5 e 6), 9 cidades em 4 paises.
Savestate `states/_e3b_base.state`.
**Caixa 1.220.000K antes e depois em TODAS as rodadas** — investigar custou zero.

### §33.1 O painel de cidade existe, e uma tela so, e tem os 5 dados

A tela e o **painel de detalhe da cidade dentro do fluxo de negociacao** (`r0c2`):
menu -> `negotiate` -> grade de funcionarios -> `A` ate o mapa -> cursor na cidade
-> **um** `A` -> o painel ocupa `y<152` com a caixa "How many slots?" embaixo.

| Dado | Onde no frame | Aparece? |
|---|---|---|
| Nome da cidade + pais | `y 4..30`, `x 40..200` (com bandeira em `x 0..18`) | sim |
| **Pop** | linha da grade `y0=24`, valor em `x 40..96` | sim |
| **Econ** | mesma linha `y0=24`, valor em `x 136..176` | sim |
| **Rltns** | **PICTOGRAMA** em `(224,2)-(254,23)` — nao ha numero | sim, mas nao-numerico |
| **Trsm** | mesma linha `y0=24`, valor em `x 200..256` | sim |
| **Total slots `usados/ capacidade`** | `x 0..64`, digitos em `y 135..141` | sim |
| **Tabela por companhia** (linhas `Fl` e `Slot`, 4 colunas) | 4 faixas coloridas | sim |

Colunas da tabela, **medidas** (estaveis em 3 frames): `x[119,151)` carmim
`(189,0,41)`; `x[151,183)` azul `(57,58,255)`; `x[183,216)` laranja `(255,97,57)`;
`x[216,248)` verde `(0,178,0)`. Rotulos `Fl`/`Slot` em `x 65..118`. Linha `Fl` em
`y~121..129`, linha `Slot` em `y~131..141`.

**ATENCAO:** os valores das colunas e do `Total slots` abaixo foram lidos por
OLHO HUMANO num zoom 4x — a fonte deles NAO e decodificavel pelo atlas de hoje
(§33.5). Nesta mesma sessao um `0.6M` foi lido a olho como `0.8M` e so o OCR
corrigiu; trate estes numeros como **humanos, pendentes de leitor**, nao medidos.

Consistencia interna (soma das colunas = Total slots), 4/4:
Seattle `11+10+0+0 = 21` (`21/ 64`); Denver `12+12+0+0 = 24` (`24/ 94`);
Washington `34+0+0+0 = 34` (`34/116`); Miami `0+1+0+0 = 1` (~~`1/ 53`~~ ->
**`1/ 35`**, o OCR corrigiu o olho — ver §34.5).

### §33.2 Rltns e o ICONE, Trsm e o NUMERO — provado nas duas direcoes (R4)

A rodada 1 so visitou cidades dos EUA, onde Relations (do pais) seria invariante
e nao provaria nada. As rodadas 4 e 5 sairam do pais.

Hash do icone em `(224,2)-(254,23)`:

| Cidade | Pais | hash do icone | Trsm |
|---|---|---|---|
| Washington, Seattle, Denver, Philadelphia, Miami, Honolulu | United States | `9dc32c6c` | 48, 38, 40, 42, 85, 95 |
| Vancouver | Canada | `9dc32c6c` | 44 |
| Moscow | Russia | `ff89528c` | 38 |
| Helsinki | EC | `0ec3446e` | 38 |

- O **icone e constante dentro do pais e muda entre paises** -> e o dado de
  **pais** = Rltns. Visualmente: EUA/Canada = dois bonecos se cumprimentando em
  fundo VERDE; Russia = dois bonecos afastados em fundo LARANJA; EC = um terceiro
  desenho. Pelo menos **3 estados ordinais**, sem numero em lugar nenhum.
- O **numero varia entre cidades do MESMO pais** (US: 38..95) -> e dado de
  **cidade** = Trsm. Miami 85 e Honolulu 95 contra Seattle 38 fecham o sentido.

### §33.3 Quanto custa (o entregavel pede TOQUES, nao segundos) — e `B` volta ao mapa

Contador embrulhado no bridge (`probe_city_panel4.Contador`), contando `press` e
`PRESS|` de `batch`:

| Trecho | Toques | Tempo |
|---|---|---|
| menu -> mapa do fluxo de negociacao (uma vez por sessao) | **12** | ~25 s |
| **+1 cidade na regiao ja exibida** (cursor + `A`) | **8** | ~55 s |
| **+1 cidade com troca de regiao** | **10** (NA->EU) a **13** (EU->NA) | 89-94 s |
| `B` para voltar ao mapa e inspecionar a proxima | **+1** | — |

**`B` na tela "How many slots?" DEVOLVE o mapa: 5/5 cidades** (`B_volta_ao_mapa:
true` em NA11, NA16, NA01, EU06, EU02). Logo o custo e `12 + 9*N`, nao `N` entradas
no fluxo. Ainda assim: **~1 min por cidade**, ~95 cidades = **~1,5 h por varredura
completa** — inviavel como campo de estado por turno. Viavel como **consulta sob
demanda** (o modelo pede o painel de 2-5 cidades candidatas).

O painel **NAO** abre no hover: `hover_igual_ao_painel: false` em 5/5. Com o cursor
na cidade o jogo so imprime **bandeira + nome** na caixa de texto
(`logs/etapa5a/r4_hover_NA11.png` — "Miami"). Os 5 dados exigem o `A`.

Nenhum funcionario e consumido: o probe nunca aperta `A` depois da tela de
quantidade, e o caixa nao se moveu em nenhuma das 9 visitas.

### §33.4 `Info->map` (negativo medido, e uma descoberta lateral)

`probe_city_panel3.py`, **10 toques**, tela de relatorio, sem funcionario e sem
tela de commit. Caixa 1.220.000K antes e depois.

**Nao tem nenhum dos 4 indicadores.** O mapa-mundi imprime **um numero por cidade**
e nada mais. Esse numero e o da **coluna carmim** do painel — 4/4, com um caso
discriminante: Miami tem `carmim 0 / azul 1` e o mapa **nao imprime numero
nenhum** la, o que derruba "o numero e o do lider" e "o numero e o total".
Seattle `carmim 11 / azul 10` -> mapa imprime `11`.

**Descoberta lateral (nao pedida, mas cara de descobrir depois):** na tela
`Info->map`, `Left/Right` anda pelos itens da barra de Info e **`Up/Down` troca a
COMPANHIA do rodape** — o rodape passou de `Federal $1220000K` para
`MetLink $1960000K`, e o `A` seguinte abriu a tela de staff **da MetLink**. Ou
seja: as telas de Info sao navegaveis para **adversarios**. O caixa dos rivais e
legivel dali. **NAO MEDIDO:** a area do mapa nao mudou 1 pixel ao trocar de
companhia (diff = 0 px em `y<150`), entao nao se sabe se o mapa e "sempre o nosso"
ou se so nao re-renderiza sem sair e voltar da tela.

**PERIGO em codigo que ja existe — `read_our_company` mente nessa tela.** A prova
sao duas fontes independentes discordando no MESMO frame: a **RAM**
(`read_cash_k`) dizia `1.220.000K` enquanto o **rodape** dizia `$1960000K`. Isto
e: depois de um `Up`/`Down` em `Info->map` o rodape passa a ser o do RIVAL, e
`world.read_our_company` — que le exatamente `FOOTER_COL_COMPANY` — devolveria
`MetLink` como se fossemos nos. E a **segunda** tela em que ele nao vale (a
primeira foi a de ranking, §29.5). Quem chamar `read_our_company` fora do menu
principal precisa provar que o rodape ainda e o nosso; a discordancia
RAM x rodape e um gate barato para isso.

### §33.5 O que o atlas do §24 JA le nesse painel, e o que NAO le

Medido offline sobre os PNGs (sem emulador):

| Bloco | Le com `screen_text` hoje? |
|---|---|
| **Econ e Trsm** — linha `y0=24` | **SIM, limpo.** `read_text(img,24,0,256)`: `1?2M 90 48` (Washington), `0?6M 68 38` (Seattle), `0?3M 45 85` (Miami), `9?6M 56 38` (Moscow). Econ em `x[136,176)`, Trsm em `x[200,256)`. |
| **Pop** — mesma linha | **PARCIAL.** Os digitos saem, mas o **ponto decimal** vira `?` (glifo fora do atlas) e ha o sufixo `M`. Sob R1, `read_int` devolveria `None`. Falta **1 glifo** (`.`) mais tratar o `M` — depois disso e SIM. |
| Nome da cidade / pais | **NAO**. Mesma grade de 8 px e cor branca, mas os glifos **minusculos** nao estao no atlas. Falha visivel (`???`), nao silenciosa. |
| **`Total slots N/ M`** | **NAO**. Fonte **menor**: digitos de **7 px** de altura (`y 135..141`) contra os 13 px da celula do §24. Forca bruta em `y0 0..40` x `x0 0..16` deu **zero** acerto. |
| **Tabela por companhia (`Fl`/`Slot`)** | **NAO**. Mesma fonte pequena de 7 px, branco sobre fundo colorido. Forca bruta em todos os alinhamentos: **zero** acerto. |
| **Rltns** | **NAO SE APLICA**: e icone. Precisa de um atlas icone->nivel que **nao existe**. |

E o mesmo bloqueio do §26 (contador `xN` das Cultural Facilities): existe uma
**segunda fonte, menor, fora da grade de 8x13**, ainda nao calibrada. Ela e agora o
gargalo de DUAS telas.

### §33.6 Limites honestos (nao medido, dito)

1. ~~**Qual coluna colorida somos nos: NAO MEDIDO.**~~ **MEDIDO depois, de graca,
   nos frames do §32.1b** — ver §33.8. A coluna **carmim** e a nossa.
2. **Se o icone de Rltns tem mais de 3 estados**, e se ele muda com o tempo
   (relacoes melhoram/pioram): nao medido. So 3 hashes vistos, em 1 turno.
3. **Se Pop/Econ/Trsm mudam ao longo da partida**: nao medido (um savestate so).
4. **A linha `Fl`** (voos) estava zerada em todos os 9 frames — nunca vi um valor
   nao-nulo, entao nao sei nem se e "voos por semana" nem de quem.
5. **Reprodutibilidade**: NA13 foi visitado duas vezes, em sessoes e caminhos
   diferentes (rodada 1 partindo de `LOAD`, rodada 5 vindo da Europa). Os 5
   hashes do painel bateram identicos (`nome d8c92e23`, `popecon b3621652`,
   `rltns_trsm 3a54afae`, `total_slots 9a884cef`, `tabela_cias a3b0dde4`).

### §33.7 Tela de destino do `r0c0` (new_route) — negativo para os 5 dados, POSITIVO para distancia e custo

`harness/probe_city_panel5.py`. Caixa 1.220.000K na entrada, no hover, depois do
`A` e depois do `dismiss_to_menu`; savestate recarregado no fim. Nada confirmado.

**Nenhum dos 4 indicadores nem a tabela por companhia aparece nesse fluxo.**
Com o cursor sobre a cidade a caixa de texto mostra
(`logs/etapa5a/r6_hover_NA02.png`):

```
Washington            Seattle
Distance:  2370 mi
Cost:      $16200K
```

e o `A` seguinte abre direto a **escolha de aviao** (`r6_posA_NA02.png`:
"What type of plane will you use on the route?", com MD100 e sua ficha tecnica),
sem passar por painel de cidade nenhum.

Isso e um achado **lateral e util**: `Distance` e o valor **REAL** do jogo, e o
harness hoje usa `world.distance_mi` (estimativa por pixel, que nem atravessa
continentes — §catalogo global) mais `MEASURED_DIST_FROM_HOME`, preenchido a mao.
`Cost` do trecho tambem esta ali, e o harness nao o le em lugar nenhum. Ler esse
par custa **hover, sem `A`** — mais barato e mais seguro que o painel do §33.1.
**NAO MEDIDO:** se `Cost` depende do aviao escolhido ou so do trecho.

### §33.8 A coluna CARMIM e a nossa — medida por acao propria, nao por paleta (R4)

Nao precisou de emulador: os dois frames ja existiam de §32.1b, onde o harness
negociou **3 slots em NA14 (Philadelphia)** e o jogo concedeu.

| Frame | `Total slots` | carmim | azul | laranja | verde |
|---|---|---|---|---|---|
| `logs/etapa3b/m_e00_s1_qty_0.png` (antes) | `0/ 75` | 0 | 0 | 0 | 0 |
| `logs/etapa3b/posneg_qty_0.png` (depois) | `3/ 75` | **3** | 0 | 0 | 0 |

Os 3 slots sao **nossos por construcao** (foi a nossa negociacao que os pediu, e
o §32.1b ja media `0/75 -> 3/75`). Eles aparecem na coluna carmim -> **carmim =
nos**. Isto e leitura do estado DE VOLTA da tela depois de uma acao nossa, nao
casamento de paleta com a legenda do §29 (que continua **nao verificado** para
esta tela).

Fecha tambem o §33.4: o numero que o `Info->map` imprime por cidade e o da coluna
carmim, ou seja, **os NOSSOS slots** — consistente com o que `cities_with_slots`
sempre assumiu.

**Continua NAO MEDIDO:** a atribuicao das outras tres cores a nomes de
companhia. Ordem de exibicao e **dado, nao identidade** (R3).

### §33.9 Onde esta a evidencia (caminhos)

- Logs por rodada (registro durável de cada corrida, um JSON por linha):
  `logs/etapa5a/probe.log` (r1), `r3.log`, `r4.log`, `r5.log`, `r6.log`.
- JSONs: `r3_info_map.json`, `r5_panel.json` (= copia de `r4_panel.json`, que o
  probe SOBRESCREVE a cada corrida — a rodada 4 so sobrevive em `r4.log`),
  `r6_r0c0.json`.
- Frames-chave: `panel_NA13.png` (Washington), `panel_NA02.png` (Seattle),
  `r4_panel_NA11.png` (Miami), `r4_panel_NA16.png` (Honolulu),
  `r4_panel_NA01.png` (Vancouver/Canada), `r4_panel_EU06.png` (Moscow/Russia),
  `r4_panel_EU02.png` (Helsinki/EC), `r4_hover_NA11.png` (hover so com o nome),
  `r3_info_map_00.png` + `r3_info_map_hover5_Up.png` (troca de companhia),
  `r6_hover_NA02.png` (Distance/Cost) e `r6_posA_NA02.png` (escolha de aviao).
- Icones de Rltns lado a lado: `rtfull_Washington_US.png`, `rtfull_Moscow_RU.png`,
  `rtfull_Helsinki_EC.png`.

## §34 `read_city_panel` — o leitor do painel de cidade (ETAPA 5b, 23/08)

O §33 fotografou a tela e disse o que EXISTE; esta etapa escreve o **leitor**.
Codigo em `harness/world.py` (bloco "ETAPA 5b"), aceite em
`harness/prova_city_panel.py` (offline, 9 PNGs, 0 toques) e
`harness/prova_city_panel_vivo.py` (ao vivo, 3 regioes novas, 48 toques,
caixa 1.220.000K antes e depois).

### §34.1 API

| funcao | devolve |
|---|---|
| `on_city_panel(img)` | `True` so no painel de cidade do fluxo `negotiate` |
| `read_city_panel(img)` | dict com TODOS os campos (abaixo) |
| `read_city_pop_m(img)` | populacao em **milhoes** (float) |
| `read_city_total_slots(img)` | `(usados, capacidade)` |
| `read_city_table(img)` | `{"fl": {cor: n}, "slot": {cor: n}}` |
| `city_panel_bands(img)` | px de cada faixa colorida (assinatura da tela) |

Campos de `read_city_panel`: `on_panel`, `name` (**sempre None**, §34.4),
`name_ocr`, `name_hash`, `pop_m`, `econ`, `trsm`, `rltns_icon`, `slots_used`,
`slots_cap`, `table`, `ours` (`"carmim"`, §33.8), `our_slots`, `soma_confere`.

O leitor **so le**: nao navega, nao aperta botao, nao toca no savestate. Quem
navega e quem ja existia (`negotiate` -> mapa -> cursor -> um `A`, §33.3).

### §34.2 A segunda fonte (7 px) estava calibrada o tempo todo, em outra tela

O §33.5 declarou a fonte pequena o gargalo de DUAS telas. Ela **ja estava** no
harness: os digitos de `Total slots` e da tabela por companhia sao **byte a byte
os mesmos** de `QTY_DIGIT_MD5` (tela de quantidade de avioes, §31) — celula
**8x7**, md5 identicos para `1..6`. Os 4 glifos que faltavam (`0`, `7`, `9`, `/`)
foram colhidos aqui. Isso e **confirmacao independente do rotulo**: o "3" deste
painel e o mesmo "3" ja rotulado noutra tela, noutra etapa, por outro caminho.

Por que a forca bruta do §33.5 nao achou: ela procurou a fonte de **13 px** na
grade do §24 e varreu `y0 0..40` — a celula certa e de **7 px**, e a de 8x13
nunca casaria em alinhamento nenhum.

Duas armadilhas MEDIDAS, nao supostas:

1. **Binarizar por luminancia, nao por igualdade com `_st.WHITE`.** O painel usa
   DOIS brancos: `(255,251,255)` e `(239,235,239)`. Um leitor que exige o branco
   exato le metade da tela e ve celula vazia na outra metade.
2. **Converter para `L` ANTES do limiar, nunca `.point()` sobre RGB.** O
   `_bin_md5` que ja existe no `world.py` limiariza **cada banda separadamente**:
   carmim `(189,0,41)` e verde `(0,178,0)` virariam preto, mas azul
   `(57,58,255)` e laranja `(255,97,57)` **nao** — o mesmo digito hasharia
   diferente conforme a cor da coluna, e a falha so apareceria em 2 das 4
   colunas. O aceite testa exatamente isso (bloco `[4]`): o `0` da linha `Fl`
   nas 4 colunas coloridas tem que dar o **mesmo** caractere.

### §34.3 Geometria MEDIDA (nao herdada de outra tela)

- **Fonte grande** (`screen_text`, celula 8x13), linha `y0=24`: Pop `x[40,96)`,
  Econ `x[136,176)`, Trsm `x[200,256)`. Faltava **1 glifo** no atlas do §24: o
  ponto decimal (`dc965a0336` -> `"."`), agora em `glyphs.json` (43 glifos).
- **Fonte pequena** (celula 8x7), grade de **8 px**:
  - `Total slots`: ancorada em `x=0`. Usados alinhados a **direita** terminando
    na celula `x=24`; a barra `/` esta **sempre** em `x=32` (e parte do guard de
    `read_city_total_slots`); capacidade termina em `x=56`.
  - Tabela: celula mais a direita de cada coluna em `x = 136 + 32*i`, digitos
    alinhados a direita, ate 3 digitos. `Fl` em `y0=119`, `Slot` em `y0=135`.
- **Guard**: as 4 faixas coloridas em `y[118,146)` nas faixas de x do §33.1.
  MEDIDO: **660-692 px** por faixa nos 9 paineis; **0 px** em 48 frames de outras
  telas (um unico frame chegou a 23 px, numa faixa so). Corte em 400.

### §34.4 O que o leitor **recusa** a devolver (R1)

- **`name` = sempre `None`.** Os glifos MINUSCULOS do nome/pais nao estao no
  atlas do §24; `name_ocr` sai `'?????????????'` — falha **visivel**. O campo
  util e `name_hash` (md5 de `(0,0,200,32)`): deixa o chamador **conferir** que o
  painel e o da cidade para onde ele apontou o cursor. Bate com os hashes do
  §33.6.5 (`d8c92e23` = Washington).
- **`rltns_icon` = hash, nunca um nivel.** E aqui o §33.2 precisa de um reparo:
  o icone **NAO e um cracha de pais**. Mexico City (Mexico) devolveu
  `0ec3446e`, o **mesmo** de Helsinki (EC); Tehran (Ira) e Beijing (China)
  devolveram `ff89528c`, o **mesmo** de Moscow (Russia). Ou seja, 3 hashes
  distintos para 8 paises. O que sobrevive do §33.2 e a afirmacao mais fraca e
  ainda medida: o icone e **constante dentro de um pais** (US 6/6) e **se repete
  entre paises** — e um **valor** (compativel com "nivel de relacoes"), nao uma
  identidade. Continua sem ORDEM medida entre os 3 icones, entao traduzir para
  "bom/neutro/ruim" seria palpite (§33.6.2). Hash e dado.
- **Digito `8`**: nao apareceu em nenhum dos 12 paineis. Numero que o contenha
  sai `None`, nao um numero adivinhado.

### §34.5 Aceite offline — 9/9, e o leitor **corrigiu** o §33

`python harness/prova_city_panel.py` -> `ACEITE: PASSOU`. Quatro frentes:

1. **Positivo**: 9 paineis, todos os campos batem com o gabarito lido a olho no
   zoom 4x pelo §33.1.
2. **Negativo**: `on_city_panel` = `False` em **48** frames de outras telas
   (Info->map, hover sem `A`, pos-`B`, `r0c0` Distance/Cost, escolha de aviao,
   staff, orcamento, menu, mapa...). Zero falso positivo, e nenhum campo vaza
   quando o guard recusa. Este era o ponto cego real: offline TODO PNG do
   conjunto e o painel, entao o guard nunca dispararia sozinho.
3. **Oraculo**: soma das 4 colunas da linha `Slot` == `Total slots` usados,
   **9/9**. Cruza dois leitores independentes do MESMO frame (grade `x=0` da
   esquerda x grade `x=136+32i` da tabela).
4. **Fonte imune a cor**: mesmo digito nas 4 colunas coloridas -> mesmo hash.

**CORRECAO do §33.1 (R4/R5):** Miami nao e `1/ 53`, e **`1/ 35`**. O leitor
divergiu do gabarito humano e o zoom (`logs/etapa5a/r4_zoom_NA11_total_slots.png`)
deu razao ao leitor. E a **segunda** vez nesta investigacao que o OCR corrige o
olho (a primeira foi `0.6M` lido como `0.8M`, §33.1). O oraculo da soma **nao**
pegou o erro porque a CAPACIDADE nao entra nele — vale como aviso sobre o
alcance do proprio oraculo.

### §34.6 Aceite ao vivo — 3 regioes que o leitor nunca tinha visto

`python harness/prova_city_panel_vivo.py` (savestate `_e3b_base.state`).
Os PNGs do §33 cobrem 2 regioes (NA, EU). Aqui: SA, ME e AS —
**5 das 7 regioes do jogo** no total, 8 paises.

| cid | cidade / pais | Pop | Econ | Trsm | Total slots | rltns_icon | toques |
|---|---|---|---|---|---|---|---|
| SA02 | Mexico City / Mexico | 14.8M | 43 | 38 | 0/130 | `0ec3446e` | 9 |
| ME02 | Tehran / Iran | 7.0M | 58 | 30 | 0/122 | `ff89528c` | 11 |
| AS03 | Beijing / China | 14.0M | 54 | 48 | 0/102 | `ff89528c` | 9 |

Os tres valores foram **conferidos a olho** em `logs/etapa5b/panel_*.png`, um a
um, e batem digito a digito. `on_panel` true 3/3, `soma_confere` true 3/3,
`B_volta_ao_mapa` true 3/3, `cursor_verificado` true 3/3.
**Caixa 1.220.000K antes e depois**, 48 toques no total (R2 respeitado: sentinela
de caixa em cada `A`, nenhum `A` depois da tela de quantidade).

Ganho de cobertura que so o vivo deu: `pop_m` com **duas casas na parte inteira**
(`14.8`) e com **decimal zero** (`7.0`) — nenhum dos 9 PNGs tinha isso.

Nota sobre o criterio do script vivo: `soma_confere` **nao** cobre `slots_cap`,
`pop_m`, `econ` nem `trsm`. Por isso o script trata qualquer um desses vindo
`None` como FALHA explicita — sem isso ele imprimiria `PASSOU` com um campo
silenciosamente nao lido (por exemplo uma capacidade contendo o `8` que falta).
Mesmo assim, o criterio final continua sendo o PNG conferido a olho.

### §34.7 Limites honestos

1. A linha **`Fl`** estava **zerada** nos 12 paineis (9 offline + 3 ao vivo,
   §33.6.4). O leitor dela existe e le `0`, mas **nunca foi exercitado com valor
   nao-nulo** e continua sem significado medido.
2. O oraculo da soma valida a linha `Slot`. **Nao** valida `Fl`, nem a
   capacidade, nem Pop/Econ/Trsm — esses so tem a conferencia a olho.
3. As outras 3 cores continuam **sem dono medido** (R3): ordem de exibicao e
   dado, nao identidade. So a carmim tem dono, e por acao propria (§33.8).
4. Falta o digito `8` no mini-atlas da fonte de 7 px.
5. Nenhuma cidade com slots de mais de uma companhia foi vista ao vivo nesta
   etapa; a leitura multi-coluna vem dos PNGs de Seattle (`11/10`) e Denver
   (`12/12`), que sao 2 pontos.
6. Custo de navegacao inalterado (§33.3): `12 + 9*N` toques, ~1 min por cidade.
   O leitor **nao** torna a varredura completa viavel; ele torna a **consulta
   sob demanda** confiavel.
7. `read_city_panel` ainda **nao** esta ligado ao estado do piloto nem ao
   `schema.py` — esta etapa entrega o leitor, nao a integracao.

---

## §35 Intel de cidade no prompt (ETAPA 5d, 23/08) — e o cache NAO transfere

O §34 entregou o leitor e disse, no §34.7.7, que a integracao ficava para depois.
Esta etapa faz a integracao **e derruba a premissa em que ela ia se apoiar**.

Codigo: `harness/city_intel.py` (cache + recorte + codificacao compacta),
`harness/probe_intel_transfer.py` (a medida ao vivo),
`harness/etapa5d_medir.py` (o custo em chars), `pilot.build_state` (a ligacao).

### §35.1 MEDIDO: os valores do painel **mudam de savestate para savestate**

O plano era semear o cache com os 12 paineis ja fotografados (9 de `logs/etapa5a`,
3 de `logs/etapa5b`) e publicar `pop/econ/trsm/slots_cap` como "propriedade da
cidade", constante. `probe_intel_transfer.py` releu 3 desses paineis **ao vivo no
savestate que o piloto usa** (`f0_t02_route.state`), com sentinela de caixa em
cada `A` (caixa 1.014.360K antes, durante e depois; 26 toques):

| cid | cidade | cache (`logs/etapa5a`) | vivo (`f0_t02_route.state`) |
|---|---|---|---|
| NA13 | Washington | 1.2M / 90 / 48 / 34 de 116 | **0.6M / 60 / 42 / 27 de 68** |
| NA06 | Denver | 0.6M / 64 / 40 / 24 de 94 | **0.4M / 40 / 32 / ? de 47** |
| EU06 | Moscow | 9.6M / 56 / 38 / 0 de 105 | **6.5M / 37 / 20 / 0 de 71** |

**3 de 3 divergiram em todos os campos.** Nao e cidade errada: o hash do recorte
so do nome (§35.2) bate em Washington (`4376d3ff`) e Denver (`0df29b94`). E a
mesma cidade com outros numeros — a diferenca e de **epoca/cenario**. Sinal
independente disso no proprio frame: em `logs/etapa5d/panel_EU06.png` a Moscow do
piloto e da **"Soviet Union"**, e a de `logs/etapa5a` e da "Russia"; e o contador
de trimestre da RAM devolve **62 = JUL/1970** no savestate do piloto.

Consequencia adotada em `city_intel.usavel()`: **so entra no prompt registro
medido no savestate da propria run.** Os outros 9 ficam no `city_intel.json` com
`usar_no_prompt: false` e viram `historico` do cid quando ha as duas medidas —
nada de medida apagada, e a divergencia continua auditavel.

### §35.2 BUG no `name_hash` do §34: ele nao e hash de nome

`CITY_NAME_BOX = (0, 0, 200, 32)` **engloba a linha `y=24`**, que e a de
Pop/Econ/Trsm (as linhas de texto ficam em `y = 8 + 16i`, §24). Entao o
`name_hash` muda quando os **numeros** mudam:

```
logs/etapa5a/r4_panel_NA13.png  name_hash=d8c92e23   nome(y<20)=4376d3ff
logs/etapa5d/panel_NA13.png     name_hash=597feda0   nome(y<20)=4376d3ff
```

O §34.4 diz que o `name_hash` "deixa o chamador conferir que o painel e o da
cidade para onde ele apontou o cursor". Isso vale **dentro da mesma partida** e
so por sorte: qualquer coisa que mexa em Pop/Econ/Trsm muda o hash da cidade
certa. Para identidade use o recorte `(0, 0, 200, 20)` — `city_intel` grava os
dois (`name_hash_do_leitor` e `name_only_hash`). Cuidado com o segundo tambem:
ele inclui o PAIS, e "Russia" x "Soviet Union" e a mesma cidade com hashes
diferentes (medido em EU06).

### §35.3 O digito `8` que faltava (§34.7.4) apareceu — e o leitor recusou certo

Washington ao vivo mostra `Total slots 27/ 68`. `slots_cap` voltou **`None`**, e
`slots_used` de Denver tambem (a captura tem `8` em algum digito). E o R1
funcionando: `?` no prompt em vez de numero inventado. O glifo `8` da fonte de
**8x7** continua fora do mini-atlas — colher e trabalho de uma sessao com
`harvest_glyphs.py` sobre `logs/etapa5d/panel_NA13.png`, e destrava dois campos.

### §35.4 O registro de slots do piloto esta velho neste savestate

`EVAL_SLOTS_2000` da NA13=34 e NA06=12; o painel lido ao vivo da **27** e **11**.
Duas fontes discordantes no mesmo prompt e a classe de erro do §6, entao a
legenda do estado **declara a divergencia e manda acreditar no valor LIDO**. A
causa provavel e a mesma do §35.1: `EVAL_SLOTS_2000` foi medido no savestate de
2000 e `f0_t02_route.state` esta em 1970 (o `START_YEAR = 2000` de `pilot.py`
nao vale para este savestate; a data do prompt escapa porque vem da RAM).

### §35.5 O recorte, e por que ele nao e um top-N

O gargalo de cobertura **nao e o contexto do modelo, e o custo de medicao**:
~1 min de navegacao por cidade (§34.7.6), e a varredura da ETAPA 5c nunca
terminou (`city_intel.json` nao existia). Logo o criterio publicado e o unico
honesto: *toda cidade cujo painel foi lido ao vivo neste savestate* — hoje **3
de 89**. Um top-N por `econ x pop` exigiria ler as 86 restantes; ranquear so as
lidas devolveria o proprio vies de cobertura com cara de analise.

`cities_intel_declaracao` leva junto, no prompt: quantas de quantas, o criterio,
os cids descartados **com o motivo**, o que cada campo significa, o aviso de
envelhecimento da ocupacao e — o campo que mais importa —
`AUSENCIA_NAO_E_SINAL`: cidade sem intel nao e cidade ruim, a falta e do harness.
Sem essa linha o modelo ranqueia pelo que enxerga e descarta 86 cidades.

Ficam FORA por medicao (§34.4): `rltns_icon` (hash sem ordem medida), a linha
`Fl` (zerada em 12 paineis) e `name` (sempre `None`).

### §35.6 O custo, em chars (`python harness/etapa5d_medir.py`)

`prompt_tokens` nao e estimado: sai do `usage` de uma chamada por estado ao
`laguna-s-2.1-free` (`etapa5d_medir.py --tokens`), com o MESMO system prompt.

| estado | chars | vs A | prompt_tokens | vs A |
|---|---|---|---|---|
| **A** antes — `catalog_for_prompt_world`, sem intel | 17.121 | — | 6.667 | — |
| **B** antes + os 5 campos em TODAS as 95 cidades (**simulacao**) | 23.796 | **+39%** | 10.405 | **+56%** |
| **C** depois — linhas compactas + intel medida + declaracao | **13.763** | **−20%** | **6.033** | **−10%** |

O campo `cities_by_region` sozinho ia de **10.734** (63% do estado) para 17.409 no
cenario B; compactado ele cai para **5.077**; a declaracao do recorte custa 1.646
e a legenda 809. Ou seja: **a intel completa custaria +6.675 chars / +3.738 tokens
no formato antigo** — e o que paga esse espaco e a codificacao em linha, nao a
intel ser pequena. B e **simulacao**: uma linha real repetida 95 vezes so para
medir largura; nenhum desses valores encosta em `city_intel.json` nem no jogo.

Estado do turno REAL (ao vivo, `logs/etapa5d/pilot_final/turns.jsonl`): ver
§35.7 — `owned` e `routes` ao vivo diferem do contexto de bancada acima.

A informacao medida do formato antigo foi toda preservada (id, nome, slots,
`connected`, distancia real x estimada x ausente) — ver `cities_legend`.

### §35.7 A publicacao FALHA FECHADA (e por que precisou disso)

`usavel(rec, savestate)` nao tem default. `pilot.build_state` recebe
`savestate=pathlib.Path(a.state).name` do `main()`, e sem esse argumento
`slice_for_prompt` devolve **zero** intel com o motivo escrito no proprio
prompt. Um default de modulo teria publicado a Washington de 1970
(0.6M/60/42, 27 slots) numa run carregada de `eval_single_2000_lv5.state`
como se fosse atual — o §35.1 com cara amigavel. Medido offline:

```
savestate=None                         -> 0 linhas com intel
savestate='eval_single_2000_lv5.state' -> 0 linhas com intel
savestate='f0_t02_route.state'         -> 3 linhas com intel
```

### §35.8 Aceite e limites

Aceite: `python harness/pilot.py --turns 1 --run ../logs/etapa5d/pilot_final`,
savestate `f0_t02_route.state`, modelo `laguna-s-2.1-free`.

- estado do turno REAL: **13.897 chars / 6.145 `prompt_tokens`** (contexto de
  bancada: 13.763 / 6.033 — a diferenca e `owned`/`routes` lidos ao vivo)
- `cities_legend` e `cities_intel_declaracao` presentes; **3 linhas com intel**
  (NA13, NA06, EU06), declaracao `savestate=f0_t02_route.state`,
  `medido_no_trimestre=[62]`, `nossas_cidades_sem_intel=[NA02, NA03, NA05, NA14]`
- 4 acoes, **4 OK (100%)**, 0 erro de validacao; caixa 1.014.360K -> 1.013.480K;
  `end_turn` JUL/1970 -> OCT/1970 (contador 62 -> 63)
- o modelo **usou** o campo novo: o diario dele diz "Washington (NA13) with 34
  total slots / 27 mine" — leu o `nossos27` do painel ao lado do `slots=34` do
  registro. So que ele juntou os dois como "total" e "meus" — e leitura ERRADA:
  o total do aeroporto e 68 e 34 e so o que o harness anotou. A causa esta na
  propria linha, `slots=34 | ... slots27/?`: dois campos com o mesmo nome
  colados. **Corrigido depois do turno**, renomeando o do harness para
  `ledger=34` (o turno ao vivo rodou com o rotulo velho; a troca custou +205
  chars / +48 tokens e nao pede outro turno para ser verificada, porque e
  codificacao). Fica como aviso: legenda em prosa nao conserta nome ambiguo.

Artefatos: `logs/etapa5d/estado_A_antes.json`, `estado_C_depois.json`,
`estado_AOVIVO_turno1.json`, `pilot_final/turns.jsonl`, `transfer.json`,
`panel_{NA13,NA06,EU06}.png`, `harness/city_intel.json`.

Limites honestos:
1. **3 de 89 cidades** tem intel valida para este savestate. A cobertura so sobe
   gastando ~1 min por cidade — ou dando ao modelo uma acao `read_city(city)`
   que compre a leitura com uma acao do turno (proposta para a 5e, nao feita).
2. O cache e por savestate. Trocar de savestate **invalida** a intel toda; hoje
   isso e uma constante (`SAVESTATE_DO_PILOTO`), nao uma deteccao automatica.
3. **Propriedade envelhece DENTRO da run, nao so entre savestates.** Washington
   tem 0.6M em 1970 e 1.2M no outro cenario: 30 anos de jogo. A partida dura 80
   trimestres, e `usavel()` e chaveada por SAVESTATE, nao por trimestre — no
   turno 60 ela ainda publica a leitura do turno 1. Mitigacao parcial: cada
   registro carrega `medido_no_trimestre` e a declaracao leva o campo `IDADE`.
   Reler nao acontece.
4. `slots_used`/`our_slots` envelhecem dentro da propria run (as rivais negociam
   todo trimestre) e ninguem os re-le. O prompt avisa; o harness nao corrige.
5. Nao foi medido se ver a intel **melhora** a decisao — isto e encanamento com
   declaracao, nao um eval A/B.

---

## §36 ETAPA 1-RegressaoSlots — o medidor tem N posições e N muda por cidade (23/08)

**Sintoma** (2x reproduzido, bloqueava partidas): `negotiate_slots` falhava com
"saiu do mapa mas não reconheci a tela 'How many slots?' (medidor ilegível)" em
**NA06** e **NA02**, mas passava em NA05/NA14.

**Causa, levantada dos próprios PNGs com dump ASCII pixel a pixel**
(`logs/run_f0/neg_semqtd_NA06.png` = 152 px, `neg_semqtd_NA02.png` = 173 px):
a tabela `SLOTS_GAUGE_PX` (`215 + 22·(N−1)`) era a fórmula
`total = 43·escolhidos + 21·tocos + 88` avaliada **só** em `escolhidos+tocos == 5`.
O medidor **não tem 5 posições sempre**: tem **N**, e **N muda por cidade**.
Cidade com N≠5 caía fora da tabela → `None` → "medidor ilegível".

**O que fixa N NÃO foi medido.** Não é "slots livres": Denver mostra
`Total slots 24/94` (70 livres) com **N=2**, Phoenix `5/53` (48 livres) com **N=5**.
Por isso a recusa fala em *posições do medidor*, nunca em "a cidade só oferece 2
slots" (R1).

**Correção** (`world.read_slots_gauge` → `(escolhidos, N)`; `executor._read_gauge_stable`):
- cada posição é casada contra um **gabarito exato** (boneco inteiro / toco), mais
  moldura e soma de pixels como cruzamento independente;
- **armadilha medida** (`neg_EU11.png` = 105 px): o medidor é desenhado de cima
  para baixo e um frame do meio do desenho casa perfeitamente como `(1, teto 1)` —
  leitura bem-formada **não** prova desenho terminado. Por isso duas leituras iguais
  **e** `advance(240)` exigindo a mesma leitura;
- pedido `> N` é **RECUSADO** com o teto lido da tela e savestate restaurado —
  negociar 1 quando o modelo pediu 5 seria mentir (R5).

**Aceite medido** (`harness/prova_etapa1_slots.py all`, log
`logs/etapa1_slots/aceite_all.log`, savestate `eval_single_2000_lv5`):

| cidade | região | pedido | LIDO DE VOLTA | teto lido |
|---|---|---|---|---|
| NA06 | North America | 2 | 2 | **2** |
| NA02 | North America | 2 | 2 | **3** |
| EU11 | Europe | 2 | 2 | 5 |
| SA01 | South America | 2 | 2 | 5 |
| ME01 | Middle East | 2 | 2 | 5 |
| AF01 | Africa | 2 | 2 | 5 |
| NA05 | North America | 3 | 3 | 5 |

**7 cidades / 5 regiões**, todas com `pedido == lido de volta` e efeito confirmado
(funcionários livres −1 na barra do menu). **N estável**: NA06 reaberto do MESMO
savestate deu teto 2 nas duas leituras.

**Confronto offline com os frames do bug** (o mesmo leitor, rodado nos PNGs
arquivados que reproduziram a falha): `neg_semqtd_NA06.png` -> **(1, 2)**,
`neg_semqtd_NA02.png` -> **(1, 3)**, `neg_EU11.png` (frame no meio do desenho)
-> **None**. As duas cidades do bug agora leem, e o frame parcial e recusado —
e a evidencia que liga a correcao a causa levantada, nao so ao aceite ao vivo.

**Guarda (B3)**: pedir 5 em NA06 (teto 2) → recusa `False` com o teto lido,
barra de funcionários **4 → 4** e jogo no menu principal (lidos da tela), e a
negociação seguinte de 2 slots na mesma cidade fechou normalmente.


## §37 A SEDE virou parametro: `setup_game.py --city <ID>` (ETAPA 5-CidadeImplementar, 24/08)

A cidade inicial e o EIXO do experimento e e fixada pelo OPERADOR, nao escolhida
pelo modelo: o mesmo modelo roda em bases diferentes e a diferenca de desempenho
fica atribuivel a base.

### §37.1 Mecanica MEDIDA da escolha de sede
- tela de jogadores --(A)--> menu de 4 atalhos de regiao --(A)--> mapa da regiao.
  O atalho e conferido por hash do rotulo; **dentro do mapa `R` rola de regiao**
  e a regiao exibida e conferida por `world.detect_region` (NAmerica land=2275,
  Europe land=2073) — e assim que as 3 regioes sem atalho ficam alcancaveis.
- **O mapa da sede usa as MESMAS coordenadas de `world.WORLD_CITIES`**: os 24
  pontos detectados no frame da Europa batem 24/24 com o catalogo. Por isso a
  sede e enderecada por ID.
- **Hover**: o nome so acende na caixa de texto quando o centro do cursor cai em
  **(x+4..+8, y+4..+8)** do ponto da cidade — varredura em `_probe_hover_off.py`.
  O offset **(4,11)** anotado na ETAPA 4 **NAO acende**; o braco que "funcionou"
  chegou na cidade pela varredura fina, nao pelo offset (relato mentindo no
  sentido do sucesso, R4).
- **O nome da cidade e LIDO** (atlas 8x13, linha y=152, x=32): `?Washington`,
  `Amsterdam`, `?erlin`. O `?` fica onde o glifo nao esta no atlas (R1).
- A tela de apresentacao lista as 4 companhias com a CIDADE-SEDE de cada uma
  (`MAN` = a nossa, `COM` = computador) e, na direita, cenario e nivel ("4",
  "Lv 5") — tudo legivel pelo mesmo atlas. E o SEGUNDO gate de identidade:
  `setup_game.py` aborta se a linha `MAN` nao nomear a cidade mirada.
- **Adversarios sao sorteados por execucao**: a MESMA cidade (NA13) deu
  `Air LA / Air Mex / UK Air` numa passada e `MetLink / AirRoma / Air Mex` em
  outra. Logo **adversario diferente NAO prova cidade diferente** (R3).

### §37.2 A apresentacao pode COBRAR (R2)
MEDIDO em NA13: no meio das falas apareceu "Rep. of Tunisia ... $132000K is
requested" e o `A` cego aceitou — caixa **1.220.000K -> 1.088.000K**. Responder
NO a *toda* pergunta YES/NO tambem esta errado e foi medido: o NO nas perguntas
estruturais ("Customize each company's name and color?") **desfez a partida** e
o fluxo voltou para a tela de escolha de cenario. A solucao implementada e
cirurgica: a passada mede o caixa antes/depois de cada `A`, aborta na queda,
volta ao savestate da tela de jogadores e refaz recusando **aquela** tela
(identificada pelo recorte do texto do pedido). O criterio de parada da cadeia e
a assinatura do menu principal, nao um numero fixo de toques.
**NAO MEDIDO**: o replay-com-recusa nunca chegou a rodar ate o fim — na passada
final o evento nao apareceu. O que esta medido e a DETECCAO da queda de caixa.

### §37.3 Aceite (dois mundos, lidos de volta)
`prova_sede.py <stateA> <stateB>` carrega cada savestate e le da tela:

| campo (lido do jogo) | `eval_NA13_2000_lv5` | `eval_EU10_2000_lv5` |
|---|---|---|
| cidade no hover | `?Washington` | `?erlin` |
| companhia (Info->fleet) | `Federal` | `?erlin` |
| caixa | 1.220.000K | 1.510.000K |
| frota | MD100 x6 | 777 x6 + A340 x1 |

Veredito: MUNDOS DISTINTOS (`logs/prova_sede/prova.json`, nenhum campo igual).

Cenario e nivel tambem sao LIDOS da tela de apresentacao em cada criacao
(coluna x=190..250: `4` em y=40, `Lv 5` em y=64) e o setup ABORTA se nao baterem
com o rotulo do savestate — e o que impede `--from-state` de carimbar `lv5` num
state criado em outro nivel.

Ressalva medida: numa das leituras `read_fleet` DEVOLVEU LINHAS A MENOS que na
leitura seguinte do mesmo state (`777 x6 / A340 x1` contra `747-400 x1 / 777 x6
/ A340 x1`; e `MD100 x6` contra `MD12 x1 / MD100 x6`). Nos dois casos o que
mudou foi a PRIMEIRA linha — pista para quem for investigar, porque `read_fleet`
tambem alimenta o prompt a cada turno em `pilot.py`. Na repeticao final as duas
leituras bateram. A frota entra como evidencia SECUNDARIA; companhia e caixa
sao os campos estaveis.

### §37.4 O prompt deixou de dizer "Federal / NA13 (Washington)"
`pilot.sede_do_savestate()` le o JSON que `setup_game.py` grava ao lado do
savestate e alimenta `company.name`, `company.home_base`, `company.home_region`
e `company.home_fonte`. Sem JSON ao lado, o campo volta ao padrao e **diz que
foi declarado, nao lido**. Junto com isso, o que era chumbado para Washington
passou a depender da sede: `hubs={sede}`, a rota inicial NA13->NA06 (so existe
no savestate pos-F0), `EVAL_SLOTS_2000` (medido em Washington; fora de NA13 o
ledger comeca vazio) e `MEASURED_DIST_FROM_HOME` (fora de NA13 as distancias
voltam a "?"; `distance_mi` so tem catalogo de pixels da America do Norte).
**NAO MEDIDO**: nenhuma run de eval completa foi executada a partir de
`eval_EU10_2000_lv5.state` — o que foi verificado e o `build_state` montando o
prompt com a sede certa nas duas cidades.

---

## ETAPA 1-PonteLonga (25/08) — a ponte aguenta; quem nao aguenta e `detect_region`

### 1. A excecao do NLua no SCREENSHOT era COLISAO DE INSTANCIAS, nao vazamento

As 4 corridas de 12 turnos que morreram com `A .NET exception ... 51692872 /
2295192` no `client.screenshot` tinham DUAS ou mais EmuHawk servindo o MESMO
diretorio IPC — logo, escrevendo no MESMO `screen.png`. O .NET levanta
IOException quando dois processos abrem o arquivo para escrita ao mesmo tempo;
a excecao chega ao Python como aquele numero opaco.

Medicao que separa as hipoteses (registrada no comentario de `bridge.lua`):
3 instancias = 5 falhas nas 10 primeiras tentativas; 1 instancia = 0 falhas em
120. Aleatoria por tentativa, nao crescente com o tempo -> NAO e acumulo de
handle no Lua (hip. a) nem degradacao do emulador (hip. c). Savestate
corrompido (hip. d) nunca teve evidencia.

Correcao (ja no codigo, sem reciclo de emulador):
- `bridge.lua`: `owner.txt` + TOKEN por processo; quem sobe por ultimo vira dono
  e as instancias antigas param de tocar no IPC. Token entra no payload do
  `INFO` para o Python PROVAR com quem falou (R4).
- `bridge.py`: `acquire_bridge_lock` — lockfile por IPC com `msvcrt.locking`,
  liberado pelo SO se o processo morre.
- Contadores `SCREENSHOTS_OK` e `REPLACE_RETRIES` impressos no fim da run.

**Nao existe mecanismo de reciclo do emulador e nao foi preciso.** O
`pilot.py` imprimia `reciclagens do emulador: 0` como literal — numero
inventado, corrigido para `nao implementado (nao foi preciso)` (R4).

Evidencia de que nao ha degradacao: a MESMA instancia de EmuHawk (token
`1787615299-1-972758879`) serviu a run de 24/08 no frame 133.040 e a de 25/08 no
frame 1.717.116 — ~1,6 milhao de frames depois, sem uma unica falha de
screenshot.

### 2. NEGATIVO MEDIDO: `detect_region` cega a partir de 2 rotas desenhadas

A run longa passou, mas `open_route` fez 2/7. Motivo LIDO dos PNGs do mapa
(`logs/run_f0/map_t*.png`, `world.land_pixels`):

| turno | rotas no mapa | land_pixels | melhor / 2o | detect_region |
|---|---|---|---|---|
| t1 | 0 | 2265 | r0 d=3 / r2 d=192 | 0 |
| t2 | 1 | 2250 | r0 d=12 / r2 d=177 | 0 |
| t3 | 2 | 2183 | r0 d=79 / r2 d=110 | **None** |
| t5 | 2 | 2166 | **r2** d=93 / r0 d=96 | None |
| t12 | 2 | 2138 | **r2** d=65 / r0 d=124 | None |

`REGION_LAND[0]=2262` e o vizinho confundivel `REGION_LAND[2]=2073` distam 189.
Com `margin=2.0`, aceitar r0 exige `dist < 63`, isto e `land > 2199`. Cada rota
desenhada TAPA verde: 2 rotas ja derrubam o numero para 2183 e a leitura vira
`None` **para sempre** — dai o `regiao do mapa ambigua` em todo turno >= 3 e o
`_goto_region` recusando `open_route`. Pior: de t5 em diante o vizinho mais
proximo e a regiao 2, ou seja, um fallback "pega o mais perto" chutaria a regiao
ERRADA.

O docstring de `detect_region` afirma que rotas mexem "poucas dezenas de pixels,
bem abaixo da separacao de 112" — a medicao acima o desmente: −127 pixels com 2
rotas, e a separacao que importa e 189 dividida pela margem, nao 112.

Consequencia: **a ponte nao e mais o bloqueio de uma partida de 20+ turnos;
`detect_region` e.** Assinatura por contagem global de verde nao sobrevive ao
mapa sendo pintado pelo proprio jogo. Conserto candidato (NAO medido): ler a
regiao por algo que rotas nao alteram (rotulo/mascara fora da faixa das linhas),
ou normalizar descontando os pixels de rota.

### 3. Aceite medido (25/08)

- `logs/ponte_longa/aceite12b.log` (24/08): **12/12 turnos completos**,
  `screenshots ok nesta run: 1524 | retries de os.replace: 0`.
- `logs/ponte_longa/aceite12c.log` (25/08, run desta etapa, ~57 min):
  chegou ao t12 com **0 ocorrencias de "exception"/".NET"/"Traceback"** no log.
  A tarefa de background que a lancou foi reportada `killed` por volta das
  09:05, na primeira acao do t12; a CAUSA DO KILL NAO FOI ESTABELECIDA (nao foi
  o timeout de 600s que passei — o processo viveu 57 min). O que se pode afirmar
  e que a morte foi FORA da ponte — `logs/eval_random_NA13_20260825-080815/stats.json`
  registra `turnos: 11, acoes: 20, ok: 16, turnos_falhos: 0`. Nao ha resumo.json
  nem contador final de screenshots porque o processo nao chegou ao print final.
- Stress direto no mesmo EmuHawk depois das duas runs: **200 screenshots
  seguidos, 0 falhas, 0 retries de os.replace**, mesmo token de dono
  (`1787615299-1-972758879`) — a instancia serve desde 24/08.

Antes da correcao: 4 corridas de 12 turnos, 4 mortes com a excecao do NLua entre
o t1 e o t3. Depois: 2 corridas passando de t9 (onde a de 24/08 morrera) e
chegando ao t12.

### 4. NAO MEDIDO / suspeita aberta: baseline nao e reprodutivel no caixa

Mesmo savestate, mesmo `--seed 0`, mesma sequencia de acoes — o caixa diverge
e a divergencia e PERSISTENTE, nao ruido de um turno. As tres runs entram no t3
com 1183730K e a mesma lista de acoes; `aceite12`/`aceite12c` saem −440K e
`aceite12b` sai +1940K — e dai em diante `aceite12b` fica POSITIVA todo turno
(+1550, +1530, +1570) enquanto as outras duas ficam negativas (−700, −720, −680).
Alguma coisa nos t1–t2 de `aceite12b` diferiu de um jeito que o log nao mostra
(as rotas custaram o mesmo; suspeita nao medida: tarifa/voos ou frames de
acomodacao). Uma run cuja economia se bifurca de vez nao serve de piso. Se a baseline aleatoria e o PISO
de comparacao contra um modelo, essa variancia precisa ser medida (N corridas do
mesmo seed) antes de qualquer leitura de "o modelo bateu a aleatoria".

## ETAPA 1-VerRegiao (25/08) — assinatura de regiao por FORMA, nao por contagem

### 1. Diagnostico confirmado e conserto MEDIDO

A etapa anterior mediu que `detect_region` cegava a partir de 2 rotas
desenhadas. A causa e estrutural, nao de margem: `land_pixels` e uma contagem
GLOBAL, e rotas/avioes/pontos de cidade TAPAM verde. Afrouxar a margem so
trocaria "recusa" por "erra em silencio" (em t5 o vizinho mais proximo ja era a
regiao 2 quando a verdade era 0).

A propriedade que conserta: **o desenho do jogo so REMOVE verde, nunca pinta
verde FORA da massa de terra da regiao**. Logo a mascara observada e um
subconjunto (aproximado) da mascara de referencia da regiao certa, e a
PRECISAO `|obs & ref| / |obs|` e invariante ao desenho. A REVOCACAO
`|obs & ref| / |ref|` e a unica que cai com as rotas.

Implementacao: ranking por PRECISAO, revocacao so como piso largo.

| medida | valor MEDIDO |
|---|---|
| precisao da regiao certa, 12 `map_t*.png` reais (0 a 2+ rotas) | 0.998 a 0.999 |
| precisao do 2o colocado nesses mesmos 12 | 0.555 a 0.565 |
| maior precisao de regiao ERRADA em mapa limpo (7x7) | **0.774** (r1 obs vs ref r0) |
| revocacao da regiao certa, pior caso sintetico (r5, 12 rotas) | 0.813 |
| revocacao com dialogo tapando 60% da faixa | 0.525 -> recusa |

Limiares em `world.py`: `REGION_PREC_MIN=0.90`, `REGION_PREC_2ND_MAX=0.80`,
`REGION_REC_MIN=0.60`, `REGION_N_MIN=200`.

**Por que o piso de revocacao e 0.60 e nao 0.85** (o ponto que quase virou uma
falha silenciosa nova): a perda de pixels por rota e ABSOLUTA, nao proporcional.
A regiao 0 perdeu 128 px em 12 turnos = revocacao 0.943. A MESMA perda na
regiao 5 (326 px) daria 0.61. Um piso calibrado na regiao 0 recusaria as
regioes pequenas assim que o modelo comecasse a abrir rota nelas — e a regra de
hubs exige rota nas 7 regioes. O piso largo e deliberado: quem separa as
regioes e a precisao (0.999 vs 0.774 no pior caso), nao a revocacao.

### 2. Cor das linhas de rota, MEDIDA

Diff de `logs/run_f0/map_t01.png` -> `map_t12.png`, pixels que eram verde e
deixaram de ser: **(90,89,90) 688px**, (0,0,0) 263px, (255,251,239) 39px
(pontos de cidade), (57,58,255) 22px. Total 1099 px em resolucao cheia, ~5,4%
da terra da regiao 0. Essa cor alimenta os mapas sinteticos da bateria B.

### 3. Aceite OFFLINE — `harness/prova_detect_region.py`

- **A. positivo real**: 12/12 `logs/run_f0/map_t*.png` -> regiao 0 (antes:
  2/12, o resto None).
- **B. positivo sintetico**: 7 regioes x {2,6,12} rotas x 20 sorteios = **420
  mapas, 420 certos**. Cobre as regioes pequenas, que nao tem PNG real com rota.
- **C. negativo**: dialogo sintetico tapando 60/80/100% da faixa -> None;
  5 telas reais de dialogo sobre o mapa (`etapa1/yesno_antes.png`,
  `etapa1/dem_*`, `setup/04b_players.png`) -> None. O detector NAO virou um
  "aceita qualquer coisa".

`test_harness.py --offline`: 17 testes, 17 OK, 0 falha, exit 0.

Nota de metodo (R4): a primeira varredura "negativa" que fiz acusou 38 falsos
positivos em 381 telas. Ao ABRIR as telas, todas eram mapa de verdade —
`hub2/p1_menu_reg1.png` e America do Sul (n=1019 ~ ref r1=1016),
`adjust_aceite/stuck2.png` e Oceania com sprites de aviao (n=603 ~ ref r6=613).
O conjunto negativo e que estava mal rotulado, nao o detector. As telas que
importam como negativo sao as de verde PARCIAL (dialogo por cima do mapa), nao
as de verde zero — essas qualquer limiar recusa e nao provam nada.

Arquivos: `harness/region_masks.json` (mascaras congeladas),
`harness/gen_region_masks.py` (gerador), `harness/prova_detect_region.py`
(aceite). As mascaras sao congeladas de proposito: `logs/` e area de trabalho e
o detector nao pode depender de arquivo de log. `reg_7.png` foi descartado —
`land_pixels(reg_7)==2262==land_pixels(reg_0)`, e o wrap-around do ciclo de R.

### 3b. Aceite AO VIVO (25/08) — `logs/etapa1_verregiao/vivo_r1.log`

Run `--model random --seed 0 --city NA13 --turns 6`, mesmo savestate das runs
de aceite anteriores. t1 e t2 sao byte-a-byte iguais aos das runs antigas
(mesmas rotas, mesmo caixa 1220000K -> 1183730K), entao a comparacao no t3 e
limpa.

Do t3 em diante, com 2 rotas ja desenhadas — exatamente onde o detector antigo
cegava:

- A linha `regiao do mapa ambigua — slots mantidos` **desapareceu**. Ela
  aparecia em TODO turno >= 3 nas tres runs antigas.
- `negotiate_slots` passou a logar **`regiao_verificada=True`** no t3 (SA04) e
  no t4 (AS15). Nas runs antigas era `regiao_verificada=False` em todas as
  negociacoes de t >= 3.
- **`[t4] open_route -> OK: rota NA13->NA03`** (3 voos/sem, tarifa low, caixa
  1183010K -> 1163900K). E o criterio de aceite da etapa: `open_route` ACEITO
  em turno >= 3. Nas tres runs antigas, todo `open_route` de t >= 3 foi
  recusado por cegueira (t3, t7, t9, t11).
- Contagem na run inteira: **0 ocorrencias de "ambigua"**. Nas runs antigas era
  uma por turno de t3 ao t12. O contador de rotas do harness chegou a
  `rotas 3` no t5 — o detector segue lendo a regiao com 3 rotas no mapa.

Distincao que importa (R4): no **t3** o `open_route` ainda FALHOU, mas por
motivo LEGITIMO e diferente — `NA01 recusado ... nao temos slots no destino
(regiao North America, cursor=(18, 24))`. O harness LEU a regiao (North
America), chegou ao destino, e quem recusou foi o jogo, por falta de slot. Isso
e o comportamento correto, nao cegueira. A prova de que o detector destravou o
`open_route` e o t4, nao o t3.

Efeito colateral esperado: a partir do t3 a sequencia de acoes DIVERGE das runs
antigas (t3 sorteou NA01 em vez de NA06). E consequencia direta do conserto —
com a regiao legivel, mais candidatos entram na lista de legais e a baseline
aleatoria sorteia de um conjunto maior. Runs antigas e novas nao sao
comparaveis acao a acao.

### 4. NEGATIVO MEDIDO: a bifurcacao da baseline NAO e causada pelas recusas

A hipotese de trabalho era que as recusas nao-deterministas de `open_route`
faziam as partidas divergirem. **Ela e FALSA, e a prova ja estava nos logs.**

Diff programatico de `logs/ponte_longa/aceite12.log`, `aceite12b.log` e
`aceite12c.log` (mesmo savestate, `--seed 0`):

- **21 acoes em comum, 21 identicas** — mesmo verbo, mesmo alvo, mesmo
  veredito. As recusas de `open_route` acontecem nos MESMOS turnos (t3, t7, t9,
  t11) nas tres runs. Recusas diferentes apareceriam como acoes diferentes.
- Ainda assim o caixa bifurca:

| turno | aceite12 | aceite12b | aceite12c |
|---|---|---|---|
| t1 | −19720K | −19720K | −19720K |
| t2 | −16550K | −16550K | −16550K |
| t3 | −440K | **+1940K** | −440K |
| t4 | −700K | **+1550K** | −700K |
| t5 | −720K | **+1530K** | −720K |
| t6 | −680K | **+1570K** | −680K |
| t7 | −700K | −700K | −700K |
| t8 | −710K | **+590K** | −710K |
| t9 | — | +460K | −840K |

A divergencia nasce no `end_turn` do t3: as tres entram com 1183730K, a mesma
acao, e saem 1183290K / 1185670K / 1183290K. Delta de 2380K num turno em que
nenhuma acao do agente foi executada com sucesso. **A causa esta na liquidacao
trimestral do proprio jogo, nao no agente e nao no detector.**

Diff de LINHA CHEIA dos blocos t1-t2 de `aceite12b` vs `aceite12c` (nao so as
linhas de acao): as 19 linhas sao **identicas**, exceto numero de frame da
ponte, caminho da run e timestamp. Nenhum aviso a mais, nenhum popup a mais,
nenhuma retry. A primeira linha que difere de verdade e exatamente o
`end_turn` do t3. **Nada do que o harness registra distingue as tres runs.**

HIPOTESE DESCARTADA: cheguei a escrever aqui que o RNG do jogo avanca com os
frames do emulador e que por isso as runs divergiam (frames iniciais 3.054 /
133.040 / 1.717.116). **Os proprios numeros refutam isso**: as duas runs de
frame MAIS DISTANTE (3.054 e 1.717.116) concordam entre si (−440K) e a do meio
(133.040) e a discrepante. Os tres frames sao pares, entao paridade tambem nao
separa. O agrupamento e 12/12c contra 12b, e a contagem de frames nao o explica.
Registro aqui a hipotese e a sua refutacao porque ela ja estava escrita (R4/R5).

O QUE SE PODE AFIRMAR: alguma coisa no estado do emulador que o log NAO captura
diferiu na run `aceite12b`, e o efeito aparece na liquidacao trimestral do jogo,
nao nas acoes do agente. Causa NAO IDENTIFICADA. Proximo teste, agora que o
detector foi consertado: duas runs da mesma seed com o EmuHawk **relancado do
zero** nas duas (nao reusando instancia viva), registrando o frame inicial ao
lado da tabela de caixa. Rodar contra uma instancia quente ~100k frames adiante
tornaria a comparacao ininterpretavel — nao daria para saber se e o mesmo
fenomeno ou um novo.

Consequencia pratica: **a baseline `random` nao serve de piso contra modelo
enquanto isso nao for resolvido**, e o conserto do `detect_region` — embora
necessario — nao era o caminho para resolve-la.

### 5. Correcao de um relato antigo (R4)

O docstring de `detect_region` afirmava que rotas mexem "poucas dezenas de
pixels, bem abaixo da separacao de 112". Medido: −128 px com 2 rotas, e a
separacao que importava era 189/margem, nao 112. O texto foi removido junto com
a heuristica. `REGION_LAND` ficou no codigo apenas como referencia historica —
nao e mais consultado por `detect_region`.

### 6. Achado lateral NAO perseguido: token de dono da ponte degradou

A run ao vivo subiu uma instancia nova e o log traz
`[ponte] viva (frame 66024, dono 1787662703-table: 0000015E67420CA0)`. O token
da etapa anterior era `1787615299-1-972758879`. O `table: 0000015E...` e uma
TABELA Lua sendo convertida em string dentro do token — o mecanismo de
"provar com quem falei" da ETAPA 1-PonteLonga fica degradado (o endereco da
tabela nao identifica processo de forma estavel entre reinicios). NAO consertado
nesta etapa; anotado para nao se perder.

### 7. TETO do detector, MEDIDO (offline) — e o modo de falha e SEGURO

A queixa original era "quanto mais o modelo joga, mais cego o harness fica". O
teto novo foi medido no mesmo gerador sintetico, subindo o numero de rotas bem
alem dos 12 da bateria B (30 sorteios por celula):

| rotas | r0 | r1 | r2 | r3 | r4 | r5 | r6 |
|---|---|---|---|---|---|---|---|
| 12 | 30/30 | 30/30 | 30/30 | 30/30 | 30/30 | 30/30 | 30/30 |
| 20 | 30/30 | 30/30 | 30/30 | 30/30 | 30/30 | 30/30 | 30/30 |
| 30 | 30/30 | 30/30 | 30/30 | 30/30 | 30/30 | 30/30 | 30/30 |
| 40 | 30/30 | 29/30 | 30/30 | 30/30 | 30/30 | **7/30** | 30/30 |

**Todas as 7 regioes aguentam ate 30 rotas desenhadas.** A primeira a ceder e a
menor (r5, 326 px de terra) a 40 rotas, e cede pela REVOCACAO (0.54 < 0.60),
nao pela precisao. Uma partida de 20 turnos nao chega perto disso.

O que torna o teto aceitavel: **o modo de falha e sempre a recusa.** Em
7 regioes x {40, 60, 80} rotas x 30 sorteios = **630 mapas de estresse**:
354 certos, 276 `None`, **0 regiao ERRADA**. A precisao do 2o colocado nunca
passou de 0.79 em nenhuma dessas 630 telas, entao o detector nunca chega a
preferir a regiao vizinha. Era exatamente o risco central da etapa ("errado em
silencio e pior que recusar") — e ele nao se materializa nem no estouro.
