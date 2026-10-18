// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import "./Errors.sol";

/// MerchantRegistry (document 06 section 4): merchant id to recipient with a delayed change, the tokens that a merchant accepts, the charge
/// signer, the status and the merchant-level pause. Governance (a timelock in production) onboards a merchant and names its admin; the admin
/// manages the rest; the guardian can only pause. A recipient change is proposed, waits MIN_RECIPIENT_CHANGE_DELAY (PC-17, proposal) and is then
/// accepted, so a compromised admin key cannot redirect a customer's payments before the merchant and the customers' monitors can react.
contract MerchantRegistry {
    uint256 public constant MIN_RECIPIENT_CHANGE_DELAY = 172_800; // PC-17, proposal: 48 hours

    struct Merchant {
        address admin;
        address recipient;
        address chargeSigner;
        bool active;
        bool paused;
    }

    struct PendingRecipient {
        address recipient;
        uint64 readyAt;
    }

    address public immutable governance;
    address public immutable guardian;

    mapping(bytes32 => Merchant) public merchants;
    mapping(bytes32 => PendingRecipient) public pendingRecipient;
    mapping(bytes32 => mapping(address => bool)) public accepts;

    event MerchantRegistered(bytes32 indexed merchantId, address admin, address recipient, address chargeSigner);
    event RecipientProposed(bytes32 indexed merchantId, address recipient, uint64 readyAt);
    event RecipientChanged(bytes32 indexed merchantId, address recipient);
    event ChargeSignerChanged(bytes32 indexed merchantId, address chargeSigner);
    event TokenAcceptanceChanged(bytes32 indexed merchantId, address indexed token, bool accepted);
    event MerchantPauseChanged(bytes32 indexed merchantId, bool paused);
    event MerchantDeactivated(bytes32 indexed merchantId);

    constructor(address governance_, address guardian_) {
        governance = governance_;
        guardian = guardian_;
    }

    modifier onlyAdmin(bytes32 id) {
        if (msg.sender != merchants[id].admin || merchants[id].admin == address(0)) revert NotMerchantAdmin();
        _;
    }

    function register(bytes32 merchantId, address admin, address recipient, address chargeSigner) external {
        if (msg.sender != governance) revert NotGovernance();
        if (merchants[merchantId].admin != address(0)) revert AlreadyRegistered();
        if (admin == address(0) || recipient == address(0)) revert UnknownMerchant();
        merchants[merchantId] = Merchant(admin, recipient, chargeSigner, true, false);
        emit MerchantRegistered(merchantId, admin, recipient, chargeSigner);
    }

    function setAccepted(bytes32 merchantId, address token, bool accepted) external onlyAdmin(merchantId) {
        accepts[merchantId][token] = accepted;
        emit TokenAcceptanceChanged(merchantId, token, accepted);
    }

    function proposeRecipient(bytes32 merchantId, address recipient) external onlyAdmin(merchantId) {
        if (recipient == address(0)) revert UnknownMerchant();
        uint64 readyAt = uint64(block.timestamp + MIN_RECIPIENT_CHANGE_DELAY);
        pendingRecipient[merchantId] = PendingRecipient(recipient, readyAt);
        emit RecipientProposed(merchantId, recipient, readyAt);
    }

    function acceptRecipient(bytes32 merchantId) external onlyAdmin(merchantId) {
        PendingRecipient memory p = pendingRecipient[merchantId];
        if (p.recipient == address(0)) revert NoPendingRecipient();
        if (block.timestamp < p.readyAt) revert RecipientChangeNotReady();
        merchants[merchantId].recipient = p.recipient;
        delete pendingRecipient[merchantId];
        emit RecipientChanged(merchantId, p.recipient);
    }

    function cancelRecipient(bytes32 merchantId) external onlyAdmin(merchantId) {
        delete pendingRecipient[merchantId];
    }

    /// Stored for the typed charge request (finding G11: types.json has no charge-request message yet, so no contract reads this key).
    function setChargeSigner(bytes32 merchantId, address signer) external onlyAdmin(merchantId) {
        merchants[merchantId].chargeSigner = signer;
        emit ChargeSignerChanged(merchantId, signer);
    }

    /// The admin can pause and resume; the guardian can only pause (stop-only).
    function pauseMerchant(bytes32 merchantId) external {
        Merchant storage m = merchants[merchantId];
        if (msg.sender != m.admin && msg.sender != guardian && msg.sender != governance) revert NotAuthorized();
        if (m.admin == address(0)) revert UnknownMerchant();
        m.paused = true;
        emit MerchantPauseChanged(merchantId, true);
    }

    function unpauseMerchant(bytes32 merchantId) external onlyAdmin(merchantId) {
        merchants[merchantId].paused = false;
        emit MerchantPauseChanged(merchantId, false);
    }

    function deactivate(bytes32 merchantId) external {
        if (msg.sender != governance) revert NotGovernance();
        merchants[merchantId].active = false;
        emit MerchantDeactivated(merchantId);
    }

    /// What the router needs at charge time: the recipient that is valid now, if the merchant is registered, active, not paused and accepts the token.
    function settlement(bytes32 merchantId, address token) external view returns (address recipient) {
        Merchant storage m = merchants[merchantId];
        if (m.admin == address(0)) revert UnknownMerchant();
        if (!m.active || m.paused) revert MerchantInactive();
        if (!accepts[merchantId][token]) revert MerchantTokenNotAccepted();
        return m.recipient;
    }
}
