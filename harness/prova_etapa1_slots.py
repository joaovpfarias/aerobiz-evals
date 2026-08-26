"""ACEITE ETAPA 1-RegressaoSlots: negotiate_slots em >=6 cidades / >=3 regioes.

O bug: `negotiate_slots` falhava com "medidor ilegivel" em NA06 (Denver) e NA02
mas passava em NA05/NA14. Causa levantada dos PNGs (world.py §medidor): o
medidor NAO tem 5 posicoes sempre — tem N posicoes, N MUDA POR CIDADE, e a
tabela antiga (soma de pixels brancos) so cobria N=5.

O que este script MEDE (nada e assumido):
  B1/B2  negociacao completa em 7 cidades de 5 regioes, cada uma com a
         quantidade LIDA DE VOLTA da tela e o teto LIDO da tela.
  B2     NA06 repetido A PARTIR DO MESMO SAVESTATE de B1 — se N e propriedade
         da cidade, o teto tem de sair igual nas duas leituras. Teto diferente
         = o leitor esta sub-lendo (nao se repete apos negociacao ja feita:
         ai N poderia mudar por direito e a comparacao nao provaria nada).
  B3     RECUSA deliberada (pedir 5 numa cidade de teto 2) + prova de que a
         guarda restaurou: barra de funcionarios de volta ao valor de antes e
         jogo no menu principal, LIDOS DA TELA (R4 vale para o rollback tambem).
         Em seguida uma negociacao normal, para provar que a partida continua
         utilizavel depois da recusa.

Uso: python prova_etapa1_slots.py [b1|b2|b3|all]
"""
import re
import sys
import time
from pathlib import Path

from PIL import Image

import world
from bridge import BizHawkBridge
from executor import Executor
from macros import Game

O = Path("../logs/etapa1_slots")
O.mkdir(parents=True, exist_ok=True)
STATE = "../states/eval_single_2000_lv5.state"


def novo():
    b = BizHawkBridge()
    ex = Executor(b)
    ex.g = Game(b, shot_dir=O)
    b.load(STATE)
    b.advance(90)
    b.speed(400)
    return b, ex


def barra(b, ex, tag):
    """Funcionarios livres LIDOS da barra do menu (None = nao reconheci)."""
    ex._ensure_menu()
    img = Image.open(b.screenshot(O / f"{tag}.png")).convert("RGB")
    return world.free_staff_menu(img)


def teto_de(detalhe):
    """Teto LIDO DA TELA, venha do sucesso ou de uma recusa que o nomeia.

    A recusa por teto nao escreve "teto=N" e sim "tem N posicao(oes)"; sem
    cobrir as duas formas, justamente as cidades onde o teto e o numero
    interessante entrariam na tabela como teto desconhecido.
    """
    for padrao in (r"teto=(\d+)", r"tem (\d+) posicao", r"mudou de (\d+)"):
        m = re.search(padrao, detalhe or "")
        if m:
            return int(m.group(1))
    return None


def lidos_de(detalhe):
    m = re.search(r"LIDOS DE VOLTA=(\d+)", detalhe or "")
    return int(m.group(1)) if m else None


def roda(b, ex, nome, pedidos):
    """pedidos: [(cidade, slots)] -> {cidade: (ok, pedido, lido, teto, detalhe)}"""
    print(f"\n=== {nome} (savestate recarregado) ===", flush=True)
    print(f"  funcionarios livres no inicio: {barra(b, ex, nome + '_barra_ini')}", flush=True)
    out = {}
    for cid, n in pedidos:
        t0 = time.time()
        ok, det = ex.run({"action": "negotiate_slots", "params": {"city": cid, "slots": n}})
        out[cid] = (ok, n, lidos_de(det), teto_de(det), det)
        print(f"  {cid} pedido={n} -> {ok}  ({time.time() - t0:.0f}s)\n      {det}", flush=True)
    print(f"  funcionarios livres no fim: {barra(b, ex, nome + '_barra_fim')}"
          f" | retries de cursor: {ex.retries_fired}", flush=True)
    return out


def b1():
    b, ex = novo()
    # NA06 (Denver) e NA02 sao as DUAS cidades onde o bug foi reproduzido.
    # EU11 e SA01 sao regressao: passavam antes e tem de continuar passando.
    r = roda(b, ex, "B1", [("NA06", 2), ("NA02", 2), ("EU11", 2), ("SA01", 2)])
    b.speed(100)
    return r


