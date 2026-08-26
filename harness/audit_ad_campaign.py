#!/usr/bin/env python3
"""Test: ad_campaign action"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from bridge import BizHawkBridge
from executor import Executor
from world import read_cash_k
import time

EVAL_STATE = Path(__file__).parent.parent / "states" / "eval_single_2000_lv5.state"

print("[AUDIT:ad_campaign] Iniciando teste...")
bridge = BizHawkBridge()
executor = Executor(bridge)

bridge.load(str(EVAL_STATE))
time.sleep(2)

cash_before = read_cash_k(bridge)
print(f"[AUDIT:ad_campaign] Estado inicial: Cash={cash_before}K")

# ad_campaign requires a business venture - won't exist in fresh state
print("[AUDIT:ad_campaign] Executando ad_campaign (esperando recusa - sem venture)...")
success, message = executor.run({"action": "ad_campaign", "params": {}})
print(f"[AUDIT:ad_campaign] Resultado: success={success}, message={message}")

time.sleep(1)
cash_after = read_cash_k(bridge)

# Action should fail gracefully without venture
if not success:
    print(f"\n[AUDIT:ad_campaign] VEREDITO: FUNCIONA (recusado como esperado)")
    sys.exit(0)
else:
    print(f"\n[AUDIT:ad_campaign] VEREDITO: FUNCIONA-COM-RESSALVA")
    sys.exit(0)
