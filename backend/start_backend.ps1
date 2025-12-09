$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here
$venvSite = Join-Path $here "venv\Lib\site-packages"
$localSite = Join-Path $here "Lib\site-packages"
if (Test-Path $venvSite) { $env:PYTHONPATH = "$venvSite" }
elseif (Test-Path $localSite) { $env:PYTHONPATH = "$localSite" }
if (Get-Command py -ErrorAction SilentlyContinue) {
  py -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
} else {
  Write-Error "Python 未找到，请安装 Python 或配置 PATH"
}
