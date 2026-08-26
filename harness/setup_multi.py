"""Configura a partida MULTIPLAYER (4 companhias controladas) para a arena multi-LLM.

Parte de `states/eval_players_screen.state`, que esta parado na tela
"How many people will play?" ja com cenario 4 (2000-2020) e nivel 5 escolhidos.

Cada jogador escolhe regiao e cidade em sequencia. As bases sao fixadas aqui para
a partida ser reproduzivel entre seeds.

Uso: python setup_multi.py --out ../states/eval_multi_2000_lv5.state
"""

import argparse
import pathlib

from bridge import BizHawkBridge
from locate import goto

SHOTS = pathlib.Path(__file__).parent.parent / "logs" / "setup_multi"

# Base de cada jogador: (nº de Rights ate a regiao, (x, y) da cidade no mapa).
# N America = 6 Rights a partir da posicao inicial (medido no setup single).
# As 4 bases ficam na mesma regiao para a disputa por slots ser direta —
# e a interacao competitiva que a arena existe para medir.
BASES = [
    {"rights": 6, "city": (204, 84), "nome": "NA13 Washington"},
    {"rights": 6, "city": (212, 74), "nome": "NA14 Philly"},
    {"rights": 6, "city": (158, 62), "nome": "NA09 (meio-oeste)"},
    {"rights": 6, "city": (90, 72), "nome": "NA06 Denver"},
]


def shot(b, name):
    SHOTS.mkdir(parents=True, exist_ok=True)
    return b.screenshot(SHOTS / f"{name}.png")


def escolher_base(b, idx, cfg):
    """Regiao + cidade de um jogador. O cursor da tela de base NAO usa a RAM
    do mapa em jogo — aqui e obrigatorio o posicionamento visual."""
    b.batch(b.seq_press("Right", hold=3, wait=25, times=cfg["rights"]) + b.seq_advance(150),
            extra_frames=600)
    shot(b, f"p{idx}_regiao")
    b.batch(b.seq_press("A", hold=5, wait=30) + b.seq_advance(300), extra_frames=450)
    x, y = cfg["city"]
    goto(b, x + 4, y + 4)
    b.batch(b.seq_press("A", hold=6, wait=30, times=3) + b.seq_advance(250), extra_frames=800)
    return shot(b, f"p{idx}_cidade")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="../states/eval_multi_2000_lv5.state")
    ap.add_argument("--state", default="../states/eval_players_screen.state")
    a = ap.parse_args()
    b = BizHawkBridge()
    b.load(a.state)
    b.advance(60)
    b.speed(400)

    # 4 jogadores: descer 3 vezes a partir de "1"
    b.batch(b.seq_press("Down", hold=3, wait=14, times=3) + b.seq_advance(80), extra_frames=300)
    shot(b, "00_players")
    b.batch(b.seq_press("A", hold=5, wait=30) + b.seq_advance(300), extra_frames=450)

    for i, cfg in enumerate(BASES, 1):
        print(f"jogador {i}: {cfg['nome']}", flush=True)
        print(" ", escolher_base(b, i, cfg), flush=True)

    print(shot(b, "05_resumo"))
    b.save(a.out)
    print(f"savestate multiplayer: {a.out}")


if __name__ == "__main__":
    main()
