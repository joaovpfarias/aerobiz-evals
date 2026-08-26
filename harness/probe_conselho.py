"""ETAPA 11-Conselho: reinvestigacao a fundo de r1c2 (reuniao/conselho).

Mapeamento de 17/08 classificou como LEITURA + submenu de 4 topicos
(New Rtes / Adjust Rtes / Planes / Businesses) sem drill-down. Usuario indica
que HA DECISAO ali. Este probe entra em cada um dos 4 topicos, confere se e
so texto ou se aparece prompt executavel (YES/NO ou similar), e se os textos
mudam entre os 4 topicos / entre "conselheiros".

Nunca aperta as cegas: cada passo tira screenshot e le read_cash_k antes de
prosseguir. Sai por savestate de guarda, nunca B repetido as cegas se cash
mudou.
"""
import sys
import time

sys.path.insert(0, ".")

from PIL import Image

from bridge import BizHawkBridge
from executor import Executor
from world import at_main_menu_img, read_cash_k, wait_text, yesno_prompt

BASE_STATE = "../states/eval_single_2000_lv5.state"
GUARD = "../states/_conselho_guard.state"


def shot(g, name):
    p = g.shot(name)
    print(f"  [shot] {name} -> {p}")
    return p


def cur_img(b):
    return Image.open(b.screenshot()).convert("RGB")


def main():
    b = BizHawkBridge()
    ex = Executor(b)
    g = ex.g

    print(f"== carregando baseline {BASE_STATE} ==")
    b.load(BASE_STATE)
    b.advance(90)
    assert ex._ensure_menu(), "nao chegou ao menu principal a partir do baseline"

    cash0 = read_cash_k(b)
    print(f"cash baseline = {cash0}K")
    b.save(GUARD)
    print(f"guard salvo em {GUARD}")

    # --- abre a reuniao ---
    print("\n== abrindo r1c2 (meeting) ==")
    g.open_cmd("meeting")
    wait_text(b)
    shot(g, "cons_00_open")

    # cicla as dicas de tutorial ate estabilizar no submenu de topicos.
    # Cada A avanca 1 mensagem; capturamos ate 12 passos ou ate a tela parar
    # de mudar (submenu com 4 opcoes = grade fixa, nao textbox).
    seen_hashes = []
    for i in range(12):
        img = cur_img(b)
        h = None
        import hashlib
        h = hashlib.md5(img.tobytes()).digest()
        seen_hashes.append(h)
        shot(g, f"cons_tip_{i:02d}")
        cash_i = read_cash_k(b)
        if cash_i != cash0:
            print(f"!!! CASH MUDOU no passo {i}: {cash0} -> {cash_i} — PARANDO, carregando guard")
            b.load(GUARD)
            return
        # se as duas ultimas imagens sao identicas, provavelmente chegamos
        # a uma tela estavel (submenu ou prompt) — para de apertar A cego.
        if len(seen_hashes) >= 2 and seen_hashes[-1] == seen_hashes[-2]:
            print(f"  tela estabilizou no passo {i}")
            break
        b.press("A", hold=5, wait=30)
        wait_text(b)
        b.advance(60)

    shot(g, "cons_submenu_candidato")
    cash_sub = read_cash_k(b)
    print(f"cash apos ciclar dicas = {cash_sub}K")

    # ================= EXPLORA OS 4 TOPICOS =================
    # Hipotese da doc de 17/08: submenu horizontal New Rtes/Adjust Rtes/Planes/
    # Businesses. Cursor comeca no topico 0. Testamos cada um: A entra, tira
    # screenshot(s) do conteudo, procura yesno_prompt, sai com B de volta ao
    # submenu, Right para o proximo topico.
    topics = ["New_Rtes", "Adjust_Rtes", "Planes", "Businesses"]
    veredito = {}

    for idx, topic in enumerate(topics):
        print(f"\n== TOPICO {idx}: {topic} ==")
        cash_before = read_cash_k(b)
        shot(g, f"cons_topic{idx}_{topic}_cursor")

        b.press("A", hold=5, wait=30)
        wait_text(b)
        b.advance(80)
        img1 = cur_img(b)
        shot(g, f"cons_topic{idx}_{topic}_s0")

        yn = yesno_prompt(img1)
        print(f"  yesno_prompt apos entrar? {yn}")

        # cicla mais mensagens dentro do topico (ate 8), sempre monitorando
        # cash e procurando prompt YES/NO.
        prev_hash = None
        found_yesno = yn
        for j in range(8):
            import hashlib
            cur_hash = hashlib.md5(cur_img(b).tobytes()).digest()
            cash_j = read_cash_k(b)
            if cash_j != cash_before:
                print(f"  !!! CASH MUDOU dentro do topico {topic} (passo {j}): {cash_before}->{cash_j}")
            if prev_hash == cur_hash:
                print(f"  topico {topic} estabilizou no sub-passo {j}")
                break
            prev_hash = cur_hash
            img_j = cur_img(b)
            yn_j = yesno_prompt(img_j)
            if yn_j:
                found_yesno = True
                print(f"  !!! YES/NO detectado dentro de {topic} no sub-passo {j}")
                shot(g, f"cons_topic{idx}_{topic}_YESNO_{j}")
                break
            b.press("A", hold=5, wait=30)
            wait_text(b)
            b.advance(60)
            shot(g, f"cons_topic{idx}_{topic}_s{j+1}")

        cash_after_topic = read_cash_k(b)
        veredito[topic] = {
            "yesno_visto": found_yesno,
            "cash_before": cash_before,
            "cash_after": cash_after_topic,
        }
        print(f"  RESUMO {topic}: yesno={found_yesno} cash {cash_before}->{cash_after_topic}")

        if found_yesno:
            print(f"  !!! NAO vou confirmar as cegas. Recarregando guard para preservar estado.")
            b.load(GUARD)
            b.advance(90)
            # reabre a reuniao ate o submenu de novo para continuar a exploracao
            g.open_cmd("meeting")
            wait_text(b)
            for _ in range(12):
                b.press("A", hold=5, wait=30)
                wait_text(b)
                b.advance(60)
                img_chk = cur_img(b)
                # tenta reconhecer que chegamos no submenu comparando com o
                # screenshot cons_submenu_candidato capturado antes
                # (comparacao aproximada nao critica aqui; seguimos por N passos fixos)
            shot(g, f"cons_topic{idx}_pos_reload")
            # navega de volta para a posicao do proximo topico
            for _ in range(idx):
                b.press("Right", hold=3, wait=15)
                b.advance(30)
        else:
            # sai do conteudo do topico (B) de volta ao submenu de 4 topicos
            b.press("B", hold=5, wait=30)
            wait_text(b)
            b.advance(60)
            shot(g, f"cons_topic{idx}_{topic}_back")
            # move cursor para o proximo topico
            if idx < len(topics) - 1:
                b.press("Right", hold=3, wait=15)
                b.advance(30)
                shot(g, f"cons_pre_topic{idx+1}")

    print("\n=== VEREDITO POR TOPICO ===")
    for t, v in veredito.items():
        print(f"  {t}: {v}")

    # sai da reuniao com seguranca: recarrega o guard (nao aperta B as cegas
    # em sequencia longa sem saber onde estamos)
    b.load(GUARD)
    b.advance(90)
    ok_menu = ex._ensure_menu()
    print(f"\nrecarregado guard, menu principal? {ok_menu}")
    cash_final = read_cash_k(b)
    print(f"cash final (guard reload) = {cash_final}K (baseline era {cash0}K)")


if __name__ == "__main__":
    main()
