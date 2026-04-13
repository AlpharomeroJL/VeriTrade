// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Script, console2} from "forge-std/Script.sol";
import {Strings} from "@openzeppelin/contracts/utils/Strings.sol";
import {VeriTradeLocalIdentityRegistry} from "../src/VeriTradeLocalIdentityRegistry.sol";
import {VeriTradeLocalValidationRegistry} from "../src/VeriTradeLocalValidationRegistry.sol";
import {VeriTradeLocalReputationRegistry} from "../src/VeriTradeLocalReputationRegistry.sol";
import {VeriTradeEip1271IntentAdapter} from "../src/VeriTradeEip1271IntentAdapter.sol";

/// @notice Multi-role Anvil walk: deployer deploys → **agent** mints identity → **validator** validates + feedback.
/// @dev Default agent/validator keys are **public Anvil test keys** (accounts #1 / #2). Override with `AGENT_PRIVATE_KEY` / `VALIDATOR_PRIVATE_KEY`.
///      EIP-1271 adapter `owner` = **agent** so local EIP-712 demos align with “agent signs” (use agent key as `VERITRADE_INTENT_SIGNER_PRIVATE_KEY`).
///      `forge script script/LocalProofBundle.s.sol:LocalProofBundle --rpc-url http://127.0.0.1:8545 --broadcast --sig "run()" -vvvv`
contract LocalProofBundle is Script {
    /// @dev Well-known Anvil default private keys (Foundry 1.6 `anvil` output) — **never use on mainnet**.
    uint256 internal constant ANVIL_AGENT_DEFAULT_PK =
        0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d;
    uint256 internal constant ANVIL_VALIDATOR_DEFAULT_PK =
        0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a;

    function run() external {
        uint256 pkDeployer = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(pkDeployer);
        uint256 pkAgent = vm.envOr("AGENT_PRIVATE_KEY", ANVIL_AGENT_DEFAULT_PK);
        uint256 pkValidator = vm.envOr("VALIDATOR_PRIVATE_KEY", ANVIL_VALIDATOR_DEFAULT_PK);
        address agentAddr = vm.addr(pkAgent);
        address validatorAddr = vm.addr(pkValidator);

        vm.startBroadcast(pkDeployer);
        VeriTradeLocalIdentityRegistry identity = new VeriTradeLocalIdentityRegistry();
        VeriTradeEip1271IntentAdapter adapter = new VeriTradeEip1271IntentAdapter(agentAddr);
        VeriTradeLocalValidationRegistry validation = new VeriTradeLocalValidationRegistry(address(identity));
        VeriTradeLocalReputationRegistry reputation = new VeriTradeLocalReputationRegistry(address(identity));
        vm.stopBroadcast();

        string memory regUri = "http://127.0.0.1:34120/challenge/agent-registration";
        vm.startBroadcast(pkAgent);
        uint256 agentId = identity.register(regUri);
        identity.setMetadata(agentId, "agentWallet", Strings.toHexString(uint256(uint160(agentAddr))));
        identity.setAgentWalletAsOwner(agentId, agentAddr);
        vm.stopBroadcast();

        bytes32 reqHash = keccak256(bytes("veritrade-local-compliance-proof-v1"));
        vm.startBroadcast(pkDeployer);
        validation.validationRequest(
            validatorAddr,
            agentId,
            "http://127.0.0.1:34120/challenge/erc8004-shapes",
            reqHash
        );
        vm.stopBroadcast();

        bytes32 respBodyHash = keccak256(bytes("veritrade-validation-response-body"));
        vm.startBroadcast(pkValidator);
        validation.validationResponse(reqHash, 88, "ipfs://veritrade/local-proof/response.json", respBodyHash, "local_proof_ok");
        reputation.giveFeedback(
            agentId,
            50,
            0,
            "integration",
            "latency",
            "http://127.0.0.1:34120",
            "ipfs://veritrade/local-proof/feedback.json",
            keccak256(bytes("feedback-payload-commit"))
        );
        vm.stopBroadcast();

        string memory json = string.concat(
            "{\n",
            '  "note": "local_anvil_only_not_mainnet_compliance",\n',
            '  "chain_id": ',
            vm.toString(block.chainid),
            ",\n",
            '  "identity_registry": "',
            vm.toString(address(identity)),
            '",\n',
            '  "eip1271_intent_adapter": "',
            vm.toString(address(adapter)),
            '",\n',
            '  "validation_registry": "',
            vm.toString(address(validation)),
            '",\n',
            '  "reputation_registry": "',
            vm.toString(address(reputation)),
            '",\n',
            '  "deployer_address": "',
            vm.toString(deployer),
            '",\n',
            '  "agent_owner_address": "',
            vm.toString(agentAddr),
            '",\n',
            '  "validator_address": "',
            vm.toString(validatorAddr),
            '",\n',
            '  "agent_id": ',
            vm.toString(agentId),
            ",\n",
            '  "agent_uri_on_chain": "',
            regUri,
            '",\n',
            '  "validation_request_hash": "',
            Strings.toHexString(uint256(reqHash)),
            '",\n',
            '  "validation_response_body_keccak": "',
            Strings.toHexString(uint256(respBodyHash)),
            '",\n',
            '  "reputation_feedback_count_validator": ',
            vm.toString(reputation.feedbackCount(validatorAddr, agentId)),
            ",\n",
            '  "wallet_roles_doc": "docs/evidence/ANVIL_WALLET_ROLES.md"',
            "\n}\n"
        );
        vm.writeFile("evidence/latest-local-proof.json", json);

        console2.log("WROTE_JSON", "evidence/latest-local-proof.json");
        console2.log("ROLES deployer", deployer);
        console2.log("ROLES agent_owner", agentAddr);
        console2.log("ROLES validator", validatorAddr);
        console2.log("NEXT_BIND_ENV");
        console2.log("  ERC8004_IDENTITY_REGISTRY_ADDRESS=", address(identity));
        console2.log("  ERC8004_ONCHAIN_AGENT_ID=", agentId);
        console2.log("  ERC8004_VALIDATION_REGISTRY_ADDRESS=", address(validation));
        console2.log("  ERC8004_REPUTATION_REGISTRY_ADDRESS=", address(reputation));
        console2.log("  ERC8004_RPC_URL=<same host:port you passed to forge script --rpc-url>");
        console2.log("  VERITRADE_INTENT_EIP712_VERIFYING_CONTRACT=", address(adapter));
        console2.log("  VERITRADE_INTENT_SIGNER_PRIVATE_KEY=<use AGENT key for adapter owner path>");
        console2.log("  VERITRADE_AGENT_WALLET_PLACEHOLDER=", agentAddr);
        console2.log("OPTIONAL_API_QUERY");
        console2.log("  GET /challenge/erc8004/onchain-read?validation_request_hash=", Strings.toHexString(uint256(reqHash)));
    }
}
