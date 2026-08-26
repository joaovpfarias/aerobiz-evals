"""Prova ETAPA 8: ler o ranking regional (Info->finance).

ACHADO AO VIVO 17/08 (corrige a hipotese do docstring original): a cadeia de
fim de turno cai primeiro no "Quarterly Report" (P&L por companhia); um `A`
dali avanca para "Regional Rankings <ano>" (NAO entra numa caixa de regiao,
so avanca a cadeia de relatorios). O `capture_all_regions` abaixo tenta
varrer caixa-por-caixa com A/B, mas o `B` a partir do Regional Rankings volta
para o Quarterly Report (mesma paleta de fundo, por isso o AVISO abaixo
dispara sempre no primeiro item) — a varredura por caixa fica PENDENTE; o que
funcionou e ja documentado em CALIBRATION.md foi capturar a tela do ranking
inteira em 2 momentos (y1/y2) e comparar os numeros visiveis a olho.
"""
import pathlib
import sys

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from bridge import BizHawkBridge
from executor import Executor
from macros import Game
from world import at_main_menu_img, read_cash_k, read_quarter_index, date_label

OUT = pathlib.Path(__file__).parent.parent / "logs" / "rankings_probe"
OUT.mkdir(parents=True, exist_ok=True)

TITLE_PTS = [((0, 0), (57, 75, 173)), ((64, 10), (41, 123, 173)), ((128, 10), (41, 123, 173))]


def on_rankings(img):
    return all(img.getpixel(xy) == color for xy, color in TITLE_PTS)


def tela(b):
    p = b.screenshot()
    return Image.open(p).convert("RGB")


def capture_all_regions(b, g, tag):
    """Na tela Regional Rankings: entra em cada caixa de regiao com A, foto, B."""
    # Posicoes aproximadas das 7 caixas no mapa (medidas em info_finance.png,
    # grade 256x224): Europe, N America, SE Asia, Mid East, Oceania, Africa, S America.
    # O cursor comeca em alguma caixa; usamos D-pad para varrer a grade e A/B
    # para entrar/sair, fotografando cada vez que uma foto MUDAR de tela.
    shots = []
    img0 = tela(b)
    img0.save(OUT / f"{tag}_00_map.png")
    # varredura simples: Right ate dar volta completa (7 regioes), entrando com A em cada uma
    for i in range(7):
        b.press("A", hold=5, wait=30)
        b.advance(150)
        img = tela(b)
        p = OUT / f"{tag}_region{i}_A.png"
        img.save(p)
        shots.append(str(p))
        # sai
        b.press("B", hold=5, wait=25)
        b.advance(90)
        img_back = tela(b)
        if not on_rankings(img_back):
            print(f"  [{tag}] AVISO: B nao voltou para rankings apos regiao {i}; abortando varredura")
            break
        # move pro proximo
        b.press("Right", hold=5, wait=20)
        b.advance(60)
    return shots


def main():
    b = BizHawkBridge(timeout=30)
    b.load("../states/eval_single_2000_lv5.state")
    g = Game(b)
    ex = Executor(b)
    ex.g = g

    achados = 0
    alvo = 2  # duas viradas de ano
    max_quarters = 40
    q = 0
    while achados < alvo and q < max_quarters:
        q += 1
        antes = read_quarter_index(b)
        # dispara fim de turno
        g.open_cmd("end_turn")
        b.advance(150)
        # cadeia: so B, exceto quando cair no rankings
        for step in range(60):
            img = tela(b)
            if at_main_menu_img(img):
                break
            if on_rankings(img):
                achados += 1
                print(f"RANKINGS #{achados} encontrado no trimestre {antes} ({date_label(antes)})")
                capture_all_regions(b, g, f"y{achados}")
                # depois de varrer, garanta volta ao rankings e saia de vez com B
                img = tela(b)
                if on_rankings(img):
                    b.press("B", hold=5, wait=25)
                    b.advance(90)
                continue
            b.press("B", hold=5, wait=25)
            b.advance(90)
        agora = read_quarter_index(b)
        print(f"turno {q}: {date_label(antes)} -> {date_label(agora)} caixa={read_cash_k(b)}K")

    print("achados:", achados)


if __name__ == "__main__":
    main()
