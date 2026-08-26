"""Calibracao HONESTA de set_budget: 3 colunas x 2 sentidos, com leitura de volta.

Por que a calibracao anterior foi reprovada na auditoria: os casos testados
caiam todos ABAIXO da ordem corrente, entao o laco Down-only passava sem que
ninguem notasse que subir era impossivel. Aqui cada caso e explicitamente
rotulado com o sentido, e o aceite exige:
  1. a coluna pedida chega na ordem pedida (lida da tela DEPOIS de confirmar);
  2. as OUTRAS duas colunas ficam intactas — mudar o que nao foi pedido e tao
     grave quanto nao mudar o que foi;
  3. o caixa nao cai (definir orcamento e politica, nao compra a vista).
"""

import pathlib
import sys

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import world  # noqa: E402
from bridge import BizHawkBridge  # noqa: E402
from executor import Executor  # noqa: E402
from macros import Game  # noqa: E402

STATES = pathlib.Path(__file__).parent.parent / "states"
OUT = pathlib.Path(__file__).parent.parent / "logs" / "calib_budget_19ago"
OUT.mkdir(parents=True, exist_ok=True)
ORD = world.BUDGET_ORDERS  # ("maximum","raise","maintain","reduce","stop")


def le(b):
    img = Image.open(b.screenshot()).convert("RGB")
    return img


def estado_orcamento(b, g, tag):
    g.back_to_menu()
    g.open_cmd("budgets")
    b.advance(200)
    img = Image.open(g.shot(tag)).convert("RGB")
    if not world.on_budget_screen(img):
        g.back_to_menu()
        return None
    o = world.read_budget_orders(img)
    g.back_to_menu()
    return o


if __name__ == "__main__":
    b = BizHawkBridge()
    g = Game(b, shot_dir=OUT)
    ex = Executor(b)
    ex.g = g
    b.load(str((STATES / "eval_single_2000_lv5.state").resolve()))
    b.advance(120)

    casos = [
        ("repair", ORD.index("reduce"), "DESCE"),
        ("repair", ORD.index("maximum"), "SOBE"),
        ("ad", ORD.index("stop"), "DESCE"),
        ("ad", ORD.index("raise"), "SOBE"),
        ("service", ORD.index("maintain"), "DESCE"),
        ("service", ORD.index("maximum"), "SOBE"),
    ]
    falhas = []
    for cat, lvl, sentido in casos:
        antes = estado_orcamento(b, g, f"antes_{cat}_{ORD[lvl]}")
        caixa0 = world.read_cash_k(b)
        ok, msg = ex.run({"action": "set_budget", "params": {"category": cat, "level": lvl}})
        caixa1 = world.read_cash_k(b)
        depois = estado_orcamento(b, g, f"depois_{cat}_{ORD[lvl]}")
        print(f"\n--- {cat} -> {ORD[lvl]} ({sentido}) ---", flush=True)
        print(f"  executor: ok={ok} | {msg}", flush=True)
        print(f"  ordens antes:  {antes}", flush=True)
        print(f"  ordens depois: {depois}", flush=True)
        print(f"  caixa {caixa0}K -> {caixa1}K", flush=True)
        col = world.BUDGET_COLS.index(cat)
        if not ok:
            falhas.append(f"{cat}/{ORD[lvl]} ({sentido}): executor recusou -> {msg}")
            continue
        if not depois or depois[col] != ORD[lvl]:
            falhas.append(f"{cat}/{ORD[lvl]} ({sentido}): coluna ficou {depois[col] if depois else None}")
        if antes and depois:
            for j, nome in enumerate(world.BUDGET_COLS):
                if j != col and antes[j] != depois[j]:
                    falhas.append(f"{cat}/{ORD[lvl]}: coluna VIZINHA {nome} mudou {antes[j]} -> {depois[j]}")
        if caixa1 < caixa0:
            falhas.append(f"{cat}/{ORD[lvl]}: caixa CAIU {caixa0} -> {caixa1}")

    print("\n==== RESULTADO ====", flush=True)
    print("TUDO OK" if not falhas else f"{len(falhas)} FALHA(S):", flush=True)
    for f in falhas:
        print("  -", f, flush=True)
