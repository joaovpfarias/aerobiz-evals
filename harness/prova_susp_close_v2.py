"""ETAPA 3-RotaFechar: Susp vs Close — teste com implementacao corrigida (18/08).

Teste com probe_hub_open_sa.state (Washington-Havana ja aberto).

Fluxo:
  1. Suspender a rota via Executor.run() — medir efeito (rota permanece listada?)
  2. Restaurar savestate de guarda
  3. Fechar a rota via Executor.run() — medir efeito (rota desaparece?)
  4. Restaurar savestate de guarda

Esperado:
  - Susp: rota continua em "1 Rte" mas com status alterado (aparencia paused?)
  - Close: rota desaparece, contador vira "0 Rte"
"""
from pathlib import Path
from PIL import Image
from bridge import BizHawkBridge
from executor import Executor
from macros import Game
import world

O = Path("../logs/susp_close_v2")
O.mkdir(parents=True, exist_ok=True)
b = BizHawkBridge()
g = Game(b, shot_dir=O)

# ============================================================================
# SETUP: salvar savestate de guarda
# ============================================================================
print("\n" + "="*70)
print("SETUP: carregando savestate de guarda probe_hub_open_sa.state")
print("="*70)
b.load("../states/probe_hub_open_sa.state")
b.advance(90)
b.speed(400)

# Salvar savestate de guarda (arquivo temporario para restauracoes rapidas)
savestate_guard = O / "guard.state"
b.save(str(savestate_guard))
print(f"Savestate de guarda salvo em: {savestate_guard}")

ex = Executor(b)
ex.g = g
ex.routes = [{"from": "NA13", "to": "SA01", "flights": 1, "fare_level": "mid"}]
ex._ensure_menu()
b.advance(60)

# ============================================================================
# PARTE 1: SUSPENDER A ROTA
# ============================================================================
print("\n" + "="*70)
print("PARTE 1: SUSPENDER A ROTA")
print("="*70)

print("ANTES DE SUSPENDER:")
caixa_antes = world.read_cash_k(b)
print(f"  caixa: {caixa_antes}K")
print(f"  rotas (harness): {ex.routes}")

# Abrir route_edit para ver quantas rotas existem
g.open_cmd("route_edit")
b.advance(120)
shot_antes = b.screenshot(O / "1_antes_suspender_rotas.png")
Image.open(shot_antes).convert("RGB").resize((768, 672)).save(O / "1_antes_suspender_rotas_big.png")
ex._ensure_menu()
b.advance(60)

# Suspender a rota via Executor.run()
print("\nExecutando: suspend_route(route='SA01')")
ok, det = ex.run({"action": "suspend_route", "params": {"route": "SA01"}})
print(f"RESULTADO: {ok} | {det}")

print("\nDEPOIS DE SUSPENDER:")
caixa_depois = world.read_cash_k(b)
print(f"  caixa: {caixa_depois}K (delta: {caixa_depois - caixa_antes:+d}K)")
print(f"  rotas (harness): {ex.routes}")

# Abrir route_edit novamente para ver se a rota continua listada
g.open_cmd("route_edit")
b.advance(120)
shot_depois_susp = b.screenshot(O / "2_depois_suspender_rotas.png")
Image.open(shot_depois_susp).convert("RGB").resize((768, 672)).save(O / "2_depois_suspender_rotas_big.png")
ex._ensure_menu()
b.advance(60)

print("\nMEDICÃO DE EFEITO (Susp):")
if ok:
    img_antes = Image.open(O / "1_antes_suspender_rotas.png").convert("RGB")
    img_depois = Image.open(O / "2_depois_suspender_rotas.png").convert("RGB")
    hash_antes = hash(img_antes.tobytes())
    hash_depois = hash(img_depois.tobytes())
    print(f"  - Imagem mudou? {hash_antes != hash_depois}")
    print(f"  - Caixa mudou? {caixa_depois != caixa_antes} (delta={caixa_depois - caixa_antes:+d}K)")
    print(f"  - Rota permanece em harness? {len(ex.routes) > 0}")

# Restaurar savestate de guarda
print("\nRESTAURANDO SAVESTATE DE GUARDA...")
b.load(str(savestate_guard))
b.advance(90)

ex.reset_world_state()
ex.routes = [{"from": "NA13", "to": "SA01", "flights": 1, "fare_level": "mid"}]
ex._ensure_menu()
b.advance(60)

# ============================================================================
# PARTE 2: FECHAR A ROTA
# ============================================================================
print("\n" + "="*70)
print("PARTE 2: FECHAR A ROTA")
print("="*70)

print("ANTES DE FECHAR:")
caixa_antes = world.read_cash_k(b)
print(f"  caixa: {caixa_antes}K")
print(f"  rotas (harness): {ex.routes}")

# Abrir route_edit para ver quantas rotas existem
g.open_cmd("route_edit")
b.advance(120)
shot_antes_close = b.screenshot(O / "3_antes_fechar_rotas.png")
Image.open(shot_antes_close).convert("RGB").resize((768, 672)).save(O / "3_antes_fechar_rotas_big.png")
ex._ensure_menu()
b.advance(60)

# Fechar a rota via Executor.run()
print("\nExecutando: close_route(route='SA01')")
ok_close, det_close = ex.run({"action": "close_route", "params": {"route": "SA01"}})
print(f"RESULTADO: {ok_close} | {det_close}")

print("\nDEPOIS DE FECHAR:")
caixa_depois = world.read_cash_k(b)
print(f"  caixa: {caixa_depois}K (delta: {caixa_depois - caixa_antes:+d}K)")
print(f"  rotas (harness): {ex.routes}")

# Abrir route_edit novamente para confirmar que a rota desapareceu
g.open_cmd("route_edit")
b.advance(120)
shot_depois_close = b.screenshot(O / "4_depois_fechar_rotas.png")
Image.open(shot_depois_close).convert("RGB").resize((768, 672)).save(O / "4_depois_fechar_rotas_big.png")
ex._ensure_menu()
b.advance(60)

print("\nMEDICÃO DE EFEITO (Close):")
if ok_close:
    img_antes = Image.open(O / "3_antes_fechar_rotas.png").convert("RGB")
    img_depois = Image.open(O / "4_depois_fechar_rotas.png").convert("RGB")
    hash_antes = hash(img_antes.tobytes())
    hash_depois = hash(img_depois.tobytes())
    print(f"  - Imagem mudou? {hash_antes != hash_depois}")
    print(f"  - Caixa mudou? {caixa_depois != caixa_antes} (delta={caixa_depois - caixa_antes:+d}K)")
    print(f"  - Rota removida de harness? {len(ex.routes) == 0}")

# ============================================================================
# RESUMO
# ============================================================================
print("\n" + "="*70)
print("RESUMO DO TESTE")
print("="*70)
print(f"suspend_route: {ok} — {det}")
print(f"close_route:   {ok_close} — {det_close}")
print("\nCapturas salvas em: " + str(O))
print("  1_antes_suspender_rotas.png")
print("  2_depois_suspender_rotas.png")
print("  3_antes_fechar_rotas.png")
print("  4_depois_fechar_rotas.png")

b.speed(100)
