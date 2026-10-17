// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

import {Base} from "./helpers/Base.sol";
import {ContainHarness} from "./helpers/ContainHarness.sol";
import {FastPayTypes as T} from "../src/generated/FastPayTypes.sol";
import {PinLib} from "../src/lib/PinLib.sol";
import {IMandateManager} from "../src/interfaces/IMandateManager.sol";
import "../src/Errors.sol";

/// A router that lies about the charge (it passes any amount, fee, token or cycle to the manager) and is listed ACTIVE in the registry.
contract RogueRouter {
    IMandateManager public immutable manager;

    constructor(IMandateManager m) {
        manager = m;
    }

    function consume(bytes32 id, T.MandateTerms calldata t, T.AccountPin calldata p, IMandateManager.ChargeInput calldata c) external {
        manager.consume(id, t, p, c);
    }
}

/// What the manager and the ledger enforce when the router that calls `consume` is dishonest: the caps, the fee bound, the token set, settle-once and the
/// rule that a fiat-capped mandate needs a fiat value. (The quote itself is the router's job: a router that lies about the fiat value is a defect of that
/// router version, which is why router code is immutable, audited and registry-listed.)
contract RogueRouterTest is Base {
    RogueRouter rogue;
    bytes32 lid;
    bytes32 mid;

    function setUp() public override {
        super.setUp();
        rogue = new RogueRouter(IMandateManager(address(manager)));
        vm.startPrank(gov);
        routers.emergencyDisable(address(routerB)); // frees a live slot
        routers.propose(address(rogue), address(rogue).codehash, 9);
        routers.activate(address(rogue));
        vm.stopPrank();
        (lid, mid) = _activate(customer, 1, address(rogue), _terms(address(usdc)), _pin());
    }

    function _c(uint256 amount, uint256 fee, bool hasFiat, uint64 fiat, address tok, uint256 cycle) internal pure returns (IMandateManager.ChargeInput memory c) {
        c.token = tok;
        c.amount = amount;
        c.cycleIndex = cycle;
        c.feeAmount = fee;
        c.hasFiat = hasFiat;
        c.fiatValueMinor = fiat;
    }

    function _consume(IMandateManager.ChargeInput memory c) internal {
        rogue.consume(mid, _terms(address(usdc)), _pin(), c);
    }

    function test_Rogue_AFiatCappedMandateNeedsAFiatValue() public {
        vm.expectRevert(FiatQuoteRequired.selector);
        _consume(_c(10e6, 0, false, 0, address(usdc), 0));
        _consume(_c(10e6, 0, true, 1_000, address(usdc), 0)); // with a value it goes through
    }

    function test_Rogue_TheCapsHoldWhateverTheRouterSays() public {
        vm.expectRevert(TokenPerPaymentCapExceeded.selector);
        _consume(_c(100e6 + 1, 0, true, 1, address(usdc), 0));
        vm.expectRevert(FiatPerPaymentCapExceeded.selector);
        _consume(_c(10e6, 0, true, 10_001, address(usdc), 0));
    }

    function test_Rogue_TheFeeBoundOfTheMandateHolds() public {
        vm.expectRevert(FeeTooHigh.selector);
        _consume(_c(100e6, 1_000_001, true, 1, address(usdc), 0)); // the mandate allows 100 bps: 1,000,000
    }

    function test_Rogue_TheTokenMustBeInTheMandate() public {
        vm.expectRevert(TokenNotInMandate.selector);
        _consume(_c(10e6, 0, true, 1, address(dai), 0));
    }

    function test_Rogue_ACycleSettlesOnce() public {
        _consume(_c(10e6, 0, true, 1, address(usdc), 0));
        vm.warp(START + 2 hours);
        vm.expectRevert(PaymentAlreadySettled.selector);
        _consume(_c(10e6, 0, true, 1, address(usdc), 0));
    }

    function test_Rogue_ARouterCannotConsumeAMandateBoundToAnother() public {
        (, bytes32 other) = _activate(customer, 2, address(routerA), _terms(address(usdc)), _pin());
        vm.expectRevert(WrongRouter.selector);
        rogue.consume(other, _terms(address(usdc)), _pin(), _c(10e6, 0, true, 1, address(usdc), 0));
    }
}

/// The pin library, on its own: the well-formedness of each account mode, which field fails PIN_OK, and the version rule of a successor.
contract PinLibTest is Base {
    ContainHarness h;

    function setUp() public override {
        super.setUp();
        h = new ContainHarness();
    }

    function _eoa(uint8 sm) internal pure returns (T.AccountPin memory p) {
        p = T.AccountPin({accountMode: 1, accountCodeHash: T.PIN_EOA, delegate: address(0), delegateCodeHash: 0, implementationFamily: 0, pinVersion: 1, signatureMode: sm});
    }

    function _7702() internal returns (T.AccountPin memory p) {
        address d = makeAddr("delegate");
        p = T.AccountPin({
            accountMode: 2,
            accountCodeHash: PinLib.designatorHash(d),
            delegate: d,
            delegateCodeHash: keccak256("delegate code"),
            implementationFamily: keccak256("family"),
            pinVersion: 1,
            signatureMode: 0
        });
    }

    function test_WellFormed_EoaModes() public view {
        assertTrue(h.wellFormed(_eoa(0)));
        assertTrue(h.wellFormed(_eoa(1)));
        assertFalse(h.wellFormed(_eoa(2)), "an EOA has no ERC-1271 path");
        T.AccountPin memory p = _eoa(1);
        p.pinVersion = 0;
        assertFalse(h.wellFormed(p));
        p = _eoa(1);
        p.accountCodeHash = keccak256("something");
        assertFalse(h.wellFormed(p));
        p = _eoa(1);
        p.delegate = address(1);
        assertFalse(h.wellFormed(p));
    }

    function test_WellFormed_DelegatedAccount() public {
        assertTrue(h.wellFormed(_7702()));
        T.AccountPin memory p = _7702();
        p.accountCodeHash = keccak256("not the designator");
        assertFalse(h.wellFormed(p), "the account code hash must be the designator hash of the delegate");
        p = _7702();
        p.delegateCodeHash = bytes32(0);
        assertFalse(h.wellFormed(p));
        p = _7702();
        p.implementationFamily = bytes32(0);
        assertFalse(h.wellFormed(p));
    }

    function test_CheckField_ReportsTheFieldThatMoved() public {
        T.AccountPin memory p = _7702();
        assertEq(h.checkField(p, p.accountCodeHash, p.delegateCodeHash), 0);
        assertEq(h.checkField(p, keccak256("other account code"), p.delegateCodeHash), 1);
        assertEq(h.checkField(p, p.accountCodeHash, keccak256("other delegate code")), 2, "the delegate's code changed behind the same designator");
        assertEq(h.checkField(_eoa(1), bytes32(0), bytes32(0)), 0);
        assertEq(h.checkField(_eoa(1), keccak256("code"), bytes32(0)), 1);
    }

    function test_SuccessorVersion() public view {
        T.AccountPin memory a = _eoa(1);
        T.AccountPin memory b = _eoa(1);
        assertEq(h.nextVersionSuccessor(a, b), 1, "the same pin keeps its version");
        b.signatureMode = 0;
        assertEq(h.nextVersionSuccessor(a, b), 2, "a changed pin goes up by one");
    }
}
