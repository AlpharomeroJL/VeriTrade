// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {EIP712} from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";

/// @title VeriTradeLocalIdentityRegistry
/// @notice Minimal **local / Anvil-only** Identity Registry for ERC-8004 demos — **not** audited, **not** production.
/// @dev Emits draft-shaped `Registered` / `URIUpdated` events. Not a normative EIP-8004 reference implementation.
///      Adds a first-class `agentWallet` address plus optional EIP-712 `SetAgentWallet` signatures (local demo semantics).
contract VeriTradeLocalIdentityRegistry is EIP712 {
    bytes32 private constant _SET_AGENT_WALLET_TYPEHASH =
        keccak256("SetAgentWallet(uint256 agentId,address newWallet,uint256 nonce)");

    uint256 private _nextAgentId = 1;

    mapping(uint256 => string) private _agentURI;
    mapping(uint256 => address) public ownerOf;
    /// @notice Optional string metadata per agent (key hashed on-chain); draft-shaped subset for local demos.
    mapping(uint256 => mapping(bytes32 => string)) private _metadata;

    /// @notice First-class agent execution wallet (distinct from `ownerOf`); unset until configured.
    mapping(uint256 => address) private _agentWallet;
    /// @notice Monotonic nonce for EIP-712 `SetAgentWallet` replay protection (also advanced on owner-direct updates).
    mapping(uint256 => uint256) public walletNonce;

    event Registered(uint256 indexed agentId, string agentURI, address indexed owner);
    event URIUpdated(uint256 indexed agentId, string newURI, address indexed updatedBy);
    event MetadataUpdated(uint256 indexed agentId, string key, string value);
    event AgentWalletUpdated(uint256 indexed agentId, address newWallet, address indexed updatedBy, uint256 newNonce);

    constructor() EIP712("VeriTradeLocalIdentityRegistry", "1") {}

    function register(string calldata uri) external returns (uint256 agentId) {
        agentId = _nextAgentId++;
        _agentURI[agentId] = uri;
        ownerOf[agentId] = msg.sender;
        emit Registered(agentId, uri, msg.sender);
    }

    function setAgentURI(uint256 agentId, string calldata newURI) external {
        require(ownerOf[agentId] == msg.sender, "not_owner");
        _agentURI[agentId] = newURI;
        emit URIUpdated(agentId, newURI, msg.sender);
    }

    /// @notice Transfer on-chain ownership of `agentId` (local semantics; not a full ERC-721 transfer).
    function transferAgentOwnership(uint256 agentId, address newOwner) external {
        require(newOwner != address(0), "zero_owner");
        require(ownerOf[agentId] == msg.sender, "not_owner");
        ownerOf[agentId] = newOwner;
    }

    function exists(uint256 agentId) external view returns (bool) {
        return ownerOf[agentId] != address(0);
    }

    function agentURI(uint256 agentId) external view returns (string memory) {
        return _agentURI[agentId];
    }

    function setMetadata(uint256 agentId, string calldata key, string calldata value) external {
        require(ownerOf[agentId] == msg.sender, "not_owner");
        _metadata[agentId][keccak256(bytes(key))] = value;
        emit MetadataUpdated(agentId, key, value);
    }

    function getMetadata(uint256 agentId, string calldata key) external view returns (string memory) {
        return _metadata[agentId][keccak256(bytes(key))];
    }

    /// @notice Current agent wallet for `agentId` (address(0) if never set).
    function agentWallet(uint256 agentId) external view returns (address) {
        return _agentWallet[agentId];
    }

    /// @dev EIP-712 digest for off-chain signing / tests (`SetAgentWallet` typed data).
    function digestSetAgentWallet(uint256 agentId, address newWallet, uint256 nonce) external view returns (bytes32) {
        bytes32 structHash = keccak256(abi.encode(_SET_AGENT_WALLET_TYPEHASH, agentId, newWallet, nonce));
        return _hashTypedDataV4(structHash);
    }

    /// @notice Owner sets wallet directly (local convenience); advances `walletNonce`.
    function setAgentWalletAsOwner(uint256 agentId, address newWallet) external {
        require(ownerOf[agentId] == msg.sender, "not_owner");
        require(newWallet != address(0), "zero_wallet");
        _agentWallet[agentId] = newWallet;
        uint256 n = ++walletNonce[agentId];
        emit AgentWalletUpdated(agentId, newWallet, msg.sender, n);
    }

    /// @notice EIP-712 signed wallet update. Signer must be `ownerOf[agentId]` or the current `agentWallet` when non-zero.
    function setAgentWalletWithSig(uint256 agentId, address newWallet, uint256 nonce, bytes calldata signature) external {
        require(ownerOf[agentId] != address(0), "no_agent");
        require(newWallet != address(0), "zero_wallet");
        require(nonce == walletNonce[agentId], "bad_nonce");

        address current = _agentWallet[agentId];
        address owner = ownerOf[agentId];
        bytes32 structHash = keccak256(abi.encode(_SET_AGENT_WALLET_TYPEHASH, agentId, newWallet, nonce));
        bytes32 digest = _hashTypedDataV4(structHash);
        address signer = ECDSA.recover(digest, signature);

        bool ok = signer == owner || (current != address(0) && signer == current);
        require(ok, "bad_sig");

        _agentWallet[agentId] = newWallet;
        uint256 n = ++walletNonce[agentId];
        emit AgentWalletUpdated(agentId, newWallet, signer, n);
    }
}
