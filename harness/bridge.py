"""Cliente Python da ponte file-IPC com o BizHawk (ver bridge.lua para o protocolo)."""

import atexit
import os
import pathlib
import sys
import threading
import time

try:
    import msvcrt
except ImportError:  # nao-Windows: sem trava de arquivo
    msvcrt = None


class BridgeError(RuntimeError):
    pass


class BridgeBusyError(BridgeError):
    """Outro processo ja segura a ponte deste IPC."""


# --- trava de instancia unica -------------------------------------------------
# Mecanismo: lockfile por diretorio IPC, byte 0 travado com msvcrt.locking
# (LK_NBLCK). Escolhido porque o SO libera a trava quando o processo morre —
# crash nao deixa trava presa e nao exige checagem racy de PID vivo; a
# identidade (PID/argv/hora) fica fora da faixa travada, a partir do byte 1,
# para o segundo processo poder ler e dizer QUEM segura em vez de corromper.

_LOCKS = {}  # ipc resolvido (lower) -> fd aberto, mantido ate o fim do processo
_LOCKS_GUARD = threading.Lock()


def _lock_holder_info(path):
    try:
        with open(path, "rb") as f:
            f.seek(1)
            txt = f.read(1024).decode("ascii", "replace").strip("\x00 \r\n")
        return txt or "(sem identificacao gravada)"
    except OSError as exc:
        return f"(nao consegui ler {path}: {exc})"


def acquire_bridge_lock(ipc):
    """Trava o IPC para este processo. Reentrante: 2a chamada no mesmo processo
    (o mesmo IPC) e no-op, porque travas de faixa no Windows sao por handle e
    varios modulos constroem seu proprio BizHawkBridge."""
    if msvcrt is None or os.environ.get("AEROBIZ_BRIDGE_NOLOCK") == "1":
        return None
    key = str(pathlib.Path(ipc).resolve()).lower()
    with _LOCKS_GUARD:
        if key in _LOCKS:
            return _LOCKS[key]
        path = pathlib.Path(ipc) / "bridge.lock"
        fd = os.open(str(path), os.O_RDWR | os.O_CREAT | os.O_BINARY, 0o666)
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        except OSError:
            os.close(fd)
            raise BridgeBusyError(
                f"ponte IPC ocupada: {path}\n"
                f"  segurada por: {_lock_holder_info(path)}\n"
                f"  este processo: pid={os.getpid()} {' '.join(sys.argv[:3])}\n"
                "  rode uma coisa de cada vez (ou AEROBIZ_BRIDGE_NOLOCK=1 para ignorar)."
            )
        info = "pid=%d started=%s cmd=%s" % (
            os.getpid(),
            time.strftime("%Y-%m-%d %H:%M:%S"),
            " ".join(sys.argv[:4]),
        )
        payload = info.encode("ascii", "replace")[:1023] + b"\n"
        os.lseek(fd, 1, os.SEEK_SET)
        os.write(fd, payload)
        # Sem truncar, o rabo do dono ANTERIOR (argv mais longo) sobrevive e a
        # recusa nomearia dois donos colados. O byte 0 (travado) e preservado.
        try:
            os.ftruncate(fd, 1 + len(payload))
        except OSError:
            pass
        _LOCKS[key] = fd
        atexit.register(_release_bridge_lock, key)
        return fd


def release_bridge_lock(ipc=None):
    """Solta a trava deste processo. Use antes de entregar a ponte a um FILHO
    (run_eval -> pilot.py): a trava e por processo, o filho precisa poder pegar."""
    if msvcrt is None:
        return
    ipc = ipc or (pathlib.Path(__file__).parent / "ipc")
    _release_bridge_lock(str(pathlib.Path(ipc).resolve()).lower())


def _release_bridge_lock(key):
    with _LOCKS_GUARD:
        fd = _LOCKS.pop(key, None)
    if fd is None:
        return
    try:
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    except OSError:
        pass
    try:
        os.close(fd)
    except OSError:
        pass


REPLACE_RETRIES = 0  # quantas vezes o retry abaixo teve que agir nesta sessao
SCREENSHOTS_OK = 0   # screenshots bem-sucedidos neste processo (ver .screenshot)


def _replace_retry(src, dst, attempts=40, delay=0.025):
    """os.replace com retry curto: no Windows o proprio bridge.lua abre cmd.txt
    a cada frame (io.open sem share-delete), e antivirus/indexador tambem
    seguram o arquivo por instantes -> PermissionError [WinError 5] transitorio."""
    global REPLACE_RETRIES
    last = None
    for i in range(attempts):
        try:
            os.replace(src, dst)
            if i:
                REPLACE_RETRIES += i
                print(f"[ponte] os.replace cedeu apos {i} retry(s) "
                      f"(total na sessao: {REPLACE_RETRIES})", file=sys.stderr, flush=True)
            return
        except PermissionError as exc:
            last = exc
            time.sleep(delay)
    raise BridgeError(f"nao consegui publicar {dst} apos {attempts} tentativas: {last}")


