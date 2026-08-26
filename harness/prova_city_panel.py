"""ACEITE da ETAPA 5b — `world.read_city_panel` sobre PNGs (offline, sem emulador).

Por que offline: um leitor e funcao PURA do frame. Os 9 paineis do §33 ja estao
em `logs/etapa5a/` (4 paises, 2 regioes) e o §33.6.5 mostrou que os hashes do
painel se repetem entre sessoes e caminhos diferentes. Rodar o emulador so para
re-fotografar a mesma tela gastaria toques sem aumentar a evidencia.

O que este script prova, em quatro frentes:
  1. POSITIVO — le os 9 paineis e imprime todos os campos para conferencia A OLHO
     contra o PNG (o entregavel pede isso).
  2. NEGATIVO — `on_city_panel` e False em todo frame que NAO e o painel. Sem
     isto o leitor devolveria numeros plausiveis da tela errada.
  3. ORACULO — soma das 4 colunas da linha `Slot` == `Total slots` usados.
     Cruzamento automatico entre DOIS leitores independentes (grade x=0 da
     esquerda e grade x=136+32i da tabela).
  4. FONTE — o mesmo digito sobre fundos de cores diferentes tem que dar o MESMO
     hash. E o teste que mata a armadilha de binarizar RGB banda-a-banda.

Uso: python prova_city_panel.py
"""

import pathlib
import sys

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import world  # noqa: E402

RAIZ = HERE.parent
SHOTS = RAIZ / "logs" / "etapa5a"

# Os 9 paineis do §33, com o que o OLHO HUMANO leu no zoom 4x (§33.1) — e o
# gabarito independente do leitor. `None` onde o §33 nao registrou o valor.
PAINEIS = [
    # arquivo, cidade, pais, pop_m, econ, trsm, usados, cap, slot por cor
    ("r4_panel_NA13.png", "Washington", "United States", 1.2, 90, 48, 34, 116, (34, 0, 0, 0)),
    ("panel_NA02.png", "Seattle", "United States", 0.6, 68, 38, 21, 64, (11, 10, 0, 0)),
    ("panel_NA06.png", "Denver", "United States", 0.6, 64, 40, 24, 94, (12, 12, 0, 0)),
    ("panel_NA14.png", "Philadelphia", "United States", 1.9, 86, 42, 0, 75, (0, 0, 0, 0)),
    # CORRIGIDO PELO LEITOR: o §33.1 registrou "1/ 53" lido a olho no zoom 4x. O
    # leitor devolveu 35, e o zoom (`r4_zoom_NA11_total_slots.png`) confirma
    # "1/ 35" — quem errou foi o olho. Segunda vez nesta investigacao que o OCR
    # corrige a leitura humana (a primeira foi 0.6M lido como 0.8M). A soma das
    # colunas nao pegou isso porque a CAPACIDADE nao entra no oraculo.
    ("r4_panel_NA11.png", "Miami", "United States", 0.3, 45, 85, 1, 35, (0, 1, 0, 0)),
    ("r4_panel_NA16.png", "Honolulu", "United States", 0.3, 35, 95, 0, 64, (0, 0, 0, 0)),
    ("r4_panel_NA01.png", "Vancouver", "Canada", 1.4, 64, 44, 0, 124, (0, 0, 0, 0)),
    ("r4_panel_EU06.png", "Moscow", "Russia", 9.6, 56, 38, 0, 105, (0, 0, 0, 0)),
    ("r4_panel_EU02.png", "Helsinki", "EC", 0.5, 38, 38, 0, 32, (0, 0, 0, 0)),
]

# Frames que NAO sao o painel — o guard tem que recusar todos.
NEGATIVOS = [
    SHOTS / "r3_info_map_00.png",     # Info->map
    SHOTS / "r3_info_map_A.png",
    SHOTS / "r4_hover_NA11.png",      # cursor na cidade, SEM o A
    SHOTS / "r4_posB_NA11.png",       # depois do B (de volta ao mapa)
    SHOTS / "r4_posB_EU06.png",
    SHOTS / "r6_hover_NA02.png",      # fluxo r0c0: Distance/Cost
    SHOTS / "r6_posA_NA02.png",       # escolha de aviao
    SHOTS / "r6_r0c0_entrada.png",
]


def _extra_negativos(limite=40):
    """Varre outros diretorios de log atras de frames de telas quaisquer."""
    out = []
    for p in sorted((RAIZ / "logs").rglob("*.png")):
        if "etapa5a" in str(p):
            continue
        out.append(p)
        if len(out) >= limite:
            break
    return out


