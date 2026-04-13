// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IReputationRegistry} from "./interfaces/IReputationRegistry.sol";

/// @title VeriTradeLocalReputationRegistry
/// @notice Minimal **local / Anvil** Reputation Registry implementing `IReputationRegistry` — demo only.
/// @dev Persists feedback payloads for local read/replay; **no** Sybil resistance or score aggregation.
contract VeriTradeLocalReputationRegistry is IReputationRegistry {
    address public immutable identityRegistry;

    struct StoredFeedback {
        int128 value;
        uint8 valueDecimals;
        string tag1;
        string tag2;
        string endpoint;
        string feedbackURI;
        bytes32 feedbackHash;
    }

    mapping(address => mapping(uint256 => StoredFeedback[])) private _feedbacks;

    constructor(address identityRegistry_) {
        identityRegistry = identityRegistry_;
    }

    function giveFeedback(
        uint256 agentId,
        int128 value,
        uint8 valueDecimals,
        string calldata tag1,
        string calldata tag2,
        string calldata endpoint,
        string calldata feedbackURI,
        bytes32 feedbackHash
    ) external override {
        _feedbacks[msg.sender][agentId].push(
            StoredFeedback({
                value: value,
                valueDecimals: valueDecimals,
                tag1: tag1,
                tag2: tag2,
                endpoint: endpoint,
                feedbackURI: feedbackURI,
                feedbackHash: feedbackHash
            })
        );
        uint64 idx = uint64(_feedbacks[msg.sender][agentId].length - 1);
        emit NewFeedback(
            agentId,
            msg.sender,
            idx,
            value,
            valueDecimals,
            tag1,
            tag1,
            tag2,
            endpoint,
            feedbackURI,
            feedbackHash
        );
    }

    function revokeFeedback(uint256 agentId, uint64 feedbackIndex) external override {
        uint64 n = uint64(_feedbacks[msg.sender][agentId].length);
        require(feedbackIndex < n, "invalid_index");
        emit FeedbackRevoked(agentId, msg.sender, feedbackIndex);
    }

    /// @notice Number of persisted feedback entries `client` has issued for `agentId`.
    function feedbackCount(address client, uint256 agentId) external view returns (uint64) {
        return uint64(_feedbacks[client][agentId].length);
    }

    /// @notice Read back a single stored feedback row (local evidence / replay helper).
    function getFeedback(address client, uint256 agentId, uint64 index)
        external
        view
        returns (
            int128 value,
            uint8 valueDecimals,
            string memory tag1,
            string memory tag2,
            string memory endpoint,
            string memory feedbackURI,
            bytes32 feedbackHash
        )
    {
        require(index < _feedbacks[client][agentId].length, "invalid_index");
        StoredFeedback storage s = _feedbacks[client][agentId][index];
        return (s.value, s.valueDecimals, s.tag1, s.tag2, s.endpoint, s.feedbackURI, s.feedbackHash);
    }

    function getIdentityRegistry() external view override returns (address) {
        return identityRegistry;
    }
}
