// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

import {Script, console2} from "forge-std/Script.sol";
import {IAllowanceTransfer} from "../src/interfaces/IPermit2.sol";
import {IMandateManager} from "../src/interfaces/IMandateManager.sol";
import {IRouterRegistry} from "../src/interfaces/IRouterRegistry.sol";
import {ISuccessorValidator} from "../src/interfaces/ISuccessorValidator.sol";
import {ITokenPolicyRegistry} from "../src/interfaces/ITokenPolicyRegistry.sol";
import {ISignerSetRegistry} from "../src/interfaces/ISignerSetRegistry.sol";
import {IMerchantRegistry, IExecutorRegistry, IFeeController} from "../src/interfaces/IRegistries.sol";
import {RouterRegistry} from "../src/RouterRegistry.sol";
import {TokenPolicyRegistry} from "../src/TokenPolicyRegistry.sol";
import {SignerSetRegistry} from "../src/SignerSetRegistry.sol";
import {MerchantRegistry} from "../src/MerchantRegistry.sol";
import {ExecutorRegistry} from "../src/ExecutorRegistry.sol";
import {FeeController} from "../src/FeeController.sol";
import {UsageLedger} from "../src/UsageLedger.sol";
import {SuccessorValidator} from "../src/SuccessorValidator.sol";
import {MandateGateway} from "../src/MandateGateway.sol";
import {MigrationQueue} from "../src/MigrationQueue.sol";
import {MandateManager} from "../src/MandateManager.sol";
import {PaymentRouter} from "../src/PaymentRouter.sol";

