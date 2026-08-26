"""Ferramenta de engenharia reversa da WRAM: acha variaveis por diferenca.

Substituir visao por leitura de memoria e o caminho certo aqui — screenshot custa
~0.5s e depende de animacao; ler RAM e instantaneo e deterministico.

Uso como biblioteca:
    from ramdiff import snap, delta, stable
    a = snap(b); ...faz algo...; c = snap(b)
    delta(a, c, +10)      # enderecos que aumentaram exatamente 10
    changed(a, c)         # todos que mudaram
    same_across(snaps)    # constantes em todos os snapshots

CLI:
    python ramdiff.py cursor      # acha X/Y do cursor do mapa
    python ramdiff.py screen      # acha o byte que identifica a tela atual
"""

import argparse

from bridge import BizHawkBridge

WRAM = 0x20000
CHUNK = 4096


def snap(b, size=WRAM):
    parts = []
    for off in range(0, size, CHUNK):
        parts.append(b.read_ram(off, min(CHUNK, size - off)))
    return b"".join(parts)


def delta(a, c, d, signed=True):
    """Enderecos cujo byte mudou exatamente `d` (com wrap de 8 bits)."""
    out = []
    for i in range(len(a)):
        if a[i] == c[i]:
            continue
        diff = (c[i] - a[i]) if not signed else ((c[i] - a[i] + 128) % 256) - 128
        if diff == d:
            out.append(i)
    return out


def changed(a, c):
    return [i for i in range(len(a)) if a[i] != c[i]]


def intersect(*lists):
    s = set(lists[0])
    for l in lists[1:]:
        s &= set(l)
    return sorted(s)


def find_cursor_addrs(b, taps=5, px_per_tap=2):
    """Move o cursor e procura os bytes que acompanham o movimento.

    Testa varias escalas: o jogo pode guardar a posicao em pixels, em passos do
    d-pad, ou em coordenadas internas do mapa.
    """
    a = snap(b)
    for _ in range(taps):
        b.press("Right", hold=1, wait=6)
    c = snap(b)
    for _ in range(taps):
        b.press("Left", hold=1, wait=6)
    d = snap(b)

    results = {}
    for scale, label in ((taps * px_per_tap, "px"), (taps, "passos")):
        # subiu ao ir para a direita E voltou ao valor original ao voltar
        up = set(delta(a, c, scale))
        back = set(delta(c, d, -scale))
        hits = sorted(up & back)
        if hits:
            results[label] = hits
    return results


def find_screen_byte(b, open_cmd_name="info"):
    """Bytes que mudam ao entrar numa tela e voltam ao sair — candidatos a
    identificador de tela/modo, que substitui o reconhecimento por imagem."""
    from macros import Game

    g = Game(b)
    g.back_to_menu()
    a = snap(b)
    g.open_cmd(open_cmd_name)
    c = snap(b)
    g.back_to_menu()
    d = snap(b)
    voltou = [i for i in changed(a, c) if a[i] == d[i]]
    return [(i, a[i], c[i]) for i in voltou]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["cursor", "screen"])
    ap.add_argument("--cmdname", default="info")
    a = ap.parse_args()
    b = BizHawkBridge()
    if a.cmd == "cursor":
        res = find_cursor_addrs(b)
        for label, hits in res.items():
            print(f"escala {label}: {len(hits)} candidatos")
            for h in hits[:20]:
                print(f"  0x{h:05x}")
        if not res:
            print("nenhum candidato — o cursor pode estar em 16 bits ou nao ter se movido")
    else:
        hits = find_screen_byte(b, a.cmdname)
        print(f"{len(hits)} candidatos a byte de tela (mudou e voltou):")
        for i, v0, v1 in hits[:30]:
            print(f"  0x{i:05x}: menu={v0} tela={v1}")


if __name__ == "__main__":
    main()
