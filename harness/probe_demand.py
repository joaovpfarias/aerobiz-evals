"""Tela de PEDIDO DE PATROCINIO ("Will you back this Project?") — a que trava o fim de turno.

Encontrada em 17/08 pelo aceite do end_turn no savestate `probe_hub_open_sa`:
a virada JUL.2001 -> OCT.2001 para numa caixa (YES NO) do "Rep. of EC" pedindo
**$372.000K**. `dismiss_to_menu` nao sai dela (B ignorado) e o A que ele arrisca
depois de duas telas paradas cairia sobre **YES** — 1/3 do caixa da companhia.

Fases (argv):
  capture  chega na tela e grava o savestate de guarda
  b        so B (o botao que o dismiss tenta primeiro)
  right    Right (o destaque anda de YES para NO?)
  no       Right + A  (recusar)  -> volta ao menu? caixa intacto?
  yes      A direto (aceitar)    -> mede o custo. NAO rodar sem necessidade.
"""

import pathlib
import sys

from PIL import Image

import world
from bridge import BizHawkBridge
from executor import Executor
from macros import Game

RAIZ = pathlib.Path(__file__).parent.parent
OUT = RAIZ / "logs" / "etapa1"
OUT.mkdir(parents=True, exist_ok=True)
ORIGEM = RAIZ / "states" / "probe_hub_open_sa.state"
GUARDA = RAIZ / "states" / "_demand_guard.state"


def snap(b, tag):
    p = b.screenshot(OUT / f"dem_{tag}.png")
    img = Image.open(p).convert("RGB")
    print(f"  {tag}: menu={world.at_main_menu_img(img)} "
          f"caixa={world.read_cash_k(b)}K q={world.read_quarter_index(b)} ({p})",
          flush=True)
    return img


def main():
    fase = sys.argv[1] if len(sys.argv) > 1 else "capture"
    b = BizHawkBridge(timeout=60)
    g = Game(b)
    ex = Executor(b)
    ex.g = g
    b.speed(400)

    if fase == "hunt":
        # A tela de pedido NAO e deterministica por savestate: o mesmo turno,
        # percorrido com timing diferente, ora a mostra ora nao (medido: aceite
        # a mostrou na virada JUL->OCT.2001, o `walk` do mesmo savestate nao).
        # Entao caca-se jogando turnos com B ate ela aparecer, e grava-se o
        # savestate NO frame em que ela esta na tela.
        b.load(ORIGEM)
        b.advance(90)
        ex.dismiss_to_menu()
        for turno in range(1, 13):
            g.open_cmd("end_turn")
            b.advance(120)
            for i in range(120):
                img = Image.open(b.screenshot()).convert("RGB")
                sel = world.yesno_prompt(img)
                if sel:
                    b.save(GUARDA)
                    print(f"ACHEI no turno {turno}, toque {i}: selecionado={sel} "
                          f"caixa={world.read_cash_k(b)}K", flush=True)
                    snap(b, "hunt_achei")
                    return
                if world.at_main_menu_img(img):
                    print(f"  turno {turno}: menu em {i} toques de B "
                          f"(sem pedido), q={world.read_quarter_index(b)}", flush=True)
                    break
                b.batch(b.seq_press("B", hold=5, wait=25) + b.seq_advance(90),
                        extra_frames=200)
        print("nao apareceu em 12 turnos", flush=True)
        return

    if fase == "walk":
        # Percorre a cadeia de fim de turno SO com B, um toque por vez, gravando
        # cada tela. Mede o comprimento real da cadeia (o teto de 48 do
        # dismiss_to_menu foi estourado no savestate com rota+hub) e mostra em
        # que ponto entra a caixa de pedido de patrocinio.
        b.load(ORIGEM)
        b.advance(90)
        ex.dismiss_to_menu()
        c0 = world.read_cash_k(b)
        print(f"menu, q={world.read_quarter_index(b)} caixa={c0}K", flush=True)
        g.open_cmd("end_turn")
        b.advance(120)
        for i in range(1, 121):
            img = Image.open(b.screenshot(OUT / f"walk_{i:03d}.png")).convert("RGB")
            menu = world.at_main_menu_img(img)
            caixa = world.read_cash_k(b)
            print(f"  B#{i - 1:3d} menu={menu} caixa={caixa}K "
                  f"q={world.read_quarter_index(b)}", flush=True)
            if menu:
                print(f"CHEGOU AO MENU com {i - 1} toques de B; "
                      f"caixa {c0}K -> {caixa}K", flush=True)
                break
            b.batch(b.seq_press("B", hold=5, wait=25) + b.seq_advance(90), extra_frames=200)
        return

    if fase == "capture":
        b.load(ORIGEM)
        b.advance(90)
        ex.dismiss_to_menu()
        print("menu, q =", world.read_quarter_index(b), flush=True)
        g.open_cmd("end_turn")
        b.advance(120)
        # atravessa a cadeia com B ate a tela travar (nunca A: e o botao que paga)
        for i in range(40):
            img = Image.open(b.screenshot()).convert("RGB")
            if world.at_main_menu_img(img):
                print("chegou ao menu sem passar pela tela de pedido", flush=True)
                break
            antes = b.screenshot()
            a1 = pathlib.Path(antes).read_bytes()
            b.batch(b.seq_press("B", hold=5, wait=25) + b.seq_advance(90), extra_frames=200)
            a2 = pathlib.Path(b.screenshot()).read_bytes()
            if a1 == a2:
                print(f"tela parada apos {i+1} B's", flush=True)
                break
        b.save(GUARDA)
        snap(b, "capture")
        return

    b.load(GUARDA)
    b.advance(60)
    snap(b, f"{fase}_00")
    if fase == "b":
        for i in range(1, 4):
            b.press("B", hold=5, wait=25)
            b.advance(90)
            snap(b, f"b_{i}")
    elif fase == "right":
        for i in range(1, 3):
            b.press("Right", hold=5, wait=25)
            b.advance(60)
            snap(b, f"right_{i}")
    elif fase in ("no", "yes"):
        if fase == "no":
            b.press("Right", hold=5, wait=25)
            b.advance(60)
            snap(b, "no_apos_right")
        b.press("A", hold=5, wait=25)
        b.advance(120)
        snap(b, f"{fase}_apos_A")
        ok = ex.dismiss_to_menu()
        print(f"  dismiss_to_menu -> {ok}", flush=True)
        snap(b, f"{fase}_final")


if __name__ == "__main__":
    main()
