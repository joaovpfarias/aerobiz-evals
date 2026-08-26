"""Calibração COMPLETA e CORRIGIDA do comando r0c4 (orcamentos).

Rerun após as correções de 18/08 em executor._do_set_budget:
- Navegação de ordem em malha fechada (read_budget_orders)
- Guard on_budget_screen entre os _step
- Retorno de False se label não bater

Uso:
  python calib_budget_complete.py wrap       # Testa wrap (STOP->MAXIMUM)
  python calib_budget_complete.py sweep [col]  # Sweep coluna col (0-2)
  python calib_budget_complete.py all        # Wrap test + sweep todas colunas
"""
import sys
from pathlib import Path
from PIL import Image
import world
from bridge import BizHawkBridge
from macros import Game
from executor import Executor

O = Path("../logs/calib_budget_complete")
O.mkdir(parents=True, exist_ok=True)

BASE = "../states/_edit_2rotas.state"
COLS = ["Repair", "Ad", "Service"]
ORDERS = ["MAXIMUM", "RAISE", "MAINTAIN", "REDUCE", "STOP"]

b = BizHawkBridge()
g = Game(b, shot_dir=O)


def show(tag, extra=""):
    p = b.screenshot(O / f"{tag}.png")
    img = Image.open(p).convert("RGB")
    col = world.read_budget_col(img)
    orders = world.read_budget_orders(img)
    money = world.read_budget_money(img)
    levels = world.read_budget_levels(img)
    cash = world.read_cash_k(b)
    msg = f"  {tag}: col={col} orders={orders} money={money} levels={levels} cash={cash}K"
    if extra:
        msg += f" | {extra}"
    print(msg, flush=True)
    return img, (col, orders, money, levels, cash)


def open_budgets():
    ex = Executor(b)
    ex._ensure_menu()
    g.open_cmd("budgets")
    b.advance(200)
    return ex


def test_wrap():
    """Teste se popup de ordem envolve: STOP (idx 4) + 1 Down = MAXIMUM (idx 0)?"""
    print("\n=== TESTE WRAP ===")
    b.load(BASE)
    b.advance(120)
    b.speed(400)
    ex = open_budgets()
    b.advance(100)

    print("Navega para Repair col e abre popup...")
    img = Image.open(b.screenshot()).convert("RGB")
    col = world.read_budget_col(img)
    print(f"  Col atual: {col}")

    # Abrir popup
    b.press("A", hold=5, wait=25)
    b.advance(200)

    # Navegar para STOP (idx 4) — 4 Downs
    print("Navega para STOP...")
    for i in range(4):
        b.press("Down", hold=3, wait=14)
        b.advance(40)

    # Verificar estado em STOP
    img = Image.open(b.screenshot()).convert("RGB")
    orders = world.read_budget_orders(img)
    order_em_stop = orders[0] if orders and orders[0] else "?"
    print(f"  Em STOP: {order_em_stop}")
    b.screenshot(O / "wrap_before.png")

    # Um Down a mais — vai para MAXIMUM (wrap) ou fica em STOP (clamp)?
    print("Aperta Down uma vez mais...")
    b.press("Down", hold=3, wait=14)
    b.advance(40)

    img = Image.open(b.screenshot()).convert("RGB")
    orders = world.read_budget_orders(img)
    order_depois = orders[0] if orders and orders[0] else "?"
    print(f"  Depois: {order_depois}")
    b.screenshot(O / "wrap_after.png")

    wraps = order_depois and order_depois.upper() == "MAXIMUM"
    print(f"\n  RESULTADO: {'ENVOLVE (wrap)' if wraps else 'NAO ENVOLVE (clamp)'}")

    b.speed(100)
    return wraps


