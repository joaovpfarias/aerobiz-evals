"""ETAPA 7-LerFrota: caca de enderecos de RAM para Info->fleet (Plane|In Use|Avail|Order).

Metodo (mesmo de ramfind.py): dump da WRAM inteira em savestates com valores de
tela CONHECIDOS (lidos via Game.info_screen('fleet') + screenshot), interseccao
dos enderecos que casam o valor em TODOS os savestates.

Resultado desta sessao (18/08, ETAPA 7): ver CALIBRATION.md secao ETAPA 7.
  - Avail[MD100] CONFIRMADO: 0x2840 (unico candidato ja no par de 2 estados,
    reconfirmado em 4 estados: eval_single_2000_lv5=6, probe_hub_open_sa=5,
    _etapa7_md100x3=6, _buy_entregue=6).
  - Order[MD100] CANDIDATO (nao reconfirmado num 2o estado com Order!=0):
    0x28bc = 3 em _etapa7_md100x3.state (unico candidato num raio de 256 bytes
    de 0x2840 entre os 60 enderecos que batem 0->3 nos dois primeiros estados).
  - In Use[MD100] NAO ENCONTRADO: mesmo cruzando 4 savestates (eval_single,
    probe_hub_open_sa com In Use=1, _etapa7_md100x3, _buy_entregue) sobram 157
    candidatos a 0->1 na WRAM inteira — nenhum perto de 0x2840/0x28bc.
    Hipotese nao testada: "In Use" pode ser CALCULADO na hora (contagem de
    rotas ativas que referenciam o modelo) em vez de armazenado num contador
    proprio, o que explicaria a ausencia de um endereco fixo estavel.
  - A340 (2o modelo, _buy_entregue.state): Avail=1 aparenta estar em 0x284d/
    0x284e (nao confirmado com 2o estado do A340) — o stride entre modelos
    NAO e fixo (0x284d - 0x2840 = 0x0d, nao bate com nenhuma potencia de 2
    obvia), entao NAO da para generalizar "endereco do modelo N = base + N*stride"
    sem mais dados.

NAO CALIBRADO O SUFICIENTE PARA build_state ainda. Proximos passos:
  1. Conseguir savestate com In Use=2 (2 rotas do mesmo modelo) para reduzir
     os 157 candidatos por eliminacao.
  2. Confirmar Order com 2o estado (frota com Order != 0 e != 3).
  3. Mapear o stride real da tabela multi-modelo (precisa >=3 modelos
     possuidos simultaneamente, ou dump byte a byte da regiao 0x2800-0x2a00
     anotado contra a tela).
  4. Coluna Load(%) da tela de rotas: NEM COMECADO nesta sessao.
"""

import pathlib

from bridge import BizHawkBridge

WRAM = 0x20000
CHUNK = 2048

STATES_DIR = pathlib.Path(__file__).parent.parent / "states"

# (nome do savestate, In Use, Avail, Order) lido na tela Info->fleet (MD100, 1a linha)
KNOWN = [
    ("eval_single_2000_lv5.state", 0, 6, 0),
    ("probe_hub_open_sa.state", 1, 5, 0),
    ("_etapa7_md100x3.state", 0, 6, 3),
    ("_buy_entregue.state", 0, 6, 0),  # MD100 e a 1a linha; A340 e a 2a (0,1,0)
]


def dump(b):
    parts = []
    for off in range(0, WRAM, CHUNK):
        parts.append(b.read_ram(off, min(CHUNK, WRAM - off), domain="WRAM"))
    return b"".join(parts)


def main():
    b = BizHawkBridge()
    dumps = []
    for name, *_ in KNOWN:
        b.load(str(STATES_DIR / name))
        b.advance(30)
        dumps.append(dump(b))

    def candidates(field_idx):
        vals = [row[field_idx] for row in KNOWN]
        return [i for i in range(WRAM) if all(d[i] == v for d, v in zip(dumps, vals))]

    inuse = candidates(1)
    avail = candidates(2)
    order = candidates(3)
    print(f"In Use candidates (4-state intersect): {len(inuse)}")
    print(f"Avail candidates (4-state intersect): {len(avail)} -> {[hex(x) for x in avail]}")
    print(f"Order candidates (4-state intersect): {len(order)} -> {[hex(x) for x in order]}")


if __name__ == "__main__":
    main()
