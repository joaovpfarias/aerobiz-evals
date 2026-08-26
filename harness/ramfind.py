"""Encontra variaveis do jogo na WRAM procurando um valor conhecido.

Ler o caixa da RAM e mais confiavel e mais barato que OCR de fonte SNES.
Estrategia: carregar um savestate cujo valor na tela e conhecido, varrer a WRAM
nas codificacoes plausiveis e depois confirmar que o endereco acompanha o valor.

Uso:
  python ramfind.py 1019360                     # procura o valor
  python ramfind.py 1019360 --verify 0x1f2a     # le um endereco ja encontrado
"""

import argparse

from bridge import BizHawkBridge

WRAM = 0x20000  # SNES: 128KB
CHUNK = 2048


def dump(b, size=WRAM, domain="WRAM"):
    parts = []
    for off in range(0, size, CHUNK):
        parts.append(b.read_ram(off, min(CHUNK, size - off), domain=domain))
    return b"".join(parts)


def encodings(value):
    """Codificacoes plausiveis para um inteiro em jogos SNES da Koei."""
    out = {}
    for n in (2, 3, 4):
        try:
            out[f"le{n * 8}"] = value.to_bytes(n, "little")
            out[f"be{n * 8}"] = value.to_bytes(n, "big")
        except OverflowError:
            pass
    s = str(value)
    if len(s) % 2:
        s = "0" + s
    bcd = bytes.fromhex(s)
    out["bcd_be"] = bcd
    out["bcd_le"] = bcd[::-1]
    return out


def search(data, value):
    hits = []
    for name, pat in encodings(value).items():
        start = 0
        while True:
            i = data.find(pat, start)
            if i < 0:
                break
            hits.append((i, name))
            start = i + 1
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("value", type=int)
    ap.add_argument("--verify", help="endereco hex para ler (ex: 0x1f2a)")
    ap.add_argument("--size", type=int, default=4)
    a = ap.parse_args()
    b = BizHawkBridge()

    if a.verify:
        addr = int(a.verify, 16)
        raw = b.read_ram(addr, a.size)
        print(f"{a.verify}: bytes={raw.hex()} le={int.from_bytes(raw, 'little')} be={int.from_bytes(raw, 'big')}")
        return

    print("lendo WRAM...", flush=True)
    data = dump(b)
    print(f"{len(data)} bytes lidos")
    hits = search(data, a.value)
    print(f"{len(hits)} candidatos para {a.value}:")
    for addr, enc in hits[:40]:
        print(f"  0x{addr:05x}  {enc}")


if __name__ == "__main__":
    main()
