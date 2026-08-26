# ETAPA 4-Orcamentos — Preparação Completa (18/08/2026)

## Resumo da Etapa

**Objetivo:** Implementar e calibrar a ação `set_budget(category, level)` para ajustar orçamentos de 3 categorias (Repair, Ad, Service), cada uma com 5 níveis discretos (MAXIMUM, RAISE, MAINTAIN, REDUCE, STOP).

**Status:** Código corrigido e testes prontos. Aguarda execução com EmuHawk.

---

## O que foi feito

### 1. Problema Identificado (pelo Advisor, 18/08)

A calibração anterior de Repair (§20 CALIBRATION.md, 17/08) era um **falso-positivo**:

- Script `calib_budget_fixed.py` usa **apenas Down** para navegar entre ordens
- Se o savestate começava em MAXIMUM (idx 0), então:
  - level 0: 0 Downs → [110K] (nenhuma mudança, falso positivo)
  - level 1: 1 Down → [muda para RAISE] (verdadeiro)
  - level 2: 2 Downs → [muda para MAINTAIN] (verdadeiro)
  - level 3: 3 Downs → [$100K] (verdadeiro)
  - level 4: 4 Downs → [$90K] (verdadeiro)

- **Resultado publicado:** [110K, 110K, 110K, 100K, 90K] = **3 falsos + 2 verdadeiros**

Tentativas de Ad/Service em 18/08 (3 logs diferentes) falharam antes de completar.

### 2. Correções em `executor.py::_do_set_budget()`

Implementadas em malha fechada com verificação de rótulos (conforme `calib_budget_fixed.py::goto_col_order()`):

#### (a) Navegação de ordem com leitura de rótulo

```python
# Antes: for _ in range(level): self.b.press("Down", ...)
# Depois: malha fechada
img = Image.open(b.screenshot()).convert("RGB")
orders = read_budget_orders(img)
order_idx_atual = ORDERS.index(orders[col].upper()) if orders[col] else 0

while order_idx_atual < level and tries < max_tries:
    self.b.press("Down", hold=3, wait=14)
    b.advance(40)
    img = Image.open(b.screenshot()).convert("RGB")
    orders = read_budget_orders(img)
    order_idx_atual = ORDERS.index(orders[col].upper()) if orders[col] else order_idx_atual
    tries += 1
```

- Verifica qual ordem está selecionada APÓS cada Down
- Prossegue apenas se mudou para a ordem alvo
- Retorna False se não alcançou o alvo após max_tries

#### (b) Guard `on_budget_screen()` entre os `_step` chamados

```python
# Antes: for _ in range(2): self._step(tries=4)  [cego]
# Depois:
for i in range(2):
    img_check = Image.open(b.screenshot()).convert("RGB")
    if not world.on_budget_screen(img_check):
        self._restore_guard()
        return False, f"deixei a tela de orcamento no confirm A#{i+1}"
    self._step(tries=4)
```

- Protege contra sair da tela durante a confirmação
- Evita aceitar prompts de patrocínio (−$372.000K, ver CALIBRATION.md §17)

#### (c) Verificação de rótulo pós-confirmação

```python
# Antes: comment "a ordem foi lida" + retorna True
# Depois:
orders_pos = read_budget_orders(img_pos)
order_pos = orders_pos[col] if orders_pos and orders_pos[col] else None
if order_pos and order_pos.upper() != BUDGET_ORDERS[level]:
    self._restore_guard()
    return False, f"ordem não foi aplicada: li '{order_pos}', esperava '{BUDGET_ORDERS[level]}'"
```

- Confirma que a ordem foi realmente aplicada
- Retorna False em mismatch (não warn-and-continue)
- Satisfaz o requisito do aceite: "com LEITURA do rótulo confirmando"

### 3. Scripts de Teste Criados

#### `probe_wrap_test.py`

Testa um comportamento crítico ainda desconhecido:

```
A popup de ordem envolve (wrap)?
  De STOP (idx 4), um Down vai para MAXIMUM (idx 0)?
  Ou clamp em STOP?
```

Execução:
```bash
python probe_wrap_test.py
# Analisa logs/wrap_test/pre_wrap.png e pos_wrap.png
# Imprime: POPUP ENVOLVE ou POPUP NAO ENVOLVE
```

#### `calib_budget_complete.py`

Script de calibração completo para as 3 colunas:

```bash
# Fase 1: Descobrir wrap behavior
python calib_budget_complete.py wrap

# Fase 2: Sweep individual (com o comportamento descoberto)
python calib_budget_complete.py sweep 0  # Repair
python calib_budget_complete.py sweep 1  # Ad
python calib_budget_complete.py sweep 2  # Service

# Tudo de uma vez
python calib_budget_complete.py all
```

Características:
- Malha fechada: lê rótulo após cada Down
- Captura pré e pós-confirmação
- Salva imagens de evidência em `logs/calib_budget_complete/`
- Resumo claro dos valores observados (money, levels, orders)

---

## Descoberta Pendente: Wrap Behavior

Questão ainda aberta que o `probe_wrap_test.py` vai responder:

| Cenário | Comportamento | Implicação |
|---------|---|---|
| STOP (idx 4) + Down → MAXIMUM (idx 0) | **Envolve (wrap)** | Usar `(target - current) % 5` para navegar |
| STOP (idx 4) + Down → STOP (idx 4) | **Clamp** | DOWN-only funciona em uma direção; considerar Up key |

**Atualmente implementado:** assume clamp (Down-only, sem Up)

---

## Checklist de Execução (Próxima Sessão com EmuHawk)

- [ ] Ligar EmuHawk
- [ ] Verificar que `states/_edit_2rotas.state` existe e é carregável
- [ ] Executar `python probe_wrap_test.py` → descobrir wrap behavior
- [ ] Executar `python calib_budget_complete.py all` → calibrar todas 3 colunas
- [ ] Verificar `logs/calib_budget_complete/` → confirmar imagens e valores
- [ ] Atualizar CALIBRATION.md §20 com tabelas de Repair/Ad/Service calibradas
- [ ] Atualizar ACTION_SPACE.md r0c4 com os valores reais
- [ ] Re-adicionar `set_budget` a `pilot.SUPPORTED` em pilot.py
- [ ] Validar com `python prova_set_budget.py` (novo probe via Executor.run())

---

## Arquivos Modificados (18/08)

| Arquivo | Mudança | Tipo |
|---------|---------|------|
| `executor.py` | `_do_set_budget()` reescrita com malha fechada + guards | Correção crítica |
| `pilot.py` | Removido `set_budget` de SUPPORTED | Ajuste de status |
| `STATUS.md` | Documentado problema e solução | Documentação |
| `CALIBRATION.md` | §20 marcado como falso-positivo, corrigido fluxo | Documentação |
| `ACTION_SPACE.md` | r0c4 marcado como PENDENTE REVALIDAÇÃO | Documentação |
| `probe_wrap_test.py` | Novo | Teste |
| `calib_budget_complete.py` | Novo | Calibração |
| `ETAPA4_PREPARACAO.md` | Novo (este arquivo) | Documentação |

---

## Referências

- **CALIBRATION.md §20:** descrição técnica do problema e correção
- **executor.py linhas 2191–2280:** implementação corrigida
- **calib_budget_fixed.py linhas 59–142:** padrão de malha fechada (modelo para a correção)
- **REGRA 3 (início do README):** "nada entra sem calibração"
- **Advisor feedback (18/08):** análise que levou às correções
