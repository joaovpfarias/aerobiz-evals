"""ETAPA 12-HubsCompleto: fechar hub (verificado) + guardar estado LIMPO no
menu principal + tentar reabrir na MESMA cidade + tentar abrir em cidade
DIFERENTE da mesma regiao (se houver rota la)."""
from pathlib import Path
from PIL import Image

import world
from bridge import BizHawkBridge
from executor import Executor, wait_text
from macros import Game

O = Path("../logs/close_hub_full_18ago")
O.mkdir(parents=True, exist_ok=True)

b = BizHawkBridge()
g = Game(b, shot_dir=O)
ex = Executor(b)
ex.g = g

b.load("../states/_hub_rota_do_hub.state")
b.advance(90)
b.speed(400)

ex.reset_world_state(
    hubs={world.HOME, "SA01"},
    routes=[{"from": world.HOME, "to": "SA01", "flights": 1},
            {"from": "SA01", "to": "SA03", "flights": 1}],
    owned_slots={**world.EVAL_SLOTS_2000, "SA01": 2, "SA03": 1},
)

print("=== FECHANDO HUB (via executor.run, ja corrigido) ===")
caixa0 = world.read_cash_k(b)
ok, det = ex.run({"action": "close_hub", "params": {"region": 1}})
print("close_hub(1):", ok)
print(det)
print("hubs apos close:", ex.hubs, "hubs_pending:", ex.hubs_pending)
print("routes apos close (harness):", ex.routes)

assert ex._ensure_menu(), "nao conseguiu confirmar menu principal apos close_hub"
img_menu = Image.open(b.screenshot(O / "10_menu_confirmado.png")).convert("RGB")
print("at_main_menu confirmado:", world.at_main_menu_img(img_menu))

b.save("../states/_close_hub_clean.state")
print("Estado limpo salvo em _close_hub_clean.state")

print("\n=== TENTATIVA 1: reabrir hub na MESMA cidade (Havana, regiao 1) ===")
caixa1 = world.read_cash_k(b)
ok2, det2 = ex.run({"action": "open_hub", "params": {"region": 1}})
print("open_hub(1) reabrir:", ok2)
print(det2)
caixa2 = world.read_cash_k(b)
print(f"caixa {caixa1}K -> {caixa2}K ({caixa2-caixa1:+d}K)")

# restaurar para o estado limpo antes do proximo teste (nao empilhar estado)
b.load("../states/_close_hub_clean.state")
b.advance(90)
ex.reset_world_state(
    hubs={world.HOME},
    routes=[{"from": world.HOME, "to": "SA01", "flights": 1}],
    owned_slots={**world.EVAL_SLOTS_2000, "SA01": 2},
)

b.speed(100)
print("\nDONE")