/// The deployment of one FastPay system on one chain, in the one order that makes the cyclic links work. The manager, the usage ledger, the gateway and
/// the migration queue point at each other through immutable addresses, so the manager's address is PREDICTED from the deployer's nonce and the three
/// contracts that need it are deployed before it; the manager's constructor then receives theirs. The script ends with a check that the links are mutual:
/// a wrong prediction (another transaction sent from the same account in between) makes it revert, it never leaves a half-wired system.
///
/// This is deployment CODE, not a deployment: no address of any chain is recorded anywhere, no role is held by an owner, and the timelock, the guardian and
/// every constant that has no value yet (the fee ceiling, PC-05) must be supplied: there are no defaults. The script is exercised by contracts/test/Deploy.t.sol
/// on a local EVM only.
///
///   FASTPAY_PERMIT2 FASTPAY_GOVERNANCE FASTPAY_GUARDIAN FASTPAY_RISK_AUTHORITY FASTPAY_MAX_QUOTE_TTL FASTPAY_MAX_BAND_WIDTH_BPS FASTPAY_QUOTE_SET_GRACE
///   FASTPAY_FEE_CEILING_BPS FASTPAY_FEE_BPS FASTPAY_FEE_RECIPIENT      forge script script/Deploy.s.sol --rpc-url ... --broadcast
contract Deploy is Script {
    struct Params {
        address permit2; // the canonical Permit2 of the chain (PC-13); the caller checks it against the pinned record
        address governance; // a timelock in production (PC-14)
        address guardian; // stop-only
        address riskAuthority; // the pause authority of the manager
        uint32 maxQuoteTtl; // PC-06
        uint256 maxBandWidthBps; // PC-07
        uint256 quoteSetGrace; // PC-08
        uint16 feeCeilingBps; // PC-05: its value is pending (Finance)
        uint16 feeBps;
        address feeRecipient;
    }

    struct System {
        RouterRegistry routers;
        TokenPolicyRegistry policy;
        SignerSetRegistry signers;
        MerchantRegistry merchants;
        ExecutorRegistry executors;
        FeeController fees;
        UsageLedger ledger;
        SuccessorValidator validator;
        MandateGateway gateway;
        MigrationQueue queue;
        MandateManager manager;
        PaymentRouter router;
    }

    error WrongPrediction();
    error WiringBroken();

    function run() external returns (System memory s) {
        Params memory p = Params({
            permit2: vm.envAddress("FASTPAY_PERMIT2"),
            governance: vm.envAddress("FASTPAY_GOVERNANCE"),
            guardian: vm.envAddress("FASTPAY_GUARDIAN"),
            riskAuthority: vm.envAddress("FASTPAY_RISK_AUTHORITY"),
            maxQuoteTtl: uint32(vm.envUint("FASTPAY_MAX_QUOTE_TTL")),
            maxBandWidthBps: vm.envUint("FASTPAY_MAX_BAND_WIDTH_BPS"),
            quoteSetGrace: vm.envUint("FASTPAY_QUOTE_SET_GRACE"),
            feeCeilingBps: uint16(vm.envUint("FASTPAY_FEE_CEILING_BPS")),
            feeBps: uint16(vm.envUint("FASTPAY_FEE_BPS")),
            feeRecipient: vm.envAddress("FASTPAY_FEE_RECIPIENT")
        });
        vm.startBroadcast();
        (, address deployer,) = vm.readCallers();
        s = deploy(deployer, p);
        vm.stopBroadcast();
        console2.log("MandateManager", address(s.manager));
        console2.log("PaymentRouter ", address(s.router));
    }

    /// Creates the system from `deployer` (the account whose nonce is consumed by the `new` expressions below: the broadcaster, or this contract in a test).
    function deploy(address deployer, Params memory p) public returns (System memory s) {
        uint64 n = vm.getNonce(deployer);
        s.routers = new RouterRegistry(p.governance, p.guardian);
        s.policy = new TokenPolicyRegistry(p.governance, p.guardian, p.maxQuoteTtl, p.maxBandWidthBps);
        s.signers = new SignerSetRegistry(p.governance, p.guardian, p.maxQuoteTtl, p.quoteSetGrace);
        s.merchants = new MerchantRegistry(p.governance, p.guardian);
        s.executors = new ExecutorRegistry(p.governance, p.guardian);
        s.fees = new FeeController(p.governance, p.feeCeilingBps, p.feeBps, p.feeRecipient);

        // six creations are done; the next four are the ledger, the validator, the gateway and the queue, and the manager is the fifth
        address predicted = vm.computeCreateAddress(deployer, n + 6 + 4);
        s.ledger = new UsageLedger(predicted);
        s.validator = new SuccessorValidator(IRouterRegistry(address(s.routers)), IAllowanceTransfer(p.permit2));
        s.gateway = new MandateGateway(IMandateManager(predicted), IRouterRegistry(address(s.routers)));
        s.queue = new MigrationQueue(IMandateManager(predicted), IRouterRegistry(address(s.routers)));
        s.manager = new MandateManager(
            IRouterRegistry(address(s.routers)), ISuccessorValidator(address(s.validator)), s.ledger, address(s.gateway), address(s.queue), p.riskAuthority
        );
        if (address(s.manager) != predicted) revert WrongPrediction();
        s.router = new PaymentRouter(
            IAllowanceTransfer(p.permit2),
            IMandateManager(address(s.manager)),
            IRouterRegistry(address(s.routers)),
            IMerchantRegistry(address(s.merchants)),
            IExecutorRegistry(address(s.executors)),
            IFeeController(address(s.fees)),
            ITokenPolicyRegistry(address(s.policy)),
            ISignerSetRegistry(address(s.signers))
        );
        if (
            s.ledger.manager() != address(s.manager) || address(s.gateway.manager()) != address(s.manager) || address(s.queue.manager()) != address(s.manager)
                || address(s.manager.ledger()) != address(s.ledger) || s.manager.gateway() != address(s.gateway) || s.manager.queue() != address(s.queue)
                || address(s.manager.validator()) != address(s.validator) || address(s.manager.registry()) != address(s.routers)
                || address(s.router.manager()) != address(s.manager)
        ) revert WiringBroken();
    }
}
