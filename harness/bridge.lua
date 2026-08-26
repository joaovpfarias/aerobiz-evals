-- bridge.lua — Aerobiz Evals: ponte file-IPC entre BizHawk (Lua) e Python
--
-- Protocolo (arquivos em IPC_DIR, default: <dir deste script>/ipc):
--   cmd.txt  : linha1=id, linha2=OP, linhas 3+ = args posicionais (1 por linha)
--   resp.txt : linha1=id, linha2=OK|ERR, linhas 3+ = payload
-- O Python escreve cmd.txt via replace atomico; o Lua le, apaga, executa,
-- escreve resp.tmp e renomeia para resp.txt. Um comando em voo por vez.
--
-- OPs: PING | INFO | SCREENSHOT <path> | PRESS <btns_csv> <hold> <wait>
--      ADVANCE <n> | SAVE <path> | LOAD <path> | RAM <dominio> <addr_hex> <n>
--      SPEED <pct>
--
-- Uso: EmuHawk.exe --lua=<este arquivo> <rom>

local function script_dir()
  local src = debug.getinfo(1, "S").source
  src = src:gsub("^@", "")
  return src:match("^(.*)[/\\]") or "."
end

INVISIBLE = false  -- emulacao sem renderizacao (ligada via op SPEED)

local IPC = os.getenv("AEROBIZ_IPC") or (script_dir() .. "/ipc")
local CMD = IPC .. "/cmd.txt"
local RESP = IPC .. "/resp.txt"
local RESPTMP = IPC .. "/resp.tmp"
local OWNER = IPC .. "/owner.txt"

-- DONO UNICO DO IPC (medido 24/08): a trava do bridge.py e por PROCESSO PYTHON
-- e nao impede um EmuHawk esquecido de continuar servindo o mesmo diretorio.
-- Com 2+ instancias, todas leem cmd.txt, todas escrevem resp.txt e todas
-- chamam client.screenshot no MESMO screen.png -> IOException do .NET que
-- chega ao Python como "[string \"main\"]:99: A .NET exception ... <numero>".
-- Medicao: 3 instancias = 5 falhas nas 10 primeiras tentativas; 1 instancia =
-- 0 falhas em 120. Aqui: quem sobe por ultimo escreve seu token em owner.txt e
-- vira o dono; as instancias antigas param de tocar no IPC (mas seguem vivas,
-- sem roubar comando nem corromper o PNG).
-- Entropia do token: NAO usar math.random — o Lua embutido no NLua nao e
-- semeado por instancia, entao duas EmuHawk abertas no mesmo segundo tirariam o
-- MESMO numero, ambas se achariam donas e a prova de instancia unica passaria
-- justamente no caso que ela existe para pegar. O endereco de heap de uma
-- tabela recem-criada e unico por processo e nao depende de semente.
local TOKEN = tostring(os.time()) .. "-" .. (tostring({}):match("0x(%x+)") or tostring({}))
local desistiu = false

local function claim_owner()
  local f = io.open(OWNER, "w")
  if f then f:write(TOKEN .. "\n"); f:close() end
end

local function sou_dono()
  local f = io.open(OWNER, "r")
  if not f then return true end  -- sem arquivo: ninguem reivindicou
  local t = (f:read("*l") or ""):gsub("%s+$", "")
  f:close()
  return t == "" or t == TOKEN
end

