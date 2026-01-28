param(
  [Parameter(Mandatory=$true)][string]$CRS_OAI_KEY,
  [switch]$SetGlobal
)

$userSettingsPaths = @(
  Join-Path $env:APPDATA "Code\User\settings.json",
  Join-Path $env:APPDATA "Code - Insiders\User\settings.json"
)

foreach ($path in $userSettingsPaths) {
  $dir = Split-Path $path
  New-Item -ItemType Directory -Path $dir -Force | Out-Null
  $json = "{}"
  if (Test-Path $path) { $json = Get-Content $path -Raw }
  $obj = $json | ConvertFrom-Json
  if (-not $obj) { $obj = [ordered]@{} }

  if (-not $obj.PSObject.Properties.Match('terminal.integrated.env.linux')) {
    $obj.'terminal.integrated.env.linux' = [ordered]@{}
  }
  if (-not $obj.PSObject.Properties.Match('terminal.integrated.env.windows')) {
    $obj.'terminal.integrated.env.windows' = [ordered]@{}
  }

  $obj.'terminal.integrated.env.linux'.CRS_OAI_KEY = $CRS_OAI_KEY
  $obj.'terminal.integrated.env.windows'.CRS_OAI_KEY = $CRS_OAI_KEY

  $out = $obj | ConvertTo-Json -Depth 10
  Set-Content -Path $path -Value $out -Encoding UTF8
}

if ($SetGlobal) {
  setx CRS_OAI_KEY $CRS_OAI_KEY | Out-Null
}

Write-Output "VSCode settings updated. Please kill all VSCode processes and reopen."
