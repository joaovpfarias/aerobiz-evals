"""Monitor baseline runs and wait for completion."""
import time
import json
import pathlib
from datetime import datetime

LOGS_DIR = pathlib.Path(__file__).parent.parent / "logs"

def get_latest_random():
    runs = sorted(LOGS_DIR.glob("eval_random_NA13_*"), key=lambda p: p.name, reverse=True)
    return runs[0] if runs else None

def get_latest_greedy():
    runs = sorted(LOGS_DIR.glob("eval_greedy_NA13_*"), key=lambda p: p.name, reverse=True)
    return runs[0] if runs else None

def has_resumo(run_dir):
    return (run_dir / "resumo.json").exists() if run_dir else False

def read_stats(run_dir):
    sp = run_dir / "stats.json"
    if sp.exists():
        return json.loads(sp.read_text(encoding="utf-8"))
    return {}

def main():
    print(f"[{datetime.now().isoformat()}] Monitoring baselines...")
    
    while True:
        r_run = get_latest_random()
        g_run = get_latest_greedy()
        
        r_done = has_resumo(r_run)
        g_done = has_resumo(g_run)
        
        r_stats = read_stats(r_run) if r_run else {}
        g_stats = read_stats(g_run) if g_run else {}
        
        print(f"[{datetime.now().isoformat()}] Random: {r_run.name if r_run else 'N/A'} turns={r_stats.get('turnos', 0)}/12 done={r_done}")
        print(f"[{datetime.now().isoformat()}] Greedy: {g_run.name if g_run else 'N/A'} turns={g_stats.get('turnos', 0)}/12 done={g_done}")
        
        if r_done and g_done:
            print(f"[{datetime.now().isoformat()}] Both baselines complete!")
            print(f"Random: {r_run}")
            print(f"Greedy: {g_run}")
            break
        
        time.sleep(30)

if __name__ == "__main__":
    main()
