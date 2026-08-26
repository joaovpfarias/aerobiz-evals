#!/usr/bin/env python3
"""Diagnose panel hash mismatch in sell_aircraft."""

import sys
from pathlib import Path
from PIL import Image
import hashlib

sys.path.insert(0, str(Path(__file__).parent))
from world import AIRCRAFT_CATALOG, BUY_PANEL

def _crop_md5(img, box):
    """Extract crop and compute MD5."""
    cropped = img.crop(box)
    return hashlib.md5(cropped.tobytes()).hexdigest()[:8]

# Load the screenshot that failed
screenshot = Path("../logs/sell_aircraft_aceite/sell_modelo_errado_MD100.png")
if screenshot.exists():
    img = Image.open(screenshot).convert("RGB")

    # Measure actual panel hash
    actual_hash = _crop_md5(img, BUY_PANEL)
    expected_hash = AIRCRAFT_CATALOG["MD100"]["panel"]

    print(f"Screenshot: {screenshot}")
    print(f"BUY_PANEL crop: {BUY_PANEL}")
    print(f"Actual hash:   {actual_hash}")
    print(f"Expected MD100: {expected_hash}")
    print(f"Match: {actual_hash == expected_hash}")

    # Try other models to see if any match
    print("\nComparing against all models:")
    for model, spec in AIRCRAFT_CATALOG.items():
        h = spec["panel"]
        match = "✓" if actual_hash == h else " "
        print(f"  {match} {model:10s}: {h}")
else:
    print(f"Screenshot not found: {screenshot}")