local function read_cmd()
  local f = io.open(CMD, "r")
  if not f then return nil end
  -- So checa o dono quando ha comando: custo zero nos frames ociosos.
  if not sou_dono() then
    f:close()
    if not desistiu then
      desistiu = true
      console.log("[aerobiz-bridge] outra instancia assumiu o IPC (" .. IPC ..
                  "); esta paro de servir comandos. Feche esta janela.")
    end
    return nil
  end
  desistiu = false
  local content = f:read("*a")
  f:close()
  if not content or #content == 0 then return nil end
  os.remove(CMD)
  local lines = {}
  for line in content:gmatch("[^\r\n]+") do lines[#lines + 1] = line end
  if #lines < 2 then return nil end
  local args = {}
  for i = 3, #lines do args[#args + 1] = lines[i] end
  return { id = lines[1], op = lines[2]:upper(), args = args }
end

local function write_resp(id, ok, payload)
  local f = io.open(RESPTMP, "w")
  if not f then
    console.log("[aerobiz-bridge] nao consegui escrever resp em " .. RESPTMP)
    return
  end
  f:write(id .. "\n" .. (ok and "OK" or "ERR") .. "\n")
  for _, line in ipairs(payload or {}) do f:write(tostring(line) .. "\n") end
  f:close()
  os.remove(RESP)
  os.rename(RESPTMP, RESP)
end

local function do_press(args)
  local btns = {}
  for b in (args[1] or ""):gmatch("[^,]+") do btns[b] = true end
  local hold = tonumber(args[2]) or 5
  local wait = tonumber(args[3]) or 8
  for _ = 1, hold do
    joypad.set(btns, 1)
    emu.frameadvance()
  end
  for _ = 1, wait do emu.frameadvance() end
  return { "pressed" }
end

local function do_ram(args)
  local domain = args[1] or "WRAM"
  local addr = tonumber(args[2], 16)
  local size = tonumber(args[3]) or 1
  -- usememorydomain devolve false quando o nome nao existe; sem checar, a
  -- leitura sai do dominio anterior e parece funcionar.
  if not memory.usememorydomain(domain) then
    error("dominio inexistente: " .. tostring(domain))
  end
  local hex = {}
  for i = 0, size - 1 do
    hex[#hex + 1] = string.format("%02x", memory.read_u8(addr + i))
  end
  return { table.concat(hex) }
end

OPS = {
  PING = function() return { tostring(emu.framecount()) } end,
  -- 4o campo = token do dono do IPC: e assim que o Python PROVA (R4) que
  -- falou com a instancia que ele mesmo lancou, em vez de confiar no taskkill.
  INFO = function()
    return { gameinfo.getromname(), gameinfo.getromhash(), tostring(emu.framecount()), TOKEN }
  end,
  -- Com emulacao invisivel ligada e preciso renderizar um frame antes de
  -- capturar, senao o PNG sai do ultimo frame desenhado.
  SCREENSHOT = function(a)
    if INVISIBLE and client.invisibleemulation then
      client.invisibleemulation(false)
      emu.frameadvance()
      client.screenshot(a[1])
      client.invisibleemulation(true)
    else
      client.screenshot(a[1])
    end
    return { a[1] }
  end,
  PRESS = do_press,
  ADVANCE = function(a)
    local n = tonumber(a[1]) or 1
    for _ = 1, n do emu.frameadvance() end
    return { tostring(n) }
  end,
  SAVE = function(a) savestate.save(a[1]); return { a[1] } end,
  LOAD = function(a) savestate.load(a[1]); return { a[1] } end,
  RAM = do_ram,
  -- WRITE <dominio> <addr_hex> <bytes_hex>
  WRITE = function(a)
    local domain, addr, hex = a[1], tonumber(a[2], 16), a[3]
    if not memory.usememorydomain(domain) then
      error("dominio inexistente: " .. tostring(domain))
    end
    for i = 0, #hex / 2 - 1 do
      memory.write_u8(addr + i, tonumber(hex:sub(i * 2 + 1, i * 2 + 2), 16))
    end
    return { tostring(#hex / 2) }
  end,
  DOMAINS = function()
    local out = {}
    for _, d in ipairs(memory.getmemorydomainlist()) do
      out[#out + 1] = d .. " size=" .. tostring(memory.getmemorydomainsize(d))
    end
    return out
  end,
  -- O core SNES roda abaixo de 60fps nesta maquina; o ganho real vem de pular
  -- a renderizacao (invisibleemulation), nao de speedmode. Chamadas sao
  -- defensivas porque a API varia entre versoes do BizHawk.
  SPEED = function(a)
    local pct = tonumber(a[1]) or 100
    INVISIBLE = pct >= 200
    if client.speedmode then pcall(client.speedmode, pct) end
    if client.invisibleemulation then pcall(client.invisibleemulation, INVISIBLE) end
    if client.frameskip then pcall(client.frameskip, INVISIBLE and 8 or 0) end
    return { tostring(pct), tostring(INVISIBLE) }
  end,
}

-- BATCH: executa varias operacoes numa unica ida-e-volta. Cada arg e uma linha
-- "OP|arg1|arg2". Sem isso, uma macro de 30 teclas custa 30 round-trips de
-- arquivo — era o gargalo real do harness (~120s por acao).
OPS.BATCH = function(args)
  local out = {}
  for _, line in ipairs(args) do
    local parts = {}
    for p in line:gmatch("[^|]+") do parts[#parts + 1] = p end
    local op = table.remove(parts, 1):upper()
    local handler = OPS[op]
    if op == "BATCH" or not handler then
      out[#out + 1] = op .. "=ERR:invalida"
    else
      local ok, res = pcall(handler, parts)
      out[#out + 1] = op .. "=" .. (ok and table.concat(res or {}, ",") or ("ERR:" .. tostring(res)))
    end
  end
  return out
end

claim_owner()
console.log("[aerobiz-bridge] ativo | IPC: " .. IPC .. " | token: " .. TOKEN)

while true do
  local ok, err = pcall(function()
    local cmd = read_cmd()
    if cmd then
      local handler = OPS[cmd.op]
      if handler then
        local okh, payload = pcall(handler, cmd.args)
        if okh then
          write_resp(cmd.id, true, payload)
        else
          write_resp(cmd.id, false, { tostring(payload) })
        end
      else
        write_resp(cmd.id, false, { "op desconhecida: " .. tostring(cmd.op) })
      end
    end
  end)
  if not ok then console.log("[aerobiz-bridge] erro no loop: " .. tostring(err)) end
  emu.frameadvance()
end
