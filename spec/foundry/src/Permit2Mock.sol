// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

import "./Errors.sol";
import "./Mutants.sol";

/// Usability of a Permit2 allowance (document 12 section 5.3): Usable = amount > 0 and now <= expiration.
/// AllowanceTransfer._transfer reverts AllowanceExpired only when block.timestamp > expiration, so the allowance is usable in the
/// block whose timestamp equals the expiration. uint160.max is unlimited and counts as usable.
library AllowanceMath {
    function usable(uint256 amount, uint256 expiration, uint256 nowTs) internal pure returns (bool) {
        return amount > 0 && nowTs <= expiration;
    }

    /// Usable with one mutation applied (mutants U_STRICT, U_NO_UNLIM, U_EXPIRY_ONLY).
    function usableMutated(uint256 amount, uint256 expiration, uint256 nowTs, uint256 mutant) internal pure returns (bool) {
        if (mutant == M_U_STRICT) return amount > 0 && nowTs < expiration;
        if (mutant == M_U_NO_UNLIM) return amount > 0 && amount < type(uint160).max && nowTs <= expiration;
        if (mutant == M_U_EXPIRY_ONLY) return nowTs <= expiration;
        return amount > 0 && nowTs <= expiration;
    }

    /// Bounded: the allowance is not the unlimited sentinel (document 12 section 5.3).
    function bounded(uint256 amount) internal pure returns (bool) {
        return amount < type(uint160).max;
    }
}

