$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

$projRoot = Split-Path -Parent $here
$rootVenvPython = Join-Path $projRoot ".venv\Scripts\python.exe"
$backendVenvPython = Join-Path $here "venv\Scripts\python.exe"

if (Test-Path $rootVenvPython) {
  & $rootVenvPython -m uvicorn app.main:socket_app --host 0.0.0.0 --port 8000 --reload
} elseif (Test-Path $backendVenvPython) {
  & $backendVenvPython -m uvicorn app.main:socket_app --host 0.0.0.0 --port 8000 --reload
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
  py -m uvicorn app.main:socket_app --host 0.0.0.0 --port 8000 --reload
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
  python -m uvicorn app.main:socket_app --host 0.0.0.0 --port 8000 --reload
} else {
  Write-Error "Python 未找到，请安装 Python 或配置 PATH"
}
