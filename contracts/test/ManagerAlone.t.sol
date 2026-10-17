// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Builders} from "./helpers/Builders.sol";
import {MockERC20} from "./helpers/MockERC20.sol";
import {FastPayTypes as T} from "../src/generated/FastPayTypes.sol";
import {IMandateManager} from "../src/interfaces/IMandateManager.sol";
import {ISuccessorValidator} from "../src/interfaces/ISuccessorValidator.sol";
import "../src/Errors.sol";

/// A validator that accepts everything: it is what a buggy or hostile validator would be at worst (it cannot write, but it can say yes).
contract AcceptAllValidator is ISuccessorValidator {
    function validate(SuccessorContext calldata) external pure {}
}

/// What the MandateManager enforces BY ITSELF when the validator says yes to everything (ADR-021: the invariants stay where the write is). The real
/// validator refuses most of these cases for its own reasons too; here it cannot help, so the test shows what the manager guarantees alone.
contract ManagerAloneTest is Builders {
    bytes32 lid;
    bytes32 m0;

    function _newValidator() internal override returns (ISuccessorValidator) {
        return new AcceptAllValidator();
    }

    function setUp() public override {
        super.setUp();
        (lid, m0) = _activate(customer, 1, address(routerA), _terms(address(usdc)), _pin());
    }

    function _go(IMandateManager.SuccessorRequest memory r) internal returns (bytes32) {
        vm.prank(customer);
        return manager.activateSuccessor(customer, r);
    }

    function _fail(IMandateManager.SuccessorRequest memory r, bytes memory err) internal {
        vm.expectRevert(err);
        vm.prank(customer);
        manager.activateSuccessor(customer, r);
    }

    function _req0(uint8 kind, address newRouter, T.MandateTerms memory nt) internal returns (IMandateManager.SuccessorRequest memory) {
        T.MandateTerms memory pt = _terms(address(usdc));
        T.AccountPin memory p = _pin();
        return _req(pt, p, nt, p, _auth(Sp(lid, m0, bytes32(0), 0, kind, newRouter), pt, nt, p));
    }

    function test_Alone_ASuccessorGoesThrough_WhenTheManagersOwnRulesHold() public {
        bytes32 m1 = _go(_req0(NORMAL, address(routerB), _terms(address(usdc))));
        assertEq(_view(m1).router, address(routerB));
        assertEq(_view(m0).status, 1);
    }

    function test_Alone_TheLineageConstantsCannotChange() public {
        T.MandateTerms memory nt = _terms(address(usdc));
        nt.merchantId = keccak256("another merchant");
        _fail(_req0(NORMAL, address(routerB), nt), abi.encodeWithSelector(LineageConstantsChanged.selector));
        nt = _terms(address(usdc));
        nt.subscriptionRef = keccak256("another subscription");
        _fail(_req0(NORMAL, address(routerB), nt), abi.encodeWithSelector(LineageConstantsChanged.selector));
        nt = _terms(address(usdc));
        nt.anchorStartsAt += 1;
        _fail(_req0(NORMAL, address(routerB), nt), abi.encodeWithSelector(LineageConstantsChanged.selector));
        nt = _terms(address(usdc));
        nt.periodSeconds += 1;
        _fail(_req0(NORMAL, address(routerB), nt), abi.encodeWithSelector(LineageConstantsChanged.selector));
    }

    function test_Alone_TheExposureBoundHoldsInTheIndexItself() public {
        for (uint256 i = 0; i < 8; ++i) {
            MockERC20 t = new MockERC20();
            _activate(customer, 100 + i, address(routerB), _terms(address(t)), _pin());
        }
        assertEq(manager.exposedCount(customer, address(routerB)), 8);
        // the validator says yes to a ninth token on router B; the index refuses
        _fail(_req0(NORMAL, address(routerB), _terms(address(usdc))), abi.encodeWithSelector(ExposureLimit.selector));
        assertEq(_view(m0).status, 0, "nothing of the failed activation was applied");
    }

    function test_Alone_TheManagerBindsTheStoredTermsAndPin() public {
        T.MandateTerms memory nt = _terms(address(usdc));
        IMandateManager.SuccessorRequest memory r = _req0(NORMAL, address(routerB), nt);
        r.predTerms.tokens[0].perPaymentMax += 1;
        _fail(r, abi.encodeWithSelector(TermsHashMismatch.selector));
        r = _req0(NORMAL, address(routerB), nt);
        r.predPin = _pin();
        r.predPin.signatureMode = 0;
        _fail(r, abi.encodeWithSelector(PinHashMismatch.selector));
    }

    function test_Alone_TheCallerRule_TheDeadline_TheNonce_AndTheActivePredecessor() public {
        IMandateManager.SuccessorRequest memory r = _req0(NORMAL, address(routerB), _terms(address(usdc)));
        vm.prank(stranger);
        vm.expectRevert(NotCustomer.selector);
        manager.activateSuccessor(customer, r);
        vm.warp(r.auth.deadline + 1);
        _fail(r, abi.encodeWithSelector(AuthorizationExpired.selector));
        vm.warp(START);
        vm.prank(address(gateway));
        manager.spendNonce(customer, r.auth.nonce);
        _fail(r, abi.encodeWithSelector(AuthorizationReplayed.selector));
        IMandateManager.SuccessorRequest memory r2 = _req0(NORMAL, address(routerB), _terms(address(usdc)));
        vm.prank(customer);
        manager.revoke(customer, m0);
        _fail(r2, abi.encodeWithSelector(WrongPredecessor.selector));
    }

    function test_Alone_TheEffectsAreAllApplied() public {
        vm.prank(customer);
        manager.pause(customer, m0);
        IMandateManager.SuccessorRequest memory r = _req0(NORMAL, address(routerB), _terms(address(usdc)));
        bytes32 m1 = _go(r);
        assertTrue(manager.usedNonce(customer, r.auth.nonce));
        assertEq(_view(m1).pause, 1, "E3: the pause bit is inherited");
        assertEq(_view(m0).reason, 2);
        assertEq(manager.live(customer, address(routerA), address(usdc)), 0);
        assertEq(manager.live(customer, address(routerB), address(usdc)), 1);
        (, uint32 gen,,,, bytes32 active) = manager.lineages(lid);
        assertEq(active, m1);
        assertEq(gen, 1);
    }
}
