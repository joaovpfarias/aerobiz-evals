"""ETAPA 6-Reversos: Vender aeronave via Executor.run() real.

Teste com eval_single_2000_lv5.state (MD100 x6 disponiveis).
Aceite: verificar caixa sobe (+preco), Info→fleet: Avail 6→5.

Dois oracles de efeito:
  1. Caixa: 1.220.000K -> X > 1.220.000K (delta > 0, lido)
  2. Fleet: MD100 Avail 6 -> 5 (visual na tela Info→fleet)
"""
from pathlib import Path
from PIL import Image
from bridge import BizHawkBridge
from executor import Executor
from macros import Game
import world

O = Path("../logs/sell_aircraft_aceite")
O.mkdir(parents=True, exist_ok=True)
b = BizHawkBridge()
g = Game(b, shot_dir=O)

print("\n" + "="*60)
print("ETAPA 6-REVERSOS: VENDER AERONAVE (MD100 x1) VIA WORLD LEASE")
print("="*60)
b.load("../states/eval_single_2000_lv5.state")
b.advance(90)
b.speed(400)

ex = Executor(b)
ex.g = g
ex._ensure_menu()

print("\n[1/3] ANTES DE VENDER:")
caixa_antes = world.read_cash_k(b)
print(f"  Caixa: {caixa_antes}K")

# Oracle 1: Abrir Info→fleet para ver a frota ANTES
print("\n[2/3] CAPTURANDO FROTA (ANTES)...")
# Padrão de macros.py: open_cmd("info") + Right x INFO[which] + A
g.open_cmd("info")
b.advance(150)
# Fleet é índice 2 em INFO dict: Right x2
b.press("Right", hold=3, wait=10)
b.advance(40)
b.press("Right", hold=3, wait=10)
b.advance(40)
b.press("A", hold=5, wait=40)
b.advance(150)
shot_frota_antes = b.screenshot(O / "a_frota_antes.png")
Image.open(shot_frota_antes).convert("RGB").resize((768, 672)).save(O / "a_frota_antes_big.png")
print(f"  Screenshot salvo: {shot_frota_antes}")
ex._ensure_menu()

# Vender 1 MD100
print("\n[3/3] EXECUTANDO VENDA VIA Executor.run()...")
ok, det = ex.run({"action": "sell_aircraft", "params": {"model": "MD100", "qty": 1}})
print(f"\n  Resultado: {ok}")
print(f"  Detalhe: {det}")

# Oracle 1 (caixa): Verificar que subiu
print("\n[4/4] VERIFICACAO DE EFEITO (DEPOIS DE VENDER):")
caixa_depois = world.read_cash_k(b)
delta = caixa_depois - caixa_antes
print(f"  Caixa: {caixa_antes}K -> {caixa_depois}K (delta: {delta:+d}K)")
print(f"    Oracle 1 (caixa sobe): {'✓ VERIFICADO' if delta > 0 else '✗ FALHA: caixa nao subiu!'}")

# Oracle 2: Abrir Info→fleet novamente para confirmar que Avail caiu de 6→5
print("\n[5/5] CAPTURANDO FROTA (DEPOIS)...")
# Mesmo padrão: open_cmd("info") + Right x2 + A
# NOTA: o cursor pode estar pegajoso (STATUS.md armadilha), mas a captura visual e o que importa
g.open_cmd("info")
b.advance(150)
b.press("Right", hold=3, wait=10)
b.advance(40)
b.press("Right", hold=3, wait=10)
b.advance(40)
b.press("A", hold=5, wait=40)
b.advance(150)
shot_frota_depois = b.screenshot(O / "b_frota_depois.png")
Image.open(shot_frota_depois).convert("RGB").resize((768, 672)).save(O / "b_frota_depois_big.png")
print(f"  Screenshot salvo: {shot_frota_depois}")
print(f"    Oracle 2 (fleet Avail 6→5): [verificar visualmente em b_frota_depois.png]")
ex._ensure_menu()

print("\n" + "="*60)
print("FIM DO TESTE VENDA")
print("="*60 + "\n")
b.speed(100)
