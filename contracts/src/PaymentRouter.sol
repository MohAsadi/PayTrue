// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

import {FastPayTypes as T} from "./generated/FastPayTypes.sol";
import {IMandateManager} from "./interfaces/IMandateManager.sol";
import {IRouterRegistry} from "./interfaces/IRouterRegistry.sol";
import {ISignerSetRegistry} from "./interfaces/ISignerSetRegistry.sol";
import {ITokenPolicyRegistry} from "./interfaces/ITokenPolicyRegistry.sol";
import {IMerchantRegistry, IExecutorRegistry, IFeeController} from "./interfaces/IRegistries.sol";
import {IAllowanceTransfer, ISignatureTransfer} from "./interfaces/IPermit2.sol";
import {IERC20} from "./interfaces/IERC20.sol";
import {AuthLib} from "./lib/AuthLib.sol";
import {ContainLib} from "./lib/ContainLib.sol";
import "./Errors.sol";

/// PaymentRouter v1.0 (document 06 section 4, documents 10 and 11): verifies the request and the quote, pulls the customer's tokens through
/// Permit2 and pays the merchant and the fee recipient directly. It holds no tokens at any point (I-ZEROBAL), keeps no state but a
/// reentrancy lock, and calls only the contracts fixed at deployment, Permit2 and the token that the registry lists (I-EXTCALL, I-NOARB).
///
/// Two protocols, two entry families, no shared code path between them (S-1, S-2):
///   * Protocol B, recurring: `charge`. The router is the Permit2 AllowanceTransfer spender. The manager checks the mandate and the ledger
///     records the usage BEFORE the pull (finding F-16), so a failed pull reverts the counters with it.
///   * Protocol A, Pay Once: `payOnceWithSignature`. A Permit2 SignatureTransfer batch with the PayOnceIntent as the witness; it references
///     neither the mandate manager nor AllowanceTransfer. `transferDetails.to` is not signed, so the router builds both transfers from the
///     very intent whose hash is the witness (F-13).
/// Not built in this pass: chargeInitial, payOnceWithSignatureAndPermit, payOnceWithAuthorization, payOnce, RefundManager, EmergencyGuardian.
contract PaymentRouter {
    IAllowanceTransfer public immutable permit2;
    IMandateManager public immutable manager;
    IRouterRegistry public immutable routerRegistry;
    IMerchantRegistry public immutable merchants;
    IExecutorRegistry public immutable executors;
    IFeeController public immutable fees;
    ITokenPolicyRegistry public immutable tokens;
    ISignerSetRegistry public immutable signers;

    uint256 private _lock = 1;

    /// One recurring charge. `amount` is the gross input and includes the fee.
    struct ChargeRequest {
        bytes32 mandateId;
        uint64 cycleIndex;
        address token;
        uint256 amount;
        uint256 feeAmount;
    }

    /// A quote and its signature. An empty signature means "no quote".
    struct QuoteBundle {
        T.PriceQuote quote;
        bytes signature;
    }

    event PaymentSettled(
        bytes32 indexed paymentId,
        bytes32 indexed mandateId,
        address indexed customer,
        address token,
        uint256 amount,
        uint256 feeAmount,
        uint64 fiatValueMinor,
        bytes32 quoteDigest
    );
    event QuoteUsed(bytes32 indexed paymentId, bytes32 indexed quoteDigest, address signer, uint256 priceE18, uint256 quoteNonce);
    event PayOnceSettled(bytes32 indexed paymentId, bytes32 indexed merchantId, address indexed payer, address token, uint256 merchantAmount, uint256 feeAmount);

    constructor(
        IAllowanceTransfer permit2_,
        IMandateManager manager_,
        IRouterRegistry routerRegistry_,
        IMerchantRegistry merchants_,
        IExecutorRegistry executors_,
        IFeeController fees_,
        ITokenPolicyRegistry tokens_,
        ISignerSetRegistry signers_
    ) {
        permit2 = permit2_;
        manager = manager_;
        routerRegistry = routerRegistry_;
        merchants = merchants_;
        executors = executors_;
        fees = fees_;
        tokens = tokens_;
        signers = signers_;
    }

    modifier nonReentrant() {
        if (_lock != 1) revert Reentrancy();
        _lock = 2;
        _;
        _lock = 1;
    }

    modifier onlyExecutor() {
        if (!executors.isExecutor(msg.sender)) revert NotExecutor();
        _;
    }

    function quoteDomainSeparator() public view returns (bytes32) {
        return T.quoteDomainSeparator(block.chainid, address(this));
    }

    /// paymentId = keccak256(abi.encode(chainId, mandateManager, lineageId, cycleId)); no router input enters it (document 11 section 3.1).
    function paymentIdOf(bytes32 lineageId, uint256 cycleIndex) public view returns (bytes32) {
        bytes32 cycleId = keccak256(abi.encode(T.CYCLE_TAG, lineageId, cycleIndex));
        return keccak256(abi.encode(block.chainid, address(manager), lineageId, cycleId));
    }

    /// The token is listed for payment (SETTLEMENT or DIRECT_PAYMENT); BLOCKED and the rest are refused.
    function _requireListed(address token) internal view {
        uint8 s = tokens.status(token);
        if (s == 4) revert TokenBlocked();
        if (s != 1 && s != 2) revert TokenNotListed();
    }

    /// The fee is within the controller's current rate; the mandate's own `maxFeeBps` is checked by the ledger.
    function _requireFee(uint256 gross, uint256 fee) internal view {
        if (fee * 10_000 > gross * fees.feeBps()) revert FeeAboveCeiling();
    }

    // ------------------------------------------------------------------------------------------------------------ Protocol B: recurring
    /// What `charge` resolves before it writes anything.
    struct Resolved {
        bytes32 lineageId;
        address customer;
        address recipient;
        bytes32 paymentId;
        bool hasFiat;
        uint64 fiatValueMinor;
        bytes32 quoteDigest;
    }

    function charge(ChargeRequest calldata req, T.MandateTerms calldata terms, T.AccountPin calldata pin, QuoteBundle calldata qb)
        external
        nonReentrant
        onlyExecutor
    {
        Resolved memory x = _resolve(req, terms, qb);
        // Step 7: effects. The manager and the ledger write the counters and the cycle record; a later failure reverts them.
        manager.consume(req.mandateId, terms, pin, _input(req, x));
        // Step 8: interactions. G8: the recipient must receive at least the merchant amount.
        _pull(x.customer, req.token, x.recipient, req.amount - req.feeAmount, req.feeAmount);
        emit PaymentSettled(x.paymentId, req.mandateId, x.customer, req.token, req.amount, req.feeAmount, x.fiatValueMinor, x.quoteDigest);
    }

    /// Steps 1 to 6 of document 11 section 5 that belong to the router: the listing, the merchant, the fee and the quote (when the mandate has
    /// a fiat cap). The terms are bound to the mandate by hash in `consume`, in the same transaction.
    function _resolve(ChargeRequest calldata req, T.MandateTerms calldata terms, QuoteBundle calldata qb) internal returns (Resolved memory x) {
        (x.lineageId, x.customer) = manager.partiesOf(req.mandateId);
        _requireListed(req.token);
        x.recipient = merchants.settlement(terms.merchantId, req.token);
        _requireFee(req.amount, req.feeAmount);
        x.paymentId = paymentIdOf(x.lineageId, req.cycleIndex);
        x.hasFiat = ContainLib.hasFiatCaps(terms.fiat);
        if (x.hasFiat) {
            if (qb.signature.length == 0) revert FiatQuoteRequired();
            (x.fiatValueMinor, x.quoteDigest) = _verifyQuote(terms, x.customer, req.token, req.amount, x.paymentId, qb);
        }
    }

    function _input(ChargeRequest calldata req, Resolved memory x) internal pure returns (IMandateManager.ChargeInput memory c) {
        c.token = req.token;
        c.amount = req.amount;
        c.cycleIndex = req.cycleIndex;
        c.feeAmount = req.feeAmount;
        c.hasFiat = x.hasFiat;
        c.fiatValueMinor = x.fiatValueMinor;
        c.quoteDigest = x.quoteDigest;
    }

    /// Pull with Permit2 AllowanceTransfer (this router is the spender) and pay merchant and fee; the merchant's balance delta is the MINOUT check.
    function _pull(address customer, address token, address recipient, uint256 merchantAmount, uint256 feeAmount) internal {
        uint256 before = IERC20(token).balanceOf(recipient);
        permit2.transferFrom(customer, recipient, _u160(merchantAmount), token);
        if (IERC20(token).balanceOf(recipient) - before < merchantAmount) revert BelowMinOut();
        if (feeAmount != 0) permit2.transferFrom(customer, fees.feeRecipient(), _u160(feeAmount), token);
    }

    function _u160(uint256 x) internal pure returns (uint160) {
        if (x > type(uint160).max) revert AmountTooLarge();
        return uint160(x);
    }

    // ------------------------------------------------------------------------------------------------------------ the quote (Q1 to Q18)
    /// Returns the fiat value (rounded up) and the digest of the quote. Q19 (the fiat caps) and Q20 (once-only) are the ledger's.
    /// Q3 (the domain) is not an observable failure: the digest is built from this chain and this router, so a quote for another domain recovers
    /// a different address and fails Q1.
    function _verifyQuote(
        T.MandateTerms calldata terms,
        address customer,
        address token,
        uint256 amount,
        bytes32 paymentId,
        QuoteBundle calldata qb
    ) internal returns (uint64 fiatValueMinor, bytes32 digest) {
        T.PriceQuote calldata q = qb.quote;
        digest = T.digest(quoteDomainSeparator(), T.hashStruct(q));
        address signer = AuthLib.recover(digest, qb.signature); // Q2
        if (signer == address(0)) revert QuoteSignatureInvalid();
        signers.verifySigner(signer, q.signerSetVersion, q.issuedAt); // Q1, Q13
        if (q.paymentId != paymentId || q.payer != customer || q.token != token || q.amountIn != amount || q.currency != terms.fiat.currency) {
            revert QuoteBindingMismatch(); // Q4 to Q8
        }
        ITokenPolicyRegistry.QuoteContext memory c = tokens.quoteContext(token, q.currency, terms.fiat.boundsVersion);
        _quoteTimes(q, terms.fiat.maxQuoteAge, c.maxQuoteTtl);
        if (q.registryVersion != c.tokenVersion) revert RegistryVersionStale(); // Q14
        if (q.boundsVersion != c.currentBoundsVersion) revert BoundsVersionStale(); // Q15
        if (q.routeHash != keccak256(abi.encode(T.ROUTE_DIRECT_TAG, block.chainid, token))) revert QuoteRouteMismatch(); // Q16
        if (q.priceSourceSetHash != c.priceSourceSetHash) revert QuoteSourceSetMismatch(); // Q17
        _quoteBand(q.priceE18, c); // Q18
        fiatValueMinor = _fiatValue(amount, q.priceE18, c.decimals);
        emit QuoteUsed(paymentId, digest, signer, q.priceE18, q.nonce);
    }

    /// Q9 to Q12.
    function _quoteTimes(T.PriceQuote calldata q, uint32 mandateMaxAge, uint32 registryMaxTtl) internal view {
        if (q.issuedAt > q.validAfter || q.validAfter > q.validUntil) revert QuoteTimesInvalid(); // Q9
        if (q.validAfter > block.timestamp) revert QuoteNotYetValid(); // Q10
        if (block.timestamp > q.validUntil) revert QuoteExpired(); // Q11
        uint256 maxAge = mandateMaxAge < registryMaxTtl ? mandateMaxAge : registryMaxTtl;
        if (q.validUntil - q.issuedAt > maxAge) revert QuoteTtlTooLong(); // Q12
    }

    /// Q18: the price lies in the INTERSECTION of the band that the mandate pinned and the current band (document 11 N6): a later, tighter
    /// band narrows an existing mandate, a later, wider one never widens it.
    function _quoteBand(uint256 price, ITokenPolicyRegistry.QuoteContext memory c) internal pure {
        if (!c.pinnedExists) revert BoundsNotPublished();
        uint256 lo = c.pinnedMin > c.currentMin ? c.pinnedMin : c.currentMin;
        uint256 hi = c.pinnedMax < c.currentMax ? c.pinnedMax : c.currentMax;
        if (price < lo || price > hi) revert PriceOutOfBounds();
    }

    /// ceil(amountIn * priceE18 / (10^decimals * 1e18)), checked to fit a uint64. Both factors are bounded first so the product cannot wrap.
    function _fiatValue(uint256 amount, uint256 priceE18, uint8 decimals) internal pure returns (uint64) {
        if (amount > type(uint128).max) revert AmountTooLarge();
        if (priceE18 > type(uint128).max) revert PriceOutOfBounds();
        uint256 divisor = (10 ** uint256(decimals)) * 1e18;
        uint256 value = (amount * priceE18 + divisor - 1) / divisor;
        if (value > type(uint64).max) revert FiatValueTooLarge();
        return uint64(value);
    }

    // ------------------------------------------------------------------------------------------------------------ Protocol A: Pay Once
    /// The payer's Permit2 SignatureTransfer signature covers (merchant amount, fee) to this router as spender, with the PayOnceIntent as the
    /// witness. The router rebuilds the witness from `intent`, so any deviation from what the payer signed fails inside Permit2.
    function payOnceWithSignature(T.PayOnceIntent calldata intent, uint256 nonce, uint256 deadline, bytes calldata signature)
        external
        nonReentrant
        onlyExecutor
    {
        if (block.timestamp > intent.validUntil || intent.validUntil > deadline) revert IntentExpired();
        if (intent.grossAmountIn != intent.merchantAmount + intent.feeAmount) revert IntentInvalid();
        _requireListed(intent.token);
        // I-RECIPIENT: the signed recipient is the registry recipient valid now; the fee goes to the controller's recipient under its rate.
        if (merchants.settlement(intent.merchantId, intent.token) != intent.recipient) revert IntentInvalid();
        if (intent.feeRecipient != fees.feeRecipient()) revert IntentInvalid();
        _requireFee(intent.grossAmountIn, intent.feeAmount);
        routerRegistry.markSettled(intent.paymentId); // once only, across every router version

        uint256 beforeMerchant = IERC20(intent.token).balanceOf(intent.recipient);
        ISignatureTransfer.TokenPermissions[] memory permitted = new ISignatureTransfer.TokenPermissions[](2);
        permitted[0] = ISignatureTransfer.TokenPermissions(intent.token, intent.merchantAmount);
        permitted[1] = ISignatureTransfer.TokenPermissions(intent.token, intent.feeAmount);
        ISignatureTransfer.SignatureTransferDetails[] memory details = new ISignatureTransfer.SignatureTransferDetails[](2);
        details[0] = ISignatureTransfer.SignatureTransferDetails(intent.recipient, intent.merchantAmount);
        details[1] = ISignatureTransfer.SignatureTransferDetails(intent.feeRecipient, intent.feeAmount);
        ISignatureTransfer(address(permit2)).permitWitnessTransferFrom(
            ISignatureTransfer.PermitBatchTransferFrom(permitted, nonce, deadline),
            details,
            intent.payer,
            T.hashStruct(intent),
            T.PAY_ONCE_WITNESS_TYPESTRING,
            signature
        );
        if (IERC20(intent.token).balanceOf(intent.recipient) - beforeMerchant < intent.merchantAmount) revert BelowMinOut(); // G8
        emit PayOnceSettled(intent.paymentId, intent.merchantId, intent.payer, intent.token, intent.merchantAmount, intent.feeAmount);
    }
}
