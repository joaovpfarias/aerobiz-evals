"""Probe visual (com screenshots salvos) de r1c0 tabs Open/Close."""
from pathlib import Path
from PIL import Image
from bridge import BizHawkBridge
from executor import Executor, wait_text
from world import staff_action_is_bid, on_staff_screen

O = Path("../logs/close_hub_probe_18ago")
O.mkdir(parents=True, exist_ok=True)

b = BizHawkBridge()
ex = Executor(b)

b.load("../states/_hub_pronto.state")
b.advance(90)
b.speed(400)
ex.reset_world_state(hubs={"NA13"})

ex.g.back_to_menu()
ok_reg, det = ex._goto_region(1)
print("goto_region(1):", ok_reg, det)

ex.g.open_cmd("home_info")
wait_text(b)
b.advance(120)

img0 = Image.open(b.screenshot(O / "00_neutral.png")).convert("RGB")
print("on_staff_screen:", on_staff_screen(img0))
print("[0] neutral staff_action_is_bid:", staff_action_is_bid(img0))

b.press("Left", hold=3, wait=14)
b.advance(40)
img1 = Image.open(b.screenshot(O / "01_left.png")).convert("RGB")
print("[1] after Left:", staff_action_is_bid(img1))

b.press("Down", hold=3, wait=14)
b.advance(40)
img2 = Image.open(b.screenshot(O / "02_down.png")).convert("RGB")
print("[2] after Down:", staff_action_is_bid(img2))

b.press("Right", hold=3, wait=14)
b.advance(40)
img3 = Image.open(b.screenshot(O / "03_right.png")).convert("RGB")
print("[3] after Right:", staff_action_is_bid(img3))

for _ in range(6):
    b.press("B", hold=5, wait=25)
    b.advance(120)
img_end = Image.open(b.screenshot(O / "04_saida.png")).convert("RGB")
print("saida screenshot salva")
b.speed(100)
print("Screenshots em", O)
