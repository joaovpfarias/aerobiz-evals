"""Wait for baselines and generate REFERENCIA.md."""
import subprocess
import pathlib
import time
import sys
import json

AQUI = pathlib.Path(__file__).resolve().parent
LOGS_DIR = AQUI.parent / "logs"
BASELINES_DIR = LOGS_DIR / "baselines"
PY = sys.executable

def get_completed_runs():
    """Find most recent completed random and greedy runs."""
    random_run = None
    greedy_run = None

    for run_dir in sorted(LOGS_DIR.glob("eval_random_NA13_*"), key=lambda p: p.name, reverse=True):
        if (run_dir / "resumo.json").exists():
            random_run = run_dir
            break

    for run_dir in sorted(LOGS_DIR.glob("eval_greedy_NA13_*"), key=lambda p: p.name, reverse=True):
        if (run_dir / "resumo.json").exists():
            greedy_run = run_dir
            break

    return random_run, greedy_run

def main():
    print("[finalize] Waiting for both baselines to complete...")
    max_wait = 10800  # 3 hours
    start = time.time()

    while time.time() - start < max_wait:
        r_run, g_run = get_completed_runs()

        if r_run and g_run:
            print(f"[finalize] Both completed!")
            print(f"  Random: {r_run.name}")
            print(f"  Greedy: {g_run.name}")

            # Run the generator
            print("[finalize] Generating REFERENCIA.md...")
            result = subprocess.run(
                [PY, str(AQUI / "gen_referencia_fixed.py")],
                cwd=str(AQUI)
            )

            if result.returncode == 0:
                ref_file = BASELINES_DIR / "REFERENCIA.md"
                if ref_file.exists():
                    print(f"[finalize] SUCCESS: {ref_file}")
                    return 0
            else:
                print(f"[finalize] Generator failed (exit {result.returncode})")
                return 1

        # Report progress
        if r_run:
            stats = json.loads((r_run / "stats.json").read_text(encoding="utf-8")) if (r_run / "stats.json").exists() else {}
            print(f"[finalize] Random: {stats.get('turnos', '?')}/12")
        else:
            print(f"[finalize] Random: not yet started")

        if g_run:
            stats = json.loads((g_run / "stats.json").read_text(encoding="utf-8")) if (g_run / "stats.json").exists() else {}
            print(f"[finalize] Greedy: {stats.get('turnos', '?')}/12")
        else:
            print(f"[finalize] Greedy: not yet started")

        time.sleep(120)

    print(f"[finalize] TIMEOUT after {max_wait/3600:.1f} hours")
    return 1

if __name__ == "__main__":
    sys.exit(main())