def prova_fonte_por_cor():
    """O MESMO digito em colunas de cores diferentes tem que dar o MESMO hash.

    `_bin_md5` do harness antigo faz `.point()` sobre RGB, o que limiariza cada
    banda separadamente: carmim e verde virariam 0 mas azul e laranja nao — o
    mesmo '0' hasharia diferente por coluna. Aqui a conversao e para L ANTES do
    limiar; este teste e o que distingue os dois jeitos.
    """
    img = Image.open(SHOTS / "r4_panel_NA13.png").convert("RGB")
    gp = world._city_bin(img).load()
    chars = {}
    for i, cor in enumerate(world.CITY_COL_KEYS):
        cx = world.CITY_DIGIT_X0 + world.CITY_COL_PITCH * i
        chars[cor] = world._city_small_cell(gp, cx, world.CITY_TABLE_Y["fl"])
    ok = len(set(chars.values())) == 1 and chars["carmim"] == "0"
    print("[4] fonte imune a cor de fundo: linha Fl de NA13 =", chars, "->",
          "OK" if ok else "FALHOU")
    return ok


def main():
    falhas = []

    print("=" * 78)
    print("[1] POSITIVO — leitura dos 9 paineis (confira A OLHO contra o PNG)")
    print("=" * 78)
    for (arq, cidade, pais, pop, econ, trsm, us, cap, slots) in PAINEIS:
        p = SHOTS / arq
        img = Image.open(p).convert("RGB")
        r = world.read_city_panel(img)
        lidos = tuple(r["table"]["slot"][c] for c in world.CITY_COL_KEYS) if r["table"] else None
        esperado = (pop, econ, trsm, us, cap, slots)
        obtido = (r["pop_m"], r["econ"], r["trsm"], r["slots_used"], r["slots_cap"], lidos)
        bate = esperado == obtido
        if not bate:
            falhas.append("%s: esperado %s, lido %s" % (arq, esperado, obtido))
        print("%-20s %-13s %-14s" % (arq, cidade, pais))
        print("   pop_m=%-5s econ=%-4s trsm=%-4s  Total slots %s/%s   Slot%s  Fl%s"
              % (r["pop_m"], r["econ"], r["trsm"], r["slots_used"], r["slots_cap"],
                 lidos, tuple(r["table"]["fl"][c] for c in world.CITY_COL_KEYS)))
        print("   rltns_icon=%s  name_hash=%s  name=%s  name_ocr=%r  soma_confere=%s  %s"
              % (r["rltns_icon"], r["name_hash"], r["name"], r["name_ocr"],
                 r["soma_confere"], "OK" if bate else "<<< DIVERGE DO OLHO HUMANO"))

    print()
    print("=" * 78)
    print("[2] NEGATIVO — on_city_panel tem que ser False fora do painel")
    print("=" * 78)
    negs = NEGATIVOS + _extra_negativos()
    maus = []
    for p in negs:
        if not p.exists():
            continue
        img = Image.open(p).convert("RGB")
        if world.on_city_panel(img):
            maus.append(str(p))
        r = world.read_city_panel(img)
        if r["on_panel"] is False and any(
                r[k] is not None for k in ("pop_m", "econ", "trsm", "slots_used", "table")):
            maus.append("vazou campo em " + str(p))
    print("frames testados: %d   falsos positivos: %d" % (len(negs), len(maus)))
    for m in maus:
        print("   FALHOU:", m)
    falhas += maus

    print()
    print("=" * 78)
    print("[3] ORACULO — soma das colunas Slot == Total slots usados")
    print("=" * 78)
    n_ok = 0
    for (arq, *_rest) in PAINEIS:
        r = world.read_city_panel(Image.open(SHOTS / arq).convert("RGB"))
        if r["soma_confere"] is True:
            n_ok += 1
        else:
            falhas.append("soma nao confere em " + arq)
    print("%d/%d paineis fecham." % (n_ok, len(PAINEIS)))
    print("LIMITE HONESTO: isto valida a linha `Slot`. A linha `Fl` estava ZERADA")
    print("nos 9 frames (§33.6.4) — o leitor dela existe mas NAO foi exercitado")
    print("com valor nao-nulo, e nao se sabe o que ela significa.")

    print()
    print("=" * 78)
    if not prova_fonte_por_cor():
        falhas.append("mesmo digito hashea diferente por cor de fundo")

    print()
    print("=" * 78)
    print("ACEITE:", "PASSOU" if not falhas else "FALHOU (%d)" % len(falhas))
    for f in falhas:
        print("  -", f)
    return 0 if not falhas else 1


if __name__ == "__main__":
    sys.exit(main())
