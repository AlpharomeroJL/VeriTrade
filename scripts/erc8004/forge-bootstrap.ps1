# Installs Foundry dependencies into local-registry/lib (gitignored).
# Run from repository root:  pwsh scripts/erc8004/forge-bootstrap.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location (Join-Path $root "local-registry")

if (-not (Get-Command forge -ErrorAction SilentlyContinue)) {
    Write-Error "forge not found. Install Foundry: https://book.getfoundry.sh/getting-started/installation"
}

if (-not (Test-Path "lib/forge-std")) {
    forge install foundry-rs/forge-std@v1.9.4 --no-git
}
if (-not (Test-Path "lib/openzeppelin-contracts")) {
    forge install OpenZeppelin/openzeppelin-contracts@v5.0.2 --no-git
}

forge build
forge test -vvv
Write-Host "Done. lib/ is local only; add lib/ to .gitignore (already ignored in local-registry/.gitignore)."
