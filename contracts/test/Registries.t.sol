// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

import {Base} from "./helpers/Base.sol";
import {RouterRegistry} from "../src/RouterRegistry.sol";
import {SignerSetRegistry} from "../src/SignerSetRegistry.sol";
import {TokenPolicyRegistry} from "../src/TokenPolicyRegistry.sol";
import {PaymentRouter} from "../src/PaymentRouter.sol";
import "../src/Errors.sol";

/// The registries on their own: the router lifecycle and its notice periods, the signer sets (rotation, emergency removal, the O(1) check and
/// the bound MAX_SIGNERS_PER_SET), the token policy, the merchants and the executors.
contract RegistriesTest is Base {
    // ------------------------------------------------------------------------------------------------------------ RouterRegistry
    function test_Router_ModeIsDerivedFromTheState() public {
        assertEq(routers.mode(address(routerA)), 0);
        vm.prank(gov);
        routers.deprecate(address(routerA), address(routerB), 0, 0);
        assertEq(routers.mode(address(routerA)), 0, "deprecated for a standard reason: still trusted");
        PaymentRouter c = _newRouter();
        vm.startPrank(gov);
        routers.propose(address(c), address(c).codehash, 3);
        vm.stopPrank();
        assertEq(routers.mode(address(c)), 1, "a candidate is not trusted (fail closed)");
        assertEq(routers.mode(address(0x1234)), 1, "an unknown address is not trusted");
    }

    function test_Router_SecurityDeprecationIsEmergencyMode_WithTheShorterNotice() public {
        vm.prank(gov);
        routers.deprecate(address(routerA), address(routerB), 1, 0);
        assertEq(routers.mode(address(routerA)), 1);
        (, , , , , uint64 notBefore,,) = routers.routers(address(routerA));
        assertEq(notBefore, START + routers.MIN_NOTICE_SECURITY());
    }

    function test_Router_NoticeMinimums() public {
        uint64 shortNotice = uint64(START + routers.MIN_NOTICE_STANDARD() - 1);
        uint64 enough = uint64(START + routers.MIN_NOTICE_STANDARD());
        vm.prank(gov);
        vm.expectRevert(NoticeTooShort.selector);
        routers.deprecate(address(routerA), address(routerB), 0, shortNotice);
        vm.prank(gov);
        routers.deprecate(address(routerA), address(routerB), 0, enough);
    }

    function test_Router_SunsetAndRetentionBeforeRetire() public {
        vm.prank(gov);
        routers.deprecate(address(routerA), address(routerB), 0, 0);
        vm.prank(gov);
        vm.expectRevert(NotYetSunset.selector);
        routers.sunset(address(routerA));
        vm.warp(START + routers.MIN_NOTICE_STANDARD());
        vm.prank(gov);
        routers.sunset(address(routerA));
        assertFalse(routers.isChargeable(address(routerA)));
        assertFalse(routers.isBindable(address(routerA)));
        vm.prank(gov);
        vm.expectRevert(RetentionNotElapsed.selector);
        routers.retire(address(routerA));
        vm.warp(block.timestamp + routers.RETENTION());
        vm.prank(gov);
        routers.retire(address(routerA));
        assertEq(routers.mode(address(routerA)), 1);
    }

    function test_Router_RollbackWindowEndsBindability_ButNotChargeability() public {
        vm.prank(gov);
        routers.deprecate(address(routerA), address(routerB), 0, 0);
        assertTrue(routers.isBindable(address(routerA)));
        vm.warp(START + routers.ROLLBACK_WINDOW() + 1);
        assertFalse(routers.isBindable(address(routerA)), "no new mandate may bind to a deprecated router after the window");
        assertTrue(routers.isChargeable(address(routerA)), "but existing mandates keep charging until the sunset");
    }

    function test_Router_AtMostTwoLiveRouters() public {
        PaymentRouter c = _newRouter();
        vm.startPrank(gov);
        routers.propose(address(c), address(c).codehash, 3);
        vm.expectRevert(TooManyLiveRouters.selector);
        routers.activate(address(c));
        routers.deprecate(address(routerA), address(routerB), 0, 0); // deprecated routers still count as live
        vm.expectRevert(TooManyLiveRouters.selector);
        routers.activate(address(c));
        vm.warp(START + routers.MIN_NOTICE_STANDARD());
        routers.sunset(address(routerA)); // a sunset router frees a slot
        routers.activate(address(c));
        vm.stopPrank();
        assertEq(routers.liveRouters(), 2);
    }

    function test_Router_DeprecateNeedsAnActiveSuccessor() public {
        PaymentRouter c = _newRouter();
        vm.startPrank(gov);
        routers.propose(address(c), address(c).codehash, 3);
        vm.expectRevert(SuccessorNotActive.selector);
        routers.deprecate(address(routerA), address(c), 0, 0);
        vm.expectRevert(SuccessorNotActive.selector);
        routers.deprecate(address(routerA), address(routerA), 0, 0);
        vm.stopPrank();
    }

    function test_Router_GuardianCanOnlyDisable_AndGovernanceRestores() public {
        vm.prank(guardian);
        routers.emergencyDisable(address(routerA));
        assertEq(routers.mode(address(routerA)), 1);
        assertFalse(routers.isChargeable(address(routerA)));
        vm.prank(guardian);
        vm.expectRevert(NotGovernance.selector);
        routers.clearEmergency(address(routerA));
        vm.prank(guardian);
        vm.expectRevert(NotGovernance.selector);
        routers.activate(address(routerA));
        vm.prank(gov);
        routers.clearEmergency(address(routerA));
        assertTrue(routers.isChargeable(address(routerA)));
        assertEq(routers.liveRouters(), 2, "the live counter is exact across disable and restore");
    }

    function test_Router_OnlyGovernanceMovesTheLifecycle() public {
        vm.startPrank(stranger);
        vm.expectRevert(NotGovernance.selector);
        routers.propose(address(0x1), bytes32(0), 1);
        vm.expectRevert(NotGovernance.selector);
        routers.deprecate(address(routerA), address(routerB), 0, 0);
        vm.expectRevert(NotAuthorized.selector);
        routers.emergencyDisable(address(routerA));
        vm.stopPrank();
    }

    // ------------------------------------------------------------------------------------------------------------ SignerSetRegistry
    function _members(uint256 n, uint256 seed) internal pure returns (address[] memory m) {
        m = new address[](n);
        for (uint256 i = 0; i < n; ++i) {
            m[i] = address(uint160(uint256(keccak256(abi.encode(seed, i)))));
        }
    }

    function test_Signers_TheSetSizeIsBounded() public {
        vm.startPrank(gov);
        signerSets.proposeSignerSet(2, _members(16, 1)); // the maximum
        vm.expectRevert(abi.encodeWithSelector(TooManySigners.selector, 17, 16));
        signerSets.proposeSignerSet(3, _members(17, 2));
        vm.stopPrank();
        assertEq(signerSets.MAX_SIGNERS_PER_SET(), 16);
    }

    /// The gas of one cold `verifySigner` against a registry whose active set has `n` members (the key being checked is the last one).
    function _verifyGas(uint256 n) internal returns (uint256 used) {
        SignerSetRegistry reg = new SignerSetRegistry(gov, guardian, MAX_QUOTE_TTL, MAX_QUOTE_TTL);
        address[] memory m = _members(n, n);
        m[n - 1] = quoteSigner;
        vm.startPrank(gov);
        reg.proposeSignerSet(1, m);
        reg.activateSignerSet(1);
        vm.stopPrank();
        vm.warp(block.timestamp + 1);
        vm.cool(address(reg)); // every account and slot starts cold, as in a real transaction
        uint256 g = gasleft();
        reg.verifySigner(quoteSigner, 1, uint64(block.timestamp - 1));
        used = g - gasleft();
    }

    function test_Signers_VerifyIsConstantGas_WhateverTheSizeOfTheSet() public {
        uint256 g1 = _verifyGas(1);
        uint256 g2 = _verifyGas(2);
        uint256 g8 = _verifyGas(8);
        uint256 g16 = _verifyGas(16);
        emit log_named_uint("verifySigner gas, set of 1", g1);
        emit log_named_uint("verifySigner gas, set of 2", g2);
        emit log_named_uint("verifySigner gas, set of 8", g8);
        emit log_named_uint("verifySigner gas, set of 16", g16);
        assertEq(g1, g2, "O(1)");
        assertEq(g1, g8, "O(1)");
        assertEq(g1, g16, "O(1)");
    }

    function test_Signers_EmergencyRemovalHasNoGraceAndIsPermanent() public {
        vm.prank(guardian);
        signerSets.removeQuoteSigner(quoteSigner);
        vm.expectRevert(QuoteSignerRemoved.selector);
        signerSets.verifySigner(quoteSigner, 1, uint64(START));
        assertEq(signerSets.removedAt(quoteSigner), START);
        vm.warp(START + 1 days);
        vm.prank(guardian);
        signerSets.removeQuoteSigner(quoteSigner); // idempotent: the first timestamp stays
        assertEq(signerSets.removedAt(quoteSigner), START);
    }

    function test_Signers_TheGuardianCannotAddOrActivate() public {
        address[] memory m = _members(1, 3);
        vm.startPrank(guardian);
        vm.expectRevert(NotGovernance.selector);
        signerSets.proposeSignerSet(2, m);
        vm.expectRevert(NotGovernance.selector);
        signerSets.activateSignerSet(1);
        vm.stopPrank();
    }

    function test_Signers_SetsActivateInOrder_AndAKeyRemovedAfterTheProposalCannotJoin() public {
        address[] memory m = new address[](1);
        m[0] = makeAddr("newSigner");
        vm.startPrank(gov);
        signerSets.proposeSignerSet(3, m);
        vm.expectRevert(SignerSetVersionOrder.selector);
        signerSets.activateSignerSet(3); // 2 comes first
        signerSets.proposeSignerSet(2, m);
        vm.stopPrank();
        vm.prank(guardian);
        signerSets.removeQuoteSigner(m[0]);
        vm.prank(gov);
        vm.expectRevert(abi.encodeWithSelector(QuoteSignerTombstoned.selector, m[0]));
        signerSets.activateSignerSet(2);
        vm.expectRevert(SignerSetVersionOrder.selector);
        vm.prank(gov);
        signerSets.proposeSignerSet(2, _members(1, 9)); // a version can be proposed once
    }

    function test_Signers_GraceBoundsAreImmutableAndChecked() public {
        vm.expectRevert(InvalidBounds.selector);
        new SignerSetRegistry(gov, guardian, 300, 299);
        vm.expectRevert(InvalidBounds.selector);
        new SignerSetRegistry(gov, guardian, 300, 601);
        new SignerSetRegistry(gov, guardian, 300, 600);
    }

    // ------------------------------------------------------------------------------------------------------------ TokenPolicyRegistry
    function test_Token_ListingAndStatus() public {
        MockTok t = new MockTok();
        vm.startPrank(gov);
        vm.expectRevert(TokenNotListed.selector);
        policy.list(address(t), 3, 6); // SWAP_ONLY cannot be listed in v1
        vm.expectRevert(TokenNotListed.selector);
        policy.list(address(t), 4, 6); // nor BLOCKED
        vm.expectRevert(InvalidBounds.selector);
        policy.list(address(t), 1, 37);
        policy.list(address(t), 2, 6);
        vm.expectRevert(WrongRouterState.selector);
        policy.list(address(t), 1, 6); // once
        uint64 v = policy.tokenVersion(address(t));
        policy.setStatus(address(t), 1);
        assertEq(policy.tokenVersion(address(t)), v + 1, "every change of policy bumps the token version");
        vm.stopPrank();
    }

    function test_Token_AGuardianBlockIsFinal() public {
        vm.prank(guardian);
        policy.block_(address(usdc));
        assertEq(policy.status(address(usdc)), 4);
        vm.prank(gov);
        vm.expectRevert(TokenNotListed.selector);
        policy.setStatus(address(usdc), 1);
        vm.prank(guardian);
        vm.expectRevert(NotGovernance.selector);
        policy.setStatus(address(usdc), 1);
        vm.prank(guardian);
        vm.expectRevert(NotGovernance.selector);
        policy.publishBounds(address(usdc), USD, 99e18, 101e18);
    }

    function test_Token_BoundsVersionsAreAppendOnly() public {
        (bool p1, uint256 min1, uint256 max1) = policy.bandOf(address(usdc), USD, 1);
        vm.startPrank(gov);
        assertEq(policy.publishBounds(address(usdc), USD, 99e18, 101e18), 2);
        assertEq(policy.publishBounds(address(usdc), USD, 97e18, 101e18), 3);
        vm.stopPrank();
        (bool p1b, uint256 min1b, uint256 max1b) = policy.bandOf(address(usdc), USD, 1);
        assertTrue(p1 && p1b);
        assertEq(min1, min1b);
        assertEq(max1, max1b);
        (bool p9,,) = policy.bandOf(address(usdc), USD, 9);
        assertFalse(p9);
        assertEq(policy.currentBoundsVersion(address(usdc), USD), 3);
    }

    function test_Token_OnlyTheGuardianOrGovernanceBlocks() public {
        vm.prank(stranger);
        vm.expectRevert(NotAuthorized.selector);
        policy.block_(address(usdc));
        vm.prank(gov);
        policy.block_(address(usdc));
        assertEq(policy.status(address(usdc)), 4);
    }

    function test_Bounds_APublicationBumpsTheTokenVersion() public {
        uint64 v = policy.tokenVersion(address(usdc));
        vm.prank(gov);
        policy.publishBounds(address(usdc), USD, 99e18, 101e18);
        assertEq(policy.tokenVersion(address(usdc)), v + 1, "a quote for the old token version is stale (Q14)");
    }

    function test_Signers_OnlyTheGuardianOrGovernanceRemoveAKey() public {
        vm.prank(stranger);
        vm.expectRevert(NotAuthorized.selector);
        signerSets.removeQuoteSigner(quoteSigner);
        vm.prank(stranger);
        vm.expectRevert(NotAuthorized.selector);
        signerSets.stopSignerSet(1);
    }

    function test_Signers_TheGraceBoundaries() public {
        address[] memory m = new address[](1);
        m[0] = quoteSigner;
        vm.startPrank(gov);
        signerSets.proposeSignerSet(2, m);
        vm.warp(START + 100);
        signerSets.activateSignerSet(2); // set 1 is retired at START + 100; the grace is 300 seconds
        vm.stopPrank();
        uint64 before_ = uint64(START + 99);
        vm.warp(START + 400); // the last second of the grace
        signerSets.verifySigner(quoteSigner, 1, before_);
        vm.warp(START + 401);
        vm.expectRevert(QuoteSignerSetRetired.selector);
        signerSets.verifySigner(quoteSigner, 1, before_);
        // a quote issued at or after the retirement is refused under the retired set even inside the grace
        vm.warp(START + 200);
        vm.expectRevert(QuoteSignerSetRetired.selector);
        signerSets.verifySigner(quoteSigner, 1, uint64(START + 100));
        signerSets.verifySigner(quoteSigner, 1, uint64(START + 99));
    }

    function test_Router_ConstantsAreTheProposalsOfTheRecords() public view {
        assertEq(routers.MIN_NOTICE_STANDARD(), 180 days, "PC-01");
        assertEq(routers.MIN_NOTICE_SECURITY(), 60 days, "PC-02");
        assertEq(routers.RETENTION(), 365 days, "PC-03");
        assertEq(routers.MAX_LIVE_ROUTERS(), 2, "PC-12");
        assertEq(merchantReg.MIN_RECIPIENT_CHANGE_DELAY(), 48 hours, "PC-17");
        assertEq(signerSets.quoteSetGrace(), MAX_QUOTE_TTL, "PC-08 in this configuration");
    }

    // ------------------------------------------------------------------------------------------------------------ merchants, executors, fees
    function test_Merchant_RegistrationAndRoles() public {
        vm.prank(stranger);
        vm.expectRevert(NotGovernance.selector);
        merchantReg.register(keccak256("m2"), stranger, stranger, address(0));
        vm.prank(gov);
        vm.expectRevert(AlreadyRegistered.selector);
        merchantReg.register(MERCHANT, stranger, stranger, address(0));
        vm.prank(stranger);
        vm.expectRevert(NotMerchantAdmin.selector);
        merchantReg.proposeRecipient(MERCHANT, stranger);
        vm.prank(stranger);
        vm.expectRevert(NotAuthorized.selector);
        merchantReg.pauseMerchant(MERCHANT);
    }

    function test_Merchant_TheRecipientDelayIsEnforced_AndCancellable() public {
        address w = makeAddr("w");
        vm.startPrank(merchantAdmin);
        vm.expectRevert(NoPendingRecipient.selector);
        merchantReg.acceptRecipient(MERCHANT);
        merchantReg.proposeRecipient(MERCHANT, w);
        vm.warp(START + merchantReg.MIN_RECIPIENT_CHANGE_DELAY() - 1);
        vm.expectRevert(RecipientChangeNotReady.selector);
        merchantReg.acceptRecipient(MERCHANT);
        vm.warp(START + merchantReg.MIN_RECIPIENT_CHANGE_DELAY());
        merchantReg.acceptRecipient(MERCHANT);
        vm.stopPrank();
        assertEq(merchantReg.settlement(MERCHANT, address(usdc)), w);
        vm.startPrank(merchantAdmin);
        merchantReg.proposeRecipient(MERCHANT, merchantWallet);
        merchantReg.cancelRecipient(MERCHANT);
        vm.expectRevert(NoPendingRecipient.selector);
        merchantReg.acceptRecipient(MERCHANT);
        vm.stopPrank();
    }

    function test_Merchant_DeactivationStopsSettlement() public {
        vm.prank(gov);
        merchantReg.deactivate(MERCHANT);
        vm.expectRevert(MerchantInactive.selector);
        merchantReg.settlement(MERCHANT, address(usdc));
        vm.expectRevert(UnknownMerchant.selector);
        merchantReg.settlement(keccak256("nobody"), address(usdc));
    }

    function test_Executors_GovernanceAdds_GuardianRemoves() public {
        address e = makeAddr("e2");
        vm.prank(guardian);
        vm.expectRevert(NotGovernance.selector);
        execReg.add(e);
        vm.prank(gov);
        execReg.add(e);
        assertTrue(execReg.isExecutor(e));
        vm.prank(guardian);
        execReg.remove(e);
        assertFalse(execReg.isExecutor(e));
        vm.prank(stranger);
        vm.expectRevert(NotAuthorized.selector);
        execReg.remove(executor);
    }

    function test_Fees_TheCeilingIsImmutableAndBelowFullScale() public {
        assertEq(feeCtl.ceilingBps(), FEE_CEILING);
        FeeCtlProbe probe = new FeeCtlProbe();
        vm.expectRevert(FeeAboveCeiling.selector);
        probe.make(gov, 10_001, 0, feeWallet);
        vm.expectRevert(FeeAboveCeiling.selector);
        probe.make(gov, 100, 101, feeWallet);
        vm.prank(stranger);
        vm.expectRevert(NotGovernance.selector);
        feeCtl.setFee(1, feeWallet);
    }
}

contract MockTok {
    uint8 public constant decimals = 6;
}

import {FeeController} from "../src/FeeController.sol";

contract FeeCtlProbe {
    function make(address g, uint16 ceiling, uint16 fee, address r) external returns (FeeController) {
        return new FeeController(g, ceiling, fee, r);
    }
}
