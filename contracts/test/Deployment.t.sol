// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Base} from "./helpers/Base.sol";

/// The deployment itself: the runtime size of every contract against EIP-170 and the target of 22,000 bytes (no code-size-limit override
/// exists in foundry.toml), the predicted cyclic links, the immutable wiring, and the Permit2 under test.
contract DeploymentTest is Base {
    uint256 internal constant TARGET = 22_000;
    uint256 internal constant EIP170 = 24_576;

    function _check(string memory name, address a) internal {
        uint256 n = a.code.length;
        emit log_named_uint(string.concat("runtime bytes ", name), n);
        assertGt(n, 0, name);
        assertLe(n, TARGET, string.concat(name, " exceeds the 22,000-byte target"));
        assertLt(n, EIP170, string.concat(name, " exceeds EIP-170"));
    }

    function test_RuntimeSizes_AreUnderTheTarget() public {
        _check("MandateManager", address(manager));
        _check("MandateGateway", address(gateway));
        _check("UsageLedger", address(ledger));
        _check("SuccessorValidator", address(validator));
        _check("MigrationQueue", address(queue));
        _check("PaymentRouter A", address(routerA));
        _check("RouterRegistry", address(routers));
        _check("TokenPolicyRegistry", address(policy));
        _check("SignerSetRegistry", address(signerSets));
        _check("MerchantRegistry", address(merchantReg));
        _check("ExecutorRegistry", address(execReg));
        _check("FeeController", address(feeCtl));
    }

    function test_Wiring_CyclicLinksAreMutual() public view {
        assertEq(ledger.manager(), address(manager));
        assertEq(address(gateway.manager()), address(manager));
        assertEq(address(queue.manager()), address(manager));
        assertEq(address(manager.ledger()), address(ledger));
        assertEq(manager.gateway(), address(gateway));
        assertEq(manager.queue(), address(queue));
        assertEq(address(manager.validator()), address(validator));
        assertEq(manager.pauseAuthority(), riskService);
    }

    function test_Permit2_IsTheRebuiltCanonicalDeployment() public view {
        assertGt(CANONICAL.code.length, 0);
        assertEq(address(p2), CANONICAL);
    }
}
