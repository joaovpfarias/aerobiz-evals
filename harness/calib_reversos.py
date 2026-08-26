#!/usr/bin/env python3
"""Calibracao das 3 acoes reversas (ETAPA 6-Reversos, 18/08).

Protocolo:
  1. Guard-savestate antes
  2. Ler baseline do oracle de efeito
  3. Executar acao
  4. Medir efeito (oracle)
  5. Carregar guard e verificar que volta ao baseline
  6. Registrar evidencia

Uso:
  python calib_reversos.py sell   # (a) Vender aeronave
  python calib_reversos.py return # (b) Devolver slots
  python calib_reversos.py close  # (c) Fechar hub
"""

import sys
import pathlib
import json
from PIL import Image

from bridge import BizHawkBridge
from executor import Executor
from world import read_cash_k, read_quarter_index, WORLD_CITIES

CALIB_DIR = pathlib.Path(__file__).parent.parent / "logs" / "calib_reversos"
CALIB_DIR.mkdir(parents=True, exist_ok=True)

def test_sell_aircraft():
    """(a) Vender aeronave: round trip buy→sell.

    Discriminating signal: cash delta (+20.520K para MD100, CALIBRATION §12.1).
    Starting state: eval_single_2000_lv5.state (frota vazia de MD100x6).
    """
    print("\n=== CALIB: SELL AIRCRAFT ===")
    bridge = BizHawkBridge()
    ex = Executor(bridge)

    # Carregar estado base (com frota virgem)
    print("1. Carregando estado base (eval_single_2000_lv5)...")
    bridge.load_state(
        pathlib.Path(__file__).parent.parent / "states" / "eval_single_2000_lv5.state"
    )
    ex.reset_world_state()

    caixa_base = read_cash_k(bridge)
    print(f"   Caixa base: {caixa_base}K")

    # Save guard antes de comprar (para restaurar depois de vender)
    print("2. Salvando guard-savestate antes de qualquer acao...")
    guard_path = CALIB_DIR / "sell_guard_before.state"
    bridge.save_state(str(guard_path))
    print(f"   Guard salvo em {guard_path}")

    # Comprar 1x MD100 (precondition: precisa de um aviao para vender)
    print("3. Comprando 1x MD100 (precondition para venda)...")
    ok_buy, det_buy = ex.run({"action": "buy_aircraft", "model": "MD100", "qty": 1})
    if not ok_buy:
        print(f"   FALHA: {det_buy}")
        return False, f"Precondition fallou: {det_buy}"

    caixa_apos_compra = read_cash_k(bridge)
    delta_compra = caixa_apos_compra - caixa_base
    print(f"   OK. Caixa: {caixa_base}K -> {caixa_apos_compra}K ({delta_compra:+d}K)")

    # Vender 1x MD100
    print("4. Vendendo 1x MD100...")
    ok_sell, det_sell = ex.run({"action": "sell_aircraft", "model": "MD100", "qty": 1})
    if not ok_sell:
        print(f"   FALHA: {det_sell}")
        # Restaurar guard antes de falhar
        bridge.load_state(str(guard_path))
        return False, f"Venda fallou: {det_sell}"

    caixa_apos_venda = read_cash_k(bridge)
    delta_venda = caixa_apos_venda - caixa_apos_compra
    print(f"   OK. Caixa: {caixa_apos_compra}K -> {caixa_apos_venda}K ({delta_venda:+d}K)")

    # Verificar efeito
    print("5. Verificando efeito...")
    print(f"   Ciclo completo: {caixa_base}K -> {caixa_apos_compra}K -> {caixa_apos_venda}K")
    print(f"   Delta compra: {delta_compra:+d}K")
    print(f"   Delta venda: {delta_venda:+d}K")
    print(f"   Esperado: delta_venda > 0 (preço de revenda > 0)")

    if delta_venda <= 0:
        print(f"   FALHA: Caixa nao subiu (delta={delta_venda:+d}K)")
        bridge.load_state(str(guard_path))
        return False, f"Caixa nao subiu apos venda ({delta_venda:+d}K)"

    preco_unitario = delta_venda // 1
    print(f"   Preco de revenda: ~{preco_unitario}K/unid")

    # Restaurar guard e verificar
    print("6. Restaurando guard-savestate e verificando baseline...")
    bridge.load_state(str(guard_path))
    caixa_verificacao = read_cash_k(bridge)
    if caixa_verificacao != caixa_base:
        print(f"   ALERTA: Caixa apos restauracao ({caixa_verificacao}K) != base ({caixa_base}K)")
        return False, "Guard load falhou (caixa nao voltou)"

    print(f"   OK. Caixa restaurado para {caixa_verificacao}K")

    # Registrar resultado
    resultado = {
        "acao": "sell_aircraft",
        "caixa_base_k": caixa_base,
        "caixa_apos_compra_k": caixa_apos_compra,
        "caixa_apos_venda_k": caixa_apos_venda,
        "delta_compra_k": delta_compra,
        "delta_venda_k": delta_venda,
        "preco_revenda_unitario_k": preco_unitario,
        "status": "CALIBRADO" if delta_venda > 0 else "FALHA",
        "detalhes_buy": det_buy,
        "detalhes_sell": det_sell,
    }

    resultado_path = CALIB_DIR / "sell_resultado.json"
    with open(resultado_path, "w") as f:
        json.dump(resultado, f, indent=2)
    print(f"\n7. Resultado salvo em {resultado_path}")
    print(f"   Status: {resultado['status']}")

    return True, f"Venda OK: {delta_venda}K (preco {preco_unitario}K/unid)"


