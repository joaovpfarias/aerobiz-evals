"""ETAPA 4-CidadeInvestigar: fotografa e mede a escolha da cidade-sede.

Somente MEDICAO. Nao escreve setup, nao sobrescreve savestate eval_*.
  python _probe_sede.py regions       # enumera regioes (Right x N) na tela de base
  python _probe_sede.py cities        # lista blobs de cidade da regiao atual
"""
import argparse
import pathlib
import sys

from bridge import BizHawkBridge
import locate

ROOT = pathlib.Path(__file__).parent.parent
SHOTS = ROOT / "logs" / "etapa4_sede"
STATE = str(ROOT / "states" / "eval_players_screen.state")


def shot(b, name):
    SHOTS.mkdir(parents=True, exist_ok=True)
    return b.screenshot(SHOTS / f"{name}.png")


def start(b):
    b.load(STATE)
    b.advance(60)
    b.speed(400)


def regions(b, n):
    start(b)
    print("players_screen:", shot(b, "00_players"))
    # 1 jogador = A direto (a tela abre em "1")
    b.batch(b.seq_press("A", hold=5, wait=30) + b.seq_advance(300), extra_frames=450)
    print("region0:", shot(b, "r00"))
    for i in range(1, n + 1):
        b.batch(b.seq_press("Right", hold=3, wait=25) + b.seq_advance(150), extra_frames=300)
        print(f"region{i}:", shot(b, f"r{i:02d}"))


def cities(b, rights):
    start(b)
    b.batch(b.seq_press("A", hold=5, wait=30) + b.seq_advance(300), extra_frames=450)
    if rights:
        b.batch(b.seq_press("Right", hold=3, wait=25, times=rights) + b.seq_advance(150),
                extra_frames=300)
    p = shot(b, f"cities_r{rights}_regiao")
    print("regiao:", p)
    b.batch(b.seq_press("A", hold=5, wait=30) + b.seq_advance(300), extra_frames=450)
    p = shot(b, f"cities_r{rights}_mapa")
    print("mapa:", p)
    from PIL import Image
    img = Image.open(p).convert("RGB")
    g = locate.find_dots(img, locate.GREEN)
    bl = locate.find_dots(img, locate.BLUE)
    print("GREEN:", g)
    print("BLUE:", bl)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["regions", "cities"])
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--rights", type=int, default=0)
    a = ap.parse_args()
    b = BizHawkBridge()
    if a.cmd == "regions":
        regions(b, a.n)
    else:
        cities(b, a.rights)


if __name__ == "__main__":
    main()
