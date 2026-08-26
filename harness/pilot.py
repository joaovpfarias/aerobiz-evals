"""Piloto automatico: roda N trimestres com o LLM decidindo e o harness executando.

Estado por turno = caixa lido da RAM + contadores mantidos pelo harness
(trimestre, rotas abertas, negociacoes) + catalogo de cidades. Tudo que o
agente ve e verificavel; nada vem de suposicao.

Uso: python pilot.py --turns 20 [--state ../states/f0_t02_route.state] [--run ../logs/pilot_auto]
"""

import argparse
import json
import pathlib
import time

import city_intel
import obs
from bridge import BizHawkBridge
from executor import Executor
from macros import Game
from PIL import Image

from world import (AIRCRAFT_CATALOG, CURSOR_X, EVAL_SLOTS_2000, FLEET_START,
                   read_fleet, read_routes, on_budget_screen, read_budget_levels,
                   read_budget_numbers, read_budget_orders, BUDGET_COLS,
                   REGION_NAMES,
                   WORLD_CITIES, catalog_for_prompt_world, cities_of_region,
                   distance_mi, MEASURED_DIST_FROM_HOME,
                   cities_with_slots, detect_region, free_staff_menu, read_cash_k,
                   quarter_to_date, read_quarter_index,
                   read_victory, victory_na_signature)

QUARTER_NAMES = {1: "JAN", 2: "APR", 3: "JUL", 4: "OCT"}

# Ano inicial do CENARIO. O eval usa o cenario 4 (2000-2020); deixar 1970 fixo
# fazia o modelo planejar duas decadas na epoca errada.
START_YEAR = 2000
START_QUARTER = 1


SUPPORTED = ("open_route", "negotiate_slots", "buy_aircraft", "open_hub", "adjust_route",
             "open_venture", "wait", "ad_campaign", "close_hub",
             "set_budget")
             # SAI 24/08 ETAPA 2-OraculosFracos: `return_slots`. MEDIDO ao vivo,
             # 2 corridas, savestate eval_single_2000_lv5, NA06/Denver com 12
             # slots NOSSOS e ZERO rotas (nada ocupado):
             #   corrida 1 (1 `A` de confirmacao): parou na pergunta aberta
             #     "Will you give back 1 slot to" — nada commitado;
             #     nossos slots 12 -> 12 no painel, caixa 1.220.000K parada.
             #     (logs/suite/return_slots/return_slots_NA06_confirmado.png)
             #   corrida 2 (cadeia de ate 6 `_step()` com parada no menu, o
             #     mesmo remendo que consertou `close_hub`): a cadeia atravessa
             #     as confirmacoes e o jogo VOLTA AO MAPA de selecao de cidade
             #     com a textbox vazia; travou em A5; nossos slots 12 -> 12,
             #     caixa 1.220.000K parada. Mesma captura, agora mostrando o mapa.
             # Ou seja: com oraculo HONESTO (our_slots do painel da cidade, §33.8)
             # a acao NAO tem efeito medido em nenhuma das duas cadeias testadas.
             # O oraculo antigo ("funcionarios livres +1", §17.1, 3->3 em 2
             # corridas) era falso por construcao — devolver slot nao despacha
             # funcionario — e por isso mascarava isto com ok=True.
             # HIPOTESE NAO TESTADA (nao entra no estado, R1): o cursor do
             # YES/NO de "give back 1 slot" pode estar em NO por padrao; o
             # executor nunca mediu esse cursor, so assumiu YES.
             # `_do_return_slots` FICA no executor (guardado: le a recusa do
             # jogo, exige queda medida, restaura estado) para quem for calibrar
             # — mas o modelo nao pode mais pedi-la. 10 acoes honestas > 11 com
             # uma mentira.
             # set_budget VOLTOU 19/08: 6/6 casos (Repair/Ad/Service x sobe/desce)
             # com a ordem lida de volta DEPOIS de confirmar, colunas vizinhas
             # intactas e caixa parado — CALIBRATION §28. A remocao de 18/08 se
             # apoiava no diagnostico "Down-only", que era sintoma; a causa era
             # comparacao de caixa alta/baixa e mais tres bugs empilhados.
             # CONTINUAM FORA: suspend_route, close_route (§19, nao consertados)
