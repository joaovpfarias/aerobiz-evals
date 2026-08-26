"""Mapeamento e calibracao do fluxo r0c3 (comprar aviao).

Recortes MEDIDOS neste fluxo (a TEXTBOX do fluxo de rota NAO serve aqui: a
caixa de dialogo da compra fica no TOPO da tela, nao no rodape):
  BUY_TEXT  (60,20,250,64)  fala da vendedora / pergunta
  BUY_PANEL (8,82,250,148)  painel do aviao: modelo, alcance, assentos
  BUY_PRICE (0,148,256,178) "Start of Production" + "Price"

Fases:
  walk N        do menu: abre r0c3 e aperta A N vezes, capturando tela+hashes
  cont N        continua apertando A a partir do estado ATUAL (sem recarregar)
  keys B N tag  aperta o botao B N vezes a partir do estado ATUAL, capturando
  shot tag      so captura
"""
import hashlib
import sys
from pathlib import Path

from PIL import Image

import world
from bridge import BizHawkBridge
from macros import Game

O = Path("../logs/buy")
O.mkdir(parents=True, exist_ok=True)
EVAL = "../states/eval_single_2000_lv5.state"

BUY_TEXT = (60, 20, 250, 64)
BUY_PANEL = (8, 82, 250, 148)
BUY_PRICE = (0, 148, 256, 178)

b = BizHawkBridge()
g = Game(b, shot_dir=O)


def h(img, box):
    return hashlib.md5(img.crop(box).tobytes()).hexdigest()[:8]


def snap(tag):
    p = b.screenshot(O / f"{tag}.png")
    img = Image.open(p).convert("RGB")
    print(f"  {tag}: text={h(img, BUY_TEXT)} panel={h(img, BUY_PANEL)} "
          f"price={h(img, BUY_PRICE)} menu={world.at_main_menu_img(img)} "
          f"caixa={world.read_cash_k(b)}K", flush=True)
    return img


fase = sys.argv[1]

if fase == "walk":
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    b.load(EVAL)
    b.advance(90)
    b.speed(400)
    from executor import Executor
    ex = Executor(b)
    ex._ensure_menu()
    print("caixa inicial:", world.read_cash_k(b), "K", flush=True)
    g.open_cmd("buy_aircraft")
    b.advance(120)
    snap("walk_00")
    for i in range(1, n + 1):
        b.press("A", hold=5, wait=25)
        b.advance(90)
        snap(f"walk_{i:02d}")
    b.speed(100)

elif fase == "cont":
    n = int(sys.argv[2])
    tag = sys.argv[3] if len(sys.argv) > 3 else "cont"
    b.speed(400)
    for i in range(1, n + 1):
        b.press("A", hold=5, wait=25)
        b.advance(90)
        snap(f"{tag}_{i:02d}")
    b.speed(100)

elif fase == "keys":
    btn, n, tag = sys.argv[2], int(sys.argv[3]), sys.argv[4]
    b.speed(400)
    for i in range(n + 1):
        snap(f"{tag}_{i:02d}")
        if i < n:
            b.press(btn, hold=3, wait=14)
            b.advance(40)
    b.speed(100)

elif fase == "shot":
    snap(sys.argv[2])

elif fase == "mkstate":
    # savestate na tela "Which manufacturer would you like to visit?"
    b.load(EVAL)
    b.advance(90)
    b.speed(400)
    from executor import Executor
    ex = Executor(b)
    ex._ensure_menu()
    g.open_cmd("buy_aircraft")
    b.advance(150)
    snap("mkstate")
    b.save("../states/_buy_maker.state")
    b.speed(100)

elif fase == "mk":
    # cicla o seletor de fabricante N vezes na direcao dada, a partir do
    # savestate da tela de fabricante (repetivel)
    direction, n = sys.argv[2], int(sys.argv[3])
    b.speed(400)
    b.load("../states/_buy_maker.state")
    b.advance(240)  # a datilografia da pergunta engole o 1o toque se nao esperar
    for i in range(n + 1):
        snap(f"mk_{direction}_{i:02d}")
        if i < n:
            b.press(direction, hold=3, wait=14)
            b.advance(40)
    b.speed(100)

elif fase == "mdstate":
    # entra no fabricante de indice N (N toques Right) e salva a tela de modelo
    n = int(sys.argv[2])
    b.speed(400)
    b.load("../states/_buy_maker.state")
    b.advance(240)
    for _ in range(n):
        b.press("Right", hold=3, wait=14)
        b.advance(40)
    b.press("A", hold=5, wait=25)
    b.advance(200)
    snap(f"mdstate_{n}")
    b.save(f"../states/_buy_model_{n}.state")
    b.speed(100)

elif fase == "md":
    # cicla o seletor de MODELO dentro de um fabricante ja aberto
    mfg, direction, n = int(sys.argv[2]), sys.argv[3], int(sys.argv[4])
    b.speed(400)
    b.load(f"../states/_buy_model_{mfg}.state")
    b.advance(400)
    for i in range(n + 1):
        snap(f"md{mfg}_{direction}_{i:02d}")
        if i < n:
            b.press(direction, hold=3, wait=14)
            b.advance(40)
    b.speed(100)

elif fase == "qtystate":
    # do savestate do modelo (mfg N) ate a tela "How many do you want?"
    mfg = int(sys.argv[2])
    b.speed(400)
    b.load(f"../states/_buy_model_{mfg}.state")
    b.advance(400)
    for i in range(6):
        b.press("A", hold=5, wait=25)
        b.advance(150)
        img = snap(f"q_{mfg}_a{i}")
    b.save(f"../states/_buy_qty_{mfg}.state")
    b.speed(100)

elif fase == "qty":
    mfg, direction, n = int(sys.argv[2]), sys.argv[3], int(sys.argv[4])
    b.speed(400)
    b.load(f"../states/_buy_qty_{mfg}.state")
    b.advance(300)
    for i in range(n + 1):
        snap(f"qty{mfg}_{direction}_{i:02d}")
        if i < n:
            b.press(direction, hold=3, wait=14)
            b.advance(40)
    b.speed(100)
