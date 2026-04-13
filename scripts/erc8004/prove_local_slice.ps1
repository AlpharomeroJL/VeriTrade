# Shortest scripted evidence check for the local ERC-8004 slice (no long-running Anvil here).
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root

Write-Host "== 1) Anvil wallet roles (public defaults) =="
python scripts/erc8004/print_anvil_roles.py

Write-Host "`n== 2) Foundry unit proof (no chain) =="
$env:Path = if ($env:FOUNDRY_ROOT) { "$env:FOUNDRY_ROOT;$env:Path" } else { $env:Path }
Push-Location local-registry
forge test -vvv --match-test testComplianceEvidence_identityValidationReputationChain
Pop-Location

Write-Host "`n== 3) Full on-chain bundle (requires Anvil in another terminal) =="
Write-Host "  anvil --port 8545"
Write-Host "  cd local-registry"
Write-Host "  `$env:PRIVATE_KEY='<deployer key from print_anvil_roles>'"
Write-Host "  forge script script/LocalProofBundle.s.sol:LocalProofBundle --rpc-url http://127.0.0.1:8545 --broadcast --sig `"run()`" -vvvv"
Write-Host "`nSee docs/evidence/ERC8004_LOCAL_PROOF_WALKTHROUGH.md and docs/evidence/ANVIL_WALLET_ROLES.md"
