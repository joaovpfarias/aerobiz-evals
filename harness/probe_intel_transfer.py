"""ETAPA 5d — CHECAGEM DE TRANSFERIBILIDADE do cache de inteligencia de cidade.

Pergunta unica e medida: os valores do painel colhidos em OUTROS savestates
(logs/etapa5a = sessao do §33; logs/etapa5b = `_e3b_base.state`) valem para o
savestate que o PILOTO usa (`../states/f0_t02_route.state`, cenario 2000)?

Sem esta medida, ligar o cache ao prompt seria mandar "Washington: 34 slots
usados, 34 nossos" para o modelo por FE — exatamente o R1 que este projeto
proibe.

Sentinelas (R2): caixa antes/depois de CADA `A`, aborta se cair; nenhum `A`
depois do painel; volta pelo `B`; recarrega o savestate no fim.

Uso: python probe_intel_transfer.py [CID ...]
"""

import json
import pathlib
import sys
import time

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bridge  # noqa: E402
import world  # noqa: E402
from executor import Executor, STEP_SETTLE  # noqa: E402
from probe_city_panel4 import Contador  # noqa: E402

RAIZ = HERE.parent
SHOTS = RAIZ / "logs" / "etapa5d"
SHOTS.mkdir(parents=True, exist_ok=True)
BASE = str(RAIZ / "states" / "f0_t02_route.state")

# Gabarito = o que o cache (§33/§34) diz, colhido em OUTRO savestate.
CACHE = {
    "NA13": {"fonte": "logs/etapa5a/r4_panel_NA13.png", "pop_m": 1.2, "econ": 90,
             "trsm": 48, "slots_used": 34, "slots_cap": 116, "our_slots": 34},
    "NA06": {"fonte": "logs/etapa5a/panel_NA06.png", "pop_m": 0.6, "econ": 64,
             "trsm": 40, "slots_used": 24, "slots_cap": 94, "our_slots": 12},
    "EU06": {"fonte": "logs/etapa5a/r4_panel_EU06.png", "pop_m": 9.6, "econ": 56,
             "trsm": 38, "slots_used": 0, "slots_cap": 105, "our_slots": 0},
}
PADRAO = ["NA13", "NA06", "EU06"]
CAMPOS = ("pop_m", "econ", "trsm", "slots_used", "slots_cap", "our_slots")


def main():
    cids = sys.argv[1:] or PADRAO
    raw = bridge.BizHawkBridge(timeout=180)
    b = Contador(raw)
    ex = Executor(b)
    b.load(BASE)
    b.advance(120)
    caixa0 = world.read_cash_k(b)
    out = {"base": BASE, "caixa0": caixa0, "cidades": []}
    print(json.dumps({"caixa0": caixa0}), flush=True)

    ex.g.open_cmd("negotiate")
    world.wait_text(b)
    for _ in range(5):
        world.wait_text(b)
        antes = world.read_cash_k(b)
        b.press("A", hold=5, wait=25)
        b.advance(STEP_SETTLE)
        dep = world.read_cash_k(b)
        if antes is not None and dep is not None and dep < antes:
            print(json.dumps({"ABORTO": "caixa caiu no A de entrada",
                              "antes": antes, "depois": dep}), flush=True)
            return 1
        if world.on_map_screen(Image.open(b.screenshot()).convert("RGB")):
            break
    else:
        print(json.dumps({"erro": "nao chegou ao mapa"}), flush=True)
        return 1

    for cid in cids:
        t0, n0 = time.time(), b.n
        rec = {"cid": cid, "cache": CACHE.get(cid)}
        try:
            reg, pos, verif = world.point_cursor_at_world(b, cid, None)
            world.wait_text(b)
            antes = world.read_cash_k(b)
            b.press("A", hold=5, wait=25)
            b.advance(STEP_SETTLE)
            world.wait_text(b)
            shot = SHOTS / ("panel_%s.png" % cid)
            img = Image.open(b.screenshot(shot)).convert("RGB")
            dep = world.read_cash_k(b)
            rec.update({"caixa_antes_A": antes, "caixa_depois_A": dep,
                        "cursor_verificado": verif, "regiao_lida": reg,
                        "toques": b.n - n0, "shot": shot.name})
            if antes is not None and dep is not None and dep < antes:
                rec["ABORTO"] = "caixa caiu ao abrir o painel"
                out["cidades"].append(rec)
                print(json.dumps(rec, ensure_ascii=False), flush=True)
                break
            r = world.read_city_panel(img)
            rec["vivo"] = {k: r[k] for k in CAMPOS}
            rec["on_panel"] = r["on_panel"]
            rec["name_hash"] = r["name_hash"]
            rec["soma_confere"] = r["soma_confere"]
            if cid in CACHE:
                rec["diff"] = {k: [CACHE[cid][k], r[k]] for k in CAMPOS
                               if CACHE[cid][k] != r[k]}
                rec["bate"] = not rec["diff"]
            b.press("B", hold=5, wait=25)
            b.advance(STEP_SETTLE)
            world.wait_text(b)
            rec["B_volta_ao_mapa"] = bool(
                world.on_map_screen(Image.open(b.screenshot()).convert("RGB")))
            rec["seg"] = round(time.time() - t0, 1)
        except Exception as e:  # noqa: BLE001
            rec.update({"erro": repr(e), "seg": round(time.time() - t0, 1)})
        out["cidades"].append(rec)
        print(json.dumps(rec, ensure_ascii=False, default=str), flush=True)
        if not rec.get("B_volta_ao_mapa"):
            print(json.dumps({"parou": "B nao devolveu o mapa — nao insisto (R2)"}),
                  flush=True)
            break

    ex.dismiss_to_menu()
    out["caixa_final"] = world.read_cash_k(b)
    out["toques_total"] = b.n
    b.load(BASE)
    b.advance(120)
    (SHOTS / "transfer.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({"caixa0": caixa0, "caixa_final": out["caixa_final"],
                      "toques_total": b.n}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
