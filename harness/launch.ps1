# Lanca o EmuHawk com a ponte Lua carregada.
# Uso: .\launch.ps1 [-Rom caminho\rom.sfc] [-BizHawk pasta]
param(
    [string]$Rom = "",
    [string]$BizHawk = "$env:USERPROFILE\tools\BizHawk-2.11.1"
)
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
New-Item -ItemType Directory -Force "$here\ipc" | Out-Null
Remove-Item "$here\ipc\cmd.txt", "$here\ipc\resp.txt" -ErrorAction SilentlyContinue
$lua = Join-Path $here "bridge.lua"
$exe = Join-Path $BizHawk "EmuHawk.exe"
if (-not (Test-Path $exe)) { Write-Error "EmuHawk nao encontrado: $exe"; exit 1 }
# BUG MEDIDO 18/08: -WorkingDirectory e $BizHawk, entao um $Rom relativo (ex.
# "../roms/x.sfc", copiado do README) resolvia contra a pasta do BizHawk, nao
# a do harness -> arquivo inexistente -> EmuHawk abre sem ROM (janela sem
# titulo) e o script --lua NUNCA roda (nao ha log Lua nem resp.txt). Resolver
# sempre para caminho absoluto ANTES de montar o argList.
if ($Rom -ne "" -and -not [System.IO.Path]::IsPathRooted($Rom)) {
    $Rom = (Resolve-Path (Join-Path $here $Rom)).Path
}
$argList = @("--lua=`"$lua`"")
if ($Rom -ne "") { $argList += "`"$Rom`"" }
Start-Process -FilePath $exe -ArgumentList $argList -WorkingDirectory $BizHawk
Write-Host "EmuHawk lancado | lua: $lua | ipc: $here\ipc"
