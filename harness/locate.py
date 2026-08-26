"""Localiza cidades e o cursor no mapa por analise de pixels.

O mapa nao tem rotulo ao pairar e o cursor e um ponteiro livre, entao navegar as
cegas nao funciona. Aqui: cidades por cor, cursor por diferenca de frames
(o cursor e o unico sprite que se move quando pressionamos uma direcao).

Uso:
  python locate.py cities [--shot arquivo.png]   # lista cidades detectadas
  python locate.py cursor                        # acha o cursor ao vivo
  python locate.py goto X Y                      # move o cursor ate (X,Y)
"""

import argparse
import pathlib

from PIL import Image, ImageChops

from bridge import BizHawkBridge

TMP = pathlib.Path(__file__).parent / "ipc" / "loc.png"

GREEN = {(0, 203, 140), (0, 154, 74)}          # cidade "verde"
BLUE = {(90, 219, 255), (255, 251, 255)}        # cidade "branca/azul"
MAP_BOTTOM = 140                                 # abaixo disso e a caixa de texto
STEP_PX = 2                                      # 1 toque do d-pad = 2px (medido)


def find_dots(img, colors, min_px=6):
    """Agrupa pixels da cor dada em blobs; retorna centros (x, y, tamanho)."""
    w, h = img.size
    px = img.load()
    seen = set()
    blobs = []
    for y in range(min(h, MAP_BOTTOM)):
        for x in range(w):
            if (x, y) in seen or px[x, y] not in colors:
                continue
            stack, comp = [(x, y)], []
            seen.add((x, y))
            while stack:
                cx, cy = stack.pop()
                comp.append((cx, cy))
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        nx, ny = cx + dx, cy + dy
                        if (
                            0 <= nx < w
                            and 0 <= ny < MAP_BOTTOM
                            and (nx, ny) not in seen
                            and px[nx, ny] in colors
                        ):
                            seen.add((nx, ny))
                            stack.append((nx, ny))
            if len(comp) >= min_px:
                xs = [p[0] for p in comp]
                ys = [p[1] for p in comp]
                blobs.append((round(sum(xs) / len(xs)), round(sum(ys) / len(ys)), len(comp)))
    return sorted(blobs, key=lambda b: (b[1], b[0]))


def find_cursor(b):
    """Move 1px, diffa, volta: o bbox da diferenca contem o cursor.

    O diff e restrito a area do mapa — a caixa de texto anima (maquina de
    escrever) e contaminaria o bbox com uma regiao enorme.
    """
    crop = (0, 0, 256, MAP_BOTTOM)
    box = None
    for attempt in range(4):
        a = Image.open(b.screenshot(TMP)).convert("RGB").crop(crop)
        b.press("Right", hold=1, wait=8)
        c = Image.open(b.screenshot(TMP)).convert("RGB").crop(crop)
        b.press("Left", hold=1, wait=8)
        box = ImageChops.difference(a, c).getbbox()
        if box:
            break
        # o jogo ignora o d-pad enquanto o texto anima — esperar e tentar de novo
        b.advance(80)
    if not box:
        return None
    x0, y0, x1, y1 = box
    return {"bbox": box, "center": ((x0 + x1) // 2, (y0 + y1) // 2), "size": (x1 - x0, y1 - y0)}


def goto(b, tx, ty, tol=1, max_iter=12, verbose=False):
    """Move o cursor ate (tx, ty) em malha fechada.

    O cursor ACELERA enquanto a direcao fica pressionada (hold=30 anda ~40px),
    entao passos longos erram o alvo. Aqui damos passos de 1px e remedimos.
    """
    for i in range(max_iter):
        cur = find_cursor(b)
        if not cur:
            # o cursor fica oculto ate o primeiro movimento — acorda e remede
            b.press("Right", hold=1, wait=10)
            b.press("Left", hold=1, wait=10)
            cur = find_cursor(b)
            if not cur:
                raise RuntimeError("cursor nao encontrado nesta tela")
        cx, cy = cur["center"]
        dx, dy = tx - cx, ty - cy
        if verbose:
            print(f"  iter {i}: cursor ({cx},{cy}) -> alvo ({tx},{ty}) delta ({dx},{dy})", flush=True)
        if abs(dx) <= tol and abs(dy) <= tol:
            return cur["center"]
        for _ in range(min(round(abs(dx) / STEP_PX), 40)):
            b.press("Right" if dx > 0 else "Left", hold=1, wait=4)
        for _ in range(min(round(abs(dy) / STEP_PX), 40)):
            b.press("Down" if dy > 0 else "Up", hold=1, wait=4)
    final = find_cursor(b)
    if not final:
        raise RuntimeError(f"cursor sumiu ao tentar chegar em ({tx},{ty}) — tela mudou no meio?")
    raise RuntimeError(
        f"cursor nao convergiu para ({tx},{ty}) em {max_iter} iteracoes; parou em {final['center']}"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["cities", "cursor", "goto"])
    ap.add_argument("coords", nargs="*", type=int)
    ap.add_argument("--shot")
    a = ap.parse_args()
    b = BizHawkBridge()

    if a.cmd == "cities":
        path = a.shot or b.screenshot(TMP)
        img = Image.open(path).convert("RGB")
        g = find_dots(img, GREEN)
        w = find_dots(img, BLUE)
        print(f"verdes ({len(g)}):")
        for x, y, n in g:
            print(f"  ({x:3d},{y:3d}) {n}px")
        print(f"brancas/azuis ({len(w)}):")
        for x, y, n in w:
            print(f"  ({x:3d},{y:3d}) {n}px")
    elif a.cmd == "cursor":
        print(find_cursor(b))
    else:
        tx, ty = a.coords[:2]
        print("movido:", goto(b, tx, ty))


if __name__ == "__main__":
    main()
