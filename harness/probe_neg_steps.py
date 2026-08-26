"""ETAPA 3b: percorre o fluxo de negotiate_slots UM A DE CADA VEZ e fotografa.

Objetivo (a): descobrir se existe uma tela de "How many slots?" com escolha.
Nao aperta nada alem de A; para quando a TEXTBOX repete duas vezes.

uso: probe_neg_steps.py <CID> <cel_row> <cel_col> <prefixo>
"""
import sys, pathlib, json, hashlib
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bridge, world
from executor import Executor, STEP_SETTLE
from world import wait_text, on_map_screen, staff_sel_cell, staff_free_cells

RAIZ = HERE.parent
SHOTS = RAIZ / "logs" / "etapa3b"
SHOTS.mkdir(parents=True, exist_ok=True)
BASE = str(RAIZ / "states" / "_e3b_base.state")


def tb(b):
    img = Image.open(b.screenshot()).convert("RGB")
    return hashlib.md5(img.crop(world.TEXTBOX).tobytes()).hexdigest()[:8]


def goto_staff(b, ex):
    ex.g.open_cmd("negotiate")
    wait_text(b)


def move_to(b, alvo, tries=6):
    img = Image.open(b.screenshot()).convert("RGB")
    for _ in range(tries):
        sel = staff_sel_cell(img)
        if sel == alvo:
            return sel
        if sel is None:
            b.advance(30)
            img = Image.open(b.screenshot()).convert("RGB")
            continue
        dr, dc = alvo[0] - sel[0], alvo[1] - sel[1]
        seq = []
        if dr:
            seq += b.seq_press("Down" if dr > 0 else "Up", hold=3, wait=14, times=abs(dr))
        if dc:
            seq += b.seq_press("Right" if dc > 0 else "Left", hold=3, wait=14, times=abs(dc))
        b.batch(seq + b.seq_advance(30), extra_frames=200)
        img = Image.open(b.screenshot()).convert("RGB")
    return staff_sel_cell(img)


def main():
    cid = sys.argv[1]
    alvo = (int(sys.argv[2]), int(sys.argv[3]))
    pref = sys.argv[4]
    b = bridge.BizHawkBridge()
    ex = Executor(b)
    b.load(BASE)
    b.advance(120)
    cash0 = world.read_cash_k(b)
    goto_staff(b, ex)
    img = Image.open(b.screenshot()).convert("RGB")
    livres = staff_free_cells(img)
    b.screenshot(SHOTS / f"{pref}_00_staffgrid.png")
    sel = move_to(b, alvo)
    b.screenshot(SHOTS / f"{pref}_01_sel{alvo[0]}{alvo[1]}.png")
    if sel != alvo:
        print(json.dumps({"erro": f"sel={sel} != {alvo}", "livres": livres}))
        return
    # A ate o mapa
    for i in range(5):
        wait_text(b)
        b.press("A", hold=5, wait=25)
        b.advance(STEP_SETTLE)
        if on_map_screen(Image.open(b.screenshot()).convert("RGB")):
            break
    b.screenshot(SHOTS / f"{pref}_02_mapa.png")
    # posiciona o cursor SEM apertar A
    from world import point_cursor_at_world
    reg, pos, verif = point_cursor_at_world(b, cid, None)
    b.screenshot(SHOTS / f"{pref}_03_cursor.png")
    # agora A um de cada vez
    seq = []
    prev = tb(b)
    for i in range(10):
        wait_text(b)
        b.press("A", hold=5, wait=25)
        b.advance(STEP_SETTLE)
        wait_text(b)
        h = tb(b)
        p = b.screenshot(SHOTS / f"{pref}_A{i+1}_{h}.png")
        seq.append({"i": i + 1, "tb": h, "shot": pathlib.Path(p).name,
                    "mapa": on_map_screen(Image.open(p).convert("RGB")),
                    "cash": world.read_cash_k(b)})
        if h == prev and i > 0:
            break
        prev = h
    print(json.dumps({"cid": cid, "cel": alvo, "livres": livres, "cash0": cash0,
                      "reg": reg, "pos": str(pos), "verif": verif, "seq": seq}, default=str))


if __name__ == "__main__":
    main()
