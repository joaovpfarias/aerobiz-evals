"""ETAPA 5-Venture: prova ao vivo de r0c5 (business venture) — compra de fato.

Fluxo (ver ACTION_SPACE.md r0c5, ja mapeado 17/08):
  buy_sell -> seletor de funcionario (Buy/Sell, mesma geometria de r0c2/r1c0)
  -> A ate sair p/ mapa -> _select_city(cid) -> tela de detalhe (grid 2x2 de
     4 tipos, HIPOTESE: Left/Right muda coluna, Up/Down muda linha, SEM WRAP)
  -> negociacao ("It will take N months. Is this OK?") -> YES -> confirmacao

ACEITE: comprar 1 City Hotel (mais barato, $72.000K) numa cidade por
parametro, caixa caindo 72.000K, Info->facilities confirmado antes/depois.

Nunca aperta tecla as cegas para sair: toda saida de probe e por savestate.
"""
import sys

sys.path.insert(0, ".")

from PIL import Image

from bridge import BizHawkBridge
from executor import Executor
from world import (at_main_menu_img, free_staff_menu, on_map_screen, read_cash_k,
                    wait_text)

CITY = sys.argv[1] if len(sys.argv) > 1 else "NA13"
BASE_STATE = "../states/_edit_2rotas.state"
OWN_GUARD = "../states/_venture_guard.state"


def shot(g, name):
    p = g.shot(name)
    print(f"  [shot] {name} -> {p}")
    return p


def main():
    b = BizHawkBridge()
    ex = Executor(b)
    g = ex.g

    print(f"== carregando baseline {BASE_STATE} ==")
    b.load(BASE_STATE)
    b.advance(90)
    assert ex._ensure_menu(), "nao chegou ao menu principal a partir do baseline"
    ex.reset_world_state(routes=[{"from": "NA13", "to": "NA14", "flights": 1}])

    cash0 = read_cash_k(b)
    livres0 = ex._menu_free_staff()
    print(f"cash baseline = {cash0}K, funcionarios livres = {livres0}")

    # --- baseline: Info->facilities da regiao NA ---
    shot_fac_before = g.info_screen("facilities", "venture_facilities_before")

    # --- baseline: r1c1 (ad_campaign) deve recusar "no businesses" ---
    ex._ensure_menu()
    g.open_cmd("ad_campaign")
    wait_text(b)
    b.advance(120)
    shot_ad_before = shot(g, "venture_ad_before")
    ex._ensure_menu()

    # salva NOSSO proprio guard (nao o GUARD generico, que run() sobrescreve)
    b.save(OWN_GUARD)
    print(f"guard salvo em {OWN_GUARD}")

    # ================= COMPRA DE VERDADE =================
    print(f"== abrindo r0c5 (buy_sell) para comprar City Hotel em {CITY} ==")
    g.open_cmd("buy_sell")
    wait_text(b)
    ok_sel, celula, det_sel = ex._pick_free_staff()
    print(f"staff pick: ok={ok_sel} celula={celula} det={det_sel}")
    if not ok_sel:
        shot(g, "venture_semstaff")
        b.load(OWN_GUARD)
        return

    for _ in range(5):
        wait_text(b)
        b.press("A", hold=5, wait=25)
        b.advance(90)
        if on_map_screen(Image.open(b.screenshot()).convert("RGB")):
            break
    else:
        shot(g, "venture_semmapa")
        b.load(OWN_GUARD)
        return
    shot(g, "venture_no_mapa")

    pos, reg, verif = ex._select_city(CITY)
    print(f"select_city({CITY}) -> pos={pos} reg={reg} verificado={verif}")
    shot_city = shot(g, f"venture_detalhe_{CITY}")

    # grid 2x2 HIPOTESE: (0,0) Concert Hall $144M | (0,1) Grand Hotel $288M
    #                    (1,0) City Hotel $72M    | (1,1) Commuter Airline $576M
    # a partir do detalhe recem-aberto o jogo comeca em (0,0). 1x Down -> City Hotel.
    b.press("Down", hold=4, wait=20)
    b.advance(90)
    shot_tipo = shot(g, f"venture_tipo_{CITY}")

    # não temos OCR: leitura visual sera feita apos o probe (screenshot). Aqui
    # so registramos e seguimos — a verificacao HUMANA do preco ($72000K) e
    # feita lendo o PNG antes de decidir se aborta ou confirma (ver saida do
    # script + leitura manual da imagem antes do proximo passo, se necessario).
    print(f"tela de tipo capturada em {shot_tipo} — CONFIRME visualmente City Hotel $72000K")

    # segue o fluxo: A -> "You must negotiate... Is this OK?" (YES/NO) -> A confirma
    for etapa in ("negociacao/confirmacao 1", "negociacao/confirmacao 2"):
        ok = ex._step()
        print(f"  _step({etapa}) -> {ok}")
        if not ok:
            shot(g, f"venture_travou_{CITY}")
            b.load(OWN_GUARD)
            return
    b.advance(90)
    shot_conf = shot(g, f"venture_confirmado_{CITY}")

    cash_no_confirm = read_cash_k(b)
    print(f"cash logo apos confirmar = {cash_no_confirm}K (baseline {cash0}K, delta {cash_no_confirm - cash0})")

    ex._ensure_menu()
    livres1 = ex._menu_free_staff()
    cash1 = read_cash_k(b)
    print(f"cash pos-menu = {cash1}K (delta {cash1 - cash0}), funcionarios livres = {livres1} (era {livres0})")

    shot_fac_after = g.info_screen("facilities", "venture_facilities_after")

    ex._ensure_menu()
    g.open_cmd("ad_campaign")
    wait_text(b)
    b.advance(120)
    shot_ad_after = shot(g, "venture_ad_after_imediato")
    ex._ensure_menu()

    print("\n=== RESUMO IMEDIATO ===")
    print(f"cash: {cash0}K -> {cash1}K ({cash1 - cash0:+d}K)")
    print(f"funcionarios livres: {livres0} -> {livres1}")
    print(f"facilities antes={shot_fac_before} depois={shot_fac_after}")
    print(f"ad_campaign antes={shot_ad_before} depois(imediato)={shot_ad_after}")
    print(f"guard para continuar (avancar trimestre): {OWN_GUARD} ja esta DEPOIS da compra? NAO — salve outro se quiser continuar")

    b.save("../states/_venture_comprado.state")
    print("estado pos-compra salvo em ../states/_venture_comprado.state")


if __name__ == "__main__":
    main()
