// SPDX-License-Identifier: UNLICENSED
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

    function test_Deploy_APredictionFromAnotherAccountReverts() public {
        Deploy d = new Deploy();
        // the predicted address is computed for the wrong deployer: the manager lands elsewhere and the script refuses
        vm.expectRevert(Deploy.WrongPrediction.selector);
        d.deploy(makeAddr("somebody else"), _params());
    }
}
