"""ETAPA 3b (a): a tela "How many slots?" e uma ALAVANCA? Quantos toques = quantos slots?

Fluxo (medido em probe_neg_steps, savestate _e3b_base):
  r0c2 -> grade de funcionarios -> A -> mapa -> cursor na cidade
  -> A  -> "How many slots?"  (slider de 5 icones, rotulo "N slot(s)")
  -> A  -> "Negotiations should take N months. Shall we negotiate?" (YES/NO)
  -> A  -> "I will begin negotiations."

Este probe PARA na tela de quantidade e testa Right/Left/Up/Down, lendo o
rotulo de volta a cada toque. Nao confirma nada (B ao final) salvo --confirm.

uso: probe_slots_lever.py <CID> <cel_row> <cel_col> <n_toques> <botao> <pref> [--confirm]
"""
import sys, pathlib, json, hashlib
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bridge, world
from executor import Executor, STEP_SETTLE
from world import wait_text, on_map_screen, staff_sel_cell, staff_free_cells, point_cursor_at_world

RAIZ = HERE.parent
SHOTS = RAIZ / "logs" / "etapa3b"
SHOTS.mkdir(parents=True, exist_ok=True)
BASE = str(RAIZ / "states" / "_e3b_base.state")

# Recorte do rotulo "N slot(s)" e do slider dentro da caixa de texto.
SLOT_LABEL = (62, 152, 232, 188)   # = world.TEXTBOX (a linha inteira)


def tb(b, box=SLOT_LABEL):
    img = Image.open(b.screenshot()).convert("RGB")
    return hashlib.md5(img.crop(box).tobytes()).hexdigest()[:8]


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


def goto_qty(b, ex, cid, alvo, pref, state=None):
    b.load(state or BASE)
    b.advance(120)
    ex.g.open_cmd("negotiate")
    wait_text(b)
    livres = staff_free_cells(Image.open(b.screenshot()).convert("RGB"))
    sel = move_to(b, alvo)
    if sel != alvo:
        raise RuntimeError(f"destaque em {sel}, queria {alvo}")
    b.screenshot(SHOTS / f"{pref}_sel.png")
    for _ in range(5):
        wait_text(b)
        b.press("A", hold=5, wait=25)
        b.advance(STEP_SETTLE)
        if on_map_screen(Image.open(b.screenshot()).convert("RGB")):
            break
    else:
        raise RuntimeError("nao chegou ao mapa")
    reg, pos, verif = point_cursor_at_world(b, cid, None)
    wait_text(b)
    b.press("A", hold=5, wait=25)
    b.advance(STEP_SETTLE)
    wait_text(b)
    return livres, reg, pos, verif


def main():
    cid, r, c, n, botao, pref = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5], sys.argv[6]
    confirm = "--confirm" in sys.argv
    b = bridge.BizHawkBridge()
    ex = Executor(b)
    st = None
    for a in sys.argv[7:]:
        if a.endswith(".state"):
            st = a
    livres, reg, pos, verif = goto_qty(b, ex, cid, (r, c), pref, st)
    cash_qty = world.read_cash_k(b)
    passos = []
    # ESTABILIDADE: mesma tela fotografada duas vezes tem de dar o MESMO hash,
    # senao "hash mudou" nao prova nada (setas piscam em outras telas).
    h0a = tb(b); b.advance(60); h0b = tb(b)
    p0 = b.screenshot(SHOTS / f"{pref}_qty_0.png")
    passos.append({"k": 0, "tb": h0a, "tb_repetido": h0b, "shot": pathlib.Path(p0).name})
    for k in range(1, n + 1):
        b.press(botao, hold=3, wait=20)
        b.advance(60)
        h = tb(b)
        p = b.screenshot(SHOTS / f"{pref}_qty_{k}.png")
        passos.append({"k": k, "tb": h, "shot": pathlib.Path(p).name})
    out = {"cid": cid, "cel": [r, c], "botao": botao, "livres": livres,
           "reg": reg, "pos": str(pos), "verif": verif, "cash_na_tela_qty": cash_qty,
           "passos": passos, "confirm": confirm}
    meses_only = "--meses" in sys.argv
    if confirm or meses_only:
        # A -> tela de meses (YES/NO). Fotografa e LE os meses declarados.
        wait_text(b)
        b.press("A", hold=5, wait=25)
        b.advance(STEP_SETTLE)
        wait_text(b)
        pm = b.screenshot(SHOTS / f"{pref}_meses.png")
        out["meses_shot"] = pathlib.Path(pm).name
        out["meses_tb"] = tb(b)
        b.advance(60)
        out["meses_tb_repetido"] = tb(b)
    if confirm:
        # A -> "I will begin negotiations."
        b.press("A", hold=5, wait=25)
        b.advance(STEP_SETTLE)
        wait_text(b)
        pf = b.screenshot(SHOTS / f"{pref}_fim.png")
        out["fim_shot"] = pathlib.Path(pf).name
        out["fim_tb"] = tb(b)
        # volta ao menu SEM apertar A (R2)
        for _ in range(8):
            if world.at_main_menu_img(Image.open(b.screenshot()).convert("RGB")):
                break
            b.press("B", hold=5, wait=25)
            b.advance(90)
        img = Image.open(b.screenshot()).convert("RGB")
        out["no_menu"] = world.at_main_menu_img(img)
        out["livres_depois"] = world.free_staff_menu(img)
        out["cash_fim"] = world.read_cash_k(b)
        b.save(str(RAIZ / "states" / f"_e3b_{pref}.state"))
    else:
        for _ in range(8):
            if world.at_main_menu_img(Image.open(b.screenshot()).convert("RGB")):
                break
            b.press("B", hold=5, wait=25)
            b.advance(90)
        img = Image.open(b.screenshot()).convert("RGB")
        out["no_menu"] = world.at_main_menu_img(img)
        out["livres_depois"] = world.free_staff_menu(img)
    print(json.dumps(out, default=str))


if __name__ == "__main__":
    main()
