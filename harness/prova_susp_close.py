"""ETAPA 3-RotaFechar: Susp vs Close via Executor.run() real.

Teste com probe_hub_open_sa.state (Washington-Havana ja aberto).
Aceite: suspender, confirmar na tela, restaurar; fechar, confirmar desaparece, restaurar.
"""
from pathlib import Path
from PIL import Image
from bridge import BizHawkBridge
from executor import Executor
from macros import Game
import world

O = Path("../logs/susp_close_aceite")
O.mkdir(parents=True, exist_ok=True)
b = BizHawkBridge()
g = Game(b, shot_dir=O)

# ============================================================================
# PARTE 1: SUSPENDER A ROTA
# ============================================================================
print("\n" + "="*60)
print("PARTE 1: SUSPENDER A ROTA")
print("="*60)
b.load("../states/probe_hub_open_sa.state")
b.advance(90)
b.speed(400)

ex = Executor(b)
ex.g = g
ex.routes = [{"from": "NA13", "to": "SA01", "flights": 1, "fare_level": "mid"}]
ex._ensure_menu()

print("ANTES DE SUSPENDER:")
caixa_antes = world.read_cash_k(b)
print(f"  caixa: {caixa_antes}K")
print(f"  rotas (harness): {ex.routes}")

# Abrir route_edit para ver quantas rotas existem
g.open_cmd("route_edit")
b.advance(120)
shot_antes = b.screenshot(O / "a_antes_suspender_rotas.png")
Image.open(shot_antes).convert("RGB").resize((768, 672)).save(O / "a_antes_suspender_rotas_big.png")
ex._ensure_menu()

# Suspender a rota
ok, det = ex.run({"action": "suspend_route", "params": {"route": "SA01"}})
print(f"\nRESULTADO SUSPEND: {ok} | {det}")

print("\nDEPOIS DE SUSPENDER:")
caixa_depois = world.read_cash_k(b)
print(f"  caixa: {caixa_depois}K (delta: {caixa_depois - caixa_antes:+d}K)")
print(f"  rotas (harness): {ex.routes}")

# Abrir route_edit novamente para confirmar que a rota continua na lista
g.open_cmd("route_edit")
b.advance(120)
shot_depois = b.screenshot(O / "b_depois_suspender_rotas.png")
Image.open(shot_depois).convert("RGB").resize((768, 672)).save(O / "b_depois_suspender_rotas_big.png")
ex._ensure_menu()

# Restaurar savestate (para testar Close depois)
print("\nRESTAURANDO SAVESTATE...")
b.load("../states/probe_hub_open_sa.state")
b.advance(90)

ex.reset_world_state()
ex.routes = [{"from": "NA13", "to": "SA01", "flights": 1, "fare_level": "mid"}]
ex._ensure_menu()

print("Savestate restaurado, aguardando o próximo teste...")
b.advance(60)

# ============================================================================
# PARTE 2: FECHAR A ROTA
# ============================================================================
print("\n" + "="*60)
print("PARTE 2: FECHAR A ROTA")
print("="*60)

print("ANTES DE FECHAR:")
caixa_antes = world.read_cash_k(b)
print(f"  caixa: {caixa_antes}K")
print(f"  rotas (harness): {ex.routes}")

# Abrir route_edit para ver quantas rotas existem
g.open_cmd("route_edit")
b.advance(120)
shot_antes_close = b.screenshot(O / "c_antes_fechar_rotas.png")
Image.open(shot_antes_close).convert("RGB").resize((768, 672)).save(O / "c_antes_fechar_rotas_big.png")
ex._ensure_menu()

# Fechar a rota
ok, det = ex.run({"action": "close_route", "params": {"route": "SA01"}})
print(f"\nRESULTADO CLOSE: {ok} | {det}")

print("\nDEPOIS DE FECHAR:")
caixa_depois = world.read_cash_k(b)
print(f"  caixa: {caixa_depois}K (delta: {caixa_depois - caixa_antes:+d}K)")
print(f"  rotas (harness): {ex.routes}")

# Abrir route_edit novamente para confirmar que a rota desapareceu
g.open_cmd("route_edit")
b.advance(120)
shot_depois_close = b.screenshot(O / "d_depois_fechar_rotas.png")
Image.open(shot_depois_close).convert("RGB").resize((768, 672)).save(O / "d_depois_fechar_rotas_big.png")
ex._ensure_menu()

print("\n" + "="*60)
print("FIM DO TESTE")
print("="*60)
b.speed(100)
