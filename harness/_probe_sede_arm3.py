"""Braco A/B da ETAPA 4-CidadeInvestigar, com mira MEDIDA.

Mira: hover de uma cidade acontece quando o CENTRO do cursor (find_cursor) esta
em (dot_x+4, dot_y+11) — offset medido no frame de Rome (24/08).
Confirmacao de hover: tinta na caixa de texto (20,150)-(150,168) > 0.

Uso: python _probe_sede_arm3.py --region NAmerica --dot 118,36 --tag B
"""
import argparse
import hashlib
import pathlib
import sys

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import world  # noqa: E402
import locate  # noqa: E402
from bridge import BizHawkBridge  # noqa: E402

ROOT = pathlib.Path(__file__).parent.parent
SHOTS = ROOT / "logs" / "etapa4_sede"
STATE = str(ROOT / "states" / "eval_players_screen.state")
LABEL_BOX = (30, 126, 120, 144)
NAME_BOX = (20, 150, 150, 168)
OFF = (4, 11)
LABELS = {"e1f5ac0fe0": "Europe", "6cc4526e02": "MidEast", "14416469ee": "SEAsia",
          "53f810e1a1": "NAmerica", "2afffee160": "none"}


def label_of(p):
    h = hashlib.md5(Image.open(p).convert("RGB").crop(LABEL_BOX).tobytes()).hexdigest()[:10]
    return LABELS.get(h, "?" + h)


def ink(p):
    im = Image.open(p).convert("RGB").crop(NAME_BOX)
    return sum(1 for px in im.getdata() if sum(px) > 500)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", required=True)
    ap.add_argument("--dot", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--commit", action="store_true", help="confirmar YES e medir")
    a = ap.parse_args()
    dx, dy = (int(v) for v in a.dot.split(","))
    SHOTS.mkdir(parents=True, exist_ok=True)
    b = BizHawkBridge()
    b.load(STATE)
    b.advance(60)
    b.speed(400)
    b.batch(b.seq_press("A", hold=5, wait=30) + b.seq_advance(300), extra_frames=450)
    lab = None
    for _ in range(10):
        p = b.screenshot(SHOTS / f"{a.tag}_reg.png")
        lab = label_of(p)
        if lab == a.region:
            break
        b.batch(b.seq_press("Right", hold=3, wait=25) + b.seq_advance(150), extra_frames=300)
    print("regiao:", lab, flush=True)
    if lab != a.region:
        return 1
    b.batch(b.seq_press("A", hold=5, wait=30) + b.seq_advance(400), extra_frames=600)

    alvo = (dx + OFF[0], dy + OFF[1])
    pos = locate.goto(b, *alvo, tol=1)
    p = b.screenshot(SHOTS / f"{a.tag}_hover.png")
    print("cursor:", pos, "alvo:", alvo, "ink:", ink(p), p, flush=True)
    if ink(p) == 0:
        # varredura fina: o hover so acende numa faixa de poucos px (MEDIDO em
        # Rome: 4 toques de Up a partir do centro do cursor acendem o nome)
        achou = False
        for coluna in range(5):          # -2..+2 colunas de 2px
            for _ in range(6):
                b.press("Up", hold=1, wait=8)
                b.advance(120)
                p = b.screenshot(SHOTS / f"{a.tag}_hover.png")
                if ink(p) > 0:
                    achou = True
                    break
            if achou:
                break
            for _ in range(12):          # volta e desce
                b.press("Down", hold=1, wait=8)
                b.advance(120)
                p = b.screenshot(SHOTS / f"{a.tag}_hover.png")
                if ink(p) > 0:
                    achou = True
                    break
            if achou:
                break
            for _ in range(6):
                b.press("Up", hold=1, wait=8)
            b.press("Right" if coluna % 2 == 0 else "Left", hold=1, wait=8)
            b.advance(120)
        print("   busca fina ink", ink(p), flush=True)
    if ink(p) == 0:
        print("ABORT: sem nome na caixa (cursor nao esta sobre cidade)")
        return 1
    if not a.commit:
        print("dry-run: nao confirmei")
        return 0
    b.press("A", hold=6, wait=40)
    b.advance(400)
    print("pergunta:", b.screenshot(SHOTS / f"{a.tag}_pergunta.png"), flush=True)
    b.press("A", hold=6, wait=40)
    b.advance(600)
    print("roster:", b.screenshot(SHOTS / f"{a.tag}_roster.png"), "cash", world.read_cash_k(b), flush=True)
    for i in range(5):
        b.press("A", hold=6, wait=40)
        b.advance(500)
        b.screenshot(SHOTS / f"{a.tag}_pos{i}.png")
        print(f"  pos{i} cash", world.read_cash_k(b), flush=True)
    out = str((ROOT / "states" / f"_sede_{a.tag}.state").resolve())
    b.save(out)
    print("state:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
