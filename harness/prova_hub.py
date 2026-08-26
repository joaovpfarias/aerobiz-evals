"""ACEITE da mecanica de HUB (17/08).

Criterio: abrir um hub regional DE VERDADE fora da America do Norte e depois
abrir uma rota PARTINDO desse hub, com efeito verificado nos dois passos.

Fases (para nao perder trabalho se a sessao cair):
  a  — do savestate pre-hub: open_hub(regiao 1) + negociar slots nas duas pontas
       da rota futura (Havana precisa de um 2o slot: o 1o ja e consumido pela
       rota Washington->Havana). Salva ../states/_hub_chain.state
  b  — passa turnos ate o hub ficar PRONTO e as negociacoes voltarem;
       salva ../states/_hub_pronto.state a cada progresso
  c  — abre a rota SA01 -> SA03 partindo do hub e confere o efeito

Uso: python prova_hub.py a|b|c
"""
import sys
from pathlib import Path

from PIL import Image

import world
from bridge import BizHawkBridge
from executor import Executor
from macros import Game

O = Path("../logs/hub2"); O.mkdir(parents=True, exist_ok=True)
PRE = "../states/prova_ic_rota_sa.state"      # rota WAS->Havana aberta, sem hub
CHAIN = "../states/_hub_chain.state"          # depois da fase a
PRONTO = "../states/_hub_pronto.state"        # depois da fase b

DEST = "SA03"   # cidade da America do Sul mais proxima de Havana no mapa da regiao

b = BizHawkBridge()
g = Game(b, shot_dir=O)
ex = Executor(b)
ex.g = g


def escritura():
    """O que o harness ACREDITA sobre o savestate de partida (nao e leitura do jogo).

    Fonte de cada numero:
      hubs        — so a base; o jogo confirma ("we don't need a regional hub" na NA)
      rotas       — a rota Washington->Havana foi aberta e verificada em 15/08
      slots NA    — world.EVAL_SLOTS_2000 (medidos dos digitos do mapa)
      slots SA01  — 1, LIDO na tela de detalhe de Havana ("Total slots 1/96",
                    logs/hub2/p3_A2.png)
    """
    ex.reset_world_state(
        hubs={world.HOME},
        routes=[{"from": world.HOME, "to": "SA01", "flights": 1}],
        owned_slots={**world.EVAL_SLOTS_2000, "SA01": 1},
    )


def linha(tag, ok, det):
    print(f"  {tag:34} -> {ok}\n     {det}", flush=True)


def fase_a():
    b.load(PRE); b.advance(90); b.speed(400)
    escritura()
    img = Image.open(b.screenshot(O / "a_menu0.png")).convert("RGB")
    print(f"inicio: cash={world.read_cash_k(b)} livres={world.free_staff_menu(img)} "
          f"regiao={world.detect_region(img)}", flush=True)
    print(f"regra ANTES do hub: {ex.check_route('SA01', DEST)}", flush=True)

    res = []
    for act in (
        {"action": "open_hub", "params": {"region": 1}},
        {"action": "negotiate_slots", "params": {"city": "SA01"}},
        {"action": "negotiate_slots", "params": {"city": DEST}},
    ):
        ok, det = ex.run(act)
        linha(f"{act['action']} {act['params']}", ok, det)
        res.append(ok)

    img = Image.open(b.screenshot(O / "a_fim.png")).convert("RGB")
    print(f"fim fase a: cash={world.read_cash_k(b)} livres={world.free_staff_menu(img)} "
          f"hubs={sorted(ex.hubs)} pendentes={ex.hubs_pending}", flush=True)
    b.save(CHAIN)
    b.speed(100)
    print(f"salvo {CHAIN} | {sum(res)}/3 acoes OK", flush=True)


