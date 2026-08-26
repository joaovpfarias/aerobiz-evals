"""Varredura UNICA de estado: um passeio pelas telas de leitura por turno.

Por que uma varredura so e nao cinco leitores independentes: cada entrada em
tela custa uma sequencia de B/A, e o `A` perdido ja custou $276.000K (tela de
Regional Rankings) e $372.000K (caixa YES/NO de patrocinio). Uma passada, com
sentinela de caixa em volta dela.
"""

import pathlib
import sys

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import world  # noqa: E402
from bridge import BizHawkBridge  # noqa: E402
from macros import Game  # noqa: E402

OUT = pathlib.Path(__file__).parent.parent / "logs" / "ler_estado"
STATES = pathlib.Path(__file__).parent.parent / "states"


def sweep(b, g, tag):
    """Devolve (dados, shots). NUNCA levanta por tela ilegivel: campo nao lido
    vira None e o chamador decide — abortar a varredura no meio deixaria o jogo
    numa tela intermediaria, que e pior que um campo faltando."""
    caixa0 = world.read_cash_k(b)
    shots = {}
    for item in ("map", "fleet", "facilities"):
        shots[item] = g.info_screen(item, f"{tag}_{item}")
    g.back_to_menu()
    g.open_cmd("budgets")
    b.advance(200)
    shots["budgets"] = g.shot(f"{tag}_budgets")
    g.back_to_menu()
    caixa1 = world.read_cash_k(b)

    img_map = Image.open(shots["map"]).convert("RGB")
    img_fleet = Image.open(shots["fleet"]).convert("RGB")
    img_bud = Image.open(shots["budgets"]).convert("RGB")
    rotas, n_rte = world.read_routes(img_map)
    dados = {
        "caixa_k": caixa1,
        "caixa_caiu": caixa1 < caixa0,
        "rotas": rotas,
        "n_rte": n_rte,
        "frota": world.read_fleet(img_fleet),
        "orcamento_tela": world.on_budget_screen(img_bud),
        "orcamento_niveis": world.read_budget_levels(img_bud) if world.on_budget_screen(img_bud) else None,
        "orcamento_ordens": world.read_budget_orders(img_bud) if world.on_budget_screen(img_bud) else None,
    }
    return dados, shots


if __name__ == "__main__":
    b = BizHawkBridge()
    g = Game(b, shot_dir=OUT)
    for name in (sys.argv[1:] or ["probe_hub_open_sa"]):
        b.load(str((STATES / f"{name}.state").resolve()))
        b.advance(120)
        dados, shots = sweep(b, g, f"sweep_{name}")
        print(f"=== {name} ===", flush=True)
        for k, v in dados.items():
            print(f"  {k}: {v}", flush=True)
        for k, v in shots.items():
            print(f"  shot {k}: {v}", flush=True)
