#!/usr/bin/env python3
"""ETAPA 1c — cheque INDEPENDENTE do P&L: Repair/Ad/Service contra a tela de
orcamentos (leitor calibrado no §20/§22, outra tela, outro leitor).

Se as tres rubricas do P&L baterem com o orcamento do mesmo savestate, a
coluna de valores esta confirmada por algo que nao e ela mesma.
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from PIL import Image
from bridge import BizHawkBridge
from macros import Game, INFO, READ_SETTLE
import world

OUT = pathlib.Path(__file__).parent.parent / "logs" / "pnl_19ago"
OUT.mkdir(parents=True, exist_ok=True)
ALVOS = sys.argv[1:] or ["_cityhotel_3turnos_real", "_hub_rota_do_hub", "_close_hub_after_turns"]


def main():
    b = BizHawkBridge(timeout=60)
    res = {}
    for nome in ALVOS:
        print("=" * 60, flush=True)
        b.load(f"../states/{nome}.state")
        g = Game(b, shot_dir=OUT)
        caixa0 = world.read_cash_k(b)
        g.back_to_menu()
        g.open_cmd("budgets")
        p = b.screenshot(OUT / f"{nome}_budget.png")
        img = Image.open(p).convert("RGB")
        money = world.read_budget_money(img)
        niveis = world.read_budget_levels(img)
        g.back_to_menu()
        caixa1 = world.read_cash_k(b)
        print(nome, "budget_money(Repair,Ad,Service)=", money, "niveis=", niveis,
              "on_budget_screen=", world.on_budget_screen(img),
              f"caixa {caixa0}->{caixa1}", flush=True)
        res[nome] = {"budget_money": money, "niveis": niveis,
                     "caixa_antes": caixa0, "caixa_depois": caixa1, "shot": str(p)}
    (OUT / "budget_cross.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
