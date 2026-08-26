#!/usr/bin/env python3
"""ETAPA 1c — busca AO VIVO de um Quarterly Report com Airline Sales != 0.

Le (nao age) em varios savestates: Info->map para saber se ha rotas e
Info->finance para o P&L. Sentinela de caixa em volta de cada savestate — ler
tem que custar zero (R2).
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from PIL import Image
from bridge import BizHawkBridge
from macros import Game, INFO, READ_SETTLE
import world

OUT = pathlib.Path(__file__).parent.parent / "logs" / "pnl_19ago"
OUT.mkdir(parents=True, exist_ok=True)

CANDIDATOS = sys.argv[1:] or [
    "_cityhotel_3turnos_real", "_close_hub_after_turns", "_edit_2rotas",
    "_hub_rota_do_hub", "_turn_guard",
]


def main():
    b = BizHawkBridge(timeout=60)
    resultados = {}
    for nome in CANDIDATOS:
        print("=" * 60, flush=True)
        print("savestate:", nome, flush=True)
        try:
            b.load(f"../states/{nome}.state")
        except Exception as e:
            print("  falhou load:", e, flush=True)
            continue
        g = Game(b, shot_dir=OUT)
        caixa0 = world.read_cash_k(b)
        q0 = world.read_quarter_index(b)
        print(f"  quarter={q0} ({world.date_label(q0)}) caixa={caixa0}K", flush=True)

        g.back_to_menu()
        p_map = g.info_screen("map", f"{nome}_map")
        img_map = Image.open(p_map).convert("RGB")
        rotas, rodape = world.read_routes(img_map)
        print("  on_route_table=", world.on_route_table(img_map),
              "rotas=", rotas, "rodape=", rodape, flush=True)

        g.back_to_menu()
        g.open_cmd("info")
        for _ in range(INFO["finance"]):
            b.press("Right", hold=3, wait=10)
        b.press("A", hold=5, wait=40)
        b.advance(READ_SETTLE)
        p = b.screenshot(OUT / f"{nome}_finance.png")
        img = Image.open(p).convert("RGB")
        pnl = world.read_pnl(img)
        print("  quarterly2=", world.on_quarterly_report_img2(img), flush=True)
        print("  pnl=", json.dumps(pnl), flush=True)

        g.back_to_menu()
        caixa1 = world.read_cash_k(b)
        print(f"  caixa {caixa0} -> {caixa1} (delta {caixa1 - caixa0})", flush=True)
        resultados[nome] = {
            "quarter": q0, "data": world.date_label(q0), "rotas": rotas,
            "rodape_map": rodape, "pnl": pnl,
            "caixa_antes": caixa0, "caixa_depois": caixa1,
            "shot": str(p),
        }
    (OUT / "varredura.json").write_text(json.dumps(resultados, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
