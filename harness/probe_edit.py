"""Mapeamento e calibracao de r0c1 (route_edit), r0c4 (orcamentos) e r1c1 (anuncio).

Fases (cada uma parte de um savestate, para ser repetivel):
  base            abre 2 rotas a partir do savestate do eval -> _edit_2rotas.state
  walk CMD N      abre o comando CMD e aperta A N vezes, capturando tela + hashes
                  das DUAS caixas de dialogo (rodape TEXTBOX e topo BUY_TEXT)
  keys BTN N tag  aperta BTN N vezes a partir do estado ATUAL, capturando cada passo
  mk CMD tag      salva savestate na 1a tela do comando CMD
  from ST BTN N tag  carrega savestate ST e aperta BTN N vezes capturando
  shot tag        so captura
"""
import hashlib
import sys
from pathlib import Path

from PIL import Image

import world
from bridge import BizHawkBridge
from macros import Game

O = Path("../logs/edit")
O.mkdir(parents=True, exist_ok=True)
EVAL = "../states/eval_single_2000_lv5.state"

b = BizHawkBridge()
g = Game(b, shot_dir=O)


def h(img, box):
    return hashlib.md5(img.crop(box).tobytes()).hexdigest()[:8]


def snap(tag):
    p = b.screenshot(O / f"{tag}.png")
    img = Image.open(p).convert("RGB")
    print(f"  {tag}: foot={h(img, world.TEXTBOX)} top={h(img, world.BUY_TEXT)} "
          f"red={world.menu_red(img)} land={world.land_pixels(img)} "
          f"menu={world.at_main_menu_img(img)} caixa={world.read_cash_k(b)}K", flush=True)
    return img


fase = sys.argv[1]

if fase == "base":
    from executor import Executor
    b.load(EVAL)
    b.advance(90)
    b.speed(400)
    ex = Executor(b)
    print("caixa inicial:", world.read_cash_k(b), flush=True)
    for dest in ("NA06", "NA03"):
        ok, det = ex.run({"action": "open_route", "params": {"to": dest}})
        print(f"open_route {dest} -> {ok} | {det}", flush=True)
    ex._ensure_menu()
    snap("base_2rotas")
    b.save("../states/_edit_2rotas.state")
    b.speed(100)

elif fase == "walk":
    cmd = sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    st = sys.argv[4] if len(sys.argv) > 4 else "../states/_edit_2rotas.state"
    from executor import Executor
    b.load(st)
    b.advance(90)
    b.speed(400)
    ex = Executor(b)
    ex._ensure_menu()
    g.open_cmd(cmd)
    b.advance(150)
    snap(f"w_{cmd}_00")
    for i in range(1, n + 1):
        b.press("A", hold=5, wait=25)
        b.advance(120)
        snap(f"w_{cmd}_{i:02d}")
    b.speed(100)

elif fase == "mk":
    cmd, tag = sys.argv[2], sys.argv[3]
    st = sys.argv[4] if len(sys.argv) > 4 else "../states/_edit_2rotas.state"
    from executor import Executor
    b.load(st)
    b.advance(90)
    b.speed(400)
    ex = Executor(b)
    ex._ensure_menu()
    g.open_cmd(cmd)
    b.advance(200)
    snap(f"mk_{tag}")
    b.save(f"../states/_{tag}.state")
    b.speed(100)

elif fase == "keys":
    btn, n, tag = sys.argv[2], int(sys.argv[3]), sys.argv[4]
    b.speed(400)
    for i in range(n + 1):
        snap(f"{tag}_{i:02d}")
        if i < n:
            b.press(btn, hold=3, wait=14)
            b.advance(60)
    b.speed(100)

elif fase == "from":
    st, btn, n, tag = sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]
    b.load(st)
    b.advance(240)
    b.speed(400)
    for i in range(n + 1):
        snap(f"{tag}_{i:02d}")
        if i < n:
            b.press(btn, hold=3, wait=14)
            b.advance(60)
    b.speed(100)

elif fase == "shot":
    snap(sys.argv[2])

elif fase == "load":
    b.load(sys.argv[2])
    b.advance(120)
    snap("loaded")
