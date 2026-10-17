// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import "../src/Errors.sol";
import {ContainModel} from "../src/ContainModel.sol";
import {MigrationModel} from "../src/MigrationModel.sol";
import {PinModel} from "../src/PinModel.sol";
import {Permit2Mock} from "../src/Permit2Mock.sol";
import {RegistryModel} from "../src/RegistryModel.sol";
import {Fixture} from "./helpers/Fixture.sol";

/// `consume` as it was until finding F-16: the Permit2 pull first, the effects (usage counter, settled cycle) after it. Document 11 section 5
/// orders them the other way (step 7 effects, step 8 interactions). Kept here, as a subclass, to show what the old order allowed.
contract LegacyOrderModel is MigrationModel {
    constructor(Permit2Mock p2_, RegistryModel reg_) MigrationModel(p2_, reg_) {}

    function consume(address router, bytes32 mandateId, address token, uint256 amount, uint256 cycleIndex, PinModel.Pin memory pin, uint256 mutant)
        external
        override
    {
        (bytes32 lid, address c, uint256 total) = _consumeChecks(router, mandateId, token, amount, cycleIndex, pin, mutant);
        p2.pullAs(router, c, token, amount);
        usedTotal[lid][token] = total;
        cycleSettled[lid][cycleEpoch[lid]][cycleIndex] = true;
        cycleCount[lid] += 1;
    }
}

