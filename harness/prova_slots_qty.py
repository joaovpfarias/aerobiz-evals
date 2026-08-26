"""Aceite OFFLINE de world.read_slots_qty (ETAPA 3b-a, CALIBRATION §32).

Roda SEM emulador: le os frames ja capturados em logs/etapa3b/ e confere
quantidade lida x quantidade esperada (a esperada veio do ROTULO da tela,
conferido a olho um por um na calibracao).
"""
import sys, pathlib
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import world  # noqa: E402

SHOTS = HERE.parent / "logs" / "etapa3b"

# toques -> slots. qR = 4 toques (calibracao), qR8 = 8 toques (teto/wrap).
ESPERADO = {
    "qR_qty_0.png": 1, "qR_qty_1.png": 2, "qR_qty_2.png": 3,
    "qR_qty_3.png": 4, "qR_qty_4.png": 5,
    "qR8_qty_0.png": 1, "qR8_qty_1.png": 2, "qR8_qty_2.png": 3,
    "qR8_qty_3.png": 4, "qR8_qty_4.png": 5,
    # TETO: os toques 5..8 nao mexem — continua 5, nao da a volta para 1.
    "qR8_qty_5.png": 5, "qR8_qty_6.png": 5, "qR8_qty_7.png": 5, "qR8_qty_8.png": 5,
    # DEPOIS da negociacao concluida (3/75 no cabecalho): o medidor volta ao
    # padrao 1 — a quantidade nao e "pegajosa" entre negociacoes.
    "posneg_qty_0.png": 1,
}
# Telas que NAO sao a de quantidade: o leitor tem de devolver None (e assim
# servir de detector de tela, nunca confundir "tela errada" com "1 slot").
NAO_E = ["s00_A2_befbff27.png", "s00_00_staffgrid.png", "s00_A4_a52d37e7.png",
         "m_e00_s1_meses.png", "m_e01_s1_meses.png", "m_e10_s1_meses.png",
         "m_e11_s1_meses.png", "m_e00_s5_meses.png"]

falhas = 0
print("read_slots_qty — telas de quantidade")
for nome, esp in ESPERADO.items():
    p = SHOTS / nome
    if not p.exists():
        print(f"  [SKIP] {nome} (ausente)")
        continue
    got = world.read_slots_qty(Image.open(p).convert("RGB"))
    ok = got == esp
    falhas += not ok
    print(f"  [{'OK ' if ok else 'FALHA'}] {nome}: esperado {esp}, lido {got}")

print("read_slots_qty — telas que NAO sao de quantidade (tem de dar None)")
for nome in NAO_E:
    p = SHOTS / nome
    if not p.exists():
        print(f"  [SKIP] {nome} (ausente)")
        continue
    got = world.read_slots_qty(Image.open(p).convert("RGB"))
    ok = got is None
    falhas += not ok
    print(f"  [{'OK ' if ok else 'FALHA'}] {nome}: lido {got}")

print("\nRESULTADO:", "TUDO OK" if falhas == 0 else f"{falhas} FALHA(S)")
sys.exit(1 if falhas else 0)
