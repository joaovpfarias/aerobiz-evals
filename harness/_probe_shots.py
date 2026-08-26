"""Conta screenshots ate a falha. Uso: _probe_shots.py N tag"""
import sys, os, time, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
os.environ.setdefault("AEROBIZ_BRIDGE_NOLOCK", "1")
from PIL import Image
from bridge import BizHawkBridge, BridgeError

n = int(sys.argv[1]); tag = sys.argv[2] if len(sys.argv) > 2 else "x"
b = BizHawkBridge(timeout=20)
ok = 0; falhas = []
t0 = time.time()
for i in range(n):
    try:
        p = b.screenshot()
        Image.open(p).convert("RGB")
        ok += 1
    except (BridgeError, OSError) as e:
        falhas.append((i, str(e)[:140]))
        if len(falhas) >= 5:
            break
print(f"[{tag}] ok={ok}/{n} falhas={len(falhas)} em {time.time()-t0:.0f}s")
for i, e in falhas:
    print(f"  falha na tentativa #{i}: {e}")
