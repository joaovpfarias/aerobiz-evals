#!/usr/bin/env python3
"""ETAPA 6-Reversos: calibracao simplificada.

Protocolo:
  1. sell_aircraft: round trip buy→sell, verificar cash delta
  2. probe de r1c0 tabs: screenshots read-only de Open/Close pixel values
  3. return_slots: verificar slot count (pendente)

Uso:
  python calib_reversos_simple.py sell   # Roda buy+sell
  python calib_reversos_simple.py probe  # Abre r1c0, tira screenshots, sai
"""

import sys
import pathlib
import json
from PIL import Image

from bridge import BizHawkBridge
from executor import Executor
from macros import Game
from world import read_cash_k, WORLD_CITIES, staff_action_is_bid, city_region

LOGS_DIR = pathlib.Path(__file__).parent.parent / "logs" / "calib_reversos_18ago"
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def test_sell_aircraft():
    """Vender aeronave: pronto para rodar.

    Buy 1x MD100 + Sell 1x MD100 = round trip.
    Oracle: cash delta > 0 apos venda.
    """
    print("\n=== TEST: SELL_AIRCRAFT (round trip) ===")

    bridge = BizHawkBridge()
    ex = Executor(bridge)

    # Estado inicial: eval_single_2000_lv5 (frota virgem MD100x6)
    state_path = pathlib.Path(__file__).parent.parent / "states" / "eval_single_2000_lv5.state"
    print(f"1. Carregando {state_path.name}...")
    bridge.load(str(state_path))
    ex.reset_world_state()

    caixa_base = read_cash_k(bridge)
    print(f"   Caixa base: {caixa_base}K")

    # Buy 1x MD100
    print("2. Comprando 1x MD100...")
    ok_buy, det_buy = ex.run({"action": "buy_aircraft", "params": {"model": "MD100", "qty": 1}})
    print(f"   {'OK' if ok_buy else 'FALHA'}: {det_buy}")
    if not ok_buy:
        return False

    caixa_apos_buy = read_cash_k(bridge)

    # Sell 1x MD100
    print("3. Vendendo 1x MD100...")
    ok_sell, det_sell = ex.run({"action": "sell_aircraft", "params": {"model": "MD100", "qty": 1}})
    print(f"   {'OK' if ok_sell else 'FALHA'}: {det_sell}")
    if not ok_sell:
        return False

    caixa_apos_sell = read_cash_k(bridge)

    # Verificar efeito
    delta_buy = caixa_apos_buy - caixa_base
    delta_sell = caixa_apos_sell - caixa_apos_buy

    print(f"\n4. Resultados:")
    print(f"   Caixa: {caixa_base}K -> {caixa_apos_buy}K -> {caixa_apos_sell}K")
    print(f"   Delta buy: {delta_buy:+d}K (esperado: < 0, compra custa)")
    print(f"   Delta sell: {delta_sell:+d}K (esperado: > 0, venda recebe)")

    success = delta_sell > 0
    print(f"   Resultado: {'CALIBRADO' if success else 'FALHA'}")

    resultado = {
        "acao": "sell_aircraft",
        "caixa_base_k": caixa_base,
        "caixa_apos_buy_k": caixa_apos_buy,
        "caixa_apos_sell_k": caixa_apos_sell,
        "delta_buy_k": delta_buy,
        "delta_sell_k": delta_sell,
        "status": "CALIBRADO" if success else "FALHA",
        "detalhe_buy": det_buy,
        "detalhe_sell": det_sell,
    }

    resultado_path = LOGS_DIR / "sell_resultado.json"
    with open(resultado_path, "w") as f:
        json.dump(resultado, f, indent=2)
    print(f"   Salvo em {resultado_path.name}")

    return success


