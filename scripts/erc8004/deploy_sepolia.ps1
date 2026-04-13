# Deploy VeriTrade local-registry stack to Ethereum Sepolia and mint agent #1.
# Requires: Foundry, funded $env:PRIVATE_KEY on Sepolia, $env:PUBLIC_AGENT_REGISTRATION_URL
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location (Join-Path $Root "local-registry")

if (-not $env:PRIVATE_KEY) { throw "Set PRIVATE_KEY (deployer with Sepolia ETH)" }
if (-not $env:PUBLIC_AGENT_REGISTRATION_URL) { throw "Set PUBLIC_AGENT_REGISTRATION_URL to HTTPS /.well-known/... URL" }

$Rpc = if ($env:SEPOLIA_RPC_URL) { $env:SEPOLIA_RPC_URL } else { "https://ethereum-sepolia.publicnode.com" }
Write-Host "Using RPC: $Rpc"

forge script script/SepoliaDeployAndMint.s.sol:SepoliaDeployAndMint `
  --rpc-url $Rpc `
  --broadcast `
  --sig "run()" `
  -vvvv

Write-Host ""
Write-Host "See local-registry/evidence/sepolia-public-proof.json — paste env lines into API .env and run export_agent_registration_static.py"
