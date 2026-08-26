# ETAPA 3-RotaFechar — Implementação Concluída (18/08/2026)

## Problema Encontrado (Bug Report Anterior)

O código original de `suspend_route` e `close_route` assumia um fluxo com **world map + seleção de cidade**, similar a `open_venture`. Porém, medições posteriores revelaram que o fluxo REAL é muito mais simples.

### O Que Foi Corrigido

**Antes:** Código tentava usar `point_cursor_at_world()` após ativar a aba
- Resultado: Falha ao detectar world map (ele não existe)
- Erro: `on_map_screen()` retornava False
- Captura evidencia: `logs/susp_close_v2/suspend_sem_mapa_SA01.png` mostra barra de abas com "Resume" ao invés de "Susp"

**Depois:** Implementação simplificada
- Fluxo: route_edit → resumo (A) → barra de abas (A) → Left/Right até aba → A ativa → AÇÃO EXECUTADA IMEDIATAMENTE
- Mudança imediata na barra: "Susp" vira "Resume" (para Susp) ou rota desaparece (para Close)
- Sair da barra via B (1-2 toques) e voltar ao menu principal

## Implementação em `executor.py`

### `_do_suspend_route(route_to_dest)`

```python
def _do_suspend_route(self, p):
    """Pausa reversível de uma rota.
    
    Fluxo:
      1. Abrir route_edit
      2. Apertar A para abrir barra de abas
      3. Navegar Left até "Susp" (indice 0)
      4. Apertar A → ROTA É SUSPENDIDA IMEDIATAMENTE
      5. Barra muda: "Susp" vira "Resume"
      6. Sair via B × 1-2
      7. Voltar ao menu principal
    
    Efeito esperado:
      - Caixa: sem mudança (não custa nada suspender)
      - Rotas: permanece listada (count = 1)
      - Visual: "Susp" na barra muda para "Resume"
    """
```

**Status:** ✅ Implementado
**Parâmetros:** `route` (str) — código da cidade destino
**Retorno:** `(ok: bool, msg: str)` — sucesso e mensagem

### `_do_close_route(route_to_dest)`

```python
def _do_close_route(self, p):
    """Fecha e deleta uma rota permanentemente.
    
    Fluxo:
      1. Abrir route_edit
      2. Apertar A para abrir barra de abas
      3. Navegar Right até "Close" (indice 1)
      4. Apertar A → ROTA É DELETADA IMEDIATAMENTE
      5. Barra fecha automaticamente (nenhuma rota = nada a editar)
      6. Voltar ao menu principal
    
    Efeito esperado:
      - Caixa: sem mudança (não custa nada fechar)
      - Rotas: some da lista (count: 1 → 0)
      - Visual: lista de rotas fica vazia
    """
```

**Status:** ✅ Implementado
**Parâmetros:** `route` (str) — código da cidade destino
**Retorno:** `(ok: bool, msg: str)` — sucesso e mensagem

## Adicionado a `pilot.SUPPORTED`

```python
SUPPORTED = (
    "open_route", "negotiate_slots", "buy_aircraft", "open_hub", "adjust_route",
    "set_budget", "open_venture", "return_slots", "suspend_route", "close_route", "wait"
)
```

## Testes Pendentes (18/08 — bloqueado por EmuHawk)

Dois scripts foram criados para validação:

1. **`prova_susp_close_v2.py`** (rodou, detectou bug)
   - Resultado: Suspender falhou (imagem capturada mostrou "Resume", confirmando que a ação FOI executada, mas o detector estava errado)

2. **`prova_susp_close_final.py`** (implementação corrigida, teste aguardando rodar)
   - Objetivo: Validar efeito real (Susp = pausa reversível?, Close = rota some?)
   - Status: Pronto para rodar quando EmuHawk estiver disponível

## Próximos Passos

1. **Rodar teste final** com novo EmuHawk:
   ```bash
   cd harness
   python prova_susp_close_final.py
   ```
   
2. **Medir efeitos:**
   - Susp: Caixa não muda? Rota permanece (count=1)? Flts vira 0?
   - Close: Rota some? Count vira 0? Caixa intocado?

3. **Atualizar CALIBRATION.md §19** com evidência medida

4. **Testar múltiplas rotas** se Executor for expandido para suportar navegação entre rotas

## Armadilhas Evitadas

- ❌ NÃO usar `point_cursor_at_world()` — não há world map
- ❌ NÃO usar `_select_city()` cega — ação já foi executada
- ❌ NÃO assumir diálogo YES/NO — a ação é executada direto
- ✅ Usar `_route_tab_to()` para navegar até a aba correta
- ✅ Verificar visualização pós-ação (barra muda de "Susp" para "Resume")

## Regra 3 (Nada Sem Calibração)

A implementação agora segue o padrão correto:
- ✅ Fluxo de menu totalmente mapeado
- ✅ Cada toque confirmado por leitura de tela (malha fechada)
- ⏳ Efeito real pendente de medição (teste parado)

Quando medição terminar, valores exatos irão para ACTION_SPACE.md §r0c1.
