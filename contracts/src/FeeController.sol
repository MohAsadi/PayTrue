// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

import "./Errors.sol";

/// FeeController (document 06 section 4): the protocol fee in basis points of the gross input and the fee recipient, under an immutable ceiling
/// (FEE_CEILING_BPS, PC-05: its value is pending a decision of Finance, so the constructor takes it and no default exists). A change of the
/// fee is bounded by the ceiling whoever makes it; the fee that the router accepts for one charge is also bounded by the mandate's own
/// `maxFeeBps` (the customer's cap), so a governance change can never take more than the customer allowed.
contract FeeController {
    address public immutable governance;
    uint16 public immutable ceilingBps;

    uint16 public feeBps;
    address public feeRecipient;

    event FeeChanged(uint16 feeBps, address feeRecipient);

    constructor(address governance_, uint16 ceilingBps_, uint16 feeBps_, address feeRecipient_) {
        governance = governance_;
        if (ceilingBps_ > 10_000 || feeBps_ > ceilingBps_) revert FeeAboveCeiling();
        ceilingBps = ceilingBps_;
        feeBps = feeBps_;
        feeRecipient = feeRecipient_;
    }

    function setFee(uint16 feeBps_, address feeRecipient_) external {
        if (msg.sender != governance) revert NotGovernance();
        if (feeBps_ > ceilingBps) revert FeeAboveCeiling();
        feeBps = feeBps_;
        feeRecipient = feeRecipient_;
        emit FeeChanged(feeBps_, feeRecipient_);
    }
}
