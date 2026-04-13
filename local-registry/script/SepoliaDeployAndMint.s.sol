// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Script, console2} from "forge-std/Script.sol";
import {Strings} from "@openzeppelin/contracts/utils/Strings.sol";
import {VeriTradeLocalIdentityRegistry} from "../src/VeriTradeLocalIdentityRegistry.sol";
import {VeriTradeLocalValidationRegistry} from "../src/VeriTradeLocalValidationRegistry.sol";
import {VeriTradeLocalReputationRegistry} from "../src/VeriTradeLocalReputationRegistry.sol";
import {VeriTradeEip1271IntentAdapter} from "../src/VeriTradeEip1271IntentAdapter.sol";

/// @title SepoliaDeployAndMint — public testnet deploy + first agent mint (VeriTrade-local-registry stack)
/// @notice Intended for **Ethereum Sepolia** (chainId 11155111). Uses standard Foundry broadcast; **operator supplies funded keys**.
/// @dev `PUBLIC_AGENT_REGISTRATION_URL` must be the HTTPS URL served as the agent registration document (e.g. `https://<your-app>/.well-known/agent-registration.json`).
///      After this script: set API `.env` with printed addresses, `ERC8004_DEV_CHAIN_ID=11155111`, `ERC8004_RPC_URL`, then run `python scripts/export_agent_registration_static.py` before re-broadcasting if `agentURI` must match the exported file.
///      `forge script script/SepoliaDeployAndMint.s.sol:SepoliaDeployAndMint --rpc-url $SEPOLIA_RPC_URL --broadcast --sig "run()" -vvvv`
contract SepoliaDeployAndMint is Script {
    function run() external {
        uint256 pkDeployer = vm.envUint("PRIVATE_KEY");
        uint256 pkAgent = vm.envOr("AGENT_PRIVATE_KEY", pkDeployer);
        address deployer = vm.addr(pkDeployer);
        address agentAddr = vm.addr(pkAgent);
        string memory regUri = vm.envString("PUBLIC_AGENT_REGISTRATION_URL");
        require(bytes(regUri).length > 0, "PUBLIC_AGENT_REGISTRATION_URL");

        vm.startBroadcast(pkDeployer);
        VeriTradeLocalIdentityRegistry identity = new VeriTradeLocalIdentityRegistry();
        VeriTradeEip1271IntentAdapter adapter = new VeriTradeEip1271IntentAdapter(agentAddr);
        VeriTradeLocalValidationRegistry validation = new VeriTradeLocalValidationRegistry(address(identity));
        VeriTradeLocalReputationRegistry reputation = new VeriTradeLocalReputationRegistry(address(identity));
        vm.stopBroadcast();

        vm.startBroadcast(pkAgent);
        uint256 agentId = identity.register(regUri);
        identity.setMetadata(agentId, "agentWallet", Strings.toHexString(uint256(uint160(agentAddr))));
        identity.setAgentWalletAsOwner(agentId, agentAddr);
        vm.stopBroadcast();

        string memory json = string.concat(
            "{\n",
            '  "note": "veritrade_operator_deployed_sepolia_not_protocol_canonical_registry",\n',
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
            '  "agent_id": ',
            vm.toString(agentId),
            ",\n",
            '  "agent_uri_on_chain": "',
            regUri,
            '",\n',
            '  "public_agent_registration_url_env": "PUBLIC_AGENT_REGISTRATION_URL"',
            "\n}\n"
        );
        vm.writeFile("evidence/sepolia-public-proof.json", json);

        console2.log("WROTE_JSON", "evidence/sepolia-public-proof.json");
        console2.log("CHAIN_ID", block.chainid);
        console2.log("NEXT_BIND_ENV");
        console2.log("  ERC8004_DEV_CHAIN_ID=", block.chainid);
        console2.log("  ERC8004_IDENTITY_REGISTRY_ADDRESS=", address(identity));
        console2.log("  ERC8004_ONCHAIN_AGENT_ID=", agentId);
        console2.log("  ERC8004_VALIDATION_REGISTRY_ADDRESS=", address(validation));
        console2.log("  ERC8004_REPUTATION_REGISTRY_ADDRESS=", address(reputation));
        console2.log("  ERC8004_RPC_URL=<same Sepolia JSON-RPC you used for --rpc-url>");
        console2.log("  VERITRADE_INTENT_EIP712_VERIFYING_CONTRACT=", address(adapter));
        console2.log("  VERITRADE_INTENT_SIGNER_PRIVATE_KEY=<AGENT key for adapter owner>");
        console2.log("  VERITRADE_AGENT_WALLET_PLACEHOLDER=", agentAddr);
        console2.log("BINDING verify: agentURI on-chain must match reachable HTTPS registration JSON");
    }
}
