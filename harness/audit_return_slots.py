#!/usr/bin/env python3
"""Test: return_slots action"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from bridge import BizHawkBridge
from executor import Executor
import time

EVAL_STATE = Path(__file__).parent.parent / "states" / "eval_single_2000_lv5.state"

print("[AUDIT:return_slots] Iniciando teste...")
bridge = BizHawkBridge()
executor = Executor(bridge)

bridge.load(str(EVAL_STATE))
time.sleep(2)

# return_slots requires negotiated slots - no slots in fresh state
print("[AUDIT:return_slots] Testando return_slots sem slots negociados...")
success, message = executor.run({"action": "return_slots", "params": {"city": "Washington"}})
print(f"[AUDIT:return_slots] Resultado: success={success}, message={message}")

# Should fail or succeed - just verify the action works mechanically
if success or "sem efeito" in message.lower():
    print(f"\n[AUDIT:return_slots] VEREDITO: FUNCIONA")
    sys.exit(0)
else:
    print(f"\n[AUDIT:return_slots] VEREDITO: FALHA")
    sys.exit(1)
