<#
.SYNOPSIS
  One-command build: uses the Python 3.12 .venv, runs the tests, and leaves dist\Rebind\Rebind.exe.
.EXAMPLE
  .\build.ps1            # full build
  .\build.ps1 -SkipTests
#>
param([switch]$SkipTests)
$ErrorActionPreference = "Continue"   # native tools write progress to stderr; exit codes are checked instead
Set-Location $PSScriptRoot

function Fail($msg) { Write-Host "BUILD FAILED: $msg" -ForegroundColor Red; exit 1 }

$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    & py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { Fail "could not create the 3.12 venv" }
}
& $py -m pip install -q --disable-pip-version-check -r requirements.txt
if ($LASTEXITCODE -ne 0) { Fail "pip install" }

if (-not $SkipTests) {
    & $py -m pytest -q
    if ($LASTEXITCODE -ne 0) { Fail "pytest" }
}

if (Get-Process Rebind -ErrorAction SilentlyContinue) { Fail "Rebind is running. Quit it from the tray icon, then build again." }

& $py tools\make_icon.py
if ($LASTEXITCODE -ne 0) { Fail "icon" }
& $py -m PyInstaller --noconfirm --clean --windowed --name Rebind --icon assets\rebind.ico run.py
if ($LASTEXITCODE -ne 0) { Fail "PyInstaller" }
Write-Host "Built dist\Rebind\Rebind.exe" -ForegroundColor Green
