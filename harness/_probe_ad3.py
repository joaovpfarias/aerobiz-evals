"""Probe: continuar r1c1 ad_campaign a partir de _venture_pronto.state,
usando Executor helpers (_pick_free_staff, _step) para navegar passo a passo
com screenshot em cada etapa."""
from PIL import Image
from bridge import BizHawkBridge
from executor import Executor
from macros import Game
from world import read_cash_k

b = BizHawkBridge()
ex = Executor(b)
g = ex.g

b.load("../states/_venture_pronto.state")
b.advance(60)
cash0 = read_cash_k(b)
print("cash antes:", cash0)

g.back_to_menu()
g.open_cmd("ad_campaign")
b.advance(120)
Image.open(b.screenshot()).convert("RGB").save("../logs/action_space_map/ad3_step1_staff.png")

ok_sel, cel, det = ex._pick_free_staff()
print("pick staff:", ok_sel, cel, det)
Image.open(b.screenshot()).convert("RGB").save("../logs/action_space_map/ad3_step2_selected.png")

for i in range(1, 6):
    ok = ex._step()
    img = Image.open(b.screenshot()).convert("RGB")
    p = f"../logs/action_space_map/ad3_step{i+2}.png"
    img.save(p)
    cash_now = read_cash_k(b)
    print(f"_step {i}: ok={ok} cash={cash_now} shot={p}")
    if not ok:
        break

print("cash final:", read_cash_k(b))
