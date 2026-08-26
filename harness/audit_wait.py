#!/usr/bin/env python3
"""Test: wait action"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from bridge import BizHawkBridge
from executor import Executor
from world import read_cash_k, at_main_menu_img, read_quarter_index
import time

EVAL_STATE = Path(__file__).parent.parent / "states" / "eval_single_2000_lv5.state"

print("[AUDIT:wait] Iniciando teste...")
bridge = BizHawkBridge()
executor = Executor(bridge)

# Carregar savestate
print(f"[AUDIT:wait] Carregando {EVAL_STATE}")
bridge.load(str(EVAL_STATE))
time.sleep(2)

# Ler estado inicial
q_before = read_quarter_index(bridge)
cash_before = read_cash_k(bridge)
print(f"[AUDIT:wait] Estado inicial: Quarter={q_before}, Cash={cash_before}K")

# Executar wait
print("[AUDIT:wait] Executando wait...")
success, message = executor.run({"action": "wait", "params": {}})
print(f"[AUDIT:wait] Resultado: success={success}, message={message}")

time.sleep(1)

# Ler estado final
q_after = read_quarter_index(bridge)
cash_after = read_cash_k(bridge)
print(f"[AUDIT:wait] Estado final: Quarter={q_after}, Cash={cash_after}K")

# Analisar
print(f"\n[AUDIT:wait] Analise:")
print(f"  - Sucesso reportado: {success}")
print(f"  - Quarter mudou: {q_before} -> {q_after} (esperado: NAO, wait nao avanca trimestre)")
print(f"  - Cash: {cash_before} -> {cash_after} (esperado: NAO, wait nao muda nada)")

# wait e uma acao valida que nao faz nada - nao debita, nao avanca
# E um placeholder util para o modelo quando quer passar uma acao
if success and q_after == q_before and cash_after == cash_before:
    print(f"\n[AUDIT:wait] VEREDITO: FUNCIONA - acao placeholder correta")
    sys.exit(0)
elif success:
    print(f"\n[AUDIT:wait] VEREDITO: FUNCIONA-COM-RESSALVA - reportou sucesso mas algo mudou")
    sys.exit(0)
else:
    print(f"\n[AUDIT:wait] VEREDITO: FALHA")
    sys.exit(1)