def sweep_col(col, wraps=False):
    """Sweep 5 ordens na coluna col (0-2)."""
    print(f"\n=== SWEEP COLUNA {col} ({COLS[col]}) [wrap={wraps}] ===")
    results = {}

    for level in range(5):
        print(f"\nOrdem {level} ({ORDERS[level]}):")
        b.load(BASE)
        b.advance(120)
        b.speed(400)
        ex = open_budgets()
        b.advance(100)

        # Navegare para coluna col
        print(f"  -> navegando para col={col}")
        img = Image.open(b.screenshot()).convert("RGB")
        col_atual = world.read_budget_col(img)
        steps_needed = (col - col_atual) % 3
        for step in range(steps_needed):
            b.press("Right", hold=3, wait=14)
            b.advance(40)

        # Abrir popup
        b.press("A", hold=5, wait=25)
        b.advance(200)

        # Navegar para ordem level (malha fechada com leitura)
        print(f"  -> navegando para ordem {level}")
        img = Image.open(b.screenshot()).convert("RGB")
        orders = world.read_budget_orders(img)
        order_atual_str = orders[col] if orders and orders[col] else "?"
        order_idx_atual = ORDERS.index(order_atual_str.upper()) if order_atual_str.upper() in ORDERS else 0
        print(f"     ordem atual: {order_atual_str} (idx {order_idx_atual})")

        tries = 0
        max_tries = 20
        while order_idx_atual < level and tries < max_tries:
            b.press("Down", hold=3, wait=14)
            b.advance(40)
            img = Image.open(b.screenshot()).convert("RGB")
            orders = world.read_budget_orders(img)
            order_nova_str = orders[col] if orders and orders[col] else "?"
            order_idx_novo = ORDERS.index(order_nova_str.upper()) if order_nova_str.upper() in ORDERS else order_idx_atual
            print(f"     try {tries + 1}: {order_nova_str} (idx {order_idx_novo})")
            order_idx_atual = order_idx_novo
            tries += 1

        # Captura PRÉ-confirmação
        img_pre, (col_pre, ord_pre, money_pre, lvls_pre, cash_pre) = show(
            f"s_{col}_{level:d}_pre_{COLS[col]}_{ORDERS[level]}"
        )

        # Confirmar (2 A's com guard)
        for i in range(2):
            img = Image.open(b.screenshot()).convert("RGB")
            if not world.on_budget_screen(img):
                print(f"     AVISO: deixei tela de orcamento no A#{i+1}")
                break
            ex._step(tries=4)
        b.advance(120)

        # Captura PÓS-confirmação
        img_pos, (col_pos, ord_pos, money_pos, lvls_pos, cash_pos) = show(
            f"s_{col}_{level:d}_pos_{COLS[col]}_{ORDERS[level]}"
        )

        # Armazenar resultado
        results[level] = {
            "pre": {"orders": ord_pre, "money": money_pre, "levels": lvls_pre},
            "pos": {"orders": ord_pos, "money": money_pos, "levels": lvls_pos},
        }

        b.speed(100)

    # Resumo final para a coluna
    print(f"\n=== RESUMO COLUNA {col} ({COLS[col]}) ===")
    for level in range(5):
        res = results[level]
        money_pre = res["pre"]["money"][col] if res["pre"]["money"] else None
        money_pos = res["pos"]["money"][col] if res["pos"]["money"] else None
        order_pos = res["pos"]["orders"][col] if res["pos"]["orders"] else None
        delta = money_pos - money_pre if money_pos and money_pre else None
        delta_str = f"{delta:+d}" if delta is not None else "?"
        print(f"  {level} ({ORDERS[level]:8s}): {money_pre}K -> {money_pos}K ({delta_str}K) | label={order_pos}")

    return results


fase = sys.argv[1] if len(sys.argv) > 1 else "all"

if fase == "wrap":
    wraps = test_wrap()
    if wraps:
        print("\n>>> Próximo: python calib_budget_complete.py sweep [col]")
        print("    Com wrap=True, a navegação usará (target - current) % 5")

elif fase == "sweep":
    col = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    # Por enquanto, assume clamp (não usa wrap)
    results = sweep_col(col, wraps=False)
    print(f"\nResultados salvos em {O}/")

elif fase == "all":
    wraps = test_wrap()
    for col in range(3):
        results = sweep_col(col, wraps=wraps)
    print(f"\nTodos os sweeps completos. Resultados em {O}/")

else:
    print(f"Fase desconhecida: {fase}")
    print("Use: wrap | sweep [col] | all")
