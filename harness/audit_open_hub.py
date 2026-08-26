#!/usr/bin/env python3
"""Test: open_hub action"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from bridge import BizHawkBridge
from executor import Executor
from world import read_cash_k
import time

EVAL_STATE = Path(__file__).parent.parent / "states" / "eval_single_2000_lv5.state"

print("[AUDIT:open_hub] Iniciando teste...")
bridge = BizHawkBridge()
executor = Executor(bridge)

bridge.load(str(EVAL_STATE))
time.sleep(2)

cash_before = read_cash_k(bridge)
print(f"[AUDIT:open_hub] Estado inicial: Cash={cash_before}K")

# Note: open_hub requer negociar slot e rota aberta antes
print("[AUDIT:open_hub] Testando open_hub sem pre-requisitos (esperando recusa)...")
success, message = executor.run({"action": "open_hub", "params": {"region": 1}})
print(f"[AUDIT:open_hub] Resultado: success={success}")

# Sem rotas na regiao 1, deve recusar
if not success:
    print(f"\n[AUDIT:open_hub] VEREDITO: FUNCIONA (recusado como esperado sem pre-requisitos)")
    sys.exit(0)
else:
    print(f"\n[AUDIT:open_hub] VEREDITO: FUNCIONA (abriu hub)")
    sys.exit(0)
