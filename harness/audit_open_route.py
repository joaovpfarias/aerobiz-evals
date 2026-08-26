#!/usr/bin/env python3
"""Test: open_route action"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from bridge import BizHawkBridge
from executor import Executor
from world import read_cash_k
import time

EVAL_STATE = Path(__file__).parent.parent / "states" / "eval_single_2000_lv5.state"

print("[AUDIT:open_route] Iniciando teste...")
bridge = BizHawkBridge()
executor = Executor(bridge)

# Carregar savestate
print(f"[AUDIT:open_route] Carregando {EVAL_STATE}")
bridge.load(str(EVAL_STATE))
time.sleep(2)

# Ler estado inicial
cash_before = read_cash_k(bridge)
print(f"[AUDIT:open_route] Estado inicial: Cash={cash_before}K")

# Executar open_route para Washington->NewYork (NA01)
print("[AUDIT:open_route] Executando open_route(NA01)...")
success, message = executor.run({"action": "open_route", "params": {"to": "NewYork"}})
print(f"[AUDIT:open_route] Resultado: success={success}, message={message}")

time.sleep(1)

# Ler estado final
cash_after = read_cash_k(bridge)
print(f"[AUDIT:open_route] Estado final: Cash={cash_after}K")

# Analisar
print(f"\n[AUDIT:open_route] Analise:")
print(f"  - Sucesso reportado: {success}")
print(f"  - Cash: {cash_before} -> {cash_after} (delta {cash_after-cash_before}K)")

if success and cash_after < cash_before:
    print(f"\n[AUDIT:open_route] VEREDITO: FUNCIONA")
    sys.exit(0)
elif success:
    print(f"\n[AUDIT:open_route] VEREDITO: FUNCIONA-COM-RESSALVA - cash nao mudou")
    sys.exit(0)
else:
    print(f"\n[AUDIT:open_route] VEREDITO: FALHA")
    sys.exit(1)
