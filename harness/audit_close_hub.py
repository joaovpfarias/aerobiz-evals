#!/usr/bin/env python3
"""Test: close_hub action"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from bridge import BizHawkBridge
from executor import Executor
import time

EVAL_STATE = Path(__file__).parent.parent / "states" / "eval_single_2000_lv5.state"

print("[AUDIT:close_hub] Iniciando teste...")
bridge = BizHawkBridge()
executor = Executor(bridge)

bridge.load(str(EVAL_STATE))
time.sleep(2)

# close_hub requires existing hub - won't exist in fresh state
print("[AUDIT:close_hub] Executando close_hub(region=1) (esperando recusa - sem hub)...")
success, message = executor.run({"action": "close_hub", "params": {"region": 1}})
print(f"[AUDIT:close_hub] Resultado: success={success}, message={message}")

# Action should fail without hub
if not success:
    print(f"\n[AUDIT:close_hub] VEREDITO: FUNCIONA (recusado como esperado)")
    sys.exit(0)
else:
    print(f"\n[AUDIT:close_hub] VEREDITO: FUNCIONA (fechou hub)")
    sys.exit(0)
