#!/usr/bin/env python3
"""Test: open_venture action"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from bridge import BizHawkBridge
from executor import Executor
from world import read_cash_k
import time

EVAL_STATE = Path(__file__).parent.parent / "states" / "eval_single_2000_lv5.state"

print("[AUDIT:open_venture] Iniciando teste...")
bridge = BizHawkBridge()
executor = Executor(bridge)

bridge.load(str(EVAL_STATE))
time.sleep(2)

cash_before = read_cash_k(bridge)
print(f"[AUDIT:open_venture] Estado inicial: Cash={cash_before}K")

print("[AUDIT:open_venture] Executando open_venture(Washington, type_index=0)...")
success, message = executor.run({"action": "open_venture", "params": {"city": "Washington", "type_index": 0}})
print(f"[AUDIT:open_venture] Resultado: success={success}")

time.sleep(1)
cash_after = read_cash_k(bridge)
print(f"[AUDIT:open_venture] Estado final: Cash={cash_after}K (delta {cash_after-cash_before}K)")

if success and cash_after < cash_before:
    print(f"\n[AUDIT:open_venture] VEREDITO: FUNCIONA")
    sys.exit(0)
elif success:
    print(f"\n[AUDIT:open_venture] VEREDITO: FUNCIONA-COM-RESSALVA")
    sys.exit(0)
else:
    print(f"\n[AUDIT:open_venture] VEREDITO: FALHA")
    sys.exit(1)
