# Harness — Aerobiz Evals

Ponte BizHawk↔Python por file-IPC + agente jogador via OpenCode (free models).
Contexto: [../VIABILIDADE.md](../VIABILIDADE.md) | [../PLANO_EXECUCAO.md](../PLANO_EXECUCAO.md)

## Setup (1x)

1. BizHawk 2.11.1 em `%USERPROFILE%\tools\BizHawk-2.11.1\`
2. ROM do usuario em `../roms/` (ver `../roms/README.md`)
3. Python: Anaconda (`<python>`) — usa so stdlib + requests

## Uso

```powershell
# 1. Lancar emulador com a ponte
.\launch.ps1 -Rom "..\roms\Aerobiz Supersonic (USA).sfc"

# 2. Dirigir pelo cockpit (F0)
python cli.py ping                  # smoke test da ponte
python cli.py shot                  # screenshot -> ipc/screen.png
python cli.py press Start           # aperta botao
python cli.py seq "Down*3 A"        # macro rapida
python cli.py save ..\states\t01.state
python cli.py ram 0 16              # le 16 bytes do WRAM em 0x0000

# 3. Turno do agente (estado extraido por vision -> JSON)
python agent.py turn --state ..\logs\run_f0\state_t01.json --run ..\logs\run_f0

# Bake-off dos modelos free
python probe_models.py
```

## Arquivos

| Arquivo | Papel |
|---|---|
| `bridge.lua` | Lado BizHawk (carregar via `--lua=`); protocolo file-IPC em `ipc/` |
| `bridge.py` | Cliente Python da ponte |
| `cli.py` | Cockpit manual (F0) |
| `opencode_client.py` | Chat OpenAI-compat com a API OpenCode Go (+ extract_json) |
| `schema.py` | Action space semantico + validacao |
| `agent.py` | Loop de turno: diario + decisao + log JSONL |
| `baselines.py` | Aleatoria-legal e gulosa (mesma interface do agente) |
| `probe_models.py` | Bake-off dos modelos `-free` |
| `state_template.json` | Template do estado v0 preenchido pelo extrator no F0 |
| `prova_endturn.py` | **Aceite do fim de turno**: N `end_turn` seguidos, contador da RAM x data lida dos pixels x caixa. `python prova_endturn.py 6 [savestate] [tag]` |
| `probe_endturn_caixa.py` | Por que o detector antigo ("o caixa mudou") errava: le caixa/contador antes, durante e depois da cadeia de relatorios |
| `probe_demand.py` | A caixa (YES NO) de patrocinio que trava o fim de turno (`hunt`/`walk`/`b`/`right`/`no`/`yes`) — o `A` ali custa −372.000K |
| `prova_yesno.py` | Prova dirigida: atravessar a caixa de decisao sem pagar |
| `test_dismiss_yesno.py` | Teste offline (ponte-duble, sem emulador): com a caixa (YES NO) na tela o `dismiss_to_menu` nao aperta A; contraprova de que o A sobrevive nas telas de noticia |

## Fluxo F0 (semi-manual)

```
BizHawk roda o jogo -> cli.py shot -> Claude le o PNG e preenche state_tNN.json
-> agent.py turn (modelo free decide + atualiza diario) -> Claude executa acoes
via cli.py press/seq -> proximo trimestre -> repete
```

O objetivo do F0 nao e automacao: e responder legibilidade/coerencia/tensao e
produzir o inventario de telas que vira `macros.py` no F1.