# ENTRA 18/08 ETAPA 12-HubsCompleto: `close_hub` (r1c0, aba Close) —
# CALIBRADO AO VIVO. O gate antigo (funcionario livre saiu) era SEMPRE falso
# para essa acao e `_restore_guard()` desfazia fechamentos que tinham
# funcionado de verdade; reescrito para exigir CREDITO de caixa (fechar
# hub credita, nao debita) e uma cadeia de ate 6 `_step()` com parada
# antecipada no menu (a cadeia real tem 2 confirmacoes YES/NO, nao 1 —
# ver docstring de `_do_close_hub` e ACTION_SPACE.md r1c0). Round-trip
# fechar+reabrir verificado ao vivo em `_verify_close_hub_final.py`.
# ENTRA 18/08 ETAPA 10-Marketing: `ad_campaign` (r1c1) — CALIBRADO. Fluxo de
# sucesso e as duas recusas medidos ao vivo (`_verify_adcampaign.py`,
# `_verify_adcampaign_refusal.py`), reverificado nesta sessao: caixa
# 1.040.220K -> 1.038.420K, -1.800K EXATOS. Pre-requisito: `open_venture`
# (venture cultural comprado) + 1 `end_turn` (fica "pronto"). Ver
# `executor.py::_do_ad_campaign` e ACTION_SPACE.md ("r1c1 — Campanha de
# anuncio").
# 18/08 ETAPA 3-RotaFechar: suspend_route e close_route CONSERTADAS
# - Ambas abriam dialogo YES/NO que NAO EXISTE; real: tela de selecao de mundo
# - Documentado em CALIBRATION.md §19 (bug report inicial) com evidencia de imagens
# - Padrão adotado: point_cursor_at_world (como open_venture) + 1 A exato + menu
# - Medição pendente: efeito real (Susp = pausa reversível?, Close = rota some?)
# REGRA: so entra aqui ferramenta CALIBRADA (ver CALIBRATION.md) — alavanca que
# faz outra coisa e pior que alavanca ausente.
# ENTRA em 17/08: `adjust_route` (route, flights_week?, fare_level?) — CALIBRADO
# (CALIBRATION §18): mesma alavanca de open_route (1 toque=+1 voo, 1 toque=+5%
# tarifa), mas Flts tem TETO POR ROTA nao caracterizado (o executor detecta e
# reporta o valor REALMENTE alcancado, nunca o pedido). So opera sobre a rota
# default-mostrada — com mais de uma rota aberta a acao recusa (sem navegacao
# de lista calibrada ainda).
# OFERECIDOS (medidos): `fare_level` (1 toque = +5% sobre a media) e
# `flights_week` (1 toque = +1 voo), calibrados em 12/08.
# ATUALIZADO 19/08 (ETAPA 3a, CALIBRATION §31): `planes` e `aircraft_index`
# deixaram de ser "nunca medidos". Os dois agora sao lidos DE VOLTA da tela a
# cada toque (`Executor._pick_planes` / `_pick_aircraft`), com recusa explicita
# quando o alvo e inalcancavel (teto de unidades disponiveis / indice fora do
# ciclo de modelos que possuimos). O motivo historico de manter `aircraft_index`
# fora do prompt — "o harness nao le Info->fleet" — CAIU: o pilot ja le a frota
# por turno (`read_fleet`) e a ordem da tabela e a mesma do seletor, entao o
# indice deixou de ser cego. Texto historico abaixo, preservado:
# FORA: `planes` (nunca medido) e `aircraft_index` — este ultimo por MEDICAO, nao
# por omissao: o seletor de aeronave so cicla modelos que a companhia possui e o
# savestate do eval tem um unico modelo, entao o parametro nao faz nada
# (CALIBRATION §7 — CORRIGIDO em §13: com DOIS modelos na frota o seletor cicla
# normalmente; o "nao e alavanca" era artefato de frota de modelo unico somado
# a toques engolidos pela datilografia). Continua FORA do prompt porque o
# indice e a POSICAO NA FROTA e o harness ainda nao le a tabela Info->fleet:
# oferecer o indice sem dizer a que aviao ele corresponde e dar ao modelo uma
# alavanca cega.
# ENTRA em 19/08 (ETAPA 3b-a, CALIBRATION §32): `negotiate_slots.slots` (1..5).
# A tela "How many slots?" SEMPRE existiu e a macro sempre apertava A nela sem
# olhar, ficando com o padrao 1. Agora a quantidade e escolhida e LIDA DE VOLTA
# do medidor de bonequinhos a cada toque; fora de 1..5 e recusa (o medidor
# satura em 5 e nao da a volta, medido nos toques 5..8).
# NAO ENTRA (ETAPA 3b-b, medicao NEGATIVA em §32): `employee`. Ver la.
# ENTRA em 15/08: `buy_aircraft` (model, qty) — calibrado em CALIBRATION §12,
# com debito de caixa exato como verificacao de efeito.
# ENTRA em 17/08: `open_hub` (region) — CALIBRADO: custa $28.800K na hora
# (Construction Costs, lido da tela "Hub Set-up") + 1 negociador, verificado por
# DOIS sinais independentes. E a alavanca mais importante do jogo: toda rota
# parte de um hub nosso, entao sem ela o modelo esta preso a America do Norte e
# a condicao de vitoria ("hub em toda regiao") e inatingivel por construcao.
# ENTRA em 17/08: `open_venture` (city, type_index?) — CALIBRADO AO VIVO
# (ETAPA 5-Venture, CALIBRATION §21): compra o business venture no indice
# `type_index` (default 0) do catalogo DESSA CIDADE — catalogo e preco NAO sao
# fixos, variam por cidade (Washington: Concert Hall/Grand Hotel/Commuter
# Airline, $144K/$288K/$576K; Denver: 1o tipo ja e "Arts Pavilion" $27K). Como
# o hub, debita o caixa NA HORA mas fica em negociacao por meses — Info->
# facilities e a campanha de anuncio (r1c1) continuam sem contar a compra
# ate la (medido 17/08, sem contador `ventures_pending` implementado ainda —
# o modelo NAO deve assumir que o venture ja esta ativo so porque a acao
# devolveu sucesso).
# ENTRA em 18/08: `return_slots` (city) — CALIBRADO (ETAPA 6-Reversos,
# CALIBRATION §17.1): devolve slots negociados numa cidade, abrindo a tela de
# negociacao (staff picker), navegando para Return (celula 1,2), confirmando e
# selecionando a cidade no mapa. Verifica efeito via staff_action_is_bid() —
# aborta se Bid esta destacado (359px) em vez de Return (297px), impedindo que
# comece uma negociacao por engano. Funcionarios livres pode nao mudar (gate
# fraco); oracle principal e Return ser realmente selecionado.


SEDE_PADRAO = {"id": "NA13", "nome": "Washington", "companhia": "Federal",
               "regiao": 0, "regiao_nome": REGION_NAMES[0],
               "fonte": "DECLARADO pelo harness (savestate sem JSON de metadados ao lado) "
                        "— nao foi lido do jogo nesta run"}


def sede_do_savestate(state_path):
    """Sede LIDA do JSON que `setup_game.py` grava ao lado do savestate.

    Sem o JSON, devolve `SEDE_PADRAO` — e o texto do prompt diz que a sede foi
    DECLARADA, nao lida (R1/R5: melhor um campo que se confessa do que um nome
    inventado que o modelo tomaria por medicao).
    """
    meta = pathlib.Path(state_path).with_suffix(".json")
    if not meta.exists():
        return dict(SEDE_PADRAO)
    d = json.loads(meta.read_text(encoding="utf-8"))
    cid = d["city"]
    # O nome vai CRU, com os "?" onde o atlas nao reconheceu o glifo (MEDIDO:
    # 'Washington' sai '?Washington' — o '?' e o icone de bandeira — e Berlim
    # sai '?erlin', onde o '?' e a propria letra. Apagar o '?' produziria
    # "erlin", um nome errado com cara de medido; por R1 ele fica visivel.
    nome = (d.get("mira", {}).get("nome_lido_da_tela") or "").strip() or None
    comp = (d.get("medido_do_jogo", {}).get("our_company_fleet") or None)
    reg = d.get("mira", {}).get("region", WORLD_CITIES[cid][2])
    return {"id": cid, "nome": nome or "?", "companhia": comp or "?",
            "regiao": reg, "regiao_nome": REGION_NAMES[reg],
            "fonte": f"LIDO do jogo na criacao do savestate ({meta.name}); "
                     f"'?' = glifo fora do atlas (R1)"}