/// Reference model of the Permit2 AllowanceTransfer ledger at Uniswap/permit2 commit cc306b601f172c51bc04334a109e98340456620b
/// (AllowanceTransfer.sol, libraries/Allowance.sol). Tokens are not moved: this is the allowance ledger only.
/// The external functions without the `As` suffix are the real ones (the owner or spender is msg.sender); the `As` functions are
/// harness entry points that take the actor explicitly, so that a scenario machine can drive them without pranks.
/// `permit` is out of scope except as a re-grant (`permitRegrantAs`): the same write as a signed permit that passes its checks.
contract Permit2Mock {
    struct PackedAllowance {
        uint160 amount;
        uint48 expiration;
        uint48 nonce;
    }

    struct TokenSpenderPair {
        address token;
        address spender;
    }

    mapping(address => mapping(address => mapping(address => PackedAllowance))) public allowance;

    event Approval(address indexed owner, address indexed token, address indexed spender, uint160 amount, uint48 expiration);
    event Permit(address indexed owner, address indexed token, address indexed spender, uint160 amount, uint48 expiration, uint48 nonce);
    event Lockdown(address indexed owner, address token, address spender);
    event NonceInvalidation(address indexed owner, address indexed token, address indexed spender, uint48 newNonce, uint48 oldNonce);

    // ---- the real interface (msg.sender is the owner, or the spender for transferFrom)
    function approve(address token, address spender, uint160 amount, uint48 expiration) external {
        _approve(msg.sender, token, spender, amount, expiration);
    }

    function lockdown(TokenSpenderPair[] calldata approvals) external {
        uint256 length = approvals.length;
        // loop-bound: EXTERNAL | approvals.length chosen by the caller of Permit2 | Permit2's own function (a mock of the external contract): the caller supplies the array and pays its gas; no FastPay function calls it
        for (uint256 i = 0; i < length; ++i) {
            _lockdown(msg.sender, approvals[i].token, approvals[i].spender);
        }
    }

    function transferFrom(address from, address to, uint160 amount, address token) external {
        to; // the ledger does not move tokens
        _pull(from, token, msg.sender, amount);
    }

    function invalidateNonces(address token, address spender, uint48 newNonce) external {
        _invalidate(msg.sender, token, spender, newNonce);
    }

    // ---- harness entry points (explicit actor; values wider than the real types are refused like an ABI decoder would)
    function approveAs(address owner, address token, address spender, uint256 amount, uint256 expiration) external {
        if (amount > type(uint160).max || expiration > type(uint48).max) revert AbiOutOfRange();
        _approve(owner, token, spender, uint160(amount), uint48(expiration));
    }

    function lockdownAs(address owner, address token, address spender) external {
        _lockdown(owner, token, spender);
    }

    function pullAs(address spender, address owner, address token, uint256 amount) external {
        if (amount > type(uint160).max) revert AbiOutOfRange();
        _pull(owner, token, spender, uint160(amount));
        // The real Permit2 spends the allowance and then calls token.transferFrom (PR-14), so a token with a callback runs HERE: after the
        // allowance is spent, before Permit2 returns to the spender, with no reentrancy guard in between. A test arms one call (`setHook`).
        if (hookTarget != address(0)) {
            address target = hookTarget;
            hookTarget = address(0);
            hookCalls += 1;
            (hookSucceeded, hookReturn) = target.call(hookData);
        }
    }

    // ---- test hook: the callback of a hostile token (one call, then disarmed)
    address public hookTarget;
    bytes public hookData;
    bool public hookSucceeded;
    bytes public hookReturn;
    uint256 public hookCalls;

    function setHook(address target, bytes calldata data) external {
        hookTarget = target;
        hookData = data;
        hookSucceeded = false;
        delete hookReturn;
    }

    function invalidateAs(address owner, address token, address spender, uint256 newNonce) external {
        if (newNonce > type(uint48).max) revert AbiOutOfRange();
        _invalidate(owner, token, spender, uint48(newNonce));
    }

    /// The write of a signed `permit` whose signature, deadline and nonce checks pass (nonce = the stored nonce).
    function permitRegrantAs(address owner, address token, address spender, uint256 amount, uint256 expiration, uint256 nonce) external {
        if (amount > type(uint160).max || expiration > type(uint48).max || nonce > type(uint48).max) revert AbiOutOfRange();
        PackedAllowance storage a = allowance[owner][token][spender];
        if (a.nonce != nonce) revert InvalidNonce();
        a.amount = uint160(amount);
        a.expiration = expiration == 0 ? uint48(block.timestamp) : uint48(expiration);
        a.nonce = uint48(nonce + 1);
        emit Permit(owner, token, spender, uint160(amount), a.expiration, uint48(nonce));
    }

    /// Would a pull of `amount` by `spender` from `owner` succeed right now (no state change)?
    function canPull(address owner, address token, address spender, uint256 amount) external view returns (bool) {
        PackedAllowance storage a = allowance[owner][token][spender];
        if (amount > type(uint160).max) return false;
        if (block.timestamp > a.expiration) return false;
        return a.amount == type(uint160).max || amount <= a.amount;
    }

    // ---- internals (exact semantics)
    function _approve(address owner, address token, address spender, uint160 amount, uint48 expiration) internal {
        PackedAllowance storage a = allowance[owner][token][spender];
        a.expiration = expiration == 0 ? uint48(block.timestamp) : expiration; // F5: 0 stores block.timestamp
        a.amount = amount; // F2: overwrite
        emit Approval(owner, token, spender, amount, expiration);
    }

    function _lockdown(address owner, address token, address spender) internal {
        allowance[owner][token][spender].amount = 0; // F3: amount only
        emit Lockdown(owner, token, spender);
    }

    function _pull(address owner, address token, address spender, uint160 amount) internal {
        PackedAllowance storage a = allowance[owner][token][spender];
        if (block.timestamp > a.expiration) revert AllowanceExpired(a.expiration);
        uint256 maxAmount = a.amount;
        if (maxAmount != type(uint160).max) {
            if (amount > maxAmount) revert InsufficientAllowance(maxAmount);
            a.amount = uint160(maxAmount - amount); // F4: the unlimited sentinel is never decremented
        }
    }

    function _invalidate(address owner, address token, address spender, uint48 newNonce) internal {
        uint48 oldNonce = allowance[owner][token][spender].nonce;
        if (newNonce <= oldNonce) revert InvalidNonce();
        uint256 delta = uint256(newNonce) - uint256(oldNonce);
        if (delta > type(uint16).max) revert ExcessiveInvalidation();
        allowance[owner][token][spender].nonce = newNonce;
        emit NonceInvalidation(owner, token, spender, newNonce, oldNonce);
    }
}
