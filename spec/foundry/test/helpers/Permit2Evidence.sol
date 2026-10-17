// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import {FastPayTypes as T} from "../../src/generated/FastPayTypes.sol";
import {MockERC20} from "./MockERC20.sol";

/// The part of the Permit2 SignatureTransfer interface that the Pay Once witness uses (Uniswap/permit2 at commit
/// cc306b601f172c51bc04334a109e98340456620b, ISignatureTransfer.sol).
interface ISigTransfer {
    struct TokenPermissions {
        address token;
        uint256 amount;
    }

    struct PermitTransferFrom {
        TokenPermissions permitted;
        uint256 nonce;
        uint256 deadline;
    }

    struct PermitBatchTransferFrom {
        TokenPermissions[] permitted;
        uint256 nonce;
        uint256 deadline;
    }

    struct SignatureTransferDetails {
        address to;
        uint256 requestedAmount;
    }

    function permitWitnessTransferFrom(
        PermitTransferFrom memory permit,
        SignatureTransferDetails calldata transferDetails,
        address owner,
        bytes32 witness,
        string calldata witnessTypeString,
        bytes calldata signature
    ) external;

    function permitWitnessTransferFrom(
        PermitBatchTransferFrom memory permit,
        SignatureTransferDetails[] calldata transferDetails,
        address owner,
        bytes32 witness,
        string calldata witnessTypeString,
        bytes calldata signature
    ) external;

    function nonceBitmap(address, uint256) external view returns (uint256);
    function DOMAIN_SEPARATOR() external view returns (bytes32);
}

/// The Permit2 evidence of this repository (foundry/vectors/permit2-evidence.json, written by tools/export_permit2_fixtures.py from
/// evidence/permit2/rebuild.json) and the helpers that deploy or check Permit2 against it.
abstract contract Permit2Evidence is Test {
    /// Selectors of the Permit2 errors the witness tests expect (SignatureVerification.sol, PermitErrors.sol, ISignatureTransfer.sol at the
    /// pinned commit). Spelled as selectors so that this file never clashes with the error declarations of src/Errors.sol.
    bytes4 internal constant ERR_INVALID_SIGNER = bytes4(keccak256("InvalidSigner()"));
    bytes4 internal constant ERR_SIGNATURE_EXPIRED = bytes4(keccak256("SignatureExpired(uint256)"));
    bytes4 internal constant ERR_INVALID_AMOUNT = bytes4(keccak256("InvalidAmount(uint256)"));
    bytes4 internal constant ERR_INVALID_NONCE = bytes4(keccak256("InvalidNonce()"));
    bytes4 internal constant ERR_LENGTH_MISMATCH = bytes4(keccak256("LengthMismatch()"));

    address internal constant CANONICAL = address(uint160(0x00000000000022d473030f116ddee9f6b43ac78ba3)); // 0x000000000022D473030F116dDEE9F6B43aC78BA3
    address internal constant DEPLOYER = address(uint160(0x004e59b44847b379578588920ca78fbf26c0b4956c)); // 0x4e59b44847b379578588920cA78FbF26c0B4956C
    bytes32 internal constant SALT = 0x0000000000000000000000000000000000000000d3af2663da51c10215000000;
    /// Runtime code of the deterministic deployment proxy (69 bytes); its keccak256 is checked against the evidence hash read from
    /// Ethereum, Base and Arbitrum One.
    bytes internal constant DEPLOYER_CODE =
        hex"7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffe03601600081602082378035828234f58015156039578182fd5b8082525050506014600cf3";

    function _evidence() internal view returns (string memory) {
        return vm.readFile("vectors/permit2-evidence.json");
    }

    function _creationCode() internal view returns (bytes memory c) {
        c = vm.parseBytes(vm.readFile("vectors/permit2-creation-code.hex"));
        require(keccak256(c) == vm.parseJsonBytes32(_evidence(), ".creationCodeKeccak256"), "creation code fixture differs from the evidence");
    }

    function _runtimeCodeZeroImmutables() internal view returns (bytes memory c) {
        c = vm.parseBytes(vm.readFile("vectors/permit2-runtime-code.hex"));
        require(
            keccak256(c) == vm.parseJsonBytes32(_evidence(), ".runtimeCodeKeccak256WithZeroImmutables"), "runtime code fixture differs from the evidence"
        );
    }

    function _create2Address(bytes memory creation) internal pure returns (address) {
        return address(uint160(uint256(keccak256(abi.encodePacked(bytes1(0xff), DEPLOYER, SALT, keccak256(creation))))));
    }

    /// Deploys the rebuilt Permit2 through the deterministic deployment proxy exactly as the original deployment did.
    function _deployRebuiltPermit2() internal returns (address deployed) {
        bytes memory creation = _creationCode();
        vm.etch(DEPLOYER, DEPLOYER_CODE);
        require(DEPLOYER.codehash == vm.parseJsonBytes32(_evidence(), ".deployerProxyCodeKeccak256"), "deployer proxy code is not the evidenced one");
        (bool ok, bytes memory out) = DEPLOYER.call(abi.encodePacked(SALT, creation));
        require(ok && out.length == 20, "CREATE2 deployment failed");
        deployed = address(bytes20(out));
    }

    function _setWord(bytes memory code, uint256 offset, bytes32 value) internal pure {
        require(offset + 32 <= code.length, "offset");
        assembly ("memory-safe") { // lint: allow assembly
            mstore(add(add(code, 32), offset), value)
        }
    }

    function _offset(string memory name) internal view returns (uint256) {
        return vm.parseJsonUint(_evidence(), string.concat(".immutableOffsets.", name));
    }

    /// The runtime code that the rebuilt creation code would leave at `at` on the current chain: the zero-immutable code with the
    /// chain id and the domain separator written into the two immutable slots that solc's immutableReferences name.
    function _expectedRuntime(address at) internal view returns (bytes memory c) {
        c = _runtimeCodeZeroImmutables();
        _setWord(c, _offset("_CACHED_CHAIN_ID"), bytes32(block.chainid));
        _setWord(c, _offset("_CACHED_DOMAIN_SEPARATOR"), T.permit2DomainSeparator(block.chainid, at));
    }
}

