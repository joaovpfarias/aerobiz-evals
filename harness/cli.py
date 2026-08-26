"""Cockpit CLI da ponte BizHawk — para dirigir o emulador manualmente (F0).

Uso (python cli.py <op> ...):
  ping | info
  shot [caminho.png]
  press A,Start [--hold 5] [--wait 8]     # botoes: A B X Y Up Down Left Right Start Select L R
  seq "Down*3 A Right A*2"                # macro: botao[*repeticoes], espacos separam
  advance N
  save caminho.state | load caminho.state
  ram ADDR_HEX SIZE [--domain WRAM]
  speed PCT
"""

import argparse
import sys

from bridge import BizHawkBridge


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("op")
    ap.add_argument("args", nargs="*")
    ap.add_argument("--hold", type=int, default=5)
    ap.add_argument("--wait", type=int, default=8)
    ap.add_argument("--domain", default="WRAM")
    a = ap.parse_args()
    b = BizHawkBridge()

    op = a.op.lower()
    if op == "ping":
        print(f"frame {b.ping()}")
    elif op == "info":
        print(b.info())
    elif op == "shot":
        print(b.screenshot(a.args[0] if a.args else None))
    elif op == "press":
        b.press(*a.args[0].split(","), hold=a.hold, wait=a.wait)
        print("ok")
    elif op == "seq":
        for token in a.args[0].split():
            if "*" in token:
                btn, n = token.split("*")
                for _ in range(int(n)):
                    b.press(*btn.split(","), hold=a.hold, wait=a.wait)
            else:
                b.press(*token.split(","), hold=a.hold, wait=a.wait)
        print("ok")
    elif op == "advance":
        b.advance(int(a.args[0]))
        print("ok")
    elif op == "save":
        b.save(a.args[0])
        print("ok")
    elif op == "load":
        b.load(a.args[0])
        print("ok")
    elif op == "ram":
        data = b.read_ram(int(a.args[0], 16), int(a.args[1]), domain=a.domain)
        print(data.hex())
    elif op == "speed":
        b.speed(int(a.args[0]))
        print("ok")
    else:
        print(f"op desconhecida: {a.op}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
