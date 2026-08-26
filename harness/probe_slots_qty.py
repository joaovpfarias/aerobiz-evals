"""ETAPA 3b (a): a tela "How many slots?" da negociacao aceita escolha?

Anda o fluxo de negotiate_slots ate a tela de quantidade e PARA. Fotografa,
le o texto (screen_text) e devolve o hash da TEXTBOX. Depois quem chama
testa Left/Right/Up/Down e ve se algo muda.
"""
import sys, pathlib, json
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bridge, world
from executor import Executor, STEP_SETTLE
from world import wait_text, on_map_screen

RAIZ = HERE.parent
SHOTS = RAIZ / "logs" / "etapa3b"
SHOTS.mkdir(parents=True, exist_ok=True)


def tb_hash(b):
    import hashlib
    img = Image.open(b.screenshot()).convert("RGB")
    return hashlib.md5(img.crop(world.TEXTBOX).tobytes()).hexdigest()[:8]


def goto_slots_screen(b, ex, cid):
    """Repete o inicio de _do_negotiate_slots ate a tela de quantidade."""
    ex.g.open_cmd("negotiate")
    wait_text(b)
    ok, cel, det = ex._pick_free_staff()
    if not ok:
        raise RuntimeError(f"staff: {det}")
    for _ in range(5):
        wait_text(b)
        b.press("A", hold=5, wait=25)
        b.advance(STEP_SETTLE)
        if on_map_screen(Image.open(b.screenshot()).convert("RGB")):
            break
    else:
        raise RuntimeError("nao chegou ao mapa")
    pos, reg, verif = ex._select_city(cid)
    return cel, det, (pos, reg, verif)


if __name__ == "__main__":
    cid = sys.argv[1] if len(sys.argv) > 1 else "EU01"
    b = bridge.BizHawkBridge()
    ex = Executor(b)
    cel, det, sel = goto_slots_screen(b, ex, cid)
    wait_text(b)
    p = b.screenshot(SHOTS / f"a_slots_screen_{cid}.png")
    print(json.dumps({"cell": cel, "det": det, "sel": [str(s) for s in sel],
                      "shot": str(p), "tb": tb_hash(b)}))
