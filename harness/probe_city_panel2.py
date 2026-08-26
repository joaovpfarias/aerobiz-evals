"""ETAPA 5a (rodada 2) — duas perguntas que a rodada 1 nao pode responder.

P1. O "42" e Trsm e o ICONE e Rltns? A rodada 1 so viu cidades dos ESTADOS
    UNIDOS (Rltns e do PAIS, entao seria invariante e nao provaria nada).
    Aqui visito cidades de OUTROS paises: o painel imprime o pais, entao a
    atribuicao se verifica sozinha.

P2. Da para inspecionar VARIAS cidades numa unica entrada no fluxo? A rodada 1
    gastou ~4 min por cidade porque recarregava o savestate e refazia o menu.
    Se `B` na tela "How many slots?" volta ao MAPA, o custo por cidade extra
    cai para o tempo de mover o cursor.

Nunca aperta A depois da tela do painel (R2). Mede caixa e funcionarios livres
no fim e compara com o inicio.
"""
import sys, pathlib, json, hashlib
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bridge, world
from executor import Executor, STEP_SETTLE
from world import (wait_text, on_map_screen, staff_free_cells,
                   point_cursor_at_world, read_cash_k)

RAIZ = HERE.parent
SHOTS = RAIZ / "logs" / "etapa5a"
SHOTS.mkdir(parents=True, exist_ok=True)
BASE = str(RAIZ / "states" / "_e3b_base.state")

from probe_city_panel import BOXES, h


def main():
    cids = sys.argv[1:] or ["NA12", "NA01", "NA08", "NA16"]
    b = bridge.BizHawkBridge()
    ex = Executor(b)
    b.load(BASE); b.advance(120)
    caixa0 = read_cash_k(b)
    livres0 = staff_free_cells(Image.open(b.screenshot()).convert("RGB"))
    out = {"caixa0": caixa0, "livres0": livres0, "cidades": []}

    ex.g.open_cmd("negotiate")
    wait_text(b)
    for _ in range(5):
        wait_text(b)
        b.press("A", hold=5, wait=25)
        b.advance(STEP_SETTLE)
        if on_map_screen(Image.open(b.screenshot()).convert("RGB")):
            break
    else:
        print(json.dumps({"erro": "nao chegou ao mapa"})); return

    import time
    for cid in cids:
        t0 = time.time()
        rec = {"cid": cid}
        try:
            reg, pos, verif = point_cursor_at_world(b, cid, None)
            wait_text(b)
            b.press("A", hold=5, wait=25)
            b.advance(STEP_SETTLE)
            wait_text(b)
            img = Image.open(b.screenshot()).convert("RGB")
            img.save(SHOTS / f"r2_panel_{cid}.png")
            for nome, box in BOXES.items():
                w, hh = box[2] - box[0], box[3] - box[1]
                img.crop(box).resize((w * 4, hh * 4), Image.NEAREST).save(
                    SHOTS / f"r2_zoom_{cid}_{nome}.png")
            rec.update({"ok": True, "regiao": reg, "pos": str(pos),
                        "cursor_verificado": verif,
                        "gauge_px": world.count_rgb(img, world.SLOTS_GAUGE_BOX, world.TEXT_RGB),
                        "hashes": {k: h(img, v) for k, v in BOXES.items()},
                        "caixa_na_tela": read_cash_k(b)})
            # P2: B volta ao mapa?
            b.press("B", hold=5, wait=25)
            b.advance(STEP_SETTLE)
            wait_text(b)
            depois = Image.open(b.screenshot()).convert("RGB")
            depois.save(SHOTS / f"r2_posB_{cid}.png")
            rec["B_volta_ao_mapa"] = bool(on_map_screen(depois))
            rec["seg"] = round(time.time() - t0, 1)
        except Exception as e:
            rec.update({"ok": False, "erro": repr(e), "seg": round(time.time() - t0, 1)})
        out["cidades"].append(rec)
        print(json.dumps(rec, ensure_ascii=False), flush=True)
        if not rec.get("B_volta_ao_mapa"):
            print(json.dumps({"parou": "B nao devolveu o mapa — nao insisto (R2)"}), flush=True)
            break

    ex.dismiss_to_menu()
    img = Image.open(b.screenshot()).convert("RGB")
    out["caixa_final"] = read_cash_k(b)
    out["livres_final"] = staff_free_cells(img)
    (SHOTS / "panel_r2.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(json.dumps({"caixa0": caixa0, "caixa_final": out["caixa_final"],
                      "livres0": livres0, "livres_final": out["livres_final"]}))


if __name__ == "__main__":
    main()
