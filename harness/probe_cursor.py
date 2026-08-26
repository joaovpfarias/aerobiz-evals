"""Probe de diagnostico do cursor do mapa (tarefa 1.2/1.3).

Sempre parte do savestate do eval — cada iteracao precisa ser comparavel.
Uso: python probe_cursor.py <passo>
"""

import pathlib
import sys

from PIL import Image

from bridge import BizHawkBridge
from macros import Game
import locate
import world

EVAL = pathlib.Path(__file__).parent.parent / "states" / "eval_single_2000_lv5.state"
OUT = pathlib.Path(__file__).parent.parent / "logs" / "probe12"
OUT.mkdir(parents=True, exist_ok=True)


def fresh(b):
    b.load(EVAL)
    b.advance(60)
    return Game(b)


def cur(b):
    r = b.read_ram(world.CURSOR_X, 3)
    return r[0], r[2]


def shot(b, name):
    p = b.screenshot(OUT / f"{name}.png")
    return Image.open(p).convert("RGB")


def step_catalog():
    """1) o catalogo de cidades vale neste savestate (cenario 4)?"""
    b = BizHawkBridge()
    g = fresh(b)
    g.back_to_menu()
    g.open_cmd("new_route")
    g.wait_stable()
    img = shot(b, "01_route_prompt")
    print("--- ANTES do A de reconhecimento ---")
    dots = world.detect_cities(img)
    print(f"pontos grandes (>= {world.DOT_MIN_PX}px): {len(dots)}")
    for x, y, n in dots:
        print(f"  ({x:3d},{y:3d}) {n}px")
    # A de reconhecimento
    b.batch(b.seq_press("A", hold=5, wait=25) + b.seq_advance(60), extra_frames=150)
    g.wait_stable()
    img2 = shot(b, "02_route_after_ack")
    print("--- DEPOIS do A ---")
    dots2 = world.detect_cities(img2)
    print(f"pontos grandes: {len(dots2)}")
    for x, y, n in dots2:
        print(f"  ({x:3d},{y:3d}) {n}px")
    print("cursor RAM:", cur(b))
    print("--- catalogo NA_CITIES x pontos detectados ---")
    for cid, (cx, cy, nm) in sorted(world.NA_CITIES.items()):
        hit = [d for d in dots2 if abs(d[0] - cx) <= 3 and abs(d[1] - cy) <= 3]
        print(f"  {cid} ({cx:3d},{cy:3d}) {nm or '':10s} -> {'OK ' + str(hit[0]) if hit else 'NAO ENCONTRADO'}")


def step_taps():
    """2) input de d-pad move a RAM do cursor apos o A de reconhecimento?"""
    b = BizHawkBridge()
    g = fresh(b)
    g.back_to_menu()
    g.open_cmd("new_route")
    g.wait_stable()
    print("cursor antes do A:", cur(b))
    b.batch(b.seq_press("A", hold=5, wait=25) + b.seq_advance(60), extra_frames=150)
    g.wait_stable()
    print("cursor depois do A:", cur(b))
    for n in (1, 1, 2, 4, 8):
        before = cur(b)
        b.batch(b.seq_press("Right", hold=1, wait=4, times=n) + b.seq_advance(20), extra_frames=60)
        after = cur(b)
        print(f"  {n:2d}x Right: {before} -> {after}  dx={after[0]-before[0]}")
    for n in (1, 2, 4, 8):
        before = cur(b)
        b.batch(b.seq_press("Down", hold=1, wait=4, times=n) + b.seq_advance(20), extra_frames=60)
        after = cur(b)
        print(f"  {n:2d}x Down : {before} -> {after}  dy={after[1]-before[1]}")
    shot(b, "03_after_taps")
    c = cur(b)
    print("cursor final RAM:", c)
    fc = locate.find_cursor(b)
    print("cursor visual (find_cursor):", fc)


