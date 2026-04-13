// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {VeriTradeLocalIdentityRegistry} from "../src/VeriTradeLocalIdentityRegistry.sol";
import {VeriTradeLocalValidationRegistry} from "../src/VeriTradeLocalValidationRegistry.sol";
import {VeriTradeLocalReputationRegistry} from "../src/VeriTradeLocalReputationRegistry.sol";
import {VeriTradeEip1271IntentAdapter} from "../src/VeriTradeEip1271IntentAdapter.sol";

contract RegistryTest is Test {
    address alice = address(0xA11CE);
    address bob = address(0xB0B);

    function testIdentity_register_setURI_transfer() public {
        VeriTradeLocalIdentityRegistry id = new VeriTradeLocalIdentityRegistry();
        vm.prank(alice);
        uint256 aid = id.register("uri-a");
        assertEq(aid, 1);
        assertEq(id.ownerOf(aid), alice);
        assertTrue(id.exists(aid));

        vm.prank(alice);
        id.setAgentURI(aid, "uri-b");
        assertEq(keccak256(bytes(id.agentURI(aid))), keccak256(bytes("uri-b")));

        vm.prank(alice);
        id.transferAgentOwnership(aid, bob);
        assertEq(id.ownerOf(aid), bob);

        vm.prank(bob);
        id.setAgentURI(aid, "uri-c");
        assertEq(keccak256(bytes(id.agentURI(aid))), keccak256(bytes("uri-c")));
    }

    function testIdentity_setMetadata_getMetadata_ownerOnly() public {
        VeriTradeLocalIdentityRegistry id = new VeriTradeLocalIdentityRegistry();
        vm.prank(alice);
        uint256 aid = id.register("u");
        vm.prank(alice);
        id.setMetadata(aid, "agentWallet", "0xabc");
        assertEq(id.getMetadata(aid, "agentWallet"), "0xabc");
        vm.prank(bob);
        vm.expectRevert();
        id.setMetadata(aid, "k", "v");
    }

    function testIdentity_setAgentWalletAsOwner_advancesNonce() public {
        VeriTradeLocalIdentityRegistry id = new VeriTradeLocalIdentityRegistry();
        vm.prank(alice);
        uint256 aid = id.register("u");
        assertEq(id.agentWallet(aid), address(0));
        assertEq(id.walletNonce(aid), 0);
        vm.prank(alice);
        id.setAgentWalletAsOwner(aid, bob);
        assertEq(id.agentWallet(aid), bob);
        assertEq(id.walletNonce(aid), 1);
        vm.prank(bob);
        vm.expectRevert();
        id.setAgentWalletAsOwner(aid, alice);
    }

    function testIdentity_setAgentWalletWithSig_ownerSigner() public {
        uint256 pkAlice = uint256(keccak256("veritrade_test_owner_pk"));
        address aliceAddr = vm.addr(pkAlice);
        VeriTradeLocalIdentityRegistry id = new VeriTradeLocalIdentityRegistry();
        vm.prank(aliceAddr);
        uint256 aid = id.register("u");
        vm.prank(aliceAddr);
        id.setAgentWalletAsOwner(aid, aliceAddr);
        address newWallet = address(0xBEEF);
        uint256 nonce = id.walletNonce(aid);
        bytes32 digest = id.digestSetAgentWallet(aid, newWallet, nonce);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(pkAlice, digest);
        bytes memory sig = abi.encodePacked(r, s, v);
        id.setAgentWalletWithSig(aid, newWallet, nonce, sig);
        assertEq(id.agentWallet(aid), newWallet);
        assertEq(id.walletNonce(aid), nonce + 1);
    }

    function testIdentity_setAgentWalletWithSig_currentWalletSigner() public {
        uint256 pkAlice = uint256(keccak256("veritrade_test_owner_pk_b"));
        uint256 pkWallet = uint256(keccak256("veritrade_test_wallet_pk"));
        address aliceAddr = vm.addr(pkAlice);
        address walletAddr = vm.addr(pkWallet);
        VeriTradeLocalIdentityRegistry id = new VeriTradeLocalIdentityRegistry();
        vm.prank(aliceAddr);
        uint256 aid = id.register("u");
        vm.prank(aliceAddr);
        id.setAgentWalletAsOwner(aid, walletAddr);
        address newWallet = address(0xCAFE);
        uint256 nonce = id.walletNonce(aid);
        bytes32 digest = id.digestSetAgentWallet(aid, newWallet, nonce);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(pkWallet, digest);
        bytes memory sig = abi.encodePacked(r, s, v);
        id.setAgentWalletWithSig(aid, newWallet, nonce, sig);
        assertEq(id.agentWallet(aid), newWallet);
    }

    function testValidation_onlyValidatorMayRespond() public {
        VeriTradeLocalIdentityRegistry id = new VeriTradeLocalIdentityRegistry();
        VeriTradeLocalValidationRegistry v = new VeriTradeLocalValidationRegistry(address(id));

        bytes32 reqHash = keccak256("payload");
        vm.prank(alice);
        v.validationRequest(bob, 7, "https://example/request.json", reqHash);

        vm.prank(alice);
        vm.expectRevert();
        v.validationResponse(reqHash, 1, "", bytes32(0), "fail");

        vm.prank(bob);
        v.validationResponse(reqHash, 88, "ipfs://resp", keccak256("body"), "ok");

        (address val, uint256 agentId, uint8 resp, bytes32 rh, string memory tag,) = v.getValidationStatus(reqHash);
        assertEq(val, bob);
        assertEq(agentId, 7);
        assertEq(resp, 88);
        assertEq(rh, keccak256("body"));
        assertEq(tag, "ok");
    }

    function testReputation_revokeRequiresIssuedIndex() public {
        VeriTradeLocalIdentityRegistry id = new VeriTradeLocalIdentityRegistry();
        VeriTradeLocalReputationRegistry r = new VeriTradeLocalReputationRegistry(address(id));

        vm.prank(alice);
        r.giveFeedback(1, 10, 0, "t1", "t2", "https://x", "ipfs://f", keccak256("fh"));

        vm.prank(alice);
        vm.expectRevert();
        r.revokeFeedback(1, 1);

        vm.prank(alice);
        r.revokeFeedback(1, 0);
    }

    function testReputation_feedbackCountTracksIssued() public {
        VeriTradeLocalIdentityRegistry id = new VeriTradeLocalIdentityRegistry();
        VeriTradeLocalReputationRegistry r = new VeriTradeLocalReputationRegistry(address(id));
        assertEq(r.feedbackCount(alice, 1), 0);
        vm.prank(alice);
        r.giveFeedback(1, 1, 0, "a", "b", "e", "f", bytes32(0));
        assertEq(r.feedbackCount(alice, 1), 1);
        vm.prank(alice);
        r.giveFeedback(1, 2, 0, "a", "b", "e", "f", bytes32(0));
        assertEq(r.feedbackCount(alice, 1), 2);
    }

    function testReputation_getFeedback_roundTrip() public {
        VeriTradeLocalIdentityRegistry id = new VeriTradeLocalIdentityRegistry();
        VeriTradeLocalReputationRegistry r = new VeriTradeLocalReputationRegistry(address(id));
        bytes32 fh = keccak256("payload");
        vm.prank(alice);
        r.giveFeedback(7, 42, 2, "t1", "t2", "https://ep", "ipfs://fb", fh);
        (int128 v, uint8 dec, string memory g1, string memory g2, string memory ep, string memory uri, bytes32 h) =
            r.getFeedback(alice, 7, 0);
        assertEq(v, 42);
        assertEq(dec, 2);
        assertEq(g1, "t1");
        assertEq(g2, "t2");
        assertEq(ep, "https://ep");
        assertEq(uri, "ipfs://fb");
        assertEq(h, fh);
    }

    function testEip1271_magicValueForOwnerSignature() public {
        uint256 pk = uint256(0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80);
        address owner = vm.addr(pk);
        VeriTradeEip1271IntentAdapter adapter = new VeriTradeEip1271IntentAdapter(owner);
        bytes32 digest = keccak256("any structured intent digest");
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(pk, digest);
        bytes memory sig = abi.encodePacked(r, s, v);
        assertEq(adapter.isValidSignature(digest, sig), bytes4(0x1626ba7e));
    }

    function testEip1271_wrongSignerReturnsInvalidMagic() public {
        uint256 pkOwner = uint256(0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80);
        uint256 pkOther = uint256(0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d);
        address owner = vm.addr(pkOwner);
        VeriTradeEip1271IntentAdapter adapter = new VeriTradeEip1271IntentAdapter(owner);
        bytes32 digest = keccak256("intent");
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(pkOther, digest);
        bytes memory sig = abi.encodePacked(r, s, v);
        assertEq(adapter.isValidSignature(digest, sig), bytes4(0xffffffff));
    }

    /// @dev Compliance-evidence chain: identity mint → validation request/response → reputation feedback (local semantics).
    function testComplianceEvidence_identityValidationReputationChain() public {
        VeriTradeLocalIdentityRegistry id = new VeriTradeLocalIdentityRegistry();
        VeriTradeLocalValidationRegistry v = new VeriTradeLocalValidationRegistry(address(id));
        VeriTradeLocalReputationRegistry rep = new VeriTradeLocalReputationRegistry(address(id));

        vm.prank(alice);
        uint256 aid = id.register("https://example/agent-registration.json");
        assertEq(aid, 1);

        bytes32 reqHash = keccak256("veritrade-compliance-evidence-v1");
        vm.prank(alice);
        v.validationRequest(bob, aid, "ipfs://request", reqHash);

        vm.prank(alice);
        vm.expectRevert();
        v.validationResponse(reqHash, 1, "", bytes32(0), "fail");

        bytes32 rh = keccak256("response-body");
        vm.prank(bob);
        v.validationResponse(reqHash, 42, "ipfs://response", rh, "pass");

        (address val, uint256 agentIdOut, uint8 resp, bytes32 responseHash, string memory tag, uint256 lastUpdate) =
            v.getValidationStatus(reqHash);
        assertEq(val, bob);
        assertEq(agentIdOut, aid);
        assertEq(resp, 42);
        assertEq(responseHash, rh);
        assertEq(tag, "pass");
        assertGt(lastUpdate, 0);

        vm.prank(alice);
        rep.giveFeedback(aid, 9, 0, "t1", "t2", "https://endpoint", "ipfs://fb", keccak256("fh"));
    }
}