class BizHawkBridge:
    def __init__(self, ipc_dir=None, timeout=30.0):
        self.ipc = pathlib.Path(ipc_dir or pathlib.Path(__file__).parent / "ipc")
        self.ipc.mkdir(parents=True, exist_ok=True)
        acquire_bridge_lock(self.ipc)
        self.cmd = self.ipc / "cmd.txt"
        self.cmdtmp = self.ipc / "cmd.tmp"
        self.resp = self.ipc / "resp.txt"
        self.timeout = timeout
        self._n = 0

    def _call(self, op, *args, timeout=None):
        self._n += 1
        cid = f"{os.getpid()}-{self._n}"
        try:
            self.resp.unlink()
        except FileNotFoundError:
            pass
        self.cmdtmp.write_text("\n".join([cid, op, *map(str, args)]) + "\n", encoding="ascii")
        _replace_retry(self.cmdtmp, self.cmd)
        deadline = time.time() + (timeout or self.timeout)
        while time.time() < deadline:
            if self.resp.exists():
                try:
                    lines = self.resp.read_text(encoding="ascii", errors="replace").splitlines()
                except OSError:
                    time.sleep(0.02)
                    continue
                if lines and lines[0] == cid:
                    try:
                        self.resp.unlink()
                    except OSError:
                        pass
                    if len(lines) > 1 and lines[1] == "OK":
                        return lines[2:]
                    raise BridgeError(f"{op}: " + (" | ".join(lines[2:]) or "ERR"))
            time.sleep(0.02)
        raise BridgeError(
            f"timeout esperando {op} — EmuHawk esta aberto com --lua=bridge.lua? IPC: {self.ipc}"
        )

    @staticmethod
    def _abspath(path):
        return str(pathlib.Path(path).resolve()).replace("\\", "/")

    def ping(self):
        return int(self._call("PING")[0])

    def info(self):
        p = self._call("INFO")
        # token = dono do IPC (bridge.lua). Ausente em EmuHawk aberto com uma
        # bridge.lua antiga — nesse caso vem "" e quem confere trata como falha.
        return {"rom": p[0], "hash": p[1], "frame": int(p[2]),
                "token": p[3] if len(p) > 3 else ""}

    def screenshot(self, path=None):
        # SCREENSHOTS_OK: quantos sobreviveram nesta sessao. Era "vibe" ate a
        # ETAPA 1-PonteLonga; com o numero da para dizer se a ponte aguenta.
        global SCREENSHOTS_OK
        path = self._abspath(path or (self.ipc / "screen.png"))
        self._call("SCREENSHOT", path)
        SCREENSHOTS_OK += 1
        return path

    def press(self, *buttons, hold=5, wait=8):
        """Botoes SNES: A B X Y Up Down Left Right Start Select L R"""
        self._call("PRESS", ",".join(buttons), hold, wait, timeout=self.timeout + (hold + wait) / 30)

    def advance(self, frames=1):
        self._call("ADVANCE", frames, timeout=self.timeout + frames / 30)

    def save(self, path):
        self._call("SAVE", self._abspath(path))

    def load(self, path):
        self._call("LOAD", self._abspath(path))

    def read_ram(self, addr, size, domain="WRAM"):
        hexs = self._call("RAM", domain, f"{addr:x}", size)[0]
        return bytes.fromhex(hexs)

    def write_ram(self, addr, data, domain="WRAM"):
        if isinstance(data, int):
            data = bytes([data])
        self._call("WRITE", domain, f"{addr:x}", bytes(data).hex())

    def speed(self, pct):
        self._call("SPEED", pct)

    # --- execucao em lote (uma ida-e-volta para a sequencia inteira) ---
    def batch(self, cmds, extra_frames=0):
        """cmds: lista de strings 'OP|arg|arg'. Use os helpers seq_* para montar."""
        return self._call("BATCH", *cmds, timeout=self.timeout + extra_frames / 30 + len(cmds) * 0.2)

    @staticmethod
    def seq_press(*buttons, hold=5, wait=12, times=1):
        return [f"PRESS|{','.join(buttons)}|{hold}|{wait}"] * times

    @staticmethod
    def seq_advance(frames):
        return [f"ADVANCE|{frames}"]

    @staticmethod
    def seq_write(addr, value, domain="WRAM"):
        return [f"WRITE|{domain}|{addr:x}|{bytes([value]).hex()}"]
