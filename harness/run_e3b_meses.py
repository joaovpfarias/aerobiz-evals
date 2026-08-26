"""ETAPA 3b: bateria de leituras da tela "Negotiations should take N months."

Quatro casos, todos a partir do MESMO savestate (_e3b_base), mesma cidade:
  (0,0) 1 slot | (0,1) 1 slot | (1,1) 1 slot | (0,0) 5 slots
Nenhum confirma a negociacao (B ao final) — custo zero, e o proprio script
confere caixa e funcionarios livres no fim de cada caso.
"""
import sys, pathlib, json, subprocess

HERE = pathlib.Path(__file__).resolve().parent
PY = sys.executable

CASOS = [
    ("m_e00_s1", "NA14", 0, 0, 0),
    ("m_e01_s1", "NA14", 0, 1, 0),
    ("m_e11_s1", "NA14", 1, 1, 0),
    ("m_e00_s5", "NA14", 0, 0, 4),
]

out = []
for pref, cid, r, c, n in CASOS:
    cmd = [PY, str(HERE / "probe_slots_lever.py"), cid, str(r), str(c), str(n),
           "Right", pref, "--meses"]
    p = subprocess.run(cmd, capture_output=True, text=True)
    linha = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else ""
    try:
        d = json.loads(linha)
    except Exception:
        d = {"erro": linha or p.stderr[-500:]}
    d["pref"] = pref
    out.append(d)
    print(json.dumps(d, default=str), flush=True)

print("=== RESUMO ===", flush=True)
for d in out:
    print(json.dumps({k: d.get(k) for k in
                      ("pref", "cel", "meses_tb", "meses_tb_repetido", "meses_shot",
                       "no_menu", "livres_depois", "erro")}, default=str), flush=True)