def b2():
    b, ex = novo()
    # NA06 e o REPETIDO a partir do mesmo savestate de B1 (teste de N estavel).
    r = roda(b, ex, "B2", [("NA06", 1), ("ME01", 2), ("AF01", 2), ("NA05", 3)])
    b.speed(100)
    return r


def b3():
    """Recusa deliberada + prova de rollback."""
    b, ex = novo()
    print("\n=== B3 (recusa deliberada + guarda) ===", flush=True)
    antes = barra(b, ex, "B3_barra_antes")
    print(f"  funcionarios livres antes: {antes}", flush=True)
    # NA06 leu teto=2 nos PNGs do bug: pedir 5 tem de ser RECUSADO, nao
    # silenciosamente reduzido — pedir 1 quando o modelo pediu 5 e mentir.
    ok, det = ex.run({"action": "negotiate_slots", "params": {"city": "NA06", "slots": 5}})
    print(f"  NA06 pedido=5 -> {ok}\n      {det}", flush=True)
    depois = barra(b, ex, "B3_barra_depois")
    img = Image.open(b.screenshot(O / "B3_tela_pos_recusa.png")).convert("RGB")
    no_menu = world.at_main_menu_img(img)
    print(f"  funcionarios livres depois: {depois} (antes {antes}) | no menu principal: {no_menu}",
          flush=True)
    # A partida continua utilizavel depois da recusa?
    ok2, det2 = ex.run({"action": "negotiate_slots", "params": {"city": "NA06", "slots": 2}})
    print(f"  NA06 pedido=2 (apos recusa) -> {ok2}\n      {det2}", flush=True)
    b.speed(100)
    guarda_ok = (ok is False and depois == antes and depois is not None and no_menu)
    print(f"\n  ACEITE B3: recusou={ok is False} barra_intacta={depois == antes} "
          f"menu={no_menu} usavel_depois={ok2} -> "
          f"{'OK' if guarda_ok and ok2 else 'FALHOU'}", flush=True)
    return {"recusa_ok": ok is False, "barra": (antes, depois), "menu": no_menu,
            "detalhe_recusa": det, "seguinte_ok": ok2, "detalhe_seguinte": det2}


def main():
    fase = sys.argv[1] if len(sys.argv) > 1 else "all"
    r1 = b1() if fase in ("b1", "all") else {}
    r2 = b2() if fase in ("b2", "all") else {}
    r3 = b3() if fase in ("b3", "all") else None
    if fase != "all":
        return
    todos = {}
    todos.update(r1)
    for k, v in r2.items():
        todos[k + "_b2" if k in todos else k] = v
    print("\n===== RESUMO ETAPA 1-RegressaoSlots =====", flush=True)
    for cid, (ok, ped, lido, teto, _) in todos.items():
        print(f"  {cid:8} ok={ok!s:5} pedido={ped} lido={lido} teto={teto}", flush=True)
    # DOIS criterios distintos (o bug era "medidor ilegivel", nao "negociacao
    # nao fechou"): uma cidade de teto 1 onde pedimos 2 e RECUSADA com o teto
    # lido da tela — isso e o medidor funcionando, nao falha. O aceite
    # (>=6 cidades / >=3 regioes) le o primeiro contador.
    lidas = sorted({c.split("_")[0] for c, v in todos.items() if v[3] is not None})
    fechadas = sorted({c.split("_")[0] for c, v in todos.items() if v[0] and v[1] == v[2]})
    regioes = {world.city_region(c) for c in lidas}
    print(f"  cidades com MEDIDOR LIDO (teto da tela): {len(lidas)} ({lidas}) "
          f"em {len(regioes)} regiao(oes)", flush=True)
    print(f"  cidades com negociacao FECHADA e pedido == lido de volta: "
          f"{len(fechadas)} ({fechadas})", flush=True)
    n06 = r1.get("NA06"), r2.get("NA06")
    if all(n06):
        print(f"  N estavel em NA06 (mesmo savestate, 2 aberturas): "
              f"teto {n06[0][3]} vs {n06[1][3]} -> "
              f"{'IGUAL' if n06[0][3] == n06[1][3] else 'DIFERENTE (leitor suspeito)'}", flush=True)
    if r3:
        print(f"  guarda: recusa={r3['recusa_ok']} barra={r3['barra']} menu={r3['menu']} "
              f"usavel_depois={r3['seguinte_ok']}", flush=True)
    print(f"  ACEITE (>=6 cidades com medidor lido, >=3 regioes): "
          f"{'OK' if len(lidas) >= 6 and len(regioes) >= 3 else 'FALHOU'}", flush=True)


if __name__ == "__main__":
    main()