def probe_hub_tabs():
    """Probe read-only de r1c0 tabs: Open vs Close pixels.

    Abre r1c0 em regiao 1 (SA), tira screenshot do estado neutro,
    tira 3 screenshots apos navegacoes (Left, Down, Right), loga
    staff_action_is_bid e raw RGB counts. Zero A presses.
    """
    print("\n=== PROBE: R1C0 TABS (Open vs Close) ===")

    bridge = BizHawkBridge()
    ex = Executor(bridge)

    # Estado com hub em SA (probe_hub_open_sa)
    state_path = pathlib.Path(__file__).parent.parent / "states" / "probe_hub_open_sa.state"
    print(f"1. Carregando {state_path.name}...")
    bridge.load(str(state_path))
    ex.reset_world_state(hubs={"NA13"})

    # Navegar ate r1c0 em regiao SA
    print("2. Navegando ate r1c0 (South America region)...")
    ex.g.back_to_menu()

    # Trocar para regiao 1 (SA)
    print("3. Trocando para regiao 1 (South America)...")
    ok_reg, _ = ex._goto_region(1)
    if not ok_reg:
        print("   FALHA ao mudar regiao!")
        return False

    # Abrir r1c0
    print("4. Abrindo r1c0 (home_info)...")
    ex.g.open_cmd("home_info")
    from world import wait_text
    wait_text(bridge)
    bridge.advance(120)

    # Screenshot 0: estado neutro (esperado: Open destacado)
    print("5. Capturando screenshots de navegacao...")
    shots = {}

    # State 0: neutral (esperado Open destacado)
    bridge.advance(30)
    img0 = Image.open(bridge.screenshot()).convert("RGB")
    shots["00_neutral"] = bridge.screenshot()
    is_bid_0 = staff_action_is_bid(img0)
    print(f"   [0] neutral: staff_action_is_bid={is_bid_0} (esperado True=Open)")

    # State 1: apos LEFT (testando se eh para Close)
    bridge.press("Left", hold=3, wait=14)
    bridge.advance(40)
    img1 = Image.open(bridge.screenshot()).convert("RGB")
    shots["01_left"] = bridge.screenshot()
    is_bid_1 = staff_action_is_bid(img1)
    print(f"   [1] after Left: staff_action_is_bid={is_bid_1} (esperado False=Close)")

    # State 2: apos DOWN
    bridge.press("Down", hold=3, wait=14)
    bridge.advance(40)
    img2 = Image.open(bridge.screenshot()).convert("RGB")
    shots["02_down"] = bridge.screenshot()
    is_bid_2 = staff_action_is_bid(img2)
    print(f"   [2] after Down: staff_action_is_bid={is_bid_2} (staff row diferente)")

    # State 3: apos RIGHT (volta a Open provavelmente)
    bridge.press("Right", hold=3, wait=14)
    bridge.advance(40)
    img3 = Image.open(bridge.screenshot()).convert("RGB")
    shots["03_right"] = bridge.screenshot()
    is_bid_3 = staff_action_is_bid(img3)
    print(f"   [3] after Right: staff_action_is_bid={is_bid_3}")

    # Sair (so B)
    print("6. Saindo sem A (seguranca)...")
    for _ in range(6):
        bridge.press("B", hold=5, wait=25)
        bridge.advance(120)
        from world import at_main_menu_img
        if at_main_menu_img(Image.open(bridge.screenshot()).convert("RGB")):
            print("   Voltou ao menu")
            break

    # Salvar resultado
    resultado = {
        "probe": "r1c0_tabs_open_close",
        "states": {
            "neutral": {"staff_action_is_bid": is_bid_0, "esperado": True},
            "after_left": {"staff_action_is_bid": is_bid_1, "esperado": False},
            "after_down": {"staff_action_is_bid": is_bid_2, "esperado": "staff row change"},
            "after_right": {"staff_action_is_bid": is_bid_3, "esperado": True},
        },
        "conclusoes": {
            "navegacao_para_close": "Left" if is_bid_1 == False else "UNKNW"
        }
    }

    resultado_path = LOGS_DIR / "probe_tabs_resultado.json"
    with open(resultado_path, "w") as f:
        json.dump(resultado, f, indent=2)
    print(f"\n7. Probe completo. Salvo em {resultado_path.name}")

    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "sell":
        ok = test_sell_aircraft()
    elif cmd == "probe":
        ok = probe_hub_tabs()
    elif cmd == "all":
        print("Executando sell + probe...\n")
        ok1 = test_sell_aircraft()
        ok2 = probe_hub_tabs()
        ok = ok1 and ok2
    else:
        print(f"Comando desconhecido: {cmd}")
        sys.exit(1)

    sys.exit(0 if ok else 1)
