#!/usr/bin/env python3
"""Test: negotiate_slots action"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from bridge import BizHawkBridge
from executor import Executor
from world import read_cash_k, free_staff_menu
import time

EVAL_STATE = Path(__file__).parent.parent / "states" / "eval_single_2000_lv5.state"

print("[AUDIT:neg] Iniciando teste negotiate_slots...")
bridge = BizHawkBridge()
executor = Executor(bridge)

# Carregar savestate
print(f"[AUDIT:neg] Carregando {EVAL_STATE}")
bridge.load(str(EVAL_STATE))
time.sleep(2)

# Ler estado inicial
from PIL import Image
img = Image.open(bridge.screenshot()).convert("RGB")
staff_before = free_staff_menu(img)
cash_before = read_cash_k(bridge)
print(f"[AUDIT:neg] Estado inicial: Staff={staff_before}, Cash={cash_before}K")

# Executar negotiate_slots
print("[AUDIT:neg] Executando negotiate_slots(Washington)...")
success, message = executor.run({"action": "negotiate_slots", "params": {"city": "Washington"}})
print(f"[AUDIT:neg] Resultado: success={success}, message={message}")

time.sleep(1)

# Ler estado final
img = Image.open(bridge.screenshot()).convert("RGB")
staff_after = free_staff_menu(img)
cash_after = read_cash_k(bridge)
print(f"[AUDIT:neg] Estado final: Staff={staff_after}, Cash={cash_after}K")

# Analisar
print(f"\n[AUDIT:neg] Analise:")
print(f"  - Sucesso reportado: {success}")
print(f"  - Staff mudou: {staff_before} -> {staff_after} (esperado: sim, -1)")
print(f"  - Cash mudou: {cash_before} -> {cash_after} (delta {cash_after-cash_before}K)")

if success and staff_after < staff_before and cash_after < cash_before:
    print(f"\n[AUDIT:neg] VEREDITO: FUNCIONA")
    sys.exit(0)
elif success and staff_after < staff_before:
    print(f"\n[AUDIT:neg] VEREDITO: FUNCIONA-COM-RESSALVA - staff diminuiu mas cash nao mudou")
    sys.exit(0)
else:
    print(f"\n[AUDIT:neg] VEREDITO: FALHA")
    sys.exit(1)
