$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..
Get-Content .env | ForEach-Object {
  if ($_ -match '^\s*([^#=]+)=(.*)$') { Set-Item -Path "env:$($matches[1].Trim())" -Value $matches[2].Trim() }
}
$port = $env:VERITRADE_API_PORT
if (-not $port) { throw "VERITRADE_API_PORT missing from .env" }
python -m uvicorn app.main:app --app-dir apps\api --host 0.0.0.0 --port $port --reload
