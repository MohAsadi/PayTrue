// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import "../../src/Errors.sol";
import "../../src/Mutants.sol";
import {Permit2Mock} from "../../src/Permit2Mock.sol";
import {RegistryModel} from "../../src/RegistryModel.sol";
import {PinModel} from "../../src/PinModel.sol";
import {ContainModel} from "../../src/ContainModel.sol";
import {MigrationModel} from "../../src/MigrationModel.sol";

/// A small world for the hand-written tests: the three models, one customer, three routers' worth of addresses, three tokens and the
/// everyday operations (activate with base terms, grant, lockdown, migrate with the authorization a correct client signs). Test
/// contracts call it as an external contract, so a revert inside a model reaches `vm.expectRevert` with the model's own revert data.
contract Fixture {
    Permit2Mock public p2;
    RegistryModel public reg;
    MigrationModel public mgr;

    address public constant CUSTOMER = address(uint160(0xC0FFEE));
    address public constant OTHER_CUSTOMER = address(uint160(0xC0FFEF));
    address public constant R0 = address(uint160(0x1000));
    address public constant R1 = address(uint160(0x1001));
    address public constant R2 = address(uint160(0x1002));
    address public constant T1 = address(uint160(0x7001));
    address public constant T2 = address(uint160(0x7002));
    address public constant T3 = address(uint160(0x7003));
    address public constant T4 = address(uint160(0x7004));
    uint256 public constant FAR = 1_900_000_000;

    uint256 public nextNonce = 1;
    uint256 public nextCreation = 1;
    uint256 public mutant;

    constructor() {
        p2 = new Permit2Mock();
        reg = new RegistryModel();
        mgr = new MigrationModel(p2, reg);
        reg.registerActive(R0, bytes32(uint256(0xC0DE00)), 1, 0);
        reg.registerActive(R1, bytes32(uint256(0xC0DE01)), 2, 0);
    }

    function setMutant(uint256 m) external {
        mutant = m;
    }

    // ---- terms and pins
    function baseTerms(address[] memory tokens) public pure returns (ContainModel.Terms memory t) {
        t.expiresAt = 1_900_000_000;
        t.merchantId = bytes32(uint256(0xA1));
        t.recipientPolicy = bytes32(uint256(0xB1));
        t.subscriptionRef = bytes32(uint256(0xC1));
        t.periodSeconds = 2_592_000;
        t.anchorStartsAt = 1_800_000_000;
        t.currency = 840;
        t.maxQuoteAge = 120;
        t.boundsVersion = 1;
        t.maxChargesPerPeriod = 1;
        t.minInterval = 86_400;
        t.maxFeeBps = 100;
        t.nTokens = uint8(tokens.length);
        for (uint256 i = 0; i < tokens.length; ++i) {
            t.tokens[i] = tokens[i];
            t.caps[i][0] = 50;
            t.caps[i][1] = 1000;
            t.caps[i][4] = 500;
        }
    }

    function one(address a) public pure returns (address[] memory r) {
        r = new address[](1);
        r[0] = a;
    }

    function two(address a, address b) public pure returns (address[] memory r) {
        r = new address[](2);
        r[0] = a;
        r[1] = b;
    }

    function three(address a, address b, address c) public pure returns (address[] memory r) {
        r = new address[](3);
        r[0] = a;
        r[1] = b;
        r[2] = c;
    }

    function eoaPin() public pure returns (PinModel.Pin memory) {
        return PinModel.Pin(1, PinModel.PIN_EOA, address(0), bytes32(0), bytes32(0), 1, 1);
    }

    // ---- Permit2 and registry shortcuts (the customer is the actor)
    function grant(address token, address router, uint256 amount, uint256 expiration) public {
        p2.approveAs(CUSTOMER, token, router, amount, expiration);
    }

    function grantBounded(address token, address router) public {
        p2.approveAs(CUSTOMER, token, router, 100, FAR);
    }

    function lock(address token, address router) public {
        p2.lockdownAs(CUSTOMER, token, router);
    }

    function allowanceOf(address token, address router) public view returns (uint256 amount, uint256 expiration) {
        (uint160 a, uint48 e,) = p2.allowance(CUSTOMER, token, router);
        return (a, e);
    }

    // ---- mandates
    function activate(address router, address[] memory tokens) public returns (bytes32 lid, bytes32 mid) {
        (lid, mid) = mgr.activate(CUSTOMER, nextCreation, router, baseTerms(tokens), eoaPin(), mutant);
        nextCreation += 1;
    }

    function activateTerms(address customer, address router, ContainModel.Terms memory t) public returns (bytes32 lid, bytes32 mid) {
        (lid, mid) = mgr.activate(customer, nextCreation, router, t, eoaPin(), mutant);
        nextCreation += 1;
    }

    function activeOf(bytes32 lid) public view returns (bytes32) {
        return mgr.activeMandateOf(lid);
    }

    function statusOf(bytes32 mid) public view returns (uint8 status, uint8 reason, bool retired) {
        MigrationModel.Mandate memory m = mgr.getMandate(mid);
        return (m.status, m.reason, m.retired);
    }

    /// The authorization of a correct client for a successor of `pid` with the same terms and pin on `newRouter`.
    function authFor(bytes32 pid, uint8 kind, address newRouter, uint256 deadline) public view returns (MigrationModel.Auth memory) {
        return mgr.buildAuth(pid, kind, newRouter, mgr.mandateTerms(pid), mgr.mandatePin(pid), deadline, nextNonce);
    }

    function migrate(bytes32 pid, uint8 kind, address newRouter) public returns (bytes32) {
        return migrateWith(pid, kind, newRouter, block.timestamp + 3600, true);
    }

    function migrateWith(bytes32 pid, uint8 kind, address newRouter, uint256 deadline, bool senderIsCustomer) public returns (bytes32 newId) {
        MigrationModel.Auth memory au = authFor(pid, kind, newRouter, deadline);
        nextNonce += 1;
        newId = mgr.activateSuccessor(
            pid,
            kind,
            newRouter,
            mgr.mandateTerms(pid),
            mgr.mandatePin(pid),
            au,
            MigrationModel.Access(senderIsCustomer, 0, false),
            mutant
        );
    }

    function charge(bytes32 mid, address router, address token, uint256 amount, uint256 cycle) public {
        mgr.consume(router, mid, token, amount, cycle, mgr.mandatePin(mid), mutant);
    }

    function revoke(bytes32 mid) public {
        mgr.revoke(mid, true, mutant);
    }

    function retire(bytes32 mid) public {
        mgr.retire(mid, mutant);
    }

    function live(address router, address token) public view returns (uint256) {
        return mgr.live(CUSTOMER, router, token);
    }

    function authRouter(bytes32 lid, address router) public view returns (bool) {
        return mgr.authRouter(lid, router, mutant);
    }
}