/// Reentrancy through a token callback (document 04 TB-08; document 16 PR-14: Permit2 spends the allowance and then calls the token, and it
/// has no reentrancy guard). The Permit2 mock runs one armed call at the moment where a hostile or hook-bearing token would run its own code.
/// The nested call is made by the test contract with the router's address as an argument; the production manager authenticates msg.sender as
/// the router, so a real attack needs the router to be re-entered as well (the router must have its own lock), and the manager's order of
/// effects is the defence in depth that these tests pin down.
contract ReentrancyTest is Test {
    address internal constant CUSTOMER = address(uint160(0xC0FFEE));
    address internal constant ROUTER = address(uint160(0x1000));
    address internal constant TOKEN = address(uint160(0x7001));
    uint256 internal constant ANCHOR = 1_800_000_000;
    uint256 internal constant PERIOD = 2_592_000;

    Fixture internal fx;
    Permit2Mock internal p2;
    RegistryModel internal reg;

    function setUp() public {
        vm.warp(ANCHOR + 2 * PERIOD + 5);
        fx = new Fixture();
        p2 = new Permit2Mock();
        reg = new RegistryModel();
        reg.registerActive(ROUTER, bytes32(uint256(0xC0DE)), 1, 0);
    }

    function _activate(MigrationModel mgr, uint256 perPayment, uint256 total) internal returns (bytes32 mid) {
        address[] memory toks = new address[](1);
        toks[0] = TOKEN;
        ContainModel.Terms memory t = fx.baseTerms(toks);
        t.caps[0][0] = perPayment;
        t.caps[0][1] = total;
        (, mid) = mgr.activate(CUSTOMER, 1, ROUTER, t, fx.eoaPin(), 0);
        p2.approveAs(CUSTOMER, TOKEN, ROUTER, 1_000, 1_900_000_000);
    }

    function _nested(MigrationModel mgr, bytes32 mid, uint256 amount, uint256 cycle) internal view returns (bytes memory) {
        return abi.encodeCall(MigrationModel.consume, (ROUTER, mid, TOKEN, amount, cycle, fx.eoaPin(), 0));
    }

    function _allowanceLeft() internal view returns (uint256 a) {
        (uint160 amount,,) = p2.allowance(CUSTOMER, TOKEN, ROUTER);
        return amount;
    }

    // ------------------------------------------------------------------------------------------------- the order of document 11 (the model today)
    /// A callback during the pull tries to charge the SAME cycle again: the cycle is already settled.
    function test_Consume_CallbackCannotChargeTheSameCycleTwice() public {
        MigrationModel mgr = new MigrationModel(p2, reg);
        bytes32 mid = _activate(mgr, 50, 1_000);
        (bytes32 lid) = mgr.getMandate(mid).lineageId;
        p2.setHook(address(mgr), _nested(mgr, mid, 10, 0));
        mgr.consume(ROUTER, mid, TOKEN, 10, 0, fx.eoaPin(), 0);
        assertEq(p2.hookCalls(), 1, "the callback ran");
        assertFalse(p2.hookSucceeded(), "the nested charge of the same cycle was refused");
        assertEq(bytes4(p2.hookReturn()), PaymentAlreadySettled.selector);
        assertEq(mgr.usedTotal(lid, TOKEN), 10, "counted once");
        assertEq(_allowanceLeft(), 990, "pulled once");
    }

    /// A callback tries another cycle that would push the total over its cap: the usage of the outer charge is already counted.
    function test_Consume_CallbackCannotExceedTheTotalCap() public {
        MigrationModel mgr = new MigrationModel(p2, reg);
        bytes32 mid = _activate(mgr, 50, 60);
        (bytes32 lid) = mgr.getMandate(mid).lineageId;
        p2.setHook(address(mgr), _nested(mgr, mid, 50, 1));
        mgr.consume(ROUTER, mid, TOKEN, 50, 0, fx.eoaPin(), 0);
        assertFalse(p2.hookSucceeded());
        assertEq(bytes4(p2.hookReturn()), TokenTotalCapExceeded.selector);
        assertEq(mgr.usedTotal(lid, TOKEN), 50);
        assertEq(_allowanceLeft(), 950);
    }

    /// A failing pull undoes the effects: the cycle is not settled and nothing is counted.
    function test_Consume_FailedPullLeavesNoEffect() public {
        MigrationModel mgr = new MigrationModel(p2, reg);
        bytes32 mid = _activate(mgr, 50, 1_000);
        (bytes32 lid) = mgr.getMandate(mid).lineageId;
        p2.lockdownAs(CUSTOMER, TOKEN, ROUTER); // allowance amount 0: the pull reverts after the effects were written
        PinModel.Pin memory pin = fx.eoaPin();
        vm.expectRevert(abi.encodeWithSelector(InsufficientAllowance.selector, 0));
        mgr.consume(ROUTER, mid, TOKEN, 10, 0, pin, 0);
        assertEq(mgr.usedTotal(lid, TOKEN), 0);
        assertFalse(mgr.cycleSettled(lid, mgr.cycleEpoch(lid), 0));
        assertEq(mgr.cycleCount(lid), 0);
    }

    // ------------------------------------------------------------------------------------------------- the old order: what it allowed
    function test_LegacyOrder_CallbackChargedTheSameCycleTwice() public {
        MigrationModel mgr = new LegacyOrderModel(p2, reg);
        bytes32 mid = _activate(mgr, 50, 1_000);
        (bytes32 lid) = mgr.getMandate(mid).lineageId;
        p2.setHook(address(mgr), _nested(mgr, mid, 10, 0));
        mgr.consume(ROUTER, mid, TOKEN, 10, 0, fx.eoaPin(), 0);
        assertTrue(p2.hookSucceeded(), "the old order let the callback charge the same cycle again");
        assertEq(_allowanceLeft(), 980, "20 were pulled for one cycle");
        assertEq(mgr.usedTotal(lid, TOKEN), 10, "while the counter says 10: the cap no longer bounds what was pulled");
    }

    function test_LegacyOrder_CallbackExceededTheTotalCap() public {
        MigrationModel mgr = new LegacyOrderModel(p2, reg);
        bytes32 mid = _activate(mgr, 50, 60);
        p2.setHook(address(mgr), _nested(mgr, mid, 50, 1));
        mgr.consume(ROUTER, mid, TOKEN, 50, 0, fx.eoaPin(), 0);
        assertTrue(p2.hookSucceeded(), "the old order let the callback pull 100 under a total cap of 60");
        assertEq(_allowanceLeft(), 900);
    }
}
