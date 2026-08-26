#!/usr/bin/env python3
"""ETAPA 3a — aceite AO VIVO de `aircraft_index` e `planes` (open_route).

Duas partes, ambas com leitura DE VOLTA da tela (R4):

A) aircraft_index — 3 indices pedidos no savestate `_3a_plane2.state`
   (frota MD100 + A340, parado na tela "What type of plane..."). O modelo
   exibido e identificado por NUMERO (alcance+assentos x AIRCRAFT_CATALOG),
   nao pelo nome, porque o jogo desenha um simbolo grafico ao lado do nome.

B) planes — 3 rotas REAIS (1, 2 e 3 avioes) a partir de
   `eval_single_2000_lv5.state`, conferidas por DOIS sinais: o "x N" da tela e
   o `in_use` de Info->fleet depois que a rota abriu.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from PIL import Image

import world
from bridge import BizHawkBridge
from executor import Executor
from macros import Game

OUT = pathlib.Path(__file__).parent.parent / "logs" / "etapa3a"
OUT.mkdir(parents=True, exist_ok=True)
ESPERADO_IDX = {0: "MD100", 1: "A340"}   # ordem de Info->fleet em _buy_entregue
DESTINOS = {1: "NA06", 2: "NA03", 3: "NA02"}


def le_frota(b, g, tag):
    g.back_to_menu()
    img = Image.open(g.info_screen("fleet", tag)).convert("RGB")
    frota = world.read_fleet(img)
    g.back_to_menu()
    if not frota or not all(x["model"] and "?" not in x["model"] for x in frota):
        return None
    return frota


def parte_a(b):
    linhas = []
    for idx in (0, 1, 2):
        ex = Executor(b)
        b.load("../states/_3a_plane2.state")
        b.advance(90)
        ok, det, modelo = ex._pick_aircraft(idx, f"proA{idx}")
        esperado = ESPERADO_IDX.get(idx)
        if esperado is None:
            # ciclo tem 2 modelos: pedir o 3o TEM de ser recusado, com o motivo
            # medido (e nao virar "modelo 0" em silencio)
            passou = (not ok) and "cicla por 2 modelo" in det
        else:
            passou = ok and modelo == esperado
        linhas.append({"idx": idx, "ok": ok, "modelo_lido": modelo,
                       "esperado": esperado or "RECUSA (indice fora do ciclo)",
                       "detalhe": det, "passou": passou})
        print("A idx=%d -> %s" % (idx, json.dumps(linhas[-1], ensure_ascii=False)), flush=True)
    return linhas


def parte_b(b):
    g = Game(b, shot_dir=OUT)
    linhas = []
    for n, dest in DESTINOS.items():
        ex = Executor(b)
        b.load("../states/eval_single_2000_lv5.state")
        b.advance(90)
        ex.reset_world_state(owned_slots=dict(world.EVAL_SLOTS_2000))
        frota0 = le_frota(b, g, f"prova3a_frota_antes_{n}")
        caixa0 = world.read_cash_k(b)
        ok, det = ex.run({"action": "open_route",
                          "params": {"from": world.HOME, "to": dest,
                                     "planes": n, "flights_week": 1}})
        frota1 = le_frota(b, g, f"prova3a_frota_depois_{n}")
        caixa1 = world.read_cash_k(b)
        in_use0 = (frota0 or [{}])[0].get("in_use")
        in_use1 = (frota1 or [{}])[0].get("in_use")
        na_tela = None
        if ok and "aeronave(s) LIDAS" in det:
            na_tela = int(det.split("), ")[1].split(" aeronave")[0])
        passou = bool(ok) and na_tela == n and in_use0 is not None and in_use1 == in_use0 + n
        linhas.append({"pedido": n, "dest": dest, "ok": ok, "na_tela": na_tela,
                       "in_use_antes": in_use0, "in_use_depois": in_use1,
                       "caixa": [caixa0, caixa1], "detalhe": det, "passou": passou})
        print("B planes=%d -> %s" % (n, json.dumps(linhas[-1], ensure_ascii=False)), flush=True)
    return linhas


def main():
    b = BizHawkBridge(timeout=120)
    b.speed(400)
    so = sys.argv[1] if len(sys.argv) > 1 else "ab"
    res = {}
    if "a" in so:
        res["A_aircraft_index"] = parte_a(b)
    if "b" in so:
        res["B_planes"] = parte_b(b)
    passou = sum(1 for bloco in res.values() for l in bloco if l["passou"])
    total = sum(len(bloco) for bloco in res.values())
    res["aceite"] = f"{passou}/{total}"
    (OUT / f"prova_etapa3a_{so}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print("ACEITE", res["aceite"], flush=True)
    return 0 if passou == total else 1


if __name__ == "__main__":
    sys.exit(main())