def fase_b(max_turnos=14):
    """Passa turnos ate o hub ficar PRONTO **e** os negociadores voltarem.

    Por que os dois: `hub_ready` so responde pelo HUB; os dois lances de slot
    (SA01 e SA03) sao negociacoes independentes e a fase c depende deles
    (Havana precisa de um 2o slot — o 1o ja e consumido pela rota
    Washington->Havana). Parar so no hub poderia levar a fase c a uma recusa
    por slot e registrar um falso negativo do ACEITE.
    """
    b.load(CHAIN); b.advance(90); b.speed(400)
    escritura()
    ex.hubs_pending = {1: "SA01"}
    anterior = world.read_cash_k(b)
    pronto = False
    for t in range(1, max_turnos + 1):
        g.end_turn()
        b.advance(120)
        # end_turn pode parar numa NOTICIA (so sai com A) ou no RELATORIO ANUAL
        # (so sai com B). Sem isto a fase inteira rodou 8 turnos lendo de uma
        # tela que nao era o menu.
        if not ex.dismiss_to_menu():
            b.screenshot(O / f"b_t{t}_PRESO.png")
            print(f"[turno +{t}] NAO cheguei ao menu — ABORTANDO para nao agir as cegas "
                  f"(tela em b_t{t}_PRESO.png)", flush=True)
            break
        img = Image.open(b.screenshot(O / f"b_t{t}.png")).convert("RGB")
        livres = world.free_staff_menu(img)
        cash = world.read_cash_k(b)
        # SENTINELA: o custo trimestral medido nesta partida e de ~$3.500K. Uma
        # queda muito maior significa que alguma tecla confirmou algo — foi
        # assim que a versao antiga de dismiss_to_menu queimou $276.000K.
        # SENTINELA COM FREIO: nao basta avisar. Se o caixa cair muito alem do
        # custo trimestral, alguma tecla confirmou algo e o savestate PRONTO
        # ficaria contaminado — foi exatamente assim que a versao antiga de
        # dismiss_to_menu queimou $276.000K e o estado seguiu adiante como se
        # nada tivesse acontecido. Aborta ANTES de salvar.
        if anterior - cash > 50000:
            b.screenshot(O / f"b_t{t}_QUEDA.png")
            print(f"[turno +{t}] QUEDA ANORMAL de caixa: {anterior} -> {cash} "
                  f"({cash - anterior:+d}). ABORTANDO sem salvar {PRONTO} "
                  f"(tela em b_t{t}_QUEDA.png)", flush=True)
            break
        pronto, det = ex.hub_ready(1, "SA01")
        print(f"[turno +{t}] cash={cash} ({cash - anterior:+d}) livres={livres}/4 | "
              f"hub pronto={pronto}\n     {det}", flush=True)
        anterior = cash
        b.save(PRONTO)
        # Duas condicoes, nao uma: hub pronto E os 3 negociadores de volta
        # (hub + slots SA01 + slots SA03 sairam na fase a: 4 -> 1).
        if pronto and livres >= 4:
            print(f"HUB PRONTO e negociadores de volta em +{t} turnos; salvo {PRONTO}",
                  flush=True)
            break
        if pronto:
            print(f"     (hub pronto, mas ainda {livres}/4 negociadores livres — "
                  "os lances de slot nao voltaram; continuo)", flush=True)
    b.speed(100)
    print(f"fim da fase b: hub_pronto={pronto}", flush=True)


def fase_c():
    b.load(PRONTO); b.advance(90); b.speed(400)
    escritura()
    # A negociacao concluida entrega 1 slot (MEDIDO 15-16/08 em Bruxelas e
    # Havana). Havana passa a ter 2 (1 consumido pela rota WAS->Havana, 1 livre)
    # e SA03 ganha o primeiro. O jogo e o juiz final: se a crenca estiver errada
    # ele recusa e a recusa fica registrada.
    ex.owned_slots["SA01"] = 2
    ex.owned_slots[DEST] = 1
    ex.hubs.add("SA01")
    ex.hubs_pending.pop(1, None)

    # conferencia visual dos slots da regiao 1 antes de agir
    ex._ensure_menu()
    ok_reg, det = ex._goto_region(1)
    img = Image.open(b.screenshot(O / "c_mapa_sa.png")).convert("RGB")
    cur = tuple(b.read_ram(world.CURSOR_X, 3)[::2])
    print(f"mapa SA ({det}): cidades com slot visivel = "
          f"{world.cities_with_slots(img, cursor=cur, region=1)}", flush=True)

    # EVIDENCIA DISCRIMINANTE do aceite: o delta de caixa NAO prova que a rota
    # partiu do hub (uma rota Washington->SA03 debitaria igual). O que prova e a
    # caixa de rodape da tela de rota dizendo de onde a rota parte. Lida aqui,
    # antes de agir, e desfeita por savestate dentro de hub_ready.
    pronto, det_hub = ex.hub_ready(1, "SA01")
    print(f"banner da tela de rota na regiao 1: pronto={pronto}\n     {det_hub}", flush=True)
    shot_banner = O / "hub_ready_r1.png"
    if shot_banner.exists():
        Image.open(shot_banner).convert("RGB").crop(world.TEXTBOX).resize(
            (768, 3 * (world.TEXTBOX[3] - world.TEXTBOX[1])), Image.NEAREST
        ).save(O / "c_banner_zoom.png")
        print(f"banner ampliado: {O / 'c_banner_zoom.png'}", flush=True)

    print(f"regra: {ex.check_route('SA01', DEST)}", flush=True)
    cash0 = world.read_cash_k(b)
    ok, det = ex.run({"action": "open_route",
                      "params": {"from": "SA01", "to": DEST,
                                 "flights_week": 1, "fare_level": "mid"}})
    linha(f"open_route SA01->{DEST}", ok, det)
    print(f"caixa {cash0} -> {world.read_cash_k(b)}", flush=True)
    print(f"rotas do harness: {ex.routes}", flush=True)
    b.save("../states/_hub_rota_do_hub.state")
    b.speed(100)
    print("ACEITE:", "OK" if ok else "FALHOU", flush=True)


{"a": fase_a, "b": fase_b, "c": fase_c}[sys.argv[1] if len(sys.argv) > 1 else "a"]()
