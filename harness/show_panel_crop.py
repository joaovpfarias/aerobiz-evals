#!/usr/bin/env python3
"""Show what the panel crop looks like."""

from pathlib import Path
from PIL import Image
from world import BUY_PANEL

screenshot = Path("../logs/sell_aircraft_aceite/sell_modelo_errado_MD100.png")
if screenshot.exists():
    img = Image.open(screenshot).convert("RGB")

    # Show full screenshot
    print(f"Full screenshot: {img.size}")

    # Crop and show
    cropped = img.crop(BUY_PANEL)
    print(f"Panel crop box: {BUY_PANEL}")
    print(f"Cropped size: {cropped.size}")

    # Save cropped version
    out_path = Path("../logs/sell_aircraft_aceite/panel_crop.png")
    cropped.save(out_path)
    print(f"Saved to: {out_path}")
