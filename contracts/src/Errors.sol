// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

// Custom errors of the FastPay contracts. Names follow documents 11, 12 and 17 where they name one; the others are named here (and are
// listed in contracts/README.md). The reference model of spec/foundry uses the same names for the same conditions, so that the vectors and
// the hand-written tests of the model can be compared with these contracts error by error.

// ---- authorization
error NotCustomer();
error SignatureModeNotPermitted();
error AuthorizationExpired();
error AuthorizationReplayed();
error AuthorizationMismatch();
error NotGovernance();
error NotGuardian();
error NotAuthorized();
error NotPauseAuthority();
error NotGateway();
error NotManager();

// ---- mandates, lineages, migration
error UnknownMandate();
error MandateNotActive();
error MandateNotConsumable();
error NotRetirable();
error NoTokensLeft();
error TokenNotInMandate();
error WrongPredecessor();
error WrongKind();
error ModeMismatch();
error WrongRouter();
error RouterNotBindable();
error RouterNotChargeable();
error ExtensionsNotSupported();
error AccountPinMalformed();
error AccountPinMismatch();
error PinVersionMismatch();
error PinHashMismatch();
error TermsHashMismatch();
error AccountCodeChanged(address customer, uint8 field);
error NewPermissionMissing(address token);
error OldPermissionNotRevoked(address token);
error ResidualAllowanceUnbounded(address token);
error ExposureLimit();
error TermsNotContained();
error LineageConstantsChanged();
error WidenedMaskMismatch();
error TermsInvalid(uint8 reason);
error ArrayTooLong(uint256 length, uint256 max);
error BatchTooLarge();
error LineageExists();

// ---- charges
error PaymentAlreadySettled();
error CycleNotYetDue();
error ChargeTooSoon();
error ChargesPerPeriodExceeded();
error TokenPerPaymentCapExceeded();
error TokenWindowCapExceeded();
error TokenTotalCapExceeded();
error FiatQuoteRequired();
error FiatPerPaymentCapExceeded();
error FiatWindowCapExceeded();
error FiatTotalCapExceeded();
error FiatValueTooLarge();
error AmountTooLarge();
error FeeTooHigh();

// ---- quotes and signer sets
error QuoteSignerUnauthorized();
error QuoteSignerRemoved();
error QuoteSignerSetRetired();
error QuoteSignerSetStopped();
error QuoteSignerTombstoned(address key);
error QuoteSignatureInvalid();
error QuoteBindingMismatch();
error QuoteTimesInvalid();
error QuoteNotYetValid();
error QuoteExpired();
error QuoteTtlTooLong();
error RegistryVersionStale();
error BoundsVersionStale();
error QuoteRouteMismatch();
error QuoteSourceSetMismatch();
error PriceOutOfBounds();
error SignerSetNotProposed();
error SignerSetVersionOrder();
error TooManySigners(uint256 count, uint256 max);

// ---- registries
error WrongRouterState();
error TooManyLiveRouters();
error SuccessorNotActive();
error NoticeTooShort();
error NotYetSunset();
error RetentionNotElapsed();
error TokenNotListed();
error TokenBlocked();
error BoundsNotPublished();
error InvalidBounds();
error BandTooWide();
error UnknownMerchant();
error MerchantInactive();
error MerchantTokenNotAccepted();
error RecipientChangeNotReady();
error NotExecutor();
error FeeAboveCeiling();
error MerchantPaused();
error AlreadyRegistered();
error NoPendingRecipient();
error NotMerchantAdmin();

// ---- router
error Reentrancy();
error RouterPaused();
error IntentInvalid();
error IntentExpired();
error BelowMinOut();
error NotRouterOfRegistry();

// ---- migration queue
error PlanExists();
error PlanUnknown();
error PlanOpen();
error PlanEntryMismatch();
error QueueClosed();
error QueueMismatch();
error QueueNotExpired();
error StepTooLarge();
