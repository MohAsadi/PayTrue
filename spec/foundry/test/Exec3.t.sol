// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import "../src/Errors.sol";
import {MigrationModel} from "../src/MigrationModel.sol";
import {Fixture} from "./helpers/Fixture.sol";

/// The wording of document 12 section 5.5 (Claim 1) as tests: at most ONE router holds executable Layer 3 authority for a mandate
/// lineage, while Layer 2 Permit2 allowances MAY coexist, also on several routers, for sibling mandates.
///
///   Exec3(L)        = { R : some mandate of lineage L is consumable on R }       (Layer 3 only: Permit2 is not consulted)
///   AuthRouters(L)  = { R in Exec3(L) : one of the tokens of that mandate has a usable Permit2 allowance to R }
///   AuthRouters(L) is a subset of Exec3(L), and |Exec3(L)| <= 1.
///
/// The Permit2 allowance (owner, token, spender) belongs to no lineage: it is shared by every mandate of the customer that uses that
/// token on that router. A usable allowance to R is therefore never evidence that R holds authority for L.
contract Exec3Test is Test {
    Fixture internal fx;
    address internal R0;
    address internal R1;
    address internal T1;
    address internal T2;

    function setUp() public {
        vm.warp(1_800_000_000);
        fx = new Fixture();
        R0 = fx.R0();
        R1 = fx.R1();
        T1 = fx.T1();
        T2 = fx.T2();
    }

    function _exec3(bytes32 lid) internal view returns (uint256 n, bool onR0, bool onR1) {
        MigrationModel mgr = fx.mgr();
        uint256 count = mgr.mandateCount(lid);
        for (uint256 i = 0; i < count; ++i) {
            bytes32 id = mgr.lineageMandateIds(lid, i);
            if (mgr.isConsumable(id, R0)) onR0 = true;
            if (mgr.isConsumable(id, R1)) onR1 = true;
        }
        n = (onR0 ? 1 : 0) + (onR1 ? 1 : 0);
    }

    function _usable(address token, address router) internal view returns (bool) {
        (uint256 a, uint256 e) = fx.allowanceOf(token, router);
        return a > 0 && vm.getBlockTimestamp() <= e;
    }

    /// Two sibling lineages share the allowance (customer, T1, R0). Lineage A migrates to R1; lineage B stays on R0. Afterwards the
    /// customer has a usable Permit2 allowance for T1 to BOTH routers, yet each lineage has exactly one router of executable authority.
    function test_Layer2Coexists_Layer3IsExclusive() public {
        fx.grantBounded(T1, R0);
        (bytes32 lidA, bytes32 midA) = fx.activate(R0, fx.two(T1, T2));
        (bytes32 lidB, bytes32 midB) = fx.activate(R0, fx.one(T1));
        fx.grantBounded(T2, R0);
        fx.grantBounded(T1, R1); // the new router must be funded (G1)
        fx.grantBounded(T2, R1);

        // before: both lineages execute on R0 only
        (uint256 nA, bool a0, bool a1) = _exec3(lidA);
        assertEq(nA, 1);
        assertTrue(a0 && !a1);

        // NORMAL migration of A: T1 has a sibling (B) on R0, so the old allowance is kept (bounded); T2 has none, so it must be unusable
        fx.lock(T2, R0);
        bytes32 newA = fx.migrate(midA, 0, R1);

        // Layer 2: two routers hold a usable allowance for T1 at the same time
        assertTrue(_usable(T1, R0), "the allowance to R0 stays: sibling B still relies on it");
        assertTrue(_usable(T1, R1), "the allowance to R1 serves A's successor");

        // Layer 3: exactly one router per lineage
        (uint256 nA2, bool a0b, bool a1b) = _exec3(lidA);
        assertEq(nA2, 1, "|Exec3(A)| = 1");
        assertTrue(!a0b && a1b, "A's executable authority moved to R1");
        (uint256 nB2, bool b0, bool b1) = _exec3(lidB);
        assertEq(nB2, 1, "|Exec3(B)| = 1");
        assertTrue(b0 && !b1, "B's executable authority stays on R0");

        // the usable allowance to R0 is NOT authority for A: A's old mandate is not consumable on R0 and R0 cannot charge it
        assertFalse(fx.mgr().isConsumable(midA, R0));
        vm.expectRevert();
        fx.charge(midA, R0, T1, 1, 1);
        // A's successor charges on R1 only
        assertTrue(fx.mgr().isConsumable(newA, R1));
        vm.expectRevert();
        fx.charge(newA, R0, T1, 1, 1);
        fx.charge(newA, R1, T1, 1, 1);

        // AuthRouters is a subset of Exec3, as defined: R0 holds a usable allowance for T1 but is not an authorized router of A
        assertFalse(fx.authRouter(lidA, R0));
        assertTrue(fx.authRouter(lidA, R1));
        assertTrue(fx.authRouter(lidB, R0));
        assertFalse(fx.authRouter(lidB, R1));
        (midB);
    }

    /// A revision (same router) and a migration never leave two routers with executable authority for one lineage, in any order.
    function test_Exec3_NeverTwoRouters_AcrossAnyChainOfSuccessors() public {
        fx.grantBounded(T1, R0);
        fx.grantBounded(T1, R1);
        (bytes32 lid, bytes32 mid) = fx.activate(R0, fx.one(T1));
        bytes32 cur = mid;
        address router = R0;
        for (uint256 i = 0; i < 12; ++i) {
            uint8 kind = i % 3 == 2 ? 2 : 0; // REVISION, NORMAL, NORMAL, ...
            address target = kind == 2 ? router : (router == R0 ? R1 : R0);
            if (kind == 0) {
                // the old allowance must be unusable (no sibling): the customer's wallet revokes it first
                fx.lock(T1, router);
                fx.grantBounded(T1, target);
            }
            cur = fx.migrate(cur, kind, target);
            router = target;
            (uint256 n,,) = _exec3(lid);
            assertEq(n, 1, "|Exec3(L)| = 1 after every successor");
            assertTrue(fx.mgr().isConsumable(cur, router));
        }
    }
}
