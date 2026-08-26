"""ETAPA 1-TravaIPC: prova de aceite. Papel A trabalha, papel B recusa.

  python _prova_trava_ipc.py A    # segura a trava e faz PING/INFO reais
  python _prova_trava_ipc.py B    # tenta abrir a ponte, deve RECUSAR
"""
import sys
import time

import bridge


def papel_a(segundos=12.0):
    b = bridge.BizHawkBridge(timeout=8)
    print("A: trava adquirida, pid=%d" % __import__("os").getpid(), flush=True)
    fim = time.time() + segundos
    n = 0
    while time.time() < fim:
        n += 1
        print("A: ping#%d frame=%d" % (n, b.ping()), flush=True)
        time.sleep(0.7)
    print("A: FIM ok, %d pings sem erro" % n, flush=True)


def papel_b():
    try:
        b = bridge.BizHawkBridge(timeout=6)
        print("B: PROBLEMA - abriu a ponte; ping=%d" % b.ping(), flush=True)
        return 1
    except bridge.BridgeBusyError as exc:
        print("B: RECUSADO como esperado ->\n%s" % exc, flush=True)
        return 0
    except Exception as exc:  # noqa: BLE001
        print("B: erro inesperado %r" % exc, flush=True)
        return 2


if __name__ == "__main__":
    papel = (sys.argv[1] if len(sys.argv) > 1 else "A").upper()
    sys.exit(papel_a() if papel == "A" else papel_b())