def ack(b, g):
    """A de reconhecimento da mensagem + o toque que a transicao consome."""
    g.wait_stable()
    b.batch(b.seq_press("A", hold=5, wait=25) + b.seq_advance(60), extra_frames=150)
    g.wait_stable()
    b.batch(b.seq_press("Right", hold=1, wait=4) + b.seq_advance(20), extra_frames=60)


def goto_ram(b, tx, ty, max_iter=8):
    """Move o cursor por TOQUES REAIS ate a posicao logica alvo, em malha
    fechada pela RAM (sem screenshot). 1 toque = 2px."""
    for _ in range(max_iter):
        x, y = cur(b)
        dx, dy = tx - x, ty - y
        if dx == 0 and dy == 0:
            return (x, y)
        seq = []
        if dx:
            seq += b.seq_press("Right" if dx > 0 else "Left", hold=1, wait=4, times=min(abs(dx) // 2, 60))
        if dy:
            seq += b.seq_press("Down" if dy > 0 else "Up", hold=1, wait=4, times=min(abs(dy) // 2, 60))
        b.batch(seq + b.seq_advance(20), extra_frames=len(seq) * 10 + 60)
    return cur(b)


def step_sprite():
    """3) onde o sprite e DESENHADO em relacao ao valor da RAM?"""
    from PIL import ImageChops

    b = BizHawkBridge()
    g = fresh(b)
    g.back_to_menu()
    g.open_cmd("new_route")
    ack(b, g)
    print("apos ack:", cur(b))
    print("goto (100,100):", goto_ram(b, 100, 100))
    a = shot(b, "10_ram_100_100")
    print("goto (120,100):", goto_ram(b, 120, 100))
    c = shot(b, "11_ram_120_100")
    box = ImageChops.difference(a, c).crop((0, 0, 256, 140)).getbbox()
    print("bbox do diff (x +20):", box)
    if box:
        x0, y0, x1, y1 = box
        print(f"  sprite esquerda com RAM_X=100 -> x0={x0} (offset {x0-100})")
        print(f"  sprite direita  com RAM_X=120 -> x1={x1} (largura {x1-x0-20})")
        print(f"  sprite topo com RAM_Y=100 -> y0={y0} (offset {y0-100}), altura {y1-y0}")


def step_hover():
    """4) existe um byte 'cidade sob o cursor'? Atravessa NA14 lendo a RAM."""
    b = BizHawkBridge()
    g = fresh(b)
    g.back_to_menu()
    g.open_cmd("new_route")
    ack(b, g)
    cx, cy = world.city_xy("NA14")  # (212,74)
    rows = []
    for ox in range(-12, 13, 2):
        goto_ram(b, cx + ox, cy - 4)
        w = b.read_ram(0x2500, 0x200)
        rows.append((ox, cur(b), w))
        print(f"  offset {ox:+3d} cursor={cur(b)}")
    base = rows[0][2]
    varia = [i for i in range(len(base)) if any(r[2][i] != base[i] for r in rows)]
    print(f"bytes que variam na travessia: {len(varia)}")
    for i in varia[:40]:
        print(f"  0x{0x2500+i:04x}: " + " ".join(f"{r[2][i]:02x}" for r in rows))


def _hash(b, name):
    import hashlib

    return hashlib.md5(pathlib.Path(b.screenshot(OUT / f"{name}.png")).read_bytes()).hexdigest()[:10]


def step_select():
    """5) qual offset RAM faz o A SELECIONAR a cidade? (sweep empirico)"""
    b = BizHawkBridge()
    cx, cy = world.city_xy("NA14")
    cands = [(ox, oy) for oy in (-6, -4, -2, 0) for ox in (-6, -4, -2, 0)]
    for ox, oy in cands:
        g = fresh(b)
        g.back_to_menu()
        g.open_cmd("new_route")
        ack(b, g)
        pos = goto_ram(b, cx + ox, cy + oy)
        antes = _hash(b, "_sel_antes")
        b.batch(b.seq_press("A", hold=5, wait=25) + b.seq_advance(120), extra_frames=200)
        g.wait_stable()
        depois = _hash(b, f"20_sel_{ox}_{oy}")
        print(f"  offset ({ox:+d},{oy:+d}) RAM={pos}: {'MUDOU -> SELECIONOU' if antes != depois else 'nada'}")


def step_write():
    """6) ESCREVER a posicao apos um toque REAL de ativacao seleciona?

    O teste anterior (que 'provou' que escrever nao funciona) escrevia (209,71)
    e dava apenas UM toque — que agora sabemos ser consumido pela transicao.
    """
    b = BizHawkBridge()
    for cid, off in (("NA14", (0, 0)), ("NA14", (-2, -2)), ("NA06", (0, 0)), ("NA10", (0, 0))):
        g = fresh(b)
        g.back_to_menu()
        g.open_cmd("new_route")
        ack(b, g)  # ja inclui o toque consumido
        cx, cy = world.city_xy(cid)
        b.batch(
            b.seq_press("Right", hold=1, wait=4)
            + b.seq_write(world.CURSOR_X, cx + off[0])
            + b.seq_write(world.CURSOR_Y, cy + off[1])
            + b.seq_advance(20),
            extra_frames=60,
        )
        pos = cur(b)
        antes = _hash(b, "_w_antes")
        b.batch(b.seq_press("A", hold=5, wait=25) + b.seq_advance(120), extra_frames=200)
        g.wait_stable()
        depois = _hash(b, f"30_write_{cid}_{off[0]}_{off[1]}")
        print(f"  {cid} off{off} RAM={pos}: {'MUDOU -> SELECIONOU' if antes != depois else 'nada'}")


def step_slots():
    """7) em QUAIS cidades temos slots neste savestate? (digitos no mapa)"""
    b = BizHawkBridge()
    g = fresh(b)
    g.back_to_menu()
    g.open_cmd("new_route")
    ack(b, g)
    img = shot(b, "40_map_slots")
    small = [d for d in locate.find_dots(img, locate.GREEN) + locate.find_dots(img, locate.BLUE)
             if d[2] < world.DOT_MIN_PX]
    print(f"blobs pequenos (digitos/cursor): {len(small)}")
    for x, y, n in small:
        perto = sorted(world.NA_CITIES.items(), key=lambda kv: (kv[1][0] - x) ** 2 + (kv[1][1] - y) ** 2)[0]
        print(f"  ({x:3d},{y:3d}) {n:2d}px -> mais perto: {perto[0]} {perto[1][:2]} {perto[1][2] or ''}")
    print("cities_with_slots():", world.cities_with_slots(img, cursor=cur(b)))


def step_flow():
    """8) mapa passo a passo do fluxo de rota apos selecionar a cidade."""
    dest = sys.argv[2] if len(sys.argv) > 2 else "NA06"
    b = BizHawkBridge()
    g = fresh(b)
    g.back_to_menu()
    g.open_cmd("new_route")
    ack(b, g)
    cx, cy = world.city_xy(dest)
    b.batch(
        b.seq_press("Right", hold=1, wait=4)
        + b.seq_write(world.CURSOR_X, cx)
        + b.seq_write(world.CURSOR_Y, cy)
        + b.seq_advance(20),
        extra_frames=60,
    )
    print("cursor:", cur(b), "caixa:", world.read_cash_k(b))
    b.batch(b.seq_press("A", hold=5, wait=25) + b.seq_advance(120), extra_frames=200)
    g.wait_stable()
    shot(b, f"50_{dest}_p00_selecionada")
    print(f"passo 00: selecionou {dest} | caixa {world.read_cash_k(b)}")
    for i in range(1, 8):
        b.batch(b.seq_press("A", hold=5, wait=25) + b.seq_advance(120), extra_frames=250)
        g.wait_stable()
        shot(b, f"50_{dest}_p{i:02d}")
        print(f"passo {i:02d}: caixa {world.read_cash_k(b)}")


if __name__ == "__main__":
    {
        "catalog": step_catalog,
        "taps": step_taps,
        "sprite": step_sprite,
        "hover": step_hover,
        "select": step_select,
        "write": step_write,
        "slots": step_slots,
        "flow": step_flow,
    }[sys.argv[1]]()
