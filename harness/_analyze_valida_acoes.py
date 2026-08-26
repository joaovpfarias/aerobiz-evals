"""Parser ad-hoc ETAPA 9-Validar: junta turns.jsonl (decisao) + .log (execucao)."""
import json
import re
import sys
import pathlib

run_dir = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "../logs/VALIDA_ACOES3")
log_path = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "../logs/VALIDA_ACOES3.log")

turns_path = run_dir / "turns.jsonl"
chosen = {}  # action -> count
models_used = set()
parse_errors = 0
n_turns = 0
for line in turns_path.read_text(encoding="utf-8").splitlines():
    d = json.loads(line)
    n_turns += 1
    models_used.add(d.get("model_respondeu"))
    if d.get("parse_error"):
        parse_errors += 1
    for act in d.get("actions_valid", []):
        chosen[act["action"]] = chosen.get(act["action"], 0) + 1

WITNESS_RE = re.compile(
    r"(caixa \d+K -> \d+K \([+-]?\d+K\))"
    r"|(funcionarios? livres \d+ -> \d+)"
    r"|(livres \d+ -> \d+)"
    r"|(rota \S+->\S+: aviao \d+)"          # open_route: aeronave alocada
    r"|(adjust_route\(\S+\): .+)"            # adjust_route: notas de aba (Flts/Fare)
)
LINE_RE = re.compile(r"\[t(\d+)\]\s+(\w+)\s+->\s+(OK|FALHA):\s*(.*)")

executed_ok = {}
executed_fail = {}
witnessed = {}
no_witness_ok = {}

if log_path.exists():
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = LINE_RE.search(line)
        if not m:
            continue
        t, action, status, detail = m.groups()
        if status == "OK":
            executed_ok[action] = executed_ok.get(action, 0) + 1
            wm = WITNESS_RE.search(detail)
            if wm:
                witnessed[action] = witnessed.get(action, 0) + 1
                witnessed.setdefault(action + "__examples", []).append(wm.group(0))
            else:
                no_witness_ok[action] = no_witness_ok.get(action, 0) + 1
        else:
            executed_fail[action] = executed_fail.get(action, 0) + 1

print("turnos logados (decisoes):", n_turns)
print("modelo(s) que respondeu:", models_used)
print("parse_error count:", parse_errors)
print()
print("acoes ESCOLHIDAS pelo modelo (coluna a):")
for k, v in sorted(chosen.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")
print()
print("acoes EXECUTADAS OK pelo harness (coluna b) / FALHA / com testemunha:")
all_types = set(executed_ok) | set(executed_fail)
for k in sorted(all_types):
    ex = [s for s in witnessed.get(k + "__examples", [])][:2]
    print(f"  {k}: ok={executed_ok.get(k,0)} falha={executed_fail.get(k,0)} "
          f"com_testemunha={witnessed.get(k,0)} sem_testemunha={no_witness_ok.get(k,0)} "
          f"exemplos={ex}")

verified_types = sorted(k for k in witnessed if not k.endswith("__examples") and witnessed[k] > 0)
print()
print("TIPOS COM EFEITO VERIFICADO (testemunha):", verified_types, "=", len(verified_types))
