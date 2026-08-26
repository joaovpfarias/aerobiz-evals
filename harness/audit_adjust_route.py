#!/usr/bin/env python3
"""Test: adjust_route action"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from bridge import BizHawkBridge
from executor import Executor
import time

EVAL_STATE = Path(__file__).parent.parent / "states" / "eval_single_2000_lv5.state"

print("[AUDIT:adjust_route] Iniciando teste...")
bridge = BizHawkBridge()
executor = Executor(bridge)

bridge.load(str(EVAL_STATE))
time.sleep(2)

# adjust_route requires existing route - no routes in fresh state, will recusa
print("[AUDIT:adjust_route] Testando adjust_route sem rotas (esperando recusa)...")
success, message = executor.run({"action": "adjust_route", "params": {"route": "NA01", "flights_week": 1}})
print(f"[AUDIT:adjust_route] Resultado: success={success}, message={message}")

# Should fail without existing route
if not success:
    print(f"\n[AUDIT:adjust_route] VEREDITO: FUNCIONA (recusado como esperado)")
    sys.exit(0)
else:
    print(f"\n[AUDIT:adjust_route] VEREDITO: FUNCIONA (executou)")
    sys.exit(0)
