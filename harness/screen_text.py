"""Leitura de TEXTO das telas de tabela do Aerobiz (SNES).

A fonte do jogo e um bitmap de celula FIXA de 8x13 px alinhada a grade: cada
caractere ocupa uma coluna multipla de 8, e as linhas de texto ficam em
y = 8, 24, 40, ... (passo 16). Medido em `logs/prova_ic/mapa_pos_rota.png` e
`logs/prova_ic/frota_1rota.png` — ver CALIBRATION "ETAPA 1-OCR-Infra".

Por que celula fixa e nao recorte justo do glifo: o recorte justo muda de
largura conforme o caractere ('1' ocupa 4 px, '8' ocupa 7), entao o hash
dependeria da segmentacao. Com a celula ancorada na grade o mesmo caractere
sempre produz o MESMO hash, venha ele do rodape de caixa ou do meio de um nome
de cidade — e um atlas so serve todas as telas.

Caractere fora do atlas NUNCA vira palpite: vira `UNKNOWN` ('?'). Ler errado um
nome de cidade seria pior que nao ler, porque o modelo decidiria sobre ficcao.
"""

import hashlib
import json
import pathlib

WHITE = (255, 251, 255)      # cor do texto nas telas de relatorio
CELL_W, CELL_H = 8, 13
GRID_Y0, ROW_PITCH = 8, 16   # y da linha de cabecalho e passo entre linhas
UNKNOWN = "?"
MIN_INK = 3                  # menos que isto e ruido de borda, nao caractere

ATLAS_PATH = pathlib.Path(__file__).parent / "glyphs.json"


def _load_atlas():
    if ATLAS_PATH.exists():
        return json.loads(ATLAS_PATH.read_text(encoding="utf-8"))
    return {}


ATLAS = _load_atlas()


def row_y(index):
    """y do topo da linha `index` (0 = cabecalho, 1 = primeira linha de dados)."""
    return GRID_Y0 + ROW_PITCH * index


def cell_bits(px, cx, y0):
    return "".join(
        "1" if px[x, y] == WHITE else "0"
        for y in range(y0, y0 + CELL_H)
        for x in range(cx, cx + CELL_W)
    )


def cell_hash(px, cx, y0):
    """Hash da celula, ou None se ela estiver vazia (sem tinta suficiente)."""
    bits = cell_bits(px, cx, y0)
    if bits.count("1") < MIN_INK:
        return None
    return hashlib.md5(bits.encode()).hexdigest()[:10]


def read_cell(px, cx, y0, atlas=None):
    h = cell_hash(px, cx, y0)
    if h is None:
        return " "
    return (atlas or ATLAS).get(h, UNKNOWN)


def read_text(img, y0, x0, x1, atlas=None):
    """Le a faixa [x0, x1) da linha que comeca em y0. Devolve string ja limpa.

    x0 e arredondado para baixo na grade de 8 px: pedir um recorte desalinhado
    e o jeito mais facil de transformar texto legivel em '?????'.
    """
    px = img.load()
    x0 -= x0 % CELL_W
    out = [read_cell(px, cx, y0, atlas) for cx in range(x0, x1 - CELL_W + 1, CELL_W)]
    return "".join(out).strip()


def read_int(img, y0, x0, x1, atlas=None):
    """Le um numero. Devolve None se houver qualquer caractere nao-digito.

    Tolera os sufixos que o jogo cola no numero ('%', 'K', '$' a esquerda);
    qualquer outra coisa (inclusive UNKNOWN) invalida a leitura inteira em vez
    de devolver um numero parcialmente adivinhado.
    """
    s = read_text(img, y0, x0, x1, atlas)
    s = s.replace("$", "").replace("%", "").replace("K", "").replace(",", "").strip()
    if not s or any(c not in "0123456789" for c in s):
        return None
    return int(s)


def unknown_hashes(img, y0, x0, x1):
    """Celulas cujo glifo nao esta no atlas — alimenta o rotulador."""
    px = img.load()
    x0 -= x0 % CELL_W
    out = {}
    for cx in range(x0, x1 - CELL_W + 1, CELL_W):
        h = cell_hash(px, cx, y0)
        if h is not None and h not in ATLAS:
            out[h] = (cx, y0)
    return out


def render(bits):
    """Bitmap da celula como arte ASCII — usado para rotular glifos novos."""
    return [bits[r * CELL_W:(r + 1) * CELL_W].replace("0", ".").replace("1", "#")
            for r in range(CELL_H)]
