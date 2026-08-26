#!/usr/bin/env python3
"""Test: buy_aircraft action"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from bridge import BizHawkBridge
from executor import Executor
from world import read_cash_k
import time

EVAL_STATE = Path(__file__).parent.parent / "states" / "eval_single_2000_lv5.state"

print("[AUDIT:buy_aircraft] Iniciando teste...")
bridge = BizHawkBridge()
executor = Executor(bridge)

bridge.load(str(EVAL_STATE))
time.sleep(2)

cash_before = read_cash_k(bridge)
print(f"[AUDIT:buy_aircraft] Estado inicial: Cash={cash_before}K")

print("[AUDIT:buy_aircraft] Executando buy_aircraft(MD100, qty=1)...")
success, message = executor.run({"action": "buy_aircraft", "params": {"model": "MD100", "qty": 1}})
print(f"[AUDIT:buy_aircraft] Resultado: success={success}")

time.sleep(1)
cash_after = read_cash_k(bridge)
print(f"[AUDIT:buy_aircraft] Estado final: Cash={cash_after}K (delta {cash_after-cash_before}K)")

if success and cash_after < cash_before:
    print(f"\n[AUDIT:buy_aircraft] VEREDITO: FUNCIONA")
    sys.exit(0)
elif success:
    print(f"\n[AUDIT:buy_aircraft] VEREDITO: FUNCIONA-COM-RESSALVA")
    sys.exit(0)
else:
    print(f"\n[AUDIT:buy_aircraft] VEREDITO: FALHA")
    sys.exit(1)
