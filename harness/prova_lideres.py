#!/usr/bin/env python3
"""ETAPA 1b-Adversarios — aceite OFFLINE de read_regional_leaders/read_rivals.

Roda SEM emulador, nos dois unicos frames de Regional Rankings existentes
(Apr2000 e Jul2000). Criterio: leitura coerente nos dois momentos e pelo menos
uma regiao muda de LIDER ou de VALOR entre eles.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from PIL import Image
import world

RAIZ = pathlib.Path(__file__).parent.parent
FRAMES = [
    ("Apr2000", RAIZ / "logs/rankings_probe/y1_region0_A.png"),
    ("Jul2000", RAIZ / "logs/rankings_probe/y2_region0_A.png"),
]
TABELA = RAIZ / "logs/prova_ic/mapa_pos_rota.png"


def main():
    tab = Image.open(TABELA).convert("RGB") if TABELA.exists() else None
    momentos = []
    for rotulo, p in FRAMES:
        img = Image.open(p).convert("RGB")
        assert world.on_regional_rankings_img(img), f"{p} nao e tela de ranking"
        r = world.read_rivals(img, img_tabela=tab)
        momentos.append((rotulo, r))
        print(f"=== {rotulo}  ({p.name})")
        print("  nos:", r["nos"], f"({r['nos_fonte']})")
        print("  legenda:", [(e["linha"], e["nome"], e["cor"]) for e in r["legenda"]])
        for reg in world.REGIONAL_RANKINGS_REGIONS:
            print(f"    {reg:10s} lider={str(r['lideres'][reg]):10s} num={r['numeros'][reg]}")
        # o rodape do PROPRIO frame de ranking (armadilha documentada)
        print("  [armadilha] read_our_company no frame de ranking =",
              world.read_our_company(img))

    (ra, a), (rb, b) = momentos
    mudou = [reg for reg in world.REGIONAL_RANKINGS_REGIONS
             if a["lideres"][reg] != b["lideres"][reg] or a["numeros"][reg] != b["numeros"][reg]]
    print("\n--- ACEITE")
    print("  regioes que mudaram entre", ra, "e", rb, ":", mudou)
    # NAO conta como "coerente nos 2 momentos": os dois recebem o MESMO
    # img_tabela, entao a comparacao nao teria como falhar. O `nos` fica aqui
    # so como demonstracao da API. A confirmacao independente de identidade e
    # outra e esta ao vivo: no Q191 o rodape do Quarterly Report leu 'Federal'
    # com caixa 1202880K, IGUAL ao da RAM (logs/lideres_19ago/run2.log).
    print("  nos (mesma img_tabela nos dois — nao e cheque):", a["nos"])
    lider_mudou = [reg for reg in mudou if a["lideres"][reg] != b["lideres"][reg]]
    print("  mudanca de LIDER:", lider_mudou or "NENHUMA (so os valores mudaram)")
    # Coerencia REAL entre os momentos: as caixas sem dado continuam sem dado e
    # as caixas com dado continuam com lider casado na legenda daquele frame.
    vazias_a = {r for r in world.REGIONAL_RANKINGS_REGIONS if a["lideres"][r] is None}
    vazias_b = {r for r in world.REGIONAL_RANKINGS_REGIONS if b["lideres"][r] is None}
    coerente = vazias_a == vazias_b
    print("  regioes sem lider legivel iguais nos 2 momentos:", coerente, sorted(vazias_a))
    ok = bool(mudou) and coerente
    print("  RESULTADO:", "OK" if ok else "FALHA")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
