"""Extrai glifos faltantes das screenshots já capturadas."""
from PIL import Image
from pathlib import Path
import world

# Processar os PNGs da run anterior
log_dir = Path("../logs/calib_budget_fixed")
pngs = sorted(log_dir.glob("x_*.png"))

print(f"Encontrados {len(pngs)} screenshots")
print("\n=== Processando screenshots para encontrar glifos faltantes ===\n")

missing_glyphs = {}

for png in pngs:
    img = Image.open(png).convert("RGB")
    print(f"Processando {png.name}...")

    # Ler com debug=True para cada coluna
    for col in range(3):
        money = world.read_budget_money(img, col=col, debug=True)
        if money is None:
            print(f"  Col {col}: NENHUM (ilegível)")
        else:
            print(f"  Col {col}: ${money}K")

print("\n=== Resumo dos glifos faltantes ===")
print("\nOs glifos faltantes aparecem acima com 'glifo novo em colN kM: <hash>'")
print("Você pode usar 'world.BUDGET_GLYPHS' para adicionar os novos hashes.")
