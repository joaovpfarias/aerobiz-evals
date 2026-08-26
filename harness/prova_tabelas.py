"""Aceite OFFLINE dos leitores de tabela (nao precisa de emulador).

Confere contra telas ja em disco cujo conteudo e conhecido. Se este teste
passa, a geometria e o atlas estao certos e as leituras ao vivo podem confiar
neles; se falha, NAO adianta ir para o emulador.
"""

import pathlib
import sys

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import world  # noqa: E402

LOGS = pathlib.Path(__file__).parent.parent / "logs"
falhas = []


def checa(nome, obtido, esperado):
    ok = obtido == esperado
    print(f"  [{'OK ' if ok else 'FALHA'}] {nome}: {obtido!r}" + ("" if ok else f"  (esperado {esperado!r})"))
    if not ok:
        falhas.append(nome)


img = Image.open(LOGS / "prova_ic" / "mapa_pos_rota.png").convert("RGB")
print("mapa_pos_rota.png (1 rota: Washington -> Havana, Load 0%, rodape '1 Rte')")
rotas, n_rte = world.read_routes(img)
checa("n de linhas", len(rotas), 1)
checa("contador Rte do rodape", n_rte, 1)
checa("origem", rotas[0]["origin"], "Washington")
checa("destino", rotas[0]["dest"], "Havana")
checa("load_pct", rotas[0]["load_pct"], 0)
checa("caixa do rodape", world.read_footer_cash_k(img), 1166820)

img = Image.open(LOGS / "prova_ic" / "frota_1rota.png").convert("RGB")
print("\nfrota_1rota.png (MD100: In Use 1 / Avail 5 / Order 0)")
frota = world.read_fleet(img)
checa("n de linhas", len(frota), 1)
checa("modelo", frota[0]["model"], "MD100")
checa("in_use", frota[0]["in_use"], 1)
checa("avail", frota[0]["avail"], 5)
checa("order", frota[0]["order"], 0)

img = Image.open(LOGS / "buy" / "frota_depois_A340.png").convert("RGB")
print("\nfrota_depois_A340.png (2 linhas: MD100 e A340 com Order preenchido)")
frota = world.read_fleet(img)
checa("n de linhas", len(frota), 2)
checa("modelo linha 1", frota[0]["model"], "MD100")
checa("modelo linha 2", frota[1]["model"], "A340")
for i, l in enumerate(frota):
    print(f"      linha {i}: {l}")

print("\nRESULTADO:", "TUDO OK" if not falhas else f"{len(falhas)} FALHA(S): {falhas}")
sys.exit(1 if falhas else 0)
