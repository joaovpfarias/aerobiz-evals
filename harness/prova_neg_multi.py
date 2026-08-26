"""ACEITE: varias negociacoes + rotas no MESMO turno, pelo caminho do piloto.

Fase A (a sequencia que reproduzia o bug):
    negotiate_slots EU11 -> negotiate_slots SA01 -> open_route NA06 -> open_route NA02
    criterio: 4/4 True, com efeito verificado e SEM o retry de cursor ter disparado.

Fase B: 3 negociacoes em regioes DIFERENTES no mesmo turno.

Uso: python prova_neg_multi.py [a|b]
"""
import sys
from pathlib import Path

from PIL import Image

import world
from bridge import BizHawkBridge
from executor import Executor
from macros import Game

O = Path("../logs/neg_multi"); O.mkdir(parents=True, exist_ok=True)
STATE = "../states/eval_single_2000_lv5.state"


def novo():
    b = BizHawkBridge()
    ex = Executor(b)
    g = Game(b, shot_dir=O)
    ex.g = g
    b.load(STATE); b.advance(90); b.speed(400)
    return b, ex, g


def barra(b, ex, tag):
    ex._ensure_menu()
    img = Image.open(b.screenshot(O / f"{tag}.png")).convert("RGB")
    return world.free_staff_menu(img)


def roda(b, ex, g, acoes, nome):
    print(f"\n=== {nome} ===", flush=True)
    print(f"  funcionarios livres no inicio: {barra(b, ex, f'{nome}_barra_ini')}", flush=True)
    res = []
    for a in acoes:
        ok, det = ex.run(a)
        alvo = a["params"].get("city") or a["params"].get("to")
        print(f"  {a['action']:16} {alvo:5} -> {ok}\n      {det}", flush=True)
        res.append(ok)
    livres = barra(b, ex, f"{nome}_barra_fim")
    print(f"  funcionarios livres no fim: {livres}", flush=True)
    print(f"  RESULTADO {nome}: {sum(res)}/{len(res)} | retries de cursor: {ex.retries_fired}",
          flush=True)
    return res, livres


def fase_a():
    b, ex, g = novo()
    acoes = [
        {"action": "negotiate_slots", "params": {"city": "EU11"}},
        {"action": "negotiate_slots", "params": {"city": "SA01"}},
        {"action": "open_route", "params": {"to": "NA06"}},
        {"action": "open_route", "params": {"to": "NA02"}},
    ]
    res, livres = roda(b, ex, g, acoes, "faseA")
    b.speed(100)
    print(f"\nACEITE A: {'OK' if all(res) and ex.retries_fired == 0 else 'FALHOU'}", flush=True)


def fase_b():
    b, ex, g = novo()
    # tres REGIOES diferentes: Europa (EU11 Bruxelas), America do Sul (SA01
    # Havana), Oriente Medio (ME01). Nenhuma e a regiao da base.
    acoes = [
        {"action": "negotiate_slots", "params": {"city": "EU11"}},
        {"action": "negotiate_slots", "params": {"city": "SA01"}},
        {"action": "negotiate_slots", "params": {"city": "ME01"}},
    ]
    res, livres = roda(b, ex, g, acoes, "faseB")
    # evidencia visual: a tela de negociacao com os crachas que sobraram
    ex._ensure_menu(); g.open_cmd("negotiate"); world.wait_text(b); b.advance(30)
    img = Image.open(b.screenshot(O / "faseB_tela_neg_final.png")).convert("RGB")
    print(f"  tela de negociacao no fim: livres={world.staff_free_cells(img)}", flush=True)
    ex._ensure_menu()
    b.speed(100)
    print(f"\nACEITE B: {'OK' if all(res) and livres == 1 and ex.retries_fired == 0 else 'FALHOU'}",
          flush=True)


def fase_c():
    """Regressao: a mudanca em switch_to_region (1 R por vez) nao pode quebrar
    os outros fluxos. Intercala negociacao, compra de aviao e rota."""
    b, ex, g = novo()
    acoes = [
        {"action": "negotiate_slots", "params": {"city": "EU11"}},
        {"action": "buy_aircraft", "params": {"model": "MD100", "qty": 1}},
        {"action": "open_route", "params": {"to": "NA06"}},
        {"action": "negotiate_slots", "params": {"city": "SA01"}},
    ]
    print("\n=== faseC (regressao mista) ===", flush=True)
    res = []
    for a in acoes:
        ok, det = ex.run(a)
        alvo = a["params"].get("city") or a["params"].get("to") or a["params"].get("model")
        print(f"  {a['action']:16} {alvo:7} -> {ok}\n      {det}", flush=True)
        res.append(ok)
    b.speed(100)
    print(f"\nACEITE C: {'OK' if all(res) and ex.retries_fired == 0 else 'FALHOU'} "
          f"({sum(res)}/{len(res)}, retries={ex.retries_fired})", flush=True)


def fase_d():
    """Esgota os 4 negociadores e tenta o 5o.

    Cobre o que as fases A-C nao tocaram:
      - o 4o despacho e o unico que exige movimento DIAGONAL ate (1,1), a celula
        vizinha do Return — se o picker errasse, devolveria slots;
      - `free_staff_menu` == 0, valor nunca observado (so 4/3/2/1);
      - o ramo de recusa "nenhum funcionario livre", ate agora codigo morto.
    Roda em VELOCIDADE DE PRODUCAO (100%) e cronometra, porque o invariante de
    regiao passou a andar um R por vez.
    """
    import time

    b, ex, g = novo()
    b.speed(100)  # producao: o custo por acao aqui e o que o eval vai pagar
    acoes = [
        {"action": "negotiate_slots", "params": {"city": "EU11"}},  # Europa
        {"action": "negotiate_slots", "params": {"city": "SA01"}},  # America do Sul
        {"action": "negotiate_slots", "params": {"city": "ME01"}},  # Oriente Medio
        {"action": "negotiate_slots", "params": {"city": "AF01"}},  # Africa
        {"action": "negotiate_slots", "params": {"city": "OC01"}},  # 5o: sem quem enviar
    ]
    print("\n=== faseD (esgotar os 4 negociadores + 5a tentativa) ===", flush=True)
    print(f"  livres no inicio: {barra(b, ex, 'faseD_barra_ini')}", flush=True)
    res = []
    for a in acoes:
        t0 = time.time()
        ok, det = ex.run(a)
        print(f"  {a['params']['city']} -> {ok}  ({time.time() - t0:.0f}s)\n      {det}", flush=True)
        res.append(ok)
    livres = barra(b, ex, "faseD_barra_fim")
    print(f"  livres no fim: {livres} | retries de cursor: {ex.retries_fired}", flush=True)
    esperado = res[:4] == [True] * 4 and res[4] is False and livres == 0
    print(f"\nACEITE D: {'OK' if esperado and ex.retries_fired == 0 else 'FALHOU'}", flush=True)


if __name__ == "__main__":
    fase = sys.argv[1] if len(sys.argv) > 1 else "a"
    {"a": fase_a, "b": fase_b, "c": fase_c, "d": fase_d}[fase]()
