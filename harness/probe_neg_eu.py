"""Mapeia o fluxo de NEGOCIACAO passo a passo, com a cidade na EUROPA.

Uma captura por passo: sem isso nao ha como afirmar que a negociacao pegou a
cidade certa — o lance nao debita o caixa na hora, entao o gate de caixa nao
serve como prova.
"""
import sys
from pathlib import Path

from PIL import Image

import world
from bridge import BizHawkBridge
from executor import Executor
from macros import Game

O = Path("../logs/negeu"); O.mkdir(parents=True, exist_ok=True)
b = BizHawkBridge(); ex = Executor(b); g = Game(b)
ALVO = sys.argv[1] if len(sys.argv) > 1 else "EU11"


def snap(tag):
    p = b.screenshot(O / f"{tag}.png")
    img = Image.open(p).convert("RGB")
    print(f"  {tag}: regiao={world.detect_region(img)} menu={world.at_main_menu_img(img)} "
          f"mapa={world.on_map_screen(img)} cursor={world.read_cursor(b)} caixa={world.read_cash_k(b)}K",
          flush=True)
    return img


b.load("../states/eval_single_2000_lv5.state"); b.advance(90); b.speed(400)
ex._ensure_menu()
g.info_screen("staff", "../negeu/00_staff_antes")
ex._ensure_menu()
snap("01_menu")

g.open_cmd("negotiate")
snap("02_funcionarios")
b.batch(b.seq_press("A", hold=5, wait=25) + b.seq_advance(150), extra_frames=400)
snap("03_apos_A1")
b.batch(b.seq_press("A", hold=5, wait=25) + b.seq_advance(150), extra_frames=400)
snap("04_apos_A2_mapa")

reg, pos, ok = world.point_cursor_at_world(b, ALVO, None)
print(f"  cursor colocado em {ALVO}: regiao={reg} pos={pos} verificado={ok}", flush=True)
snap("05_cursor_no_alvo")

b.press("A", hold=5, wait=25); b.advance(150); world.wait_text(b)
snap("06_apos_A_na_cidade")
b.press("A", hold=5, wait=25); b.advance(150); world.wait_text(b)
snap("07_apos_A")
b.press("A", hold=5, wait=25); b.advance(150); world.wait_text(b)
snap("08_apos_A")
b.press("A", hold=5, wait=25); b.advance(150); world.wait_text(b)
snap("09_apos_A")
ex._ensure_menu()
snap("10_menu_final")
g.info_screen("staff", "../negeu/11_staff_depois")
b.speed(100)
