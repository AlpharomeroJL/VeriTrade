"""Draft-aligned validation request/response helpers (EIP-8004 Validation Registry semantics, off-chain)."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from Crypto.Hash import keccak


def keccak256_bytes(data: bytes) -> bytes:
    h = keccak.new(digest_bits=256)
    h.update(data)
    return h.digest()


def keccak256_hex(data: bytes) -> str:
    """0x-prefixed hex digest (EVM-style) for commitments."""
    return "0x" + keccak256_bytes(data).hex()


def validation_request_hash_from_canonical_payload(payload: dict[str, Any]) -> str:
    """EIP-8004: requestHash is keccak256 commitment to request payload (serialized canonically)."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return keccak256_hex(canonical)


class Erc8004ValidationRequestPayload(BaseModel):
    """Off-chain payload shape suitable for pointing to from a future validationRequest."""

    veritrade_version: str = Field(default="1")
    agent_id_config: str
    validator_address_placeholder: str = Field(
        default="0x0000000000000000000000000000000000000000",
        description="Placeholder until a validator contract address is chosen.",
    )
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)


class Erc8004ValidationResponsePayload(BaseModel):
    """Maps to validationResponse fields (off-chain evidence bundle metadata)."""

    request_hash: str
    response: int = Field(ge=0, le=100)
    response_uri: str | None = None
    response_hash: str | None = None
    tag: str = ""
    validator_address: str = "0x0000000000000000000000000000000000000000"


def response_hash_from_uri_payload(payload: dict[str, Any]) -> str | None:
    """If responseURI content is JSON, commit with keccak256; else None (IPFS-style URIs may omit)."""
    if not payload:
        return None
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return keccak256_hex(canonical)
