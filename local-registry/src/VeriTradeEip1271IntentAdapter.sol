// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";

/// @title VeriTradeEip1271IntentAdapter
/// @notice Minimal **ERC-1271** adapter for dev/test: fixed `owner` EOA whose signatures over the **EIP-712 v4 digest**
///         (`0x19 0x01 ‖ domainSeparator ‖ hashStruct(message)`) return the ERC-1271 magic value.
/// @dev This is **not** a production smart wallet. Set `verifyingContract` in the EIP-712 domain to this contract’s address
///      and sign with `owner`’s private key off-chain. `isValidSignature` uses `ECDSA.recover` on the supplied `hash`.
contract VeriTradeEip1271IntentAdapter {
    address public immutable owner;

    bytes4 internal constant _ERC1271_MAGICVALUE = 0x1626ba7e;

    constructor(address owner_) {
        require(owner_ != address(0), "zero_owner");
        owner = owner_;
    }

    /// @notice ERC-1271 `isValidSignature` — returns magic value `0x1626ba7e` when `ECDSA.recover(hash, signature) == owner`.
    function isValidSignature(bytes32 hash, bytes calldata signature) external view returns (bytes4 magicValue) {
        address recovered = ECDSA.recover(hash, signature);
        if (recovered == owner) {
            return _ERC1271_MAGICVALUE;
        }
        return 0xffffffff;
    }
}
