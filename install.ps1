# RuTilites installer: dependencies, autostart, first launch.
# Run install.cmd (double-click) or:
#   powershell -ExecutionPolicy Bypass -File install.ps1 [-NoAutostart] [-NoStart]
param(
    [switch]$NoAutostart,  # do not add RuTilites to Windows startup
    [switch]$NoStart       # do not launch it at the end
)
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

function Find-Python {
    foreach ($cand in @(@('py', '-3'), @('python'))) {
        $exe = $cand[0]; $pre = @($cand | Select-Object -Skip 1)
        if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { continue }
        try { $path = & $exe @pre -c "import sys; print(sys.executable)" 2>$null } catch { continue }
        if ($LASTEXITCODE -ne 0 -or -not $path) { continue }
        $path = $path.Trim()
        # Skip the Microsoft Store stub, which opens the Store instead of running.
        if ($path -like '*\WindowsApps\*') { continue }
        return $path
    }
    return $null
}

Write-Host "RuTilites: установка в $here"

$py = Find-Python
if (-not $py) {
    Write-Host ""
    Write-Host "Python 3.10 или новее не найден. Установите его и запустите установку снова:" -ForegroundColor Yellow
    Write-Host "  winget install Python.Python.3.13"
    Write-Host "или скачайте с https://www.python.org/downloads/ (отметьте 'Add python.exe to PATH')."
    exit 1
}
$ver = & $py -c "import sys; print('%d.%d' % sys.version_info[:2])"
if ([version]$ver -lt [version]'3.10') {
    Write-Host "Нужен Python 3.10 или новее, найден $ver ($py)." -ForegroundColor Yellow
    exit 1
}
Write-Host "Python $ver`: $py"

Write-Host "Ставлю зависимости из requirements.txt..."
& $py -m pip install --disable-pip-version-check -q -r (Join-Path $here 'requirements.txt')
if ($LASTEXITCODE -ne 0) { Write-Host "pip завершился с ошибкой." -ForegroundColor Red; exit 1 }

& $py -c "import PySide6, pynput, pyperclip; print('Зависимости в порядке')"
if ($LASTEXITCODE -ne 0) { exit 1 }

if (-not $NoAutostart) {
    # Same code path as the "Автозапуск" item in the tray menu.
    & $py -c "from features import autostart; autostart.enable(); print('Автозапуск:', autostart.entry_path())"
    if ($LASTEXITCODE -ne 0) { exit 1 }
}

if (-not $NoStart) {
    Start-Process -FilePath 'wscript.exe' -ArgumentList ('"' + (Join-Path $here 'RuTilites.vbs') + '"')
    Write-Host "RuTilites запущен, значок появится в трее через пару секунд."
}
Write-Host "Готово." -ForegroundColor Green
