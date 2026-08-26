#!/usr/bin/env python3
"""
Extrae todos los pixeles blancos (255,251,255) de la imagen para ver dónde están los dígitos.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PIL import Image

LOG_DIR = Path(__file__).parent.parent / "logs" / "quick_advance"
SCREENSHOT = LOG_DIR / "quarterly_report_final.png"

def extract():
    print("=" * 70)
    print("EXTRAYENDO PIXELES BLANCOS (255,251,255)")
    print("=" * 70)

    img = Image.open(SCREENSHOT).convert("RGB")
    px = img.load()

    print(f"\nImagen: {img.width}x{img.height}")

    white_pixels = []
    for x in range(img.width):
        for y in range(img.height):
            r, g, b = px[x, y]
            if (r, g, b) == (255, 251, 255):
                white_pixels.append((x, y))

    print(f"\nEncontrados {len(white_pixels)} pixeles blancos (255,251,255)")

    if white_pixels:
        print("\nPrimeros 50 pixeles blancos (x, y):")
        for i, (x, y) in enumerate(white_pixels[:50]):
            print(f"  [{i+1:2}] ({x:3}, {y:3})", end="")
            if (i + 1) % 5 == 0:
                print()
            else:
                print("  ", end="")

        print(f"\n\nRango de X: {min(p[0] for p in white_pixels)} - {max(p[0] for p in white_pixels)}")
        print(f"Rango de Y: {min(p[1] for p in white_pixels)} - {max(p[1] for p in white_pixels)}")

        # Agrupa por Y para ver líneas de dígitos
        by_y = {}
        for x, y in white_pixels:
            if y not in by_y:
                by_y[y] = []
            by_y[y].append(x)

        print(f"\nPixeles blancos por línea Y (mostrando top 10 líneas):")
        for y in sorted(by_y.keys())[:10]:
            xs = sorted(by_y[y])
            print(f"  Y={y:3}: {len(xs):3} pixeles, X range {xs[0]:3}-{xs[-1]:3}")

        # Busca en las áreas esperadas para regiones
        print(f"\n\nANALISIS POR REGION:")

        # N America: box (180, 48, 244, 68), offset -8 = 48-8 = 40..48
        print(f"\nN America (esperado alrededor de Y=40-48, X=180-244):")
        na_whites = [(x, y) for x, y in white_pixels if 35 <= y <= 50 and 170 <= x <= 250]
        if na_whites:
            ys = set(y for x, y in na_whites)
            print(f"  Encontrados en Y: {sorted(ys)}")
            for y in sorted(ys)[:3]:
                xs = sorted(x for x, y_i in na_whites if y_i == y)
                print(f"    Y={y}: {xs}")
        else:
            print(f"  No encontrados pixeles blancos")

        # Oceania: box (140, 120, 208, 140), offset -9 = 120-9 = 111..120
        print(f"\nOceania (esperado alrededor de Y=111-120, X=140-208):")
        oc_whites = [(x, y) for x, y in white_pixels if 105 <= y <= 125 and 130 <= x <= 220]
        if oc_whites:
            ys = set(y for x, y in oc_whites)
            print(f"  Encontrados en Y: {sorted(ys)}")
            for y in sorted(ys)[:3]:
                xs = sorted(x for x, y_i in oc_whites if y_i == y)
                print(f"    Y={y}: {xs}")
        else:
            print(f"  No encontrados pixeles blancos")

    print("\n" + "=" * 70)
    return True


if __name__ == "__main__":
    try:
        success = extract()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"EXCECAO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
