"""ETAPA 6-Reversos: Fechar hub via Executor.run() real.

Teste com probe_hub_open_sa.state (hub SA ja aberto).
Aceite: verificar que hub desaparece, funcionarios podem mudar, cascade risk: rota pode deletar.
"""
from pathlib import Path
from PIL import Image
from bridge import BizHawkBridge
from executor import Executor
from macros import Game
import world

O = Path("../logs/close_hub_aceite")
O.mkdir(parents=True, exist_ok=True)
b = BizHawkBridge()
g = Game(b, shot_dir=O)

print("\n" + "="*60)
print("FECHAR HUB (AMERICA DO SUL, regiao 1)")
print("="*60)
b.load("../states/probe_hub_open_sa.state")
b.advance(90)
b.speed(400)

ex = Executor(b)
ex.g = g
ex._ensure_menu()

print("ANTES DE FECHAR:")
caixa_antes = world.read_cash_k(b)
livres_antes = ex._menu_free_staff()
print(f"  caixa: {caixa_antes}K")
print(f"  funcionarios livres: {livres_antes}")
print(f"  rotas (harness): {ex.routes}")

# Fechar hub da America do Sul (regiao 1)
ok, det = ex.run({"action": "close_hub", "params": {"region": 1}})
print(f"\nRESULTADO CLOSE_HUB: {ok} | {det}")

print("\nDEPOIS DE FECHAR:")
caixa_depois = world.read_cash_k(b)
livres_depois = ex._menu_free_staff()
print(f"  caixa: {caixa_depois}K (delta: {caixa_depois - caixa_antes:+d}K)")
print(f"  funcionarios livres: {livres_depois}")
print(f"  rotas (harness): {ex.routes}")

print("\n" + "="*60)
print("FIM DO TESTE FECHAMENTO")
print("="*60)
b.speed(100)
