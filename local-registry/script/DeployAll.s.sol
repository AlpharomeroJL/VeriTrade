// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Script, console2} from "forge-std/Script.sol";
import {VeriTradeLocalIdentityRegistry} from "../src/VeriTradeLocalIdentityRegistry.sol";
import {VeriTradeLocalValidationRegistry} from "../src/VeriTradeLocalValidationRegistry.sol";
import {VeriTradeLocalReputationRegistry} from "../src/VeriTradeLocalReputationRegistry.sol";
import {VeriTradeEip1271IntentAdapter} from "../src/VeriTradeEip1271IntentAdapter.sol";

/// @notice Broadcast deploy of Identity, EIP-1271 adapter (owner = broadcaster), Validation, Reputation.
/// @dev Usage (Anvil default key shown as example — use only on local chains):
///      `cd local-registry && forge script script/DeployAll.s.sol:DeployAll --rpc-url http://127.0.0.1:8545 --broadcast --sig "run()" -vvvv`
contract DeployAll is Script {
    function run() external {
        uint256 pk = vm.envUint("PRIVATE_KEY");
        vm.startBroadcast(pk);
        address deployer = vm.addr(pk);

        VeriTradeLocalIdentityRegistry identity = new VeriTradeLocalIdentityRegistry();
        VeriTradeEip1271IntentAdapter adapter = new VeriTradeEip1271IntentAdapter(deployer);
        VeriTradeLocalValidationRegistry validation = new VeriTradeLocalValidationRegistry(address(identity));
        VeriTradeLocalReputationRegistry reputation = new VeriTradeLocalReputationRegistry(address(identity));

        vm.stopBroadcast();

        console2.log("DEPLOYER", deployer);
        console2.log("IDENTITY_REGISTRY", address(identity));
        console2.log("EIP1271_INTENT_ADAPTER", address(adapter));
        console2.log("VALIDATION_REGISTRY", address(validation));
        console2.log("REPUTATION_REGISTRY", address(reputation));
    }
}
