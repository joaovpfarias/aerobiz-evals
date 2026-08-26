# ETAPA 6-Reversos: Status da Implementação (18/08/2026)

## Objetivo
Implementar e calibrar as 3 ações reversas (destrutivas) do Aerobiz Supersonic:
1. **(a) return_slots** (r0c2, aba Return)
2. **(b) close_hub** (r1c0, aba Close)  
3. **(c) sell_aircraft** (r0c3, fabricante "World Lease")

## Status Atual

### (a) return_slots — EM SUPPORTED, MAS GATE FRACO ⚠️
**Status**: JÁ IMPLEMENTADA em `executor.py::_do_return_slots` (linhas 1070-1163)

**O que funciona**:
- Navegação para Return (Down 1x, Right 2x)
- Verificação que Return está destacado (pixel check)
- Navegação do mapa via `point_cursor_at_world`
- Retorno ao menu principal

**O que está fraco (BLOQUEIO)**:
- Oracle de efeito: só checa "Return foi selecionado + voltamos ao menu"
- Não mede a redução real de slots (nenhuma verificação de `world.cities_with_slots`)
- False-positive possível: navegação corrompida ainda retorna True

**Próximos passos**:
1. Ler `world.cities_with_slots` ANTES da ação
2. Ler APÓS da ação (cuidado: cidade sob cursor lê como 0)
3. Verificar que slot count caiu em 1 para a cidade alvo
4. Se não caiu, restaurar guard e reportar falha

**Savestates úteis**:
- `probe_hub_open_sa.state`: Washington tem slots negociados (podia testar return aí)

---

### (b) close_hub — RESOLVIDO 18/08 EM ETAPA 12-HubsCompleto ✅

Ver `STATUS.md` (entrada "ETAPA 12-HubsCompleto"), `ACTION_SPACE.md` (seção
"Aba Close" sob r1c0) e `CALIBRATION.md` (`_do_close_hub`). Resumo: a
navegação Left estava errada (é Down 1x + Right 2x); faltava uma 2ª
pergunta YES/NO na cadeia; o oracle de "funcionário livre" era sempre falso
e desfazia closes que tinham funcionado. Está em `pilot.SUPPORTED`.

<details><summary>Diagnóstico original (17/08), mantido como histórico</summary>

### (b) close_hub — IMPLEMENTAÇÃO INCOMPLETA 🔴 (HISTÓRICO, ver acima)
**Status**: IMPLEMENTADA mas BLOQUEADA pela falta de validação de navegação

**Código novo em `executor.py::_do_close_hub` (linhas 1604-1722)**:
- Replica estrutura de `_do_open_hub`
- Tenta navegar com 1x Left para chegar à Close
- Verifica com `staff_action_is_bid(img)` que Close está destacado

**Problemas críticos (feedback do advisor)**:

1. **Navegação não validada (guess Left)**
   - Hipótese: Close é à esquerda de Open (similar a Return ←Left← Bid em r0c2)
   - Realidade: return_slots navega Down+Right para chegar em (1,2)
   - Solução: PROBE READ-ONLY primeiro (4 screenshots, zero A presses)

2. **Effect gate invertida** ⚠️ PERIGOSA
   - Código requer: `livres_depois < livres_antes` (staff saiu)
   - Problema: close_hub pode NÃO despachar ninguém (ação é caixa apenas)
   - Se staff não sair, código volta False e `_restore_guard()` oculta o dano
   - Result: HUB FECHA MAS HARNESS REPORTA FALHA (mentira)

3. **Precondição errada**
   - Código checa `reg not in self.hubs`
   - Realidade: `self.hubs` tem CITIES ("NA13"), `reg` é INT (0-6)
   - Comparação SEMPRE False, cai na segunda verificação
   - Mas probe_hub_open_sa tem hub em `hubs_pending`, não `hubs`

**Proxy**:
- Use `self.hub_regions` (Set de INTs) que _do_open_hub usa
- Verificar `reg in self.hub_regions` corretamente

**O que DEVE fazer ANTES de rodar close_hub**:
```python
# probe_hub_tabs() em calib_reversos_simple.py
# - Abre r1c0 em regiao 1
# - Screenshot 0: neutral (esperado Open=True)
# - Pressiona Left
# - Screenshot 1: after Left (validar se Close=False)
# - Pressiona Down
# - Screenshot 2: after Down (staff row muda)
# - Pressiona Right
# - Screenshot 3: after Right (volta Open?)
# - Log staff_action_is_bid para cada

# Resultados esperados:
# [0] neutral: True (Open)
# [1] after Left: False (Close) ← VALIDA A NAVEGACAO
# [2] after Down: ? (staff muda)
# [3] after Right: True (volta Open?)
```

