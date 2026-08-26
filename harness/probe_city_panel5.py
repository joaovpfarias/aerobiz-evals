"""ETAPA 5a (rodada 6) — o ultimo candidato: a tela de destino do fluxo r0c0.

O painel de cidade (Pop/Econ/Rltns/Trsm + tabela por companhia) ja esta medido no
fluxo de negociacao (§33). Falta saber se a MESMA informacao aparece no mapa de
destino de `new_route` — que seria mais barato (nao gasta funcionario).

So HOVER + um `A` com sentinela de caixa, e sai por `B`/`dismiss_to_menu`. O
savestate e recarregado no fim. Nunca confirma rota.
"""
import sys, pathlib, json, hashlib

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bridge, world
from executor import Executor, STEP_SETTLE
from world import wait_text, on_map_screen, point_cursor_at_world, read_cash_k
from probe_city_panel import BOXES, h

RAIZ = HERE.parent
SHOTS = RAIZ / "logs" / "etapa5a"
SHOTS.mkdir(parents=True, exist_ok=True)
BASE = str(RAIZ / "states" / "_e3b_base.state")


def main():
    cid = sys.argv[1] if len(sys.argv) > 1 else "NA02"  # Seattle: temos 11 slots
    b = bridge.BizHawkBridge(timeout=120)
    ex = Executor(b)
    b.load(BASE)
    b.advance(120)
    caixa0 = read_cash_k(b)
    out = {"caixa0": caixa0, "cid": cid}

    ex.dismiss_to_menu()
    ex.g.open_cmd("new_route")
    wait_text(b)
    b.advance(60)
    im0 = Image.open(b.screenshot(SHOTS / "r6_r0c0_entrada.png")).convert("RGB")
    out["entrada"] = {"on_map": bool(on_map_screen(im0)),
                      "hashes": {k: h(im0, v) for k, v in BOXES.items()},
                      "caixa": read_cash_k(b)}
    print(json.dumps(out["entrada"]), flush=True)

    try:
        reg, pos, verif = point_cursor_at_world(b, cid, None)
        wait_text(b)
        hov = Image.open(b.screenshot(SHOTS / f"r6_hover_{cid}.png")).convert("RGB")
        out["hover"] = {"pos": str(pos), "regiao": reg, "verif": verif,
                        "on_map": bool(on_map_screen(hov)),
                        "hashes": {k: h(hov, v) for k, v in BOXES.items()},
                        "caixa": read_cash_k(b)}
        print(json.dumps(out["hover"]), flush=True)

        antes = read_cash_k(b)
        b.press("A", hold=5, wait=25)
        b.advance(STEP_SETTLE)
        wait_text(b)
        pos_a = Image.open(b.screenshot(SHOTS / f"r6_posA_{cid}.png")).convert("RGB")
        dep = read_cash_k(b)
        out["apos_A"] = {"caixa_antes": antes, "caixa_depois": dep,
                         "caiu": (antes is not None and dep is not None and dep < antes),
                         "on_map": bool(on_map_screen(pos_a)),
                         "hashes": {k: h(pos_a, v) for k, v in BOXES.items()}}
        print(json.dumps(out["apos_A"]), flush=True)
    except Exception as e:
        out["erro"] = repr(e)
        print(json.dumps({"erro": repr(e)}), flush=True)

    # sai SEM confirmar e restaura o savestate (nada acumula)
    ex.dismiss_to_menu()
    out["caixa_apos_dismiss"] = read_cash_k(b)
    b.load(BASE)
    b.advance(120)
    out["caixa_restaurada"] = read_cash_k(b)
    (SHOTS / "r6_r0c0.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(json.dumps({k: out[k] for k in ("caixa0", "caixa_apos_dismiss",
                                          "caixa_restaurada")}), flush=True)


if __name__ == "__main__":
    main()
