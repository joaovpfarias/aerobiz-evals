"""Verificar se a tela após Close é uma seleção de mundo (not YES/NO)."""
from PIL import Image
from pathlib import Path
import world

# Carregar a screenshot que mostra a tela após "A" ativar Close
img_path = Path("../logs/close_debug/2_apos_A_ativar_close.png")
img = Image.open(img_path).convert("RGB")

print("\n[VERIFICACAO DA TELA APOS 'A' EM CLOSE]")
print(f"Analisando: {img_path.name}")

# Teste 1: É uma tela de mapa?
on_map = world.on_map_screen(img)
print(f"\n1. on_map_screen(): {on_map}")
print(f"   Esperado: True (tela de seleção de mundo/cidade)")

# Teste 2: É um diálogo YES/NO?
yesno = world.yesno_prompt(img)
print(f"\n2. yesno_prompt(): {yesno}")
print(f"   Esperado: False (NÃO há diálogo YES/NO)")

print("\n[CONCLUSAO]")
if on_map and not yesno:
    print("[BUG CONFIRMADO] Close abre uma tela de selecao de mundo,")
    print("  nao um dialogo YES/NO. A macro usa A cego que nao acerta.")
    print("  Solucao: usar activate_cursor() + point_cursor_at_world() como em open_venture")
elif on_map and yesno:
    print("[AMBIGUO] Tela tem mapa E dialogo YES/NO?")
else:
    print("[?] Resultado inesperado")