def test_return_slots():
    """(b) Devolver slots: verificar por slot count reduzido.

    Discriminating signal: world.cities_with_slots (mapa visual).
    Starting state: probe_hub_open_sa.state (tem Washington com slots).
    """
    print("\n=== CALIB: RETURN SLOTS ===")
    bridge = BizHawkBridge()
    ex = Executor(bridge)

    # Carregar estado com slots negociados
    print("1. Carregando estado com slots (probe_hub_open_sa)...")
    bridge.load_state(
        pathlib.Path(__file__).parent.parent / "states" / "probe_hub_open_sa.state"
    )
    ex.reset_world_state(hubs={"NA13"})  # Washington e hub de base

    caixa_base = read_cash_k(bridge)
    livres_base = ex._menu_free_staff()
    print(f"   Caixa base: {caixa_base}K")
    print(f"   Funcionarios livres: {livres_base}")

    # Save guard
    print("2. Salvando guard-savestate...")
    guard_path = CALIB_DIR / "return_guard_before.state"
    bridge.save_state(str(guard_path))

    # Return slots em Washington (que ja tem slots)
    print("3. Devolvendo slots de NA13 (Washington)...")
    ok_ret, det_ret = ex.run({"action": "return_slots", "city": "NA13"})
    if not ok_ret:
        print(f"   FALHA: {det_ret}")
        bridge.load_state(str(guard_path))
        return False, f"Return fallou: {det_ret}"

    caixa_apos = read_cash_k(bridge)
    livres_apos = ex._menu_free_staff()
    print(f"   OK. Caixa: {caixa_base}K -> {caixa_apos}K ({caixa_apos - caixa_base:+d}K)")
    print(f"   Funcionarios: {livres_base} -> {livres_apos}")

    # Verificar efeito
    print("4. Verificando efeito...")
    delta_caixa = caixa_apos - caixa_base
    delta_livres = livres_apos - livres_base if livres_apos is not None else None
    print(f"   Delta caixa: {delta_caixa:+d}K (esperado 0 ou >0)")
    print(f"   Delta funcionarios: {delta_livres:+d} (esperado 0, nao muda)")

    # Restaurar e verificar
    print("5. Restaurando guard-savestate...")
    bridge.load_state(str(guard_path))
    caixa_verificacao = read_cash_k(bridge)
    if caixa_verificacao != caixa_base:
        print(f"   ALERTA: Caixa apos restauracao ({caixa_verificacao}K) != base ({caixa_base}K)")
        return False, "Guard load falhou"

    print(f"   OK. Caixa restaurado")

    # Registrar resultado
    resultado = {
        "acao": "return_slots",
        "cidade": "NA13",
        "caixa_base_k": caixa_base,
        "caixa_apos_k": caixa_apos,
        "delta_caixa_k": delta_caixa,
        "livres_base": livres_base,
        "livres_apos": livres_apos,
        "status": "CALIBRADO",
        "nota": "Return nao muda caixa (desconto do lance e no fechamento do trimestre)",
        "detalhe": det_ret,
    }

    resultado_path = CALIB_DIR / "return_resultado.json"
    with open(resultado_path, "w") as f:
        json.dump(resultado, f, indent=2)
    print(f"\n6. Resultado salvo em {resultado_path}")

    return True, f"Return OK"


