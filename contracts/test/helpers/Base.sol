// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import {FastPayTypes as T} from "../../src/generated/FastPayTypes.sol";
import {IMandateManager} from "../../src/interfaces/IMandateManager.sol";
import {IRouterRegistry} from "../../src/interfaces/IRouterRegistry.sol";
import {IAllowanceTransfer} from "../../src/interfaces/IPermit2.sol";
import {ITokenPolicyRegistry} from "../../src/interfaces/ITokenPolicyRegistry.sol";
import {ISignerSetRegistry} from "../../src/interfaces/ISignerSetRegistry.sol";
import {IMerchantRegistry, IExecutorRegistry, IFeeController} from "../../src/interfaces/IRegistries.sol";
import {ISuccessorValidator} from "../../src/interfaces/ISuccessorValidator.sol";
import {RouterRegistry} from "../../src/RouterRegistry.sol";
import {TokenPolicyRegistry} from "../../src/TokenPolicyRegistry.sol";
import {SignerSetRegistry} from "../../src/SignerSetRegistry.sol";
import {MerchantRegistry} from "../../src/MerchantRegistry.sol";
import {ExecutorRegistry} from "../../src/ExecutorRegistry.sol";
import {FeeController} from "../../src/FeeController.sol";
import {UsageLedger} from "../../src/UsageLedger.sol";
import {SuccessorValidator} from "../../src/SuccessorValidator.sol";
import {MandateGateway} from "../../src/MandateGateway.sol";
import {MigrationQueue} from "../../src/MigrationQueue.sol";
import {MandateManager} from "../../src/MandateManager.sol";
import {PaymentRouter} from "../../src/PaymentRouter.sol";
import {MockERC20} from "./MockERC20.sol";

/// The part of Permit2's AllowanceTransfer that the tests call as a customer.
interface IP2 {
    struct TokenSpenderPair {
        address token;
        address spender;
    }

    function approve(address token, address spender, uint160 amount, uint48 expiration) external;
    function lockdown(TokenSpenderPair[] calldata approvals) external;
    function allowance(address owner, address token, address spender) external view returns (uint160, uint48, uint48);
}

