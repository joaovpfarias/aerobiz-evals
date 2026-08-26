"""ETAPA 3-RotaFechar: Susp vs Close — teste com implementacao corrigida (18/08 v2).

Fluxo: acao executada DIRETO na barra de abas, nao world map.

Aceite:
  1. Suspender e confirmar que rota permanece (count=1) com status mudado
  2. Restaurar
  3. Fechar e confirmar que rota desaparece (count=0)
  4. Restaurar
"""
from pathlib import Path
from PIL import Image
from bridge import BizHawkBridge
from executor import Executor
from macros import Game
import world

O = Path("../logs/susp_close_final")
O.mkdir(parents=True, exist_ok=True)
b = BizHawkBridge()
g = Game(b, shot_dir=O)

print("\n" + "="*70)
print("ETAPA 3-RotaFechar: Susp vs Close (FINAL)")
print("="*70)

# Usar um savestate NOVO (não o que foi corrompido pela tentativa anterior)
savestate_orig = "../states/probe_hub_open_sa.state"
b.load(savestate_orig)
b.advance(90)
b.speed(400)

ex = Executor(b)
ex.g = g
ex.routes = [{"from": "NA13", "to": "SA01", "flights": 1, "fare_level": "mid"}]
ex._ensure_menu()
b.advance(60)

# ============================================================================
# PARTE 1: SUSPENDER A ROTA
# ============================================================================
print("\nPARTE 1: SUSPENDER A ROTA")
print("-" * 70)

# Ler estado antes
g.open_cmd("route_edit")
b.advance(120)
img_antes = Image.open(b.screenshot(O / "1a_antes_suspender.png")).convert("RGB")
ex._ensure_menu()
b.advance(60)

caixa_antes = world.read_cash_k(b)
print(f"Antes:  caixa={caixa_antes}K, rotas={len(ex.routes)}")

# Suspender via Executor
ok_susp, msg_susp = ex.run({"action": "suspend_route", "params": {"route": "SA01"}})
print(f"Resultado: {ok_susp} | {msg_susp}")

# Ler estado depois
caixa_depois = world.read_cash_k(b)
print(f"Depois: caixa={caixa_depois}K, rotas={len(ex.routes)}")
print(f"Delta caixa: {caixa_depois - caixa_antes:+d}K")

# Verificar visualmente
g.open_cmd("route_edit")
b.advance(120)
img_depois = Image.open(b.screenshot(O / "1b_depois_suspender.png")).convert("RGB")
ex._ensure_menu()
b.advance(60)

if ok_susp:
    print(f"\nMEDICÃO DE EFEITO (Susp):")
    print(f"  ✓ Caixa mudou? {caixa_depois != caixa_antes}")
    print(f"  ✓ Rotas permaneceram? {len(ex.routes) > 0}")
    # Comparar imagens
    hash_antes = hash(img_antes.tobytes()[:100])
    hash_depois = hash(img_depois.tobytes()[:100])
    print(f"  ✓ Tela mudou? {hash_antes != hash_depois}")

# Restaurar para testar Close
print("\nRestaurando savestate para testar Close...")
b.load(savestate_orig)
b.advance(90)
ex.routes = [{"from": "NA13", "to": "SA01", "flights": 1, "fare_level": "mid"}]
ex._ensure_menu()
b.advance(60)

# ============================================================================
# PARTE 2: FECHAR A ROTA
# ============================================================================
print("\nPARTE 2: FECHAR A ROTA")
print("-" * 70)

# Ler estado antes
g.open_cmd("route_edit")
b.advance(120)
img_antes_close = Image.open(b.screenshot(O / "2a_antes_fechar.png")).convert("RGB")
ex._ensure_menu()
b.advance(60)

caixa_antes_close = world.read_cash_k(b)
print(f"Antes:  caixa={caixa_antes_close}K, rotas={len(ex.routes)}")

# Fechar via Executor
ok_close, msg_close = ex.run({"action": "close_route", "params": {"route": "SA01"}})
print(f"Resultado: {ok_close} | {msg_close}")

# Ler estado depois
caixa_depois_close = world.read_cash_k(b)
print(f"Depois: caixa={caixa_depois_close}K, rotas={len(ex.routes)}")
print(f"Delta caixa: {caixa_depois_close - caixa_antes_close:+d}K")

# Verificar visualmente
g.open_cmd("route_edit")
b.advance(120)
img_depois_close = Image.open(b.screenshot(O / "2b_depois_fechar.png")).convert("RGB")
ex._ensure_menu()
b.advance(60)

if ok_close:
    print(f"\nMEDICÃO DE EFEITO (Close):")
    print(f"  ✓ Caixa mudou? {caixa_depois_close != caixa_antes_close}")
    print(f"  ✓ Rota foi deletada? {len(ex.routes) == 0}")
    # Comparar imagens
    hash_antes = hash(img_antes_close.tobytes()[:100])
    hash_depois = hash(img_depois_close.tobytes()[:100])
    print(f"  ✓ Tela mudou? {hash_antes != hash_depois}")

# ============================================================================
# RESUMO
# ============================================================================
print("\n" + "="*70)
print("RESUMO")
print("="*70)
print(f"suspend_route: {ok_susp}")
print(f"close_route:   {ok_close}")
print(f"\nCapturas: {O}")

b.speed(100)
