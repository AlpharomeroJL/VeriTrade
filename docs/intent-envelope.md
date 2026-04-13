# Intent envelope: SHA-256 commitment vs EIP-712 typed signing

VeriTrade binds each trade intent with a deterministic **`intent_commitment_sha256`**: SHA-256 over **canonical JSON** (sorted keys, minimal separators) of the fields in `app/challenge/intent_commitment.py`. This remains the **default** integrity story and is unchanged for existing demos.

## Current fields in the commitment

- `intent_uuid`, `asset`, `action`, `requested_size`, `approved_size`
- `policy_version`, `risk_verdict`, `strategy_id`, `created_at` (ISO string)

This is **off-chain integrity** suitable for audit trails and UI display. It is **not** an Ethereum ECDSA signature by itself.

## EIP-712 typed signing (local / dev, optional)

When **both** of the following are set in `.env`:

- `VERITRADE_INTENT_EIP712_VERIFYING_CONTRACT` — non-zero `0x…` address (your intent “domain” anchor; often a placeholder contract on Anvil)
- `VERITRADE_INTENT_SIGNER_PRIVATE_KEY` — **throwaway** dev key (e.g. Anvil account #0)

…the API persists on each new `TradeIntent`:

- `eip712_signature` — `0x`-prefixed ECDSA signature over the typed data from `app/challenge/eip712_intent.py`
- `eip712_signer` — recovered address (must match the signing key)
- `eip712_chain_id` — from `ERC8004_DEV_CHAIN_ID` (defaults to `31337`)

Implementation details:

- **Types:** `TradeIntent` mirrors the same string fields as the SHA-256 commitment (sizes as decimal strings for stable hashing across stacks).
- **Domain:** `name` / `version` from `VERITRADE_INTENT_EIP712_DOMAIN_*`, `chainId` = `ERC8004_DEV_CHAIN_ID`, `verifyingContract` as configured.
- **Verification:** `verify_trade_intent_typed_data` recovers the signer from `(typedData, signature)` — used implicitly when persisting.

**Security:** do **not** use funded mainnet keys. This path exists for **credibility and local testing**, not custody.

## EIP-712-shaped outline (unconfigured)

`trade_intent_eip712_outline(intent)` in `intent_commitment.py` still returns a JSON-serializable object with `chainId: 0` and zero `verifyingContract` when you want a **documentation-only** envelope without implying a bound domain.

## Mapping to ERC-8004 / registry flows

- **Identity / validation registries** in the draft often assume **wallet-backed** evidence (EIP-712 for `agentWallet` updates, validators signing responses).
- VeriTrade’s **current** product story: risk router + artifacts + SHA-256 intent commitment, **plus** optional EIP-712 signatures when dev env is configured.
- **Next steps** for closer alignment: bind `verifyingContract` to a dedicated verifier contract or registry workflow, add ERC-1271 for contract wallets, and optionally anchor intent hashes on-chain.

## ERC-1271 (minimal dev path)

If the “agent wallet” is a **contract account**, proofs often use [ERC-1271](https://eips.ethereum.org/EIPS/eip-1271) `isValidSignature(bytes32,bytes)` returning the magic value `0x1626ba7e…`.

VeriTrade ships a **minimal adapter** for local/test use:

- Contract: `local-registry/src/VeriTradeEip1271IntentAdapter.sol` — fixed **owner EOA**; `isValidSignature` checks `ECDSA.recover(hash, signature) == owner` for the **EIP-712 v4 digest** (`0x19 0x01 ‖ domainSeparator ‖ hashStruct(message)`). In **`LocalProofBundle`**, `owner` is the **agent** (Anvil account **#1** by default), not the deployer — use that key as `VERITRADE_INTENT_SIGNER_PRIVATE_KEY` for local demos. Wrong signer returns **`0xffffffff`** (see Forge tests).
- Python: `app/challenge/eip1271_intent.py` performs an **`eth_call`** when `ERC8004_RPC_URL` is set and the intent has an `eip712_signature`.
- API: `GET /intents/{id}/signature-verification` returns the digest, EOA recovery, and optional ERC-1271 `eth_call` result.

**Limits (truthful):**

- This is **not** a Safe / universal smart-wallet integration.
- The adapter **does not** re-hash typed data on-chain; it trusts the supplied `bytes32` digest matches what was signed (standard ERC-1271 pattern).
- **Contract wallets** that transform digests or use nested signatures are **out of scope** for this adapter.
