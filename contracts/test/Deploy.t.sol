// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import {Deploy} from "../script/Deploy.s.sol";

/// The deployment script on a local EVM: the order, the predicted manager address, the mutual links, and that a disturbed order cannot leave a half-wired system.
contract DeployTest is Test {
    function _params() internal returns (Deploy.Params memory p) {
        p.permit2 = 0x000000000022D473030F116dDEE9F6B43aC78BA3;
        p.governance = makeAddr("governance");
        p.guardian = makeAddr("guardian");
        p.riskAuthority = makeAddr("risk");
        p.maxQuoteTtl = 300;
        p.maxBandWidthBps = 500;
        p.quoteSetGrace = 300;
        p.feeCeilingBps = 100; // TEST value: PC-05 has none
        p.feeBps = 50;
        p.feeRecipient = makeAddr("fees");
    }

    function test_Deploy_WiresTheCyclicLinks_FromAContractDeployer() public {
        Deploy d = new Deploy();
        Deploy.System memory s = d.deploy(address(d), _params());
        assertEq(s.ledger.manager(), address(s.manager));
        assertEq(address(s.gateway.manager()), address(s.manager));
        assertEq(address(s.queue.manager()), address(s.manager));
        assertEq(s.manager.gateway(), address(s.gateway));
        assertEq(s.manager.queue(), address(s.queue));
        assertEq(address(s.manager.ledger()), address(s.ledger));
        assertEq(address(s.router.manager()), address(s.manager));
        assertEq(s.manager.pauseAuthority(), makeAddr("risk"));
        assertLe(address(s.manager).code.length, 22_000);
    }

    function test_Deploy_ASecondSystemFromTheSameDeployerWiresToo_BecauseTheNonceIsReadAtTheCall() public {
        Deploy d = new Deploy();
        d.deploy(address(d), _params());
        // the nonce is read when the call starts, so the second system predicts its own manager address
        Deploy.System memory s2 = d.deploy(address(d), _params());
        assertEq(address(s2.manager.ledger()), address(s2.ledger));
    }

    // ---- the environment of `run()`: PAYTRUE_* first, the legacy FASTPAY_* name as the fallback, no defaults
    string[10] internal keys = ["PERMIT2", "GOVERNANCE", "GUARDIAN", "RISK_AUTHORITY", "MAX_QUOTE_TTL", "MAX_BAND_WIDTH_BPS", "QUOTE_SET_GRACE", "FEE_CEILING_BPS", "FEE_BPS", "FEE_RECIPIENT"];

    /// Sets every variable of one family to a value derived from `seed` and blanks the other family, so no test leaks into the next one.
    function _setFamily(string memory prefix, string memory otherPrefix, uint256 seed) internal {
        for (uint256 i = 0; i < keys.length; i++) {
            vm.setEnv(string.concat(otherPrefix, keys[i]), "");
            bool isAddress = i < 4 || i == 9;
            vm.setEnv(string.concat(prefix, keys[i]), isAddress ? vm.toString(address(uint160(seed + i))) : vm.toString(seed + i));
        }
    }

    /// One test function on purpose: environment variables are process-wide and Foundry runs the tests of a suite in parallel, so separate tests that set the
    /// same variables would race. The four cases below run one after the other and each one sets every variable of both families first.
    function test_Params_ReadThePaytrueNamesThenTheLegacyOnesAndNeverDefault() public {
        Deploy d = new Deploy();

        // 1. only the PAYTRUE_ names are set
        _setFamily("PAYTRUE_", "FASTPAY_", 1000);
        Deploy.Params memory p = d.params();
        assertEq(p.permit2, address(uint160(1000)));
        assertEq(p.governance, address(uint160(1001)));
        assertEq(p.guardian, address(uint160(1002)));
        assertEq(p.riskAuthority, address(uint160(1003)));
        assertEq(p.maxQuoteTtl, 1004);
        assertEq(p.maxBandWidthBps, 1005);
        assertEq(p.quoteSetGrace, 1006);
        assertEq(p.feeCeilingBps, 1007);
        assertEq(p.feeBps, 1008);
        assertEq(p.feeRecipient, address(uint160(1009)));

        // 2. only the legacy FASTPAY_ names are set: they are read
        _setFamily("FASTPAY_", "PAYTRUE_", 2000);
        p = d.params();
        assertEq(p.permit2, address(uint160(2000)));
        assertEq(p.guardian, address(uint160(2002)));
        assertEq(p.maxQuoteTtl, 2004);
        assertEq(p.feeRecipient, address(uint160(2009)));

        // 3. both are set for one variable: the PAYTRUE_ name wins, the others still come from the legacy names
        _setFamily("FASTPAY_", "PAYTRUE_", 3000);
        vm.setEnv("PAYTRUE_FEE_BPS", "77");
        p = d.params();
        assertEq(p.feeBps, 77, "the PAYTRUE_ name is read first");
        assertEq(p.feeCeilingBps, 3007, "the others come from the legacy names");

        // 4. a variable that is set in neither family: there is no default, the script reverts
        _setFamily("PAYTRUE_", "FASTPAY_", 4000);
        vm.setEnv("PAYTRUE_FEE_RECIPIENT", "");
        vm.expectRevert();
        d.params();
    }
    function test_Deploy_APredictionFromAnotherAccountReverts() public {
        Deploy d = new Deploy();
        // the predicted address is computed for the wrong deployer: the manager lands elsewhere and the script refuses
        vm.expectRevert(Deploy.WrongPrediction.selector);
        d.deploy(makeAddr("somebody else"), _params());
    }
}
