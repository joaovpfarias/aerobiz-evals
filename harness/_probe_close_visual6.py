"""Probe sistematico: varias combinacoes de d-pad a partir do neutro, screenshot cada uma."""
from pathlib import Path
from PIL import Image
from bridge import BizHawkBridge
from executor import Executor, wait_text
from world import staff_action_is_bid, on_staff_screen

O = Path("../logs/close_hub_probe_18ago/systematic")
O.mkdir(parents=True, exist_ok=True)

b = BizHawkBridge()
ex = Executor(b)

combos = [
    ["Down"],
    ["Down", "Right"],
    ["Down", "Right", "Right"],
    ["Down", "Down"],
    ["Down", "Down", "Right"],
    ["Down", "Down", "Right", "Right"],
    ["Right", "Down"],
]

for i, combo in enumerate(combos):
    b.load("../states/_hub_pronto.state")
    b.advance(90)
    b.speed(400)
    ex.reset_world_state(hubs={"NA13"})
    ex.g.back_to_menu()
    ex._goto_region(1)
    ex.g.open_cmd("home_info")
    wait_text(b)
    b.advance(120)
    for btn in combo:
        b.press(btn, hold=3, wait=14)
        b.advance(40)
    img = Image.open(b.screenshot(O / f"combo{i}_{'_'.join(combo)}.png")).convert("RGB")
    print(f"{combo}: staff_action_is_bid={staff_action_is_bid(img)}")
    for _ in range(6):
        b.press("B", hold=5, wait=25)
        b.advance(120)

b.speed(100)
print("done")
