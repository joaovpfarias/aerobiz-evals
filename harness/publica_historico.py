"""Publica no Logfire as partidas que ja estao em disco.

O evento de partida (`_publica_no_logfire`) so passou a existir hoje, entao o
Logfire nasceria sem historico. Este script le os resumo.json que ja foram
escritos e emite um evento por partida — sem tocar no emulador.

Idempotencia: NAO ha. Rodar duas vezes publica duas vezes. Por isso o script
imprime o que vai mandar e exige --confirmar.
"""

import glob
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import obs  # noqa: E402
import run_eval  # noqa: E402

LOGS = pathlib.Path(__file__).parent.parent / "logs"


def main():
    alvos = sorted(LOGS.glob("eval_*/resumo.json"))
    print(f"partidas com resumo.json: {len(alvos)}")
    linhas = []
    for p in alvos:
        try:
            r = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"  IGNORADA {p.parent.name}: {e}")
            continue
        linhas.append((p, r))
        print(f"  {p.parent.name}: turnos={r.get('turnos_rodados')} "
              f"subst={r.get('taxa_efeito_substantivas_pct')}% "
              f"com_wait={r.get('taxa_efeito_verificado_pct')}%")
    if "--confirmar" not in sys.argv:
        print("\n(nada enviado — repita com --confirmar)")
        return 0
    for p, r in linhas:
        run_eval._publica_no_logfire(r, p.parent)
    destino = obs.PROJETO_ESPERADO or "o projeto do arquivo de credenciais local"
    print(f"\n{len(linhas)} partidas publicadas em {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
