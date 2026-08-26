"""Calibracao do comando r0c4 (orcamentos): Repair / Ad / Service.

Fluxo MEDIDO (probe_edit.py walk budgets):
  r0c4 -> "Change which budget?"        (Right = proxima coluna, ciclo 3)
   A   -> "What are your orders?"       (Down = proxima ordem, ciclo 5:
                                         MAXIMUM RAISE MAINTAIN REDUCE STOP)
   A   -> "Are you sure you want ... ?" (datilografa em 3 telas)
   A   -> aplica e VOLTA para "Change which budget?"

Fases:
  sweep [col]   aplica cada uma das 5 ordens a coluna `col` (0=Rep 1=Ad 2=Svc),
                uma recarga do savestate por ordem, e captura a tela final
  drift col ord n   aplica a ordem e passa n trimestres, capturando a tela de
                orcamento a cada trimestre (o NIVEL e um estoque, nao muda no ato)
  repeat col ord n  aplica a MESMA ordem n vezes seguidas (sem passar turno)
"""
import sys
from pathlib import Path

from PIL import Image

import world
from bridge import BizHawkBridge
from macros import Game

O = Path("../logs/edit")
O.mkdir(parents=True, exist_ok=True)
BASE = "../states/_edit_2rotas.state"
ORDERS = ["MAXIMUM", "RAISE", "MAINTAIN", "REDUCE", "STOP"]
COLS = ["Repair", "Ad", "Service"]

b = BizHawkBridge()
g = Game(b, shot_dir=O)


def show(tag):
    p = b.screenshot(O / f"{tag}.png")
    img = Image.open(p).convert("RGB")
    print(f"  {tag}: sel={world.read_budget_col(img)} bars={world.read_budget_levels(img)} "
          f"labels={world.read_budget_orders(img)} money={world.read_budget_money(img)} "
          f"caixa={world.read_cash_k(b)}K", flush=True)
    return img


def open_budgets():
    from executor import Executor
    ex = Executor(b)
    ex._ensure_menu()
    g.open_cmd("budgets")
    b.advance(200)
    return ex


def apply_order(col, ordem):
    """Da a ordem `ordem` (indice) a coluna `col`, partindo da tela de orcamentos."""
    atual = world.wait_budget_col(b)
    for _ in range((col - atual) % 3):
        b.press("Right", hold=3, wait=14)
        b.advance(60)
    b.press("A", hold=5, wait=25)
    b.advance(200)
    for _ in range(ordem % 5):
        b.press("Down", hold=3, wait=14)
        b.advance(60)
    show(f"pre_{COLS[col]}_{ORDERS[ordem]}")
    # A ate a PERGUNTA mudar, duas vezes ("Are you sure...?" e a volta para
    # "Change which budget?"). Contar A's fixos NAO funciona: com 3 A's cegos a
    # ordem ficou registrada no rotulo mas o valor em $ nao mudou em nenhuma das
    # 5 ordens — o ultimo A caiu durante a datilografia e foi engolido.
    from executor import Executor
    ex = Executor(b)
    for _ in range(2):
        ex._step(tries=4)
    b.advance(120)


fase = sys.argv[1]

if fase == "sweep":
    col = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    for o in range(5):
        b.load(BASE)
        b.advance(120)
        b.speed(400)
        open_budgets()
        show(f"s0_{COLS[col]}_{ORDERS[o]}")
        apply_order(col, o)
        show(f"s1_{COLS[col]}_{ORDERS[o]}")
        b.speed(100)

elif fase == "repeat":
    col, o, n = int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    b.load(BASE)
    b.advance(120)
    b.speed(400)
    open_budgets()
    show(f"r0_{COLS[col]}_{ORDERS[o]}")
    for i in range(1, n + 1):
        apply_order(col, o)
        show(f"r{i}_{COLS[col]}_{ORDERS[o]}")
    b.speed(100)

elif fase == "drift":
    col, o, n = int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    b.load(BASE)
    b.advance(120)
    b.speed(400)
    ex = open_budgets()
    show(f"d0_{COLS[col]}_{ORDERS[o]}")
    apply_order(col, o)
    show(f"d0b_{COLS[col]}_{ORDERS[o]}")
    for t in range(1, n + 1):
        ex._ensure_menu()
        g.end_turn()
        b.advance(120)
        ex._ensure_menu()
        open_budgets()
        show(f"d{t}_{COLS[col]}_{ORDERS[o]}")
    b.speed(100)
