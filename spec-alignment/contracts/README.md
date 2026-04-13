# Registry interface stubs (illustrative)

Solidity snippets mirror **ERC-8004 (DRAFT)** registry responsibilities. They are **not deployed**, **not audited**, and **not wired** to VeriTrade runtime code.

| File | Maps to EIP-8004 |
|------|------------------|
| `IIdentityRegistry.sol` | Identity Registry — ERC-721 + URIStorage patterns described in the draft. |
| `IValidationRegistry.sol` | Validation Registry — `validationRequest` / `validationResponse` shape. |
| `IReputationRegistry.sol` | Reputation Registry — `giveFeedback` / read patterns. |

For normative text, always use [EIP-8004](https://eips.ethereum.org/EIPS/eip-8004) and the reference implementation at [erc-8004/erc-8004-contracts](https://github.com/erc-8004/erc-8004-contracts).

## Runnable local contracts (demo / Anvil)

See `../../local-registry/` for **optional** Solidity deployments that emit draft-shaped **Validation** / **Reputation** events and a minimal **Identity** `register` path. They are **local-only**, not wired into order execution, and not a compliance claim.