**Próximos passos**:
1. Rodar `python calib_reversos_simple.py probe` (NÃO HÁ A PRESSES)
2. Se [1] = False: Left é correto, proceder com o código
3. Se [1] ≠ False: Ajustar navegação (maybe Down+Left, Right+Left, etc.)
4. Consertar precondições (usar `self.hub_regions`)
5. Trocar effect gate: antes/depois screenshots de hub list (não staff count)

</details>

---

### (c) sell_aircraft — PRONTO PARA CALIBRAÇÃO ✅
**Status**: JÁ IMPLEMENTADA em `executor.py::_do_sell_aircraft` (linhas 1332-1449)

**O que funciona**:
- Navegação para fabricante 2 (World Lease), malha fechada
- Verificação de painel (modelo correto)
- Seletor de quantidade (Right = +1, base 1, teto 3)
- Verificação de efeito: cash delta > 0

**Oracle de efeito**:
- Cash deve SUBIR (preço de revenda)
- Validado em `_do_sell_aircraft` linhas 1441-1444
- Target pré-medido: +20.520K para MD100 (CALIBRATION §12.1)

**Script pronto**:
```bash
cd harness && python calib_reversos_simple.py sell
# Executa: buy MD100 + sell MD100
# Valida: cash delta apos venda > 0
```

**Próximos passos**:
1. Rodar calibração (script já corrigido com `params={}`)
2. Registrar preco unitário medido
3. Se OK > 0: entrar em SUPPORTED

---

## Script de Calibração

**Arquivo**: `harness/calib_reversos_simple.py`

**Uso**:
```bash
python calib_reversos_simple.py sell   # Test sell_aircraft (~2 min)
python calib_reversos_simple.py probe  # Probe r1c0 tabs (< 1 min)
python calib_reversos_simple.py all    # Both (< 3 min)
```

**Resultados salvos em**: `logs/calib_reversos_18ago/`
- `sell_resultado.json`: caixa delta, preco unitário, status
- `probe_tabs_resultado.json`: staff_action_is_bid pós cada navegação

---

## Bloqueios Atuais (ordered by risk)

| # | Ação | Bloqueio | Risco | Próx. Passo |
|----|------|---------|-------|-------------|
| 1 | close_hub | Navegação não validada (guess Left vs outros) | CRÍTICO | Rodar probe (2 min) |
| 2 | close_hub | Effect gate pode ocultar falha | CRÍTICO | Medir hub_list antes/depois |
| 3 | close_hub | Precondições erradas (hub_regions vs hubs) | ALTO | Ajustar código (10 min) |
| 4 | return_slots | Slot count oracle não implementado | ALTO | Ler cities_with_slots (20 min) |
| 5 | sell_aircraft | Esperar resultado de calibração | MÉDIO | Rodar script (2 min) |

---

## Checkpoints de Aceite

✅ **Implementação**: close_hub codado (mesmo que incompleto)
✅ **Script de calibração**: pronto com protocolo correto
⏳ **Probe de navegação**: pronta para rodar
❌ **Validação de close_hub**: aguardando probe
❌ **Return_slots com oracle**: aguardando implementação de slot count
❌ **Adicionar a SUPPORTED**: aguardando testes OK

---

## Referências

- **CALIBRATION.md §12.1** (sell_aircraft target: +20.520K MD100)
- **CALIBRATION.md §17.1** (return_slots navigate Down+Right to (1,2))
- **ACTION_SPACE.md r0c2** (grid geometry: 4 funcionarios + Return em (1,2))
- **ACTION_SPACE.md r1c0** (grid Open/Close, custo $28.800K + 1 staff)
- **world.py staff_action_is_bid()** (True=cima/Open, False=baixo/Close, None=ambíguo)
- **executor.py _snapshot/_restore_snapshot** (harness state rollback)

---

## Notas Finais

O advisor foi claro: **não adicionar nada a SUPPORTED até ter medição real**.
- return_slots: gate fraco, precisa slot count
- sell_aircraft: pronto, esperar run
- close_hub: bloqueado, probe é pré-requisito

A sequência é: **probe → fix gates → run calibrações → add to SUPPORTED**.
