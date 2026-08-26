"""Teste se popup de ordem envolve (wrap) de STOP (idx 4) para MAXIMUM (idx 0)."""
import sys
from PIL import Image
from bridge import BizHawkBridge
import world
from macros import Game
from executor import Executor

b = BizHawkBridge()
b.load("../states/_edit_2rotas.state")
b.advance(120)
b.speed(400)

O = "..\\logs\\wrap_test"
import pathlib
pathlib.Path(O).mkdir(parents=True, exist_ok=True)

g = Game(b, shot_dir=O)
ex = Executor(b)

ex._ensure_menu()
g.open_cmd("budgets")
b.advance(200)

ORDERS = ["MAXIMUM", "RAISE", "MAINTAIN", "REDUCE", "STOP"]

# Navegare para Repair (col 0)
print("Navega ndo para coluna Repair...")
img = Image.open(b.screenshot()).convert("RGB")
col = world.read_budget_col(img)
print(f"  Col atual: {col}")

# Abrir popup
b.press("A", hold=5, wait=25)
b.advance(200)

# Navegar para STOP (idx 4) — 4 Downs
print("Navegando para STOP (idx 4)...")
for i in range(4):
    b.press("Down", hold=3, wait=14)
    b.advance(40)
    img = Image.open(b.screenshot()).convert("RGB")
    orders = world.read_budget_orders(img)
    order_str = orders[0] if orders and orders[0] else "?"
    print(f"  Try {i+1}: {order_str}")

# Captura PRÉ-wrap
img = Image.open(b.screenshot()).convert("RGB")
orders = world.read_budget_orders(img)
order_antes = orders[0] if orders and orders[0] else "?"
print(f"Antes de Down (em STOP): {order_antes}")
b.screenshot(f"{O}/pre_wrap.png")

# Um Down - vai envolve para MAXIMUM ou fica em STOP?
print("\nApertando Down uma vez para testar wrap...")
b.press("Down", hold=3, wait=14)
b.advance(40)

img = Image.open(b.screenshot()).convert("RGB")
orders = world.read_budget_orders(img)
order_depois = orders[0] if orders and orders[0] else "?"
print(f"Depois de Down (testa wrap): {order_depois}")
b.screenshot(f"{O}/pos_wrap.png")

if order_depois and order_depois.upper() == "MAXIMUM":
    print("\n✓ POPUP ENVOLVE (wrap): STOP -> MAXIMUM com 1 Down")
    print("  Implicacao: usar (target - current) % 5 para navegar ordem")
elif order_depois and order_depois.upper() == "STOP":
    print("\n✗ POPUP NAO ENVOLVE (clamp): fica em STOP")
    print("  Implicacao: DOWN-only funciona em uma direcao")
else:
    print(f"\n? RESULTADO DESCONHECIDO: {order_depois}")

# Voltar
b.press("B", hold=5, wait=25)
b.advance(100)
b.speed(100)