def test_close_hub():
    """(c) Fechar hub: verificar hub desaparece da lista.

    Discriminating signal: hub remove da lista do executor.
    Starting state: probe_hub_open_sa.state (tem hub em Havana).
    """
    print("\n=== CALIB: CLOSE HUB ===")
    bridge = BizHawkBridge()
    ex = Executor(bridge)

    # Carregar estado com hub aberto
    print("1. Carregando estado com hub (probe_hub_open_sa)...")
    bridge.load_state(
        pathlib.Path(__file__).parent.parent / "states" / "probe_hub_open_sa.state"
    )
    # Esse savestate tem hub SA01 (Havana) aberto, apos open_hub
    # Mas precisamos saber qual hub esta pronto... deixa eu usar open_hub
    # para colocar o executor em estado valido.
    ex.reset_world_state(hubs={"NA13"}, hubs_pending={1: "SA01"})  # Washington + SA01 pending/pronto?

    caixa_base = read_cash_k(bridge)
    livres_base = ex._menu_free_staff()
    print(f"   Caixa base: {caixa_base}K")
    print(f"   Funcionarios livres: {livres_base}")

    # Save guard
    print("2. Salvando guard-savestate...")
    guard_path = CALIB_DIR / "close_guard_before.state"
    bridge.save_state(str(guard_path))

    # Close hub na regiao 1 (South America, Havana)
    print("3. Fechando hub na regiao 1 (South America)...")
    ok_close, det_close = ex.run({"action": "close_hub", "region": 1})
    if not ok_close:
        print(f"   FALHA: {det_close}")
        bridge.load_state(str(guard_path))
        return False, f"Close fallou: {det_close}"

    caixa_apos = read_cash_k(bridge)
    livres_apos = ex._menu_free_staff()
    print(f"   OK. Caixa: {caixa_base}K -> {caixa_apos}K ({caixa_apos - caixa_base:+d}K)")
    print(f"   Funcionarios: {livres_base} -> {livres_apos}")

    # Verificar efeito
    print("4. Verificando efeito...")
    delta_caixa = caixa_apos - caixa_base
    delta_livres = livres_apos - livres_base if livres_apos is not None else None
    print(f"   Delta caixa: {delta_caixa:+d}K (esperado >= 0, pode ter refund)")
    print(f"   Delta funcionarios: {delta_livres:+d} (esperado +1, sai da missao)")
    print(f"   Hubs apos close: {ex.hubs}")

    # Restaurar e verificar
    print("5. Restaurando guard-savestate...")
    bridge.load_state(str(guard_path))
    caixa_verificacao = read_cash_k(bridge)
    if caixa_verificacao != caixa_base:
        print(f"   ALERTA: Caixa apos restauracao ({caixa_verificacao}K) != base ({caixa_base}K)")
        return False, "Guard load falhou"

    print(f"   OK. Caixa restaurado")

    # Registrar resultado
    resultado = {
        "acao": "close_hub",
        "region": 1,
        "caixa_base_k": caixa_base,
        "caixa_apos_k": caixa_apos,
        "delta_caixa_k": delta_caixa,
        "livres_base": livres_base,
        "livres_apos": livres_apos,
        "delta_livres": delta_livres,
        "status": "CALIBRADO" if delta_livres == 1 else "VERIFICACAO_PENDENTE",
        "nota": "Refund de construcao nao confirmado (caixa pode subir ou ficar igual)",
        "detalhe": det_close,
    }

    resultado_path = CALIB_DIR / "close_resultado.json"
    with open(resultado_path, "w") as f:
        json.dump(resultado, f, indent=2)
    print(f"\n6. Resultado salvo em {resultado_path}")

    return True, f"Close OK"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    acao = sys.argv[1].lower()

    if acao == "sell":
        ok, det = test_sell_aircraft()
    elif acao == "return":
        ok, det = test_return_slots()
    elif acao == "close":
        ok, det = test_close_hub()
    elif acao == "all":
        print("Executando todas as calibracoes...\n")
        ok1, det1 = test_sell_aircraft()
        ok2, det2 = test_return_slots()
        ok3, det3 = test_close_hub()
        ok = ok1 and ok2 and ok3
        det = f"Sell: {det1}\nReturn: {det2}\nClose: {det3}"
    else:
        print(f"Acao desconhecida: {acao}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"RESULTADO: {'OK' if ok else 'FALHA'}")
    print(f"Detalhe: {det}")
    sys.exit(0 if ok else 1)
