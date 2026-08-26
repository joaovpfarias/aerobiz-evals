"""ETAPA 6-Reversos: Devolver slots via Executor.run() real.

Teste com probe_hub_open_sa.state (negociacao de Havana completada, 1 slot em SA01).
Aceite: verificar slots reduzem (1→0), funcionarios livres podem não mudar.
"""
from pathlib import Path
from PIL import Image
from bridge import BizHawkBridge
from executor import Executor
from macros import Game
import world

O = Path("../logs/return_slots_aceite")
O.mkdir(parents=True, exist_ok=True)
b = BizHawkBridge()
g = Game(b, shot_dir=O)

print("\n" + "="*60)
print("DEVOLVER SLOTS (Havana/SA01)")
print("="*60)
b.load("../states/probe_hub_open_sa.state")
b.advance(90)
b.speed(400)

ex = Executor(b)
ex.g = g
ex._ensure_menu()

print("ANTES DE DEVOLVER:")
livres_antes = ex._menu_free_staff()
print(f"  funcionarios livres: {livres_antes}")

# Devolver 1 slot de Havana
ok, det = ex.run({"action": "return_slots", "params": {"city": "SA01"}})
print(f"\nRESULTADO RETURN: {ok} | {det}")

print("\nDEPOIS DE DEVOLVER:")
livres_depois = ex._menu_free_staff()
print(f"  funcionarios livres: {livres_depois}")

print("\n" + "="*60)
print("FIM DO TESTE DEVOLUCAO")
print("="*60)
b.speed(100)
