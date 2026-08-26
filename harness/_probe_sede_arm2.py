"""ETAPA 4-CidadeInvestigar, braco: escolhe UMA sede e mede o estado inicial.

Mecanica MEDIDA (24/08): na tela de cidade o d-pad salta de cidade em cidade;
o nome da cidade aparece na caixa de texto SO quando a seta esta sobre uma
cidade elegivel — fora dela `A` e inerte. `A` sobre cidade -> "Is <X> OK?" YES/NO.

Uso: python _probe_sede_arm2.py --region NAmerica --btn Up --steps 3 --tag B
"""
import argparse
import hashlib
import pathlib
import sys

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import world  # noqa: E402
from bridge import BizHawkBridge  # noqa: E402

ROOT = pathlib.Path(__file__).parent.parent
SHOTS = ROOT / "logs" / "etapa4_sede"
STATE = str(ROOT / "states" / "eval_players_screen.state")
LABEL_BOX = (30, 126, 120, 144)
NAME_BOX = (20, 150, 150, 168)   # interior da caixa de texto (MEDIDO 24/08)
LABELS = {"e1f5ac0fe0": "Europe", "6cc4526e02": "MidEast", "14416469ee": "SEAsia",
          "53f810e1a1": "NAmerica", "2afffee160": "none"}


def label_of(p):
    h = hashlib.md5(Image.open(p).convert("RGB").crop(LABEL_BOX).tobytes()).hexdigest()[:10]
    return LABELS.get(h, "?" + h)


def name_ink(p):
    """Pixels claros na caixa do nome: >0 = a seta esta sobre uma cidade."""
    im = Image.open(p).convert("RGB").crop(NAME_BOX)
    return sum(1 for px in im.getdata() if sum(px) > 500)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", required=True)
    ap.add_argument("--btn", default="Up")
    ap.add_argument("--steps", type=int, default=6)
    ap.add_argument("--pick", type=int, default=1, help="qual cidade nomeada pegar (1=primeira)")
    ap.add_argument("--tag", required=True)
    a = ap.parse_args()
    SHOTS.mkdir(parents=True, exist_ok=True)
    b = BizHawkBridge()
    b.load(STATE)
    b.advance(60)
    b.speed(400)
    b.batch(b.seq_press("A", hold=5, wait=30) + b.seq_advance(300), extra_frames=450)

    lab = None
    for i in range(10):
        p = b.screenshot(SHOTS / f"{a.tag}_reg{i}.png")
        lab = label_of(p)
        if lab == a.region:
            break
        b.batch(b.seq_press("Right", hold=3, wait=25) + b.seq_advance(150), extra_frames=300)
    print("regiao:", lab, flush=True)
    if lab != a.region:
        return 1
    b.batch(b.seq_press("A", hold=5, wait=30) + b.seq_advance(400), extra_frames=600)

    # o 1o toque apaga o texto "Choose a city..." (senao a tinta dele vira falso
    # positivo do detector de nome) — MEDIDO 24/08
    b.batch(b.seq_press(a.btn, hold=4, wait=20) + b.seq_advance(150), extra_frames=250)
    achou = 0
    for i in range(a.steps + 1):
        p = b.screenshot(SHOTS / f"{a.tag}_nav{i:02d}.png")
        ink = name_ink(p)
        print(f"  passo {i}: ink={ink}", flush=True)
        if ink > 0:
            achou += 1
            if achou >= a.pick:
                break
        b.batch(b.seq_press(a.btn, hold=4, wait=20) + b.seq_advance(150), extra_frames=250)
    if achou < a.pick:
        print("ABORT: nenhuma cidade nomeada")
        return 1
    p_city = b.screenshot(SHOTS / f"{a.tag}_cidade.png")
    print("cidade:", p_city, flush=True)
    b.press("A", hold=6, wait=40)
    b.advance(400)
    print("pergunta:", b.screenshot(SHOTS / f"{a.tag}_pergunta.png"), flush=True)
    b.press("A", hold=6, wait=40)
    b.advance(600)
    p_roster = b.screenshot(SHOTS / f"{a.tag}_roster.png")
    print("roster:", p_roster, "cash_k", world.read_cash_k(b), flush=True)
    for i in range(4):
        b.press("A", hold=6, wait=40)
        b.advance(500)
        p = b.screenshot(SHOTS / f"{a.tag}_pos{i}.png")
    print("cash_k_final:", world.read_cash_k(b), flush=True)
    out = str((ROOT / "states" / f"_sede_{a.tag}.state").resolve())
    b.save(out)
    print("state:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