/// The whole FastPay system on the rebuilt Permit2 (the creation code of spec/evidence/permit2, deployed through the deterministic
/// deployment proxy exactly as the original was), with named actors and builders for terms, pins, grants, signatures and quotes.
/// Everything is deployed by this contract, so the cyclic links (manager <-> ledger, gateway, queue) are made with predicted CREATE addresses
/// and asserted afterwards.
abstract contract Base is Test {
    // ---- Permit2 evidence
    address internal constant CANONICAL = 0x000000000022D473030F116dDEE9F6B43aC78BA3;
    address internal constant PROXY = 0x4e59b44847b379578588920cA78FbF26c0B4956C;
    bytes32 internal constant SALT = 0x0000000000000000000000000000000000000000d3af2663da51c10215000000;
    bytes internal constant PROXY_CODE =
        hex"7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffe03601600081602082378035828234f58015156039578182fd5b8082525050506014600cf3";

    // ---- constants of the test configuration (test values, not proposals)
    uint256 internal constant START = 1_800_000_000;
    uint32 internal constant MAX_QUOTE_TTL = 300; // PC-06 proposal
    uint256 internal constant BAND_BPS = 500; // PC-07 proposal
    uint16 internal constant FEE_CEILING = 100; // PC-05 has NO proposed value: 1% is a TEST value
    uint64 internal constant PERIOD = 30 days;
    uint16 internal constant USD = 840;
    uint256 internal constant PRICE = 100e18; // 100 minor units (cents) per whole token
    bytes32 internal constant MERCHANT = keccak256("merchant-1");
    bytes32 internal constant SUBSCRIPTION = keccak256("subscription-1");
    bytes32 internal constant SOURCE_SET = keccak256("price-source-set-1");

    // ---- actors
    address internal gov = makeAddr("governance");
    address internal guardian = makeAddr("guardian");
    address internal riskService = makeAddr("risk");
    address internal executor = makeAddr("executor");
    address internal merchantAdmin = makeAddr("merchantAdmin");
    address internal merchantWallet = makeAddr("merchantWallet");
    address internal feeWallet = makeAddr("feeWallet");
    address internal stranger = makeAddr("stranger");
    address internal customer;
    uint256 internal customerKey;
    address internal quoteSigner;
    uint256 internal quoteKey;

    // ---- the system
    IP2 internal p2;
    MockERC20 internal usdc;
    MockERC20 internal dai;
    MockERC20 internal eurc;
    RouterRegistry internal routers;
    TokenPolicyRegistry internal policy;
    SignerSetRegistry internal signerSets;
    MerchantRegistry internal merchantReg;
    ExecutorRegistry internal execReg;
    FeeController internal feeCtl;
    UsageLedger internal ledger;
    ISuccessorValidator internal validator;
    MandateGateway internal gateway;
    MigrationQueue internal queue;
    MandateManager internal manager;
    PaymentRouter internal routerA;
    PaymentRouter internal routerB;

    function setUp() public virtual {
        vm.warp(START);
        (customer, customerKey) = makeAddrAndKey("customer");
        (quoteSigner, quoteKey) = makeAddrAndKey("quoteSigner");
        _deployPermit2();
        usdc = new MockERC20();
        dai = new MockERC20();
        eurc = new MockERC20();
        _deploySystem();
        _configure();
    }

    // ------------------------------------------------------------------------------------------------------------ deployment
    function _deployPermit2() internal virtual {
        bytes memory creation = vm.parseBytes(vm.readFile("../spec/foundry/vectors/permit2-creation-code.hex"));
        vm.etch(PROXY, PROXY_CODE);
        (bool ok, bytes memory out) = PROXY.call(abi.encodePacked(SALT, creation));
        require(ok && out.length == 20 && address(bytes20(out)) == CANONICAL, "Permit2 deployment failed");
        p2 = IP2(CANONICAL);
    }

    /// The fork variant of the suites: fork the chain that ETH_RPC_URL names (at FORK_BLOCK) and use the REAL Permit2 of that chain, the one at the canonical
    /// address, instead of the rebuilt one. Without ETH_RPC_URL the suite is skipped; a chain id other than EXPECT_CHAIN_ID fails.
    function _useRealPermit2() internal {
        string memory url = vm.envOr("ETH_RPC_URL", string(""));
        if (bytes(url).length == 0) {
            vm.skip(true);
            return;
        }
        uint256 blockNo = vm.envOr("FORK_BLOCK", uint256(0));
        if (blockNo == 0) vm.createSelectFork(url);
        else vm.createSelectFork(url, blockNo);
        vm.warp(START); // the fork resets the clock to the block's; the suites are written for START
        require(CANONICAL.code.length > 0, "no Permit2 at the canonical address on this fork");
        uint256 expected = vm.envOr("EXPECT_CHAIN_ID", block.chainid);
        require(block.chainid == expected, "forked chain is not the expected one");
        p2 = IP2(CANONICAL);
    }

    function _deploySystem() internal {
        routers = new RouterRegistry(gov, guardian);
        policy = new TokenPolicyRegistry(gov, guardian, MAX_QUOTE_TTL, BAND_BPS);
        signerSets = new SignerSetRegistry(gov, guardian, MAX_QUOTE_TTL, MAX_QUOTE_TTL);
        merchantReg = new MerchantRegistry(gov, guardian);
        execReg = new ExecutorRegistry(gov, guardian);
        feeCtl = new FeeController(gov, FEE_CEILING, 50, feeWallet);

        uint64 n = vm.getNonce(address(this));
        address predictedManager = vm.computeCreateAddress(address(this), n + 4);
        ledger = new UsageLedger(predictedManager); // n
        validator = _newValidator(); // n + 1
        gateway = new MandateGateway(IMandateManager(predictedManager), IRouterRegistry(address(routers))); // n + 2
        queue = new MigrationQueue(IMandateManager(predictedManager), IRouterRegistry(address(routers))); // n + 3
        manager = new MandateManager(
            IRouterRegistry(address(routers)), validator, ledger, address(gateway), address(queue), riskService
        ); // n + 4
        assertEq(address(manager), predictedManager, "the predicted manager address");
        routerA = _newRouter();
        routerB = _newRouter();
    }

    /// The validator of the system under test: the real one, unless a suite replaces it (to show what the manager enforces by itself).
    function _newValidator() internal virtual returns (ISuccessorValidator) {
        return new SuccessorValidator(IRouterRegistry(address(routers)), IAllowanceTransfer(CANONICAL));
    }

    function _newRouter() internal returns (PaymentRouter) {
        return new PaymentRouter(
            IAllowanceTransfer(CANONICAL),
            IMandateManager(address(manager)),
            IRouterRegistry(address(routers)),
            IMerchantRegistry(address(merchantReg)),
            IExecutorRegistry(address(execReg)),
            IFeeController(address(feeCtl)),
            ITokenPolicyRegistry(address(policy)),
            ISignerSetRegistry(address(signerSets))
        );
    }

    function _configure() internal {
        vm.startPrank(gov);
        routers.propose(address(routerA), address(routerA).codehash, 1);
        routers.activate(address(routerA));
        routers.propose(address(routerB), address(routerB).codehash, 2);
        routers.activate(address(routerB));
        _listToken(address(usdc));
        _listToken(address(dai));
        _listToken(address(eurc));
        address[] memory members = new address[](1);
        members[0] = quoteSigner;
        signerSets.proposeSignerSet(1, members);
        signerSets.activateSignerSet(1);
        merchantReg.register(MERCHANT, merchantAdmin, merchantWallet, address(0));
        execReg.add(executor);
        vm.stopPrank();
        vm.startPrank(merchantAdmin);
        merchantReg.setAccepted(MERCHANT, address(usdc), true);
        merchantReg.setAccepted(MERCHANT, address(dai), true);
        merchantReg.setAccepted(MERCHANT, address(eurc), true);
        vm.stopPrank();
    }

    function _listToken(address tok) internal {
        policy.list(tok, 1, 6);
        policy.setPriceSourceSet(tok, USD, SOURCE_SET);
        policy.publishBounds(tok, USD, 98e18, 102e18);
    }

    // ------------------------------------------------------------------------------------------------------------ builders
    function _pin() internal pure returns (T.AccountPin memory) {
        return T.AccountPin({accountMode: 1, accountCodeHash: T.PIN_EOA, delegate: address(0), delegateCodeHash: 0, implementationFamily: 0, pinVersion: 1, signatureMode: 1});
    }

    function _tokenTerms(address tok) internal pure returns (T.TokenTerms memory) {
        return T.TokenTerms({
            token: tok,
            perPaymentMax: 100e6,
            dayMax: 200e6,
            weekMax: 400e6,
            thirtyDayMax: 600e6,
            periodMax: 500e6,
            totalMax: 5000e6
        });
    }

    /// Fiat caps in cents; the price is 100 cents per token, so these are the token caps divided by one million and times 100.
    function _fiat() internal pure returns (T.FiatTerms memory) {
        return T.FiatTerms({
            currency: USD,
            perPaymentMaxMinor: 10_000,
            dayMaxMinor: 20_000,
            weekMaxMinor: 40_000,
            thirtyDayMaxMinor: 60_000,
            periodMaxMinor: 50_000,
            totalMaxMinor: 500_000,
            maxQuoteAge: 120,
            boundsVersion: 1
        });
    }

    function _terms(address a) internal view returns (T.MandateTerms memory t) {
        address[] memory toks = new address[](1);
        toks[0] = a;
        return _termsOf(toks);
    }

    /// Terms over the tokens, which must be in ascending address order (the canonical order of requireShape).
    function _termsOf(address[] memory toks) internal pure returns (T.MandateTerms memory t) {
        t.merchantId = MERCHANT;
        t.recipientPolicy = bytes32(0);
        t.subscriptionRef = SUBSCRIPTION;
        t.periodSeconds = PERIOD;
        t.anchorStartsAt = uint64(START);
        t.expiresAt = uint64(START + 365 days);
        t.tokens = new T.TokenTerms[](toks.length);
        for (uint256 i = 0; i < toks.length; ++i) {
            t.tokens[i] = _tokenTerms(toks[i]);
        }
        t.fiat = _fiat();
        t.maxChargesPerPeriod = 4;
        t.minIntervalSeconds = 1 hours;
        t.maxFeeBps = 100;
        t.extensionsHash = bytes32(0);
    }

    function _sorted2(address a, address b) internal pure returns (address[] memory r) {
        r = new address[](2);
        (r[0], r[1]) = uint160(a) < uint160(b) ? (a, b) : (b, a);
    }

    // ------------------------------------------------------------------------------------------------------------ actions
    function _fund(address who, MockERC20 tok, uint256 amount) internal {
        tok.mint(who, amount);
        vm.prank(who);
        tok.approve(CANONICAL, type(uint256).max);
    }

    /// Layer 2: the customer's Permit2 allowance for `spender` (a router).
    function _grant(address who, MockERC20 tok, address spender, uint160 amount) internal {
        vm.prank(who);
        p2.approve(address(tok), spender, amount, uint48(block.timestamp + 400 days));
    }

    function _activate(address who, uint256 creationNonce, address r, T.MandateTerms memory t, T.AccountPin memory p)
        internal
        returns (bytes32 lid, bytes32 mid)
    {
        vm.prank(who);
        (lid, mid) = manager.activate(who, creationNonce, r, t, p);
    }

    function _sign(uint256 key, bytes32 digest) internal pure returns (bytes memory) {
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(key, digest);
        return abi.encodePacked(r, s, v);
    }

    function _mandatesDigest(bytes32 structHash) internal view returns (bytes32) {
        return T.digest(T.mandatesDomainSeparator(block.chainid, address(manager)), structHash);
    }

    function _noQuote() internal pure returns (PaymentRouter.QuoteBundle memory q) {}

    function _charge(
        PaymentRouter r,
        bytes32 mid,
        T.MandateTerms memory t,
        T.AccountPin memory p,
        uint64 cycle,
        address tok,
        uint256 amount,
        uint256 fee,
        PaymentRouter.QuoteBundle memory q
    ) internal {
        vm.prank(executor);
        r.charge(PaymentRouter.ChargeRequest(mid, cycle, tok, amount, fee), t, p, q);
    }

    function _paymentId(PaymentRouter r, bytes32 lid, uint256 cycle) internal view returns (bytes32) {
        return r.paymentIdOf(lid, cycle);
    }

    /// A valid quote for the charge (the router that verifies it is in the domain); the tests change one field and sign again.
    function _baseQuote(PaymentRouter r, bytes32 lid, uint64 cycle, address who, address tok, uint256 amount, uint256 price)
        internal
        view
        returns (T.PriceQuote memory q)
    {
        q.paymentId = r.paymentIdOf(lid, cycle);
        q.payer = who;
        q.token = tok;
        q.amountIn = amount;
        q.currency = USD;
        q.priceE18 = price;
        q.issuedAt = uint64(block.timestamp);
        q.validAfter = uint64(block.timestamp);
        q.validUntil = uint64(block.timestamp + 120);
        q.nonce = 424_242;
        q.signerSetVersion = 1;
        q.registryVersion = policy.tokenVersion(tok);
        q.boundsVersion = policy.currentBoundsVersion(tok, USD);
        q.routeHash = keccak256(abi.encode(T.ROUTE_DIRECT_TAG, block.chainid, tok));
        q.priceSourceSetHash = SOURCE_SET;
    }

    function _bundle(PaymentRouter r, T.PriceQuote memory q) internal view returns (PaymentRouter.QuoteBundle memory b) {
        b.quote = q;
        b.signature = _signQuote(r, q);
    }

    function _quote(PaymentRouter r, bytes32 lid, uint64 cycle, address who, address tok, uint256 amount, uint256 price)
        internal
        view
        returns (PaymentRouter.QuoteBundle memory)
    {
        return _bundle(r, _baseQuote(r, lid, cycle, who, tok, amount, price));
    }

    function _signQuote(PaymentRouter r, T.PriceQuote memory q) internal view returns (bytes memory) {
        return _sign(quoteKey, T.digest(r.quoteDomainSeparator(), T.hashStruct(q)));
    }

    function _bal(MockERC20 tok, address who) internal view returns (uint256) {
        return tok.balanceOf(who);
    }

    function _view(bytes32 mid) internal view returns (IMandateManager.MandateView memory) {
        return manager.mandateView(mid);
    }
}
