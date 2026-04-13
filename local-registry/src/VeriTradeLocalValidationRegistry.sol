// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IValidationRegistry} from "./interfaces/IValidationRegistry.sol";

/// @title VeriTradeLocalValidationRegistry
/// @notice Minimal **local / Anvil** Validation Registry implementing `IValidationRegistry` — demo only.
contract VeriTradeLocalValidationRegistry is IValidationRegistry {
    address public immutable identityRegistry;

    struct Status {
        address validatorAddress;
        uint256 agentId;
        uint8 response;
        bytes32 responseHash;
        string tag;
        uint256 lastUpdate;
    }

    mapping(bytes32 => Status) private _status;

    constructor(address identityRegistry_) {
        identityRegistry = identityRegistry_;
    }

    function validationRequest(
        address validatorAddress,
        uint256 agentId,
        string calldata requestURI,
        bytes32 requestHash
    ) external override {
        require(requestHash != bytes32(0), "empty_hash");
        _status[requestHash] = Status({
            validatorAddress: validatorAddress,
            agentId: agentId,
            response: 0,
            responseHash: bytes32(0),
            tag: "",
            lastUpdate: block.timestamp
        });
        emit ValidationRequest(validatorAddress, agentId, requestURI, requestHash);
    }

    function validationResponse(
        bytes32 requestHash,
        uint8 response,
        string calldata responseURI,
        bytes32 responseHash,
        string calldata tag
    ) external override {
        Status storage s = _status[requestHash];
        require(s.validatorAddress != address(0), "unknown_request");
        require(msg.sender == s.validatorAddress, "not_validator");
        emit ValidationResponse(
            s.validatorAddress,
            s.agentId,
            requestHash,
            response,
            responseURI,
            responseHash,
            tag
        );
        s.response = response;
        s.responseHash = responseHash;
        s.tag = tag;
        s.lastUpdate = block.timestamp;
    }

    function getValidationStatus(bytes32 requestHash)
        external
        view
        override
        returns (
            address validatorAddress,
            uint256 agentId,
            uint8 response,
            bytes32 responseHash,
            string memory tag,
            uint256 lastUpdate
        )
    {
        Status storage s = _status[requestHash];
        return (s.validatorAddress, s.agentId, s.response, s.responseHash, s.tag, s.lastUpdate);
    }

    function getIdentityRegistry() external view override returns (address) {
        return identityRegistry;
    }
}