/// The Pay Once witness against a Permit2: the tests are the same on the locally deployed rebuilt Permit2 and on the real deployments of
/// the fork tests. Subclasses set `p2` and call `_prepare()`.
abstract contract WitnessSuite is Permit2Evidence {
    ISigTransfer internal p2;
    MockERC20 internal token;
    address internal owner;
    uint256 internal ownerKey;
    address internal router;
    address internal recipient;
    address internal feeRecipient;
    address internal attacker;

    uint256 internal constant GROSS = 50_000_000;
    uint256 internal constant MERCHANT = 49_500_000;
    uint256 internal constant FEE = 500_000;
    uint256 internal constant NONCE = 0x1234;

    function _ready() internal view virtual returns (bool);

    modifier ready() {
        if (!_ready()) {
            emit log_string("SKIPPED: the Permit2 under test is not available (no fork configured)");
            vm.skip(true);
        }
        _;
    }

    function _prepare() internal {
        (owner, ownerKey) = makeAddrAndKey("fastpay.payer");
        router = makeAddr("fastpay.router");
        recipient = makeAddr("fastpay.recipient");
        feeRecipient = makeAddr("fastpay.feeRecipient");
        attacker = makeAddr("fastpay.attacker");
        token = new MockERC20();
        token.mint(owner, 10 * GROSS);
        vm.prank(owner);
        token.approve(address(p2), type(uint256).max); // layer 1 (token allowance to Permit2) as for any Permit2 user
    }

    function _intent() internal view returns (T.PayOnceIntent memory i) {
        i.paymentId = keccak256("payment-1");
        i.merchantId = keccak256("merchant-1");
        i.recipient = recipient;
        i.feeRecipient = feeRecipient;
        i.token = address(token);
        i.grossAmountIn = GROSS;
        i.merchantAmount = MERCHANT;
        i.feeAmount = FEE;
        i.payer = owner;
        i.validUntil = uint64(vm.getBlockTimestamp() + 300);
        i.termsHash = keccak256("terms-1");
        i.quoteHash = bytes32(0);
    }

    function _deadline() internal view returns (uint256) {
        return vm.getBlockTimestamp() + 300;
    }

    function _sign(bytes32 structHash) internal view returns (bytes memory) {
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(ownerKey, T.digest(p2.DOMAIN_SEPARATOR(), structHash));
        return abi.encodePacked(r, s, v);
    }

    function _singleSig(T.PayOnceIntent memory i, address spender) internal view returns (bytes memory) {
        return _sign(T.permit2WitnessTransferFromHash(i.token, i.grossAmountIn, spender, NONCE, _deadline(), i));
    }

    function _permit() internal view returns (ISigTransfer.PermitTransferFrom memory) {
        return ISigTransfer.PermitTransferFrom(ISigTransfer.TokenPermissions(address(token), GROSS), NONCE, _deadline());
    }

    function _batchArrays() internal view returns (address[] memory toks, uint256[] memory amts) {
        toks = new address[](2);
        amts = new uint256[](2);
        toks[0] = address(token);
        toks[1] = address(token);
        amts[0] = MERCHANT;
        amts[1] = FEE;
    }

    function _batchPermit() internal view returns (ISigTransfer.PermitBatchTransferFrom memory p) {
        p.permitted = new ISigTransfer.TokenPermissions[](2);
        p.permitted[0] = ISigTransfer.TokenPermissions(address(token), MERCHANT);
        p.permitted[1] = ISigTransfer.TokenPermissions(address(token), FEE);
        p.nonce = NONCE;
        p.deadline = _deadline();
    }

    function _batchDetails(address to0, address to1) internal pure returns (ISigTransfer.SignatureTransferDetails[] memory d) {
        d = new ISigTransfer.SignatureTransferDetails[](2);
        d[0] = ISigTransfer.SignatureTransferDetails(to0, MERCHANT);
        d[1] = ISigTransfer.SignatureTransferDetails(to1, FEE);
    }

    function _batchSig(T.PayOnceIntent memory i, address spender) internal view returns (bytes memory) {
        (address[] memory toks, uint256[] memory amts) = _batchArrays();
        return _sign(T.permit2BatchWitnessTransferFromHash(toks, amts, spender, NONCE, _deadline(), i));
    }

    // ------------------------------------------------------------------------------------------------ single transfer
    function test_Witness_Single_Accepted() public ready {
        T.PayOnceIntent memory i = _intent();
        bytes memory sig = _singleSig(i, router);
        vm.prank(router);
        p2.permitWitnessTransferFrom(_permit(), ISigTransfer.SignatureTransferDetails(recipient, GROSS), owner, T.hashStruct(i), T.PAY_ONCE_WITNESS_TYPESTRING, sig);
        assertEq(token.balanceOf(recipient), GROSS);
        assertEq(token.balanceOf(owner), 9 * GROSS);
    }

    function test_Witness_Single_ReplayIsRefused() public ready {
        T.PayOnceIntent memory i = _intent();
        bytes memory sig = _singleSig(i, router);
        vm.prank(router);
        p2.permitWitnessTransferFrom(_permit(), ISigTransfer.SignatureTransferDetails(recipient, GROSS), owner, T.hashStruct(i), T.PAY_ONCE_WITNESS_TYPESTRING, sig);
        vm.prank(router);
        vm.expectRevert(ERR_INVALID_NONCE);
        p2.permitWitnessTransferFrom(_permit(), ISigTransfer.SignatureTransferDetails(recipient, GROSS), owner, T.hashStruct(i), T.PAY_ONCE_WITNESS_TYPESTRING, sig);
    }

    /// Permit2 hashes the spender into the signed message: only the router that the customer named can use the signature.
    function test_Witness_Single_OnlyTheSignedSpender() public ready {
        T.PayOnceIntent memory i = _intent();
        bytes memory sig = _singleSig(i, router);
        vm.prank(attacker);
        vm.expectRevert(ERR_INVALID_SIGNER);
        p2.permitWitnessTransferFrom(_permit(), ISigTransfer.SignatureTransferDetails(attacker, GROSS), owner, T.hashStruct(i), T.PAY_ONCE_WITNESS_TYPESTRING, sig);
    }

    /// Document 10 section 2.1 says `transferDetails.to` is NOT part of the signature, so the witness must bind the recipient and the
    /// router must send to it. This test shows the first half on the real code: with a valid signature the spender can name any `to`.
    /// The router therefore has to enforce `to == intent.recipient` itself (invariant I-PO-WITNESS and the router tests).
    function test_Witness_Single_DestinationIsNotBoundByPermit2() public ready {
        T.PayOnceIntent memory i = _intent();
        bytes memory sig = _singleSig(i, router);
        vm.prank(router);
        p2.permitWitnessTransferFrom(_permit(), ISigTransfer.SignatureTransferDetails(attacker, GROSS), owner, T.hashStruct(i), T.PAY_ONCE_WITNESS_TYPESTRING, sig);
        assertEq(token.balanceOf(attacker), GROSS, "Permit2 did not bind the destination: the router must");
        assertEq(token.balanceOf(recipient), 0);
    }

    /// Each of the twelve fields of the witness is bound: presenting a witness hash built from an intent that differs in one field fails.
    function test_Witness_Single_EveryFieldIsBound() public ready {
        T.PayOnceIntent memory signedIntent = _intent();
        bytes memory sig = _singleSig(signedIntent, router);
        for (uint256 k = 0; k < 12; ++k) {
            T.PayOnceIntent memory m = _intent();
            if (k == 0) m.paymentId = keccak256("other");
            else if (k == 1) m.merchantId = keccak256("other");
            else if (k == 2) m.recipient = attacker;
            else if (k == 3) m.feeRecipient = attacker;
            else if (k == 4) m.token = address(0xdead);
            else if (k == 5) m.grossAmountIn += 1;
            else if (k == 6) m.merchantAmount += 1;
            else if (k == 7) m.feeAmount += 1;
            else if (k == 8) m.payer = attacker;
            else if (k == 9) m.validUntil += 1;
            else if (k == 10) m.termsHash = keccak256("other");
            else m.quoteHash = keccak256("other");
            vm.prank(router);
            vm.expectRevert(ERR_INVALID_SIGNER);
            p2.permitWitnessTransferFrom(_permit(), ISigTransfer.SignatureTransferDetails(recipient, GROSS), owner, T.hashStruct(m), T.PAY_ONCE_WITNESS_TYPESTRING, sig);
        }
    }

    /// Permit2 does not check the witness type string; it hashes whatever the caller passes. Any deviation from the exact string fails
    /// the signature, which is why the router must hard-code it (the constant is generated from eip712/types.json).
    function test_Witness_Single_AnyChangeOfTheTypeStringFails() public ready {
        T.PayOnceIntent memory i = _intent();
        bytes memory sig = _singleSig(i, router);
        string[7] memory wrong = [
            // the referenced TokenPermissions type is missing
            "PayOnceIntent witness)PayOnceIntent(bytes32 paymentId,bytes32 merchantId,address recipient,address feeRecipient,address token,uint256 grossAmountIn,uint256 merchantAmount,uint256 feeAmount,address payer,uint64 validUntil,bytes32 termsHash,bytes32 quoteHash)",
            // the referenced types are in the wrong order
            "PayOnceIntent witness)TokenPermissions(address token,uint256 amount)PayOnceIntent(bytes32 paymentId,bytes32 merchantId,address recipient,address feeRecipient,address token,uint256 grossAmountIn,uint256 merchantAmount,uint256 feeAmount,address payer,uint64 validUntil,bytes32 termsHash,bytes32 quoteHash)",
            // a space after a comma
            "PayOnceIntent witness)PayOnceIntent(bytes32 paymentId, bytes32 merchantId,address recipient,address feeRecipient,address token,uint256 grossAmountIn,uint256 merchantAmount,uint256 feeAmount,address payer,uint64 validUntil,bytes32 termsHash,bytes32 quoteHash)TokenPermissions(address token,uint256 amount)",
            // two fields swapped
            "PayOnceIntent witness)PayOnceIntent(bytes32 merchantId,bytes32 paymentId,address recipient,address feeRecipient,address token,uint256 grossAmountIn,uint256 merchantAmount,uint256 feeAmount,address payer,uint64 validUntil,bytes32 termsHash,bytes32 quoteHash)TokenPermissions(address token,uint256 amount)",
            // another type name (a v2 witness never validates as v1)
            "PayOnceIntentV2 witness)PayOnceIntentV2(bytes32 paymentId,bytes32 merchantId,address recipient,address feeRecipient,address token,uint256 grossAmountIn,uint256 merchantAmount,uint256 feeAmount,address payer,uint64 validUntil,bytes32 termsHash,bytes32 quoteHash)TokenPermissions(address token,uint256 amount)",
            // the field widened
            "PayOnceIntent witness)PayOnceIntent(bytes32 paymentId,bytes32 merchantId,address recipient,address feeRecipient,address token,uint256 grossAmountIn,uint256 merchantAmount,uint256 feeAmount,address payer,uint256 validUntil,bytes32 termsHash,bytes32 quoteHash)TokenPermissions(address token,uint256 amount)",
            // the witness variable renamed
            "PayOnceIntent intent)PayOnceIntent(bytes32 paymentId,bytes32 merchantId,address recipient,address feeRecipient,address token,uint256 grossAmountIn,uint256 merchantAmount,uint256 feeAmount,address payer,uint64 validUntil,bytes32 termsHash,bytes32 quoteHash)TokenPermissions(address token,uint256 amount)"
        ];
        for (uint256 k = 0; k < wrong.length; ++k) {
            vm.prank(router);
            vm.expectRevert(ERR_INVALID_SIGNER);
            p2.permitWitnessTransferFrom(_permit(), ISigTransfer.SignatureTransferDetails(recipient, GROSS), owner, T.hashStruct(i), wrong[k], sig);
        }
    }

    function test_Witness_Single_ExpiredAndOverRequested() public ready {
        T.PayOnceIntent memory i = _intent();
        bytes memory sig = _singleSig(i, router);
        vm.prank(router);
        vm.expectRevert(abi.encodeWithSelector(ERR_INVALID_AMOUNT, GROSS));
        p2.permitWitnessTransferFrom(_permit(), ISigTransfer.SignatureTransferDetails(recipient, GROSS + 1), owner, T.hashStruct(i), T.PAY_ONCE_WITNESS_TYPESTRING, sig);
        // the permit as signed (its deadline is fixed before the clock moves), presented one second after the deadline
        ISigTransfer.PermitTransferFrom memory signed = _permit();
        vm.warp(signed.deadline + 1);
        vm.prank(router);
        vm.expectRevert(abi.encodeWithSelector(ERR_SIGNATURE_EXPIRED, signed.deadline));
        p2.permitWitnessTransferFrom(signed, ISigTransfer.SignatureTransferDetails(recipient, GROSS), owner, T.hashStruct(i), T.PAY_ONCE_WITNESS_TYPESTRING, sig);
    }

    // ------------------------------------------------------------------------------------------------ batch transfer (merchant and fee)
    function test_Witness_Batch_Accepted() public ready {
        T.PayOnceIntent memory i = _intent();
        bytes memory sig = _batchSig(i, router);
        vm.prank(router);
        p2.permitWitnessTransferFrom(_batchPermit(), _batchDetails(recipient, feeRecipient), owner, T.hashStruct(i), T.PAY_ONCE_WITNESS_TYPESTRING, sig);
        assertEq(token.balanceOf(recipient), MERCHANT);
        assertEq(token.balanceOf(feeRecipient), FEE);
        assertEq(token.balanceOf(owner), 9 * GROSS);
        // the nonce is spent
        vm.prank(router);
        vm.expectRevert(ERR_INVALID_NONCE);
        p2.permitWitnessTransferFrom(_batchPermit(), _batchDetails(recipient, feeRecipient), owner, T.hashStruct(i), T.PAY_ONCE_WITNESS_TYPESTRING, sig);
    }

    function test_Witness_Batch_SingleSignatureDoesNotValidateAsBatchAndViceVersa() public ready {
        T.PayOnceIntent memory i = _intent();
        bytes memory single = _singleSig(i, router);
        vm.prank(router);
        vm.expectRevert(ERR_INVALID_SIGNER);
        p2.permitWitnessTransferFrom(_batchPermit(), _batchDetails(recipient, feeRecipient), owner, T.hashStruct(i), T.PAY_ONCE_WITNESS_TYPESTRING, single);
        bytes memory batch = _batchSig(i, router);
        vm.prank(router);
        vm.expectRevert(ERR_INVALID_SIGNER);
        p2.permitWitnessTransferFrom(_permit(), ISigTransfer.SignatureTransferDetails(recipient, GROSS), owner, T.hashStruct(i), T.PAY_ONCE_WITNESS_TYPESTRING, batch);
    }

    function test_Witness_Batch_WrongSpenderAndLengthMismatch() public ready {
        T.PayOnceIntent memory i = _intent();
        bytes memory sig = _batchSig(i, router);
        vm.prank(attacker);
        vm.expectRevert(ERR_INVALID_SIGNER);
        p2.permitWitnessTransferFrom(_batchPermit(), _batchDetails(attacker, attacker), owner, T.hashStruct(i), T.PAY_ONCE_WITNESS_TYPESTRING, sig);
        ISigTransfer.SignatureTransferDetails[] memory one = new ISigTransfer.SignatureTransferDetails[](1);
        one[0] = ISigTransfer.SignatureTransferDetails(recipient, MERCHANT);
        vm.prank(router);
        vm.expectRevert(ERR_LENGTH_MISMATCH);
        p2.permitWitnessTransferFrom(_batchPermit(), one, owner, T.hashStruct(i), T.PAY_ONCE_WITNESS_TYPESTRING, sig);
    }

    /// The permitted amounts of the batch are signed: asking for more than permitted on either entry reverts.
    function test_Witness_Batch_PermittedAmountsAreBinding() public ready {
        T.PayOnceIntent memory i = _intent();
        bytes memory sig = _batchSig(i, router);
        ISigTransfer.SignatureTransferDetails[] memory d = _batchDetails(recipient, feeRecipient);
        d[1].requestedAmount = FEE + 1;
        vm.prank(router);
        vm.expectRevert(abi.encodeWithSelector(ERR_INVALID_AMOUNT, FEE));
        p2.permitWitnessTransferFrom(_batchPermit(), d, owner, T.hashStruct(i), T.PAY_ONCE_WITNESS_TYPESTRING, sig);
    }
}
