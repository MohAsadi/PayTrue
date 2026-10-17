// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

import "./Errors.sol";

/// ExecutorRegistry (document 06 section 4): the addresses that may submit charges and Pay Once payments to the router. An executor holds no
/// spending authority (the mandate and the customer's signature do); it only chooses when to submit. Governance (timelocked) adds, the guardian
/// can remove (stop-only), so a compromised executor is cut off in one transaction.
contract ExecutorRegistry {
    address public immutable governance;
    address public immutable guardian;

    mapping(address => bool) public isExecutor;

    event ExecutorAdded(address indexed executor);
    event ExecutorRemoved(address indexed executor);

    constructor(address governance_, address guardian_) {
        governance = governance_;
        guardian = guardian_;
    }

    function add(address executor) external {
        if (msg.sender != governance) revert NotGovernance();
        isExecutor[executor] = true;
        emit ExecutorAdded(executor);
    }

    function remove(address executor) external {
        if (msg.sender != guardian && msg.sender != governance) revert NotAuthorized();
        isExecutor[executor] = false;
        emit ExecutorRemoved(executor);
    }
}
