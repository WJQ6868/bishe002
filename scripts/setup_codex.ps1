param(
  [string]$Provider = "custom",
  [string]$BaseUrl,
  [string]$ApiKey,
  [string]$Model = "gpt-4.1-mini"
)

if (-not $BaseUrl) { Write-Error "BaseUrl is required"; exit 1 }
if (-not $ApiKey) { Write-Error "ApiKey is required"; exit 1 }

$home = $env:UserProfile
$dir = Join-Path $home ".codex"
$path = Join-Path $dir "config.toml"

New-Item -ItemType Directory -Path $dir -Force | Out-Null

$content = @"
provider = "$Provider"
base_url = "$BaseUrl"
api_key = "$ApiKey"
model = "$Model"
"@

Set-Content -Path $path -Value $content -Encoding UTF8
Write-Output $path