def build_state(turn, cash_k, owned, routes, negotiating, last_results, placar=None,
                comprados=None, livres=None, hubs=None, hubs_pending=None,
                quarter_idx=None, rankings=None, frota=None, rotas_jogo=None,
                orcamentos=None, pnl=None, intel=None, intel_decl=None,
                savestate=None, sede=None):
    """Estado que vai para o prompt do modelo.

    `quarter_idx` e o contador de trimestres LIDO DA RAM (ETAPA 1). Quando ele
    vem, a data do prompt e a data do JOGO. O calculo por `turn` que ficou como
    fallback e o contador PARALELO do harness: se um end_turn passar dois
    trimestres (ou nenhum), ele mente para o modelo sem que nada acuse — e a
    dessincronia que a ETAPA 1 existe para matar.
    """
    # ETAPA 5d: a intel de cidade entra sozinha a partir do cache em disco
    # (`harness/city_intel.json`). Passar `intel`/`intel_decl` explicitamente
    # continua possivel — e o que `etapa5d_medir.py` faz para comparar formatos.
    # `savestate` (basename do --state) e o que autoriza a publicacao: os
    # numeros do painel mudam de cenario para cenario (§35.1). Sem ele,
    # `slice_for_prompt` devolve ZERO intel e diz por que — falha fechada.
    if intel is None or intel_decl is None:
        _cache = city_intel.load()
        _usa, _decl = city_intel.slice_for_prompt(
            _cache, owned, routes, hubs, REGION_NAMES, cities_of_region,
            savestate, world_cities=WORLD_CITIES)
        intel = (_cache if savestate else {}) if intel is None else intel
        intel_decl = _decl if intel_decl is None else intel_decl
    sede = sede or dict(SEDE_PADRAO)
    if quarter_idx is not None:
        year, q = quarter_to_date(quarter_idx)
    else:
        idx = (START_QUARTER - 1) + (turn - 1)
        q = (idx % 4) + 1
        year = START_YEAR + idx // 4
    return {
        "turn": turn,
        "date": {"year": year, "quarter": q, "label": f"{QUARTER_NAMES[q]}. {year}"},
        "cash_k": cash_k,
        "company": {
            # SEDE (ETAPA 5-CidadeImplementar, 24/08): nome da companhia e base
            # eram CHUMBADOS aqui ("Federal", "NA13 (Washington)"). Isso quebra
            # o experimento inteiro: `setup_game.py --city` gera savestates em
            # outras cidades e o jogo troca companhia, caixa e frota junto com
            # ela (MEDIDO: Washington=Federal/1.220.000K/MD100 x6 x
            # Berlin=Berlin/1.510.000K/777 x6). Com o texto chumbado o modelo
            # rodaria em Berlim lendo "somos a Federal, base Washington" — o
            # eixo do experimento vira ruido. Agora vem de `sede`, que sai do
            # JSON de metadados do savestate (medido do jogo pelo setup).
            "name": sede["companhia"],
            "home_base": f"{sede['id']} ({sede['nome']})",
            "home_region": f"{sede['regiao']} {sede['regiao_nome']}",
            "home_fonte": sede["fonte"],
            # HUBS: a espinha do jogo. Toda rota parte de um hub NOSSO; a base e
            # hub da regiao dela. `hubs_confirmados` sao os que o JOGO ja aceita
            # como origem (testado abrindo r0c0 na regiao e lendo a caixa);
            # `hubs_em_negociacao` ja foram pagos mas AINDA NAO servem de origem
            # — medido 17/08: com a negociacao em curso o jogo continua
            # respondendo "We don't have a regional hub here.".
            "hubs_confirmados": sorted(hubs or []),
            "hubs_em_negociacao": hubs_pending or {},
            # ROTAS: quando `rotas_jogo` vem (leitura de Info->map, 18/08) ele
            # SUBSTITUI o ledger do harness — traz o campo que faltava, a
            # ocupacao. Sem ela o modelo usava adjust_route as cegas: nao havia
            # como saber QUAL rota merecia mais voos ou tarifa maior.
            "routes_open": rotas_jogo if rotas_jogo is not None else routes,
            # Sem rota aberta o jogo mostra o mapa-mundi no lugar da tabela
            # (CALIBRATION §25), entao `rotas_jogo is None` no comeco da partida
            # e o NORMAL, nao um defeito. O texto precisa dizer isso: a versao
            # anterior anunciava falha de leitura onde nao havia falha nenhuma.
            "routes_fonte": ("lido do jogo (Info->map), com ocupacao" if rotas_jogo is not None
                             else "sem rota aberta ainda, ou tabela nao lida neste turno; "
                                  "a lista acima e o registro do harness e NAO traz ocupacao"),
            "negotiations_pending": negotiating,
            # MEDIDO 16/08 na barra do menu principal (23 px por boneco): quantos
            # dos 4 negociadores estao NA BASE. Sem isto o modelo pedia uma 5a
            # negociacao no mesmo turno sem ter quem enviar e queimava a acao.
            "negociadores_livres": livres,
            "AVISO_negociacoes": "esta lista e o que o harness DISPAROU, nao o que o jogo concluiu — ainda nao lemos o status real. Uma negociacao pode ja ter terminado (com sucesso ou nao) sem sair daqui.",
            # FROTA (18/08): agora LIDA de Info->fleet. Os tres campos que
            # existiam aqui (fleet_inicial_do_savestate, avioes_comprados_nesta_run
            # e o AVISO) eram a reconstrucao que o harness fazia por NAO conseguir
            # ler a tabela. Foram REMOVIDOS de proposito: manter o valor lido ao
            # lado do valor rastreado poe duas fontes discordantes no mesmo prompt,
            # que e a classe de erro do §6 (o prompt anunciava um B707-320 que a
            # companhia nao tinha).
            # `in_use` x `avail` e um limite duro que o modelo precisava ver: cada
            # rota consome uma aeronave, entao avail == 0 significa que nenhuma
            # rota nova pode abrir por mais caixa que haja.
            **({"fleet": frota} if frota is not None else {
                "fleet": "nao lido neste turno",
                "fleet_reconstruida": ([] if not FLEET_START else FLEET_START) + (comprados or []),
                "AVISO_frota": "a leitura de Info->fleet falhou neste turno; o que "
                               "esta acima e reconstrucao do harness (frota inicial "
                               "+ compras confirmadas) e pode estar desatualizada",
            }),
        },
        # CATALOGO GLOBAL (13/08): antes so a America do Norte era oferecida, e a
        # vitoria exige hub em TODAS as 7 regioes — o modelo nao podia vencer.
        # CATALOGO DE AERONAVES A VENDA (MEDIDO 15/08, lido das telas de cada
        # fabricante): sem isto o modelo escolheria aviao sem saber alcance,
        # assentos nem preco — exatamente o tipo de decisao no escuro que
        # torna o eval ruido.
        "aircraft_catalog": {
            k: {"maker": v["maker"], "range_mi": v["range_mi"],
                "seats": v["seats"], "price_k": v["price_k"]}
            for k, v in AIRCRAFT_CATALOG.items()
        },
        # ETAPA 5d — CATALOGO COMPACTO + INTELIGENCIA DE CIDADE.
        # O dicionario verboso de `catalog_for_prompt_world` custava 10.731 de
        # 17.088 chars do estado (63%) para dizer 4 coisas por cidade. Aqui a
        # MESMA informacao medida vai em linha unica; o espaco economizado paga
        # a intel do painel (§34) sem inflar o turno. `catalog_for_prompt_world`
        # continua em world.py e e o baseline que `etapa5d_medir.py` compara.
        "cities_legend": (
            "uma linha por cidade: '<ID> <nome ou -> | ledger=<n> | "
            "rota=<sim|nao> | dist=<milhas ate a base> | <intel do painel>'. "
            "dist sem marca = LIDA do jogo (exata); '~N(est)' = estimada por pixel "
            "(errou 40% uma vez); '?' = nunca medida. 'intel:-' = painel dessa "
            "cidade nunca lido — veja cities_intel_declaracao. "
            "'ledger' e quantos slots o HARNESS anotou que temos ali ao "
            "carregar o savestate — nao foi lido do jogo e pode estar velho. Os "
            "numeros do painel sao 'slotsUSADOS/CAPACIDADE(nossosN)': USADOS e o "
            "total ocupado por todas as companhias, CAPACIDADE e o tamanho do "
            "aeroporto e nossosN e a nossa fatia, LIDA da tela. Quando "
            "ledger e nossosN discordam (MEDIDO em 5d: Washington 34 x "
            "27, Denver 12 x 11), o certo e nossosN."),
        "cities_by_region": city_intel.compact_rows(
            owned, routes, intel or {},
            REGION_NAMES, cities_of_region, WORLD_CITIES, sede["id"], sede["regiao"],
            distance_mi,
            # As distancias MEDIDAS foram levantadas a partir de Washington; com
            # outra sede elas seriam numeros de outra origem apresentados como
            # se fossem desta. Fora da base NA13 o campo volta a "?" (R1).
            MEASURED_DIST_FROM_HOME if sede["id"] == "NA13" else {}, savestate),
        # DECLARACAO DO RECORTE: sem isto o modelo ranquearia pelo que enxerga e
        # escreveria as cidades sem intel como ruins — o recorte viraria sinal.
        "cities_intel_declaracao": intel_decl,
        "valid_city_ids_by_region": {
            f"{r} {n}": cities_of_region(r) for r, n in REGION_NAMES.items()
        },
        # ORCAMENTOS (r0c4): Repair / Ad / Service. Lidos da tela; `nivel` e o
        # comprimento da barra e `ordem` e a politica corrente. E LEITURA:
        # `set_budget` continua FORA do action space desde a auditoria (a
        # calibracao anterior era falso-positivo — navegacao testada num
        # sentido so, Ad e Service nunca testados). O campo diz isso ao modelo
        # em vez de deixa-lo tentar puxar uma alavanca que nao existe.
        "orcamentos": orcamentos if orcamentos is not None else "nao lido neste turno",
        "victory_progress": placar or "nao lido neste turno",
        # RANKING REGIONAL (ETAPA 8-LerRanking, 18/08): passageiros do LIDER de
        # cada regiao, lido de Info->finance ("Regional Rankings <ano>") via
        # `world.read_regional_rankings` (OCR por hash de glifo, catalogo
        # medido ao vivo). None por regiao = sem dado ainda no jogo OU glifo
        # nao reconhecido (nunca inventa numero). NAO E LIDO AINDA no loop
        # principal (`main()`) — navegar ate essa tela custa mais A/B na
        # cadeia de fim de turno e essa cadeia ja e a que perdeu $276.000K
        # numa run anterior (CALIBRATION.md); so entra no turno quando o
        # caller passar `rankings=world.read_regional_rankings(img)`
        # explicitamente, apos abrir e fotografar a tela com guarda de caixa.
        "regional_rankings": rankings if rankings is not None else "nao lido neste turno",
        # P&L DO TRIMESTRE (ETAPA 1c, 19/08): {rotulo_lido: valor_k} da tela
        # "Quarterly Report" (Info->finance, ANTES do Regional Rankings), via
        # `world.read_pnl`. E o placar economico: receita de linha aerea e de
        # empreendimentos contra os custos de slot/hub/bid/reparo/anuncio/
        # servico do trimestre que acabou. Os ROTULOS saem da tela (fonte
        # proporcional, atlas proprio) — nao ha lista chumbada de rubricas.
        # Mesma disciplina do ranking: NAO e lido no loop principal, porque
        # abrir Info->finance custa A/B na cadeia que ja perdeu $276.000K; so
        # entra quando o caller passar `pnl=world.read_pnl(img)` depois de
        # fotografar a tela com guarda de caixa. `None` de `read_pnl` (tela
        # errada) nunca deve virar dicionario de zeros aqui.
        "pnl_trimestre": pnl if pnl is not None else "nao lido neste turno",
        "last_turn_results": last_results,
        "rules_reminder": [
            "use SOMENTE os IDs listados em valid_city_ids — qualquer outro e rejeitado",
            "TODA rota parte de um HUB NOSSO (company.hubs_confirmados). Nao existe rota "
            "entre duas cidades comuns, nem dentro do mesmo continente. Use o param "
            "'from' de open_route para escolher o hub de origem (default = NA13)",
            "CADEIA DE EXPANSAO (a mecanica central do jogo, MEDIDA em 17/08): "
            "1) negotiate_slots numa cidade da regiao nova; 2) espere concluir; "
            "3) open_route de um hub existente ate essa cidade; 4) open_hub(region) — "
            "custa $28.800K na hora + 1 negociador; 5) espere a negociacao do hub concluir; "
            "6) so entao rotas partem de la. Sem hub na regiao o jogo responde \"We don't "
            "have a regional hub here.\" e a vitoria (hub em TODAS as 7 regioes) fica "
            "impossivel",
            "open_hub e recusado: na regiao da BASE (nao precisa), numa regiao sem rota "
            "nossa chegando, com hub ja aberto/em negociacao, ou sem negociador livre",
            "abrir rota exige slots nas duas pontas, e CADA voo/semana consome 1 slot em "
            "CADA ponta — uma cidade com 1 slot ja gasto por uma rota NAO pode ser origem "
            "de outra sem negociar mais slots la",
            "negotiate_slots aceita 'slots' de 1 a 5 (default 1), MAS o teto REAL e por "
            "CIDADE: o medidor da tela tem N posicoes e N muda por cidade (MEDIDO 23/08, "
            "CALIBRATION §36: Denver=2, NA02=3, varias outras=5). Pedido acima de N e "
            "RECUSADO com o teto lido da tela na mensagem — releia o teto e peca de novo "
            "com esse valor, nada e negociado na recusa. MEDIDO (CALIBRATION "
            "§32): pedir 5 em vez de 1 ocupa o MESMO negociador pela MESMA espera "
            "declarada ('Negotiations should take 6 months.', tela identica byte a byte). "
            "So ha 4 negociadores e cada negociacao leva meses, entao pedir 1 slot por vez "
            "gasta o recurso mais escasso do jogo. NAO MEDIDO: se o PRECO do lance escala "
            "com a quantidade (ele so aparece no fechamento do trimestre)",
            "a frota COMECA com um unico modelo (MD100, 4680 mi, 200 assentos, 6 unidades); "
            "buy_aircraft compra outros (veja aircraft_catalog). Destino longe demais e "
            "RECUSADO ('no aircraft capable of flying such a great distance'). "
            "MEDIDO: Washington-Havana (1180 mi) abre; Washington-Bruxelas e recusado "
            "MESMO com um A340 de 8870 mi entregue e livre — ou seja, comprar aviao NAO "
            "basta para a Europa neste cenario (CALIBRATION §13)",
            "comprar aviao debita o caixa NA HORA (preco de tabela x quantidade) e a "
            "entrega leva 1 trimestre (~3 meses): o aviao aparece em Order e so no "
            "trimestre seguinte vira Avail",
            "cada rota consome 1 aeronave (MEDIDO: com 1 rota aberta a tela Info->fleet passou de In Use 0/Avail 6 para In Use 1/Avail 5); com 6 MD100 cabem no maximo 6 rotas",
            "dist_from_home_mi_real e a distancia LIDA do jogo (exata) e so existe para "
            "cidades ja visitadas; dist_from_home_mi_est e estimativa por pixel e errou 40% "
            "(Philly: 168 estimado vs 120 real)",
            "negociar slots ocupa 1 dos 4 funcionarios (veja negociadores_livres) por "
            "varios trimestres; com 0 livres a acao e recusada antes de tocar no jogo. MEDIDO: "
            "Bruxelas levou 6 meses (2 trimestres) e Havana 9 meses (3) — o prazo aparece "
            "na tela e varia por cidade; a negociacao entregou 1 slot em ambas",
            "ha 7 regioes; a vitoria exige presenca em TODAS. Rota so abre com slots "
            "nas DUAS pontas, entao para outro continente e preciso PRIMEIRO negociar "
            "slots la, esperar a negociacao concluir e so entao abrir a rota",
            "dist_from_home_mi_est vem null fora da America do Norte: cada regiao tem "
            "projecao propria e nao existe estimativa confiavel entre continentes",
            "buy_aircraft: 'model' tem de ser EXATAMENTE uma das chaves de "
            "aircraft_catalog (MD11, MD12, MD100, B747-400, B777, A340, TU204, "
            "IL96-300) e 'qty' um inteiro de 1 a 10; os dois params sao obrigatorios",
            "set_budget: CALIBRADO 17/08 (r0c4 Budgets). Parametros: "
            "'category' ('repair'|'ad'|'service') e 'level' (0-4: MAXIMUM/RAISE/MAINTAIN/REDUCE/STOP). "
            "O efeito eh imediato (no ato, nao apos turn): Repair 110K (MAXIMUM/RAISE) -> 100K (REDUCE) -> 90K (STOP); "
            "Ad e Service seguem padroes similares. Maior flexibilidade para baixar gastos de operacao.",
        ],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--turns", type=int, default=20)
    ap.add_argument("--state", default="../states/f0_t02_route.state")
    ap.add_argument("--run", default="../logs/pilot_auto")
    ap.add_argument("--model", default=None,
                    help="id do modelo, ou 'random'/'greedy' para rodar uma BASELINE nao-LLM")
    ap.add_argument("--seed", type=int, default=0, help="semente da baseline (so com --model random|greedy)")
    ap.add_argument("--no-fallback", action="store_true",
                    help="EVAL: exige que o modelo pedido responda (sem trocar por outro)")
    ap.add_argument("--fresh", action="store_true", help="partida nova: sem rotas e sem slots pre-carregados")
    ap.add_argument("--sem-telemetria", action="store_true",
                    help="nao envia nada ao Logfire (padrao: envia, sem o conteudo dos prompts)")
    ap.add_argument("--telemetria-conteudo", action="store_true",
                    help="inclui diario e resposta do modelo nos spans (fora do padrao)")
    a = ap.parse_args()
    # Telemetria antes de qualquer coisa que valha observar. Nunca levanta: uma
    # partida de 80 turnos leva horas e nao pode morrer por causa do exportador.
    if not a.sem_telemetria:
        obs.configurar(service_name="aerobiz-eval",
                       capturar_conteudo=a.telemetria_conteudo)

    import baselines
    from agent import Run  # import tardio: carrega o cliente so quando roda

    b = BizHawkBridge()
    g = Game(b)
    ex = Executor(b)
    kw = {"allowed_actions": SUPPORTED, "city_ids": WORLD_CITIES.keys(),
          "fallbacks": not a.no_fallback}
    # BASELINE (ETAPA 4-Baselines): `--model random|greedy` troca o JOGADOR e
    # mais nada. Mesmo savestate, mesmo Executor, mesmo turns.jsonl, mesma
    # telemetria — se qualquer outra coisa mudasse, a baseline nao seria
    # comparavel com o LLM e nao serviria de piso.
    if baselines.eh_baseline(a.model):
        kw.pop("fallbacks", None)
        run = baselines.BaselineRun(a.run, baselines.kind_de(a.model),
                                    seed=a.seed, **kw)
        print("[pilot] jogador = BASELINE %s (seed=%d), nenhuma chamada de modelo"
              % (run.kind, a.seed), flush=True)
    else:
        run = Run(a.run, model=a.model, **kw) if a.model else Run(a.run, **kw)
    outdir = pathlib.Path(a.run)
    outdir.mkdir(parents=True, exist_ok=True)

    b.load(a.state)
    b.advance(60)
    b.speed(400)  # turbo: as animacoes entre turnos sao longas

    # O savestate do cenario 2000 comeca sem rotas e com OUTRO conjunto de slots.
    # Dar START_SLOTS (cenario 1970) aqui fazia o modelo escolher destinos onde
    # nao temos slot nenhum — e o jogo RECUSA a rota ("We don't have any slots
    # in X"), o que aparecia como acao sem efeito.
    # SEDE: eixo do experimento, fixada pelo OPERADOR em `setup_game.py --city`
    # e recebida aqui como FATO (o modelo nao escolhe). Tudo o que era chumbado
    # para Washington passa a depender dela.
    sede = sede_do_savestate(a.state)
    print(f"[sede] {sede['id']} ({sede['nome']}) regiao {sede['regiao']} "
          f"{sede['regiao_nome']} — companhia {sede['companhia']} — {sede['fonte']}", flush=True)
    # EVAL_SLOTS_2000 foi MEDIDO no savestate de Washington. Em outra sede esses
    # slots seriam a escrituracao de outra partida: o modelo escolheria destinos
    # onde nao temos slot e o jogo recusaria a rota. Fora de NA13 o ledger comeca
    # vazio e o prompt ja diz que ledger nao e leitura.
    owned = dict(EVAL_SLOTS_2000) if sede["id"] == "NA13" else {}
    # ESCRITURACAO DO EXECUTOR: hubs/rotas/slots que o harness acredita. Nao sao
    # lidos do jogo — sao declarados por quem carrega o savestate, e toda recusa
    # que os usa diz "o harness acredita". Rotas viram objetos {from,to,flights}
    # porque a origem deixou de ser sempre a base.
    # A base E hub da regiao dela — em qualquer cidade, nao so em Washington.
    # A rota inicial NA13->NA06 so existe no savestate pos-F0 de Washington.
    rota_inicial = ([] if (a.fresh or sede["id"] != "NA13")
                    else [{"from": "NA13", "to": "NA06", "flights": 1}])
    ex.reset_world_state(
        hubs={sede["id"]},
        routes=rota_inicial,
        owned_slots=owned,
    )
    negotiating = []
    comprados = []  # so compras CONFIRMADAS (gate de caixa) entram aqui
    last = {"note": "run iniciada a partir do savestate pos-F0"}
    stats = {"acoes": 0, "ok": 0, "falhas": 0, "turnos": 0}

    turn_guard = pathlib.Path("../states/_turn_guard.state")
    for t in range(1, a.turns + 1):
        # RECUPERACAO DE TURNO: uma acao ruim deixava o jogo numa tela da qual o
        # B nao sai, e a run INTEIRA abortava (visto ao vivo: 1 turno de 10).
        # Um eval nao pode morrer por um turno; restauramos o savestate do inicio
        # do turno e seguimos, contabilizando a perda.
        if not ex._ensure_menu():
            if turn_guard.exists():
                print(f"[t{t}] menu inacessivel — restaurando savestate do turno", flush=True)
                b.load(str(turn_guard))
                b.advance(90)
                stats["turnos_recuperados"] = stats.get("turnos_recuperados", 0) + 1
            if not ex._ensure_menu():
                print(f"[t{t}] menu inacessivel mesmo apos restaurar — abortando", flush=True)
                break
        b.save(str(turn_guard))
        cash = read_cash_k(b)
        livres = None
        # Slots REAIS lidos do mapa — e assim que sabemos que uma negociacao
        # concluiu. Antes o harness so listava o que disparou, e o modelo ficava
        # travado achando que tudo seguia pendente para sempre.
        try:
            cur = tuple(b.read_ram(CURSOR_X, 3)[::2])
            shot = g.shot("map_t%02d" % t)
            img = Image.open(shot).convert("RGB")
            # O mapa pode ter ficado em OUTRO continente (o jogo nao volta para a
            # base sozinho). Ler os slots com as coordenadas da regiao errada
            # devolvia lista vazia e o piloto SUBSTITUIA owned por {} — dizendo ao
            # modelo que a companhia nao tem slot nenhum. Agora a regiao e lida da
            # tela e a atualizacao vale SO para ela.
            livres = free_staff_menu(img)
            reg_vis = detect_region(img)
            if reg_vis is not None:
                reais = cities_with_slots(img, cursor=cur, region=reg_vis)
                da_regiao = set(cities_of_region(reg_vis))
                # PONTAS DE ROTA NAO PODEM SER APAGADAS. MEDIDO 15/08
                # (logs/prova_ic/zoom_havana.png): numa cidade ligada por rota o
                # ponto fica VERDE e o rotulo da rota ("WAS") cobre o lugar do
                # digito — cities_with_slots NAO a enxerga (Havana, 1 slot, some
                # do mapa; Bruxelas, 1 slot e sem rota, aparece). Sem esta
                # protecao o piloto apagaria do estado justamente a cidade onde a
                # companhia acabou de investir.
                # O detector diz SE ha slots, nao QUANTOS — entao a contagem
                # conhecida (EVAL_SLOTS_2000, medida) e preservada em vez de
                # virar 1. Antes Washington caia de 34 para 1 no primeiro turno.
                prev = dict(owned)
                pontas = {c for r in ex.routes for c in (r["from"], r["to"])}
                owned = {c: v for c, v in owned.items()
                         if c not in da_regiao or c in pontas}
                owned.update({c: prev.get(c, 1) for c in reais})
                negotiating = [c for c in negotiating if c not in reais]
            else:
                print("  [t%d] regiao do mapa ambigua — slots mantidos" % t, flush=True)
        except Exception as e:  # noqa: BLE001
            print("  [t%d] leitura de slots falhou: %s" % (t, e), flush=True)
        # Placar lido do jogo (Info->victory): o status por regiao e a metrica
        # de sub-objetivo do eval E o feedback de resultado para o agente.
        placar = None
        try:
            vp = g.info_screen("victory", "placar_t%02d" % t)
            vimg = Image.open(vp).convert("RGB")
            placar = {k: v["status"] for k, v in
                      read_victory(vimg, na_ref=victory_na_signature(vimg)).items()}
        except Exception as e:  # noqa: BLE001
            print("  [t%d] leitura do placar falhou: %s" % (t, e), flush=True)
        # O executor precisa da crenca de slots ATUALIZADA para dar o motivo
        # certo de recusa (origem sem slot livre x destino sem slot x sem hub).
        ex.owned_slots = owned
        routes = [f"{r['from']}-{r['to']} ({r['flights']} voos/sem)" for r in ex.routes]
        # Rotas e frota LIDAS do jogo (18/08). Falha de leitura nunca derruba o
        # turno: cai para o ledger com aviso explicito, porque um turno perdido
        # custa mais que um campo faltando.
        rotas_jogo = frota = None
        try:
            mimg = Image.open(g.info_screen("map", "rotas_t%02d" % t)).convert("RGB")
            lidas, n_rte = read_routes(mimg)
            if lidas is not None and n_rte == len(lidas):
                rotas_jogo = lidas
            elif lidas is not None:
                print("  [t%d] leitura de rotas DESCARTADA: %d linhas x contador %s"
                      % (t, len(lidas), n_rte), flush=True)
        except Exception as e:  # noqa: BLE001
            print("  [t%d] leitura de rotas falhou: %s" % (t, e), flush=True)
        orcamentos = None
        try:
            g.back_to_menu()
            g.open_cmd("budgets")
            b.advance(200)
            bimg = Image.open(g.shot("orcamento_t%02d" % t)).convert("RGB")
            if on_budget_screen(bimg):
                # ETAPA 4: lê números exatos (custo_k + nivel) em vez de pixel-level
                nums = read_budget_numbers(bimg)
                ordens = {c: o for c, o in zip(BUDGET_COLS, read_budget_orders(bimg))}
                orcamentos = {c: {**nums[c], "ordem": ordens[c]} for c in BUDGET_COLS}
            g.back_to_menu()
        except Exception as e:  # noqa: BLE001
            print("  [t%d] leitura de orcamentos falhou: %s" % (t, e), flush=True)
        try:
            fimg = Image.open(g.info_screen("fleet", "frota_t%02d" % t)).convert("RGB")
            lida = read_fleet(fimg)
            if lida and all(x["model"] and "?" not in x["model"] for x in lida):
                frota = lida
            elif lida:
                print("  [t%d] leitura de frota DESCARTADA: glifo fora do atlas em %s"
                      % (t, [x["model"] for x in lida]), flush=True)
        except Exception as e:  # noqa: BLE001
            print("  [t%d] leitura de frota falhou: %s" % (t, e), flush=True)
        state = build_state(t, cash, owned, routes, negotiating, last, placar, comprados,
                            livres=livres, hubs=ex.hubs, hubs_pending=ex.hubs_pending,
                            quarter_idx=read_quarter_index(b),
                            frota=frota, rotas_jogo=rotas_jogo, orcamentos=orcamentos,
                            savestate=pathlib.Path(a.state).name, sede=sede)
        try:
            # INSPETOR: o modelo pode pedir os stats de ate 5 cidades e decidir
            # com eles no MESMO trimestre. Nao ha cache — os numeros mudam com a
            # epoca do cenario e envelhecem dentro da partida (§35.1), entao ler
            # na hora e a unica leitura que nao mente. Quantas cidades cada
            # modelo consulta antes de agir fica no log e E metrica do eval.
            def _inspetor(cids, _b=b, _ex=ex, _t=t):
                import city_probe
                dados, avisos = city_probe.inspect(
                    _b, _ex, cids, shot_dir=str(run.dir))
                print("  [t%d] pesquisa de cidades: %d pedida(s), %d lida(s)%s"
                      % (_t, len(cids), len(dados),
                         (" | avisos: %s" % avisos) if avisos else ""), flush=True)
                return city_probe.formatar(dados, avisos)

            valid, errors, diary = run.turn(state, inspector=_inspetor)
        except Exception as e:  # noqa: BLE001
            print(f"[t{t}] agente falhou: {e}", flush=True)
            break

        results = []
        for act in valid:
            # Span por ACAO: e aqui que mora a diferenca entre "o modelo pediu"
            # e "o jogo mudou". `ok` so e True quando o efeito foi verificado no
            # jogo (caixa que cai no valor exato, barra de staff, contador) —
            # por isso `sucesso` no Logfire mede o JOGO, nao o retorno da funcao.
            with obs.span("acao", acao=act.get("action"), turn=t) as _sa:
                caixa_antes = read_cash_k(b)
                ok, detail = ex.run(act)
                caixa_depois = read_cash_k(b)
                _sa.set_attribute("sucesso", bool(ok))
                _sa.set_attribute("params", json.dumps(act.get("params") or {},
                                                       ensure_ascii=False))
                _sa.set_attribute("caixa_antes_k", caixa_antes)
                _sa.set_attribute("caixa_depois_k", caixa_depois)
                if caixa_antes is not None and caixa_depois is not None:
                    _sa.set_attribute("caixa_delta_k", caixa_depois - caixa_antes)
                _sa.set_attribute("detalhe", (detail or "")[:400])
            stats["acoes"] += 1
            stats["ok" if ok else "falhas"] += 1
            results.append({"action": act, "ok": ok, "detail": detail})
            # LINHA POR ACAO EM DISCO (ETAPA 6-Runner): o resumo do eval precisa
            # de acoes POR TIPO com o efeito medido ao lado. Antes isso so
            # existia no stdout, e resumo tirado de stdout perde o delta de
            # caixa — que e a evidencia do efeito, nao o `ok` da funcao (R4).
            with (outdir / "acoes.jsonl").open("a", encoding="utf-8") as _f:
                _f.write(json.dumps({
                    "turn": t, "action": act.get("action"),
                    "params": act.get("params") or {},
                    "ok_oraculo_executor": bool(ok),
                    "caixa_antes_k": caixa_antes, "caixa_depois_k": caixa_depois,
                    "caixa_delta_k": (None if caixa_antes is None or caixa_depois is None
                                      else caixa_depois - caixa_antes),
                    "detalhe": detail,
                }, ensure_ascii=False) + "\n")
            # open_route NAO e anotado aqui: quem mantem a lista de rotas (com
            # origem e voos/semana) e o Executor, que a reverte junto com o
            # savestate quando a acao e desfeita.
            if ok and act["action"] == "negotiate_slots":
                negotiating.append(act["params"].get("city"))
            if ok and act["action"] == "buy_aircraft":
                comprados.append({"model": act["params"].get("model"),
                                  "qty": act["params"].get("qty"), "turno": t})
            print(f"  [t{t}] {act['action']} -> {'OK' if ok else 'FALHA'}: {detail}", flush=True)

        cash_before = cash
        # O retorno do end_turn deixou de ser decorativo (ETAPA 1): ele diz de
        # que data para que data o jogo foi, quantos disparos de r1c5 foram
        # precisos, e distingue "nao virou" de "PULOU 2 trimestres". Ignora-lo
        # era ficar cego justamente para o modo de falha que desalinha a data do
        # prompt. `dismiss_to_menu` ja e chamado por dentro do end_turn.
        ok_turno, det_turno = g.end_turn()
        print(f"  [t{t}] end_turn -> {'OK' if ok_turno else 'FALHA'}: {det_turno}",
              flush=True)
        stats["turnos_falhos"] = stats.get("turnos_falhos", 0) + (0 if ok_turno else 1)
        b.advance(120)
        ex.dismiss_to_menu()
        # Hub pendente ja concluiu? Pergunta AO JOGO (abre r0c0 na regiao e le a
        # caixa de rodape), depois desfaz por savestate. Sem isto o modelo nunca
        # saberia quando pode comecar a usar o hub novo como origem.
        for reg_pend, cid_pend in list(ex.hubs_pending.items()):
            try:
                pronto, det_hub = ex.hub_ready(reg_pend, cid_pend)
                print(f"  [t{t}] hub regiao {reg_pend} pronto={pronto}: {det_hub}", flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"  [t{t}] checagem de hub falhou: {e}", flush=True)
        cash_after = read_cash_k(b)
        stats["turnos"] += 1
        # PROGRESSO POR TURNO (25/08). Ate aqui o Logfire so tinha metrica de
        # HARNESS ("a acao teve efeito?") e nenhuma de OBJETIVO. A condicao de
        # vitoria e composta — hub em toda regiao + n1 em passageiros em 4-7
        # regioes + lucro anual (VIABILIDADE.md) — e destas tres parcelas so as
        # duas primeiras saem de graca aqui: `ex.hubs` ja esta em memoria e o
        # placar ja foi lido no inicio do turno. Passageiros e lucro exigiriam
        # abrir Info->finance TODO TURNO, na mesma cadeia de fim de turno que ja
        # perdeu $276.000K numa run anterior (CALIBRATION.md) — ficam de fora de
        # proposito, nao por esquecimento.
        #
        # RESSALVA que o grafico nao conta sozinho: `read_victory` devolve so
        # 'N/A' | 'com_valor' (assinatura de pixel contra a referencia do turno
        # 1). E um flag de PRESENCA por regiao, nao um placar com magnitude —
        # satura assim que entramos na regiao e depois nao se mexe mais.
        #
        # E um evento SOLTO, nao um atributo do span "turno": aquele span nasce
        # e morre dentro de `run.turn()` (agent.py:174, baselines.py:393) e o
        # placar e lido aqui no pilot, antes da chamada. Emitir por fora evita
        # mexer na assinatura do agente — e no baselines.py, que precisa ficar
        # identico para a baseline seguir comparavel com o LLM.
        try:
            # NOME, nao indice: `ex.hub_regions` devolve indices (0..6) e o
            # placar vem chaveado por nome ('Europe', ...). Emitir os dois em
            # espacos de chave diferentes tornaria impossivel cruzar as duas
            # metades da condicao de vitoria no mesmo grafico. MEDIDO que
            # set(VICTORY_REGIONS) == set(REGION_NAMES.values()), entao os dois
            # contadores dividem o mesmo `n_regioes_total`.
            _regs_hub = sorted(REGION_NAMES[r] for r in ex.hub_regions
                               if r in REGION_NAMES)
            _com_valor = (sorted(r for r, st in placar.items() if st == "com_valor")
                          if isinstance(placar, dict) else None)
            obs.info(
                "progresso",
                turn=t,
                caixa_antes_k=cash_before,
                caixa_depois_k=cash_after,
                caixa_delta_k=(None if cash_before is None or cash_after is None
                               else cash_after - cash_before),
                hubs=sorted(ex.hubs),
                n_hubs=len(ex.hubs),
                regioes_com_hub=_regs_hub,
                n_regioes_com_hub=len(_regs_hub),
                n_regioes_total=len(REGION_NAMES),
                hubs_pendentes=sorted(ex.hubs_pending),
                placar=placar,
                # None (e nao 0) quando a leitura do placar falhou: zero aqui
                # seria numero inventado — e e justamente o eixo do grafico.
                n_regioes_com_valor=(None if _com_valor is None else len(_com_valor)),
                regioes_com_valor=_com_valor,
                rotas=len(ex.routes),
                acoes_executadas=len(results),
                acoes_com_efeito=sum(1 for _r in results if _r["ok"]),
                erros_de_validacao=len(errors),
                end_turn_ok=bool(ok_turno),
                sede=sede.get("id"),
                model_solicitado=a.model,
            )
        except Exception as _e:  # noqa: BLE001
            # Telemetria nunca derruba uma partida de 80 turnos (mesma politica
            # do obs.configurar).
            print("  [t%d] telemetria de progresso falhou: %s" % (t, _e), flush=True)
        last = {
            "acoes_do_turno": results,
            "erros_de_validacao": errors,
            "caixa_antes_k": cash_before,
            "caixa_depois_k": cash_after,
            "variacao_k": cash_after - cash_before,
            "fim_de_turno": {"ok": ok_turno, "detalhe": det_turno},
        }
        # O caminho era CHUMBADO em ../logs/pilot_auto: com --run apontando para
        # outra pasta (o que run_eval.py faz, uma por eval), os screenshots de
        # todas as runs caiam no mesmo lugar e se sobrescreviam entre si.
        g.shot(str(outdir / f"t{t:02d}"))
        print(
            f"[t{t}] caixa {cash_before}K -> {cash_after}K ({cash_after - cash_before:+}K) | "
            f"rotas {len(routes)} | diario: {diary[:80]}",
            flush=True,
        )
        (outdir / "stats.json").write_text(
            json.dumps({**stats, "ts": time.strftime("%H:%M:%S")}, indent=2), encoding="utf-8"
        )

    b.speed(100)
    taxa = stats["ok"] / stats["acoes"] * 100 if stats["acoes"] else 0
    print(f"\n=== {stats['turnos']} turnos | {stats['acoes']} acoes | taxa de execucao {taxa:.0f}% ===")
    # Saude da ponte em numero, nao em impressao (ETAPA 1-PonteLonga).
    import bridge as _br
    # NAO imprimir "reciclagens do emulador: 0": nao existe mecanismo de
    # reciclo no harness, entao esse zero seria uma medicao inventada (R4).
    # A causa da ponte cair em partida longa era colisao de instancias no mesmo
    # screen.png, resolvida por dono unico do IPC (bridge.lua) + trava de
    # processo (bridge.py) — degradacao do emulador nao foi observada.
    print(f"[ponte] screenshots ok nesta run: {_br.SCREENSHOTS_OK} | "
          f"retries de os.replace: {_br.REPLACE_RETRIES} | "
          f"reciclagens do emulador: nao implementado (nao foi preciso)")


if __name__ == "__main__":
    main()
