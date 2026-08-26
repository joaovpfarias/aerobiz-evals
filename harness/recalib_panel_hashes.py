#!/usr/bin/env python3
"""Re-calibrate panel hashes in the current environment."""

import sys
import hashlib
from pathlib import Path
from PIL import Image
from bridge import BizHawkBridge
from macros import Game
from world import BUY_PANEL, AIRCRAFT_CATALOG

def _crop_md5(img, box):
    """Extract crop and compute MD5."""
    cropped = img.crop(box)
    return hashlib.md5(cropped.tobytes()).hexdigest()[:8]

O = Path("../logs/panel_hash_calib")
O.mkdir(parents=True, exist_ok=True)

b = BizHawkBridge()
g = Game(b, shot_dir=O)

print("\n" + "="*60)
print("RE-CALIBRATING PANEL HASHES")
print("="*60)

# Load eval savestate
b.load("../states/eval_single_2000_lv5.state")
b.advance(90)
b.speed(400)

from executor import Executor
ex = Executor(b)
ex.g = g
ex._ensure_menu()

print(f"\nStarting cash: {ex._cash()}")
print("\nMeasuring panel hashes in current environment...")
print("(Note: savestate likely only has MD100 available)")

# Try to navigate to the buy screen and measure each model
g.open_cmd("buy_aircraft")
b.advance(150)

# This is the manufacturer selector. We need to cycle through each manufacturer
# and try to measure the panel of each model

measured = {}

# Start at MDC (manufacturer 0)
# Try to measure each position
for mfr_idx in range(6):
    # Navigate to manufacturer
    if mfr_idx > 0:
        for _ in range(mfr_idx):
            b.press("Right", hold=3, wait=14)
            b.advance(40)

    # Enter manufacturer (press A)
    b.press("A", hold=5, wait=25)
    b.advance(150)

    # Now in the model selector for this manufacturer
    # Try to get to the first model and capture
    for model_idx in range(3):
        if model_idx > 0:
            b.press("Down", hold=3, wait=14)
            b.advance(40)

        # Capture screenshot
        ss_path = O / f"mfr_{mfr_idx}_mdl_{model_idx}.png"
        b.screenshot(ss_path)

        # Measure panel hash
        try:
            img = Image.open(ss_path).convert("RGB")
            panel_hash = _crop_md5(img, BUY_PANEL)

            # Try to identify which model this is by matching hash
            matched = None
            for model, spec in AIRCRAFT_CATALOG.items():
                if spec["maker_idx"] == mfr_idx and spec["model_idx"] == model_idx:
                    matched = model
                    break

            print(f"  Mfr {mfr_idx}, Mdl {model_idx} ({matched:10s}): {panel_hash}")

            if matched:
                measured[matched] = panel_hash
        except Exception as e:
            print(f"  Mfr {mfr_idx}, Mdl {model_idx}: ERROR - {e}")

    # Go back (press B)
    b.press("B", hold=5, wait=25)
    b.advance(150)

print("\n" + "="*60)
print("RESULTS - UPDATE AIRCRAFT_CATALOG IN world.py WITH:")
print("="*60)
print()
for model in sorted(AIRCRAFT_CATALOG.keys()):
    old_hash = AIRCRAFT_CATALOG[model]["panel"]
    new_hash = measured.get(model, "UNMEASURED")
    status = "CHANGED" if new_hash != old_hash and new_hash != "UNMEASURED" else "same"
    print(f'    "{model}": {{... "panel": "{new_hash}", ...}},   # was {old_hash} ({status})')

print()
print("="*60)
b.speed(100)
