"""The mutants of the ACTUAL FastPay contracts (contracts/src), for tools/contracts_mutation.py.

Each mutant is one textual change of one source file: (id, file, old, new, description). `old` must occur exactly once in the file.
A mutant is KILLED when the test suites of contracts/test (without the gas measurements and the stateful fuzz) fail on it, SURVIVED when they
all pass. A survivor is either a gap in the tests (fix the tests) or an EQUIVALENT mutant (the behaviour that anybody can observe is the same,
for example because a second contract enforces the same rule): equivalent mutants are listed in EQUIVALENT with the reason, and are the only
survivors the runner accepts.
"""

M = []


def mut(mid, file, old, new, desc):
    M.append((mid, file, old, new, desc))


def drop(mid, file, line, desc, tail=""):
    """Remove one whole statement (the text of `line` becomes empty); `tail` is the text that follows it, used only to make the match unique."""
    mut(mid, file, line + tail, tail, desc)


MM = "MandateManager.sol"
SV = "SuccessorValidator.sol"
UL = "UsageLedger.sol"
PR = "PaymentRouter.sol"
GW = "MandateGateway.sol"
MQ = "MigrationQueue.sol"
AL = "lib/AuthLib.sol"
CL = "lib/ContainLib.sol"
PL = "lib/PinLib.sol"
RR = "RouterRegistry.sol"
TP = "TokenPolicyRegistry.sol"
SS = "SignerSetRegistry.sol"
MR = "MerchantRegistry.sol"
ER = "ExecutorRegistry.sol"
FC = "FeeController.sol"

# ------------------------------------------------------------------------------------------------------------------- MandateManager
mut("MM01", MM, "if (msg.sender != customer && msg.sender != gateway) revert NotCustomer();", "if (false) revert NotCustomer();", "_as: anyone may act as the customer")
drop("MM02", MM, "        if (m.customer != customer) revert NotCustomer();\n", "_own: the mandate need not belong to the customer named")
mut("MM03", MM, "        if (n == 1) {\n            address[] storage lst = exposedList[c][r];\n            if (lst.length", "        if (n == 2) {\n            address[] storage lst = exposedList[c][r];\n            if (lst.length", "_liveInc: the list is extended at the wrong count")
mut("MM04", MM, "        live[c][r][t] = n;\n        if (n == 0) {", "        live[c][r][t] = n;\n        if (n == 1) {", "_liveDec: the token leaves the list at the wrong count")
drop("MM05", MM, "                exposedPos[c][r][moved] = pos;\n", "_liveDec: the moved token keeps its old position")
mut("MM06", MM, "if (lst.length >= MAX_EXPOSED_TOKENS_PER_ROUTER) revert ExposureLimit();", "if (lst.length > MAX_EXPOSED_TOKENS_PER_ROUTER) revert ExposureLimit();", "_liveInc: the bound of the index is off by one (a ninth token)")
mut("MM07", MM, "if (exposedUnionCount(customer, router, terms.tokens) > MAX_EXPOSED_TOKENS_PER_ROUTER) revert ExposureLimit();", "if (exposedUnionCount(customer, router, terms.tokens) >= MAX_EXPOSED_TOKENS_PER_ROUTER) revert ExposureLimit();", "activate: the exposure bound is off by one (the eighth token is refused)")
drop("MM08", MM, "        if (pin.pinVersion != 1) revert PinVersionMismatch();\n", "activate: the first pin version is not 1")
drop("MM09", MM, "        if (PinLib.liveCheck(customer, pin) != 0) revert AccountPinMismatch();\n", "activate: PIN_OK is not checked")
drop("MM10", MM, '        if (terms.extensionsHash != bytes32(0)) revert ExtensionsNotSupported();\n', "activate: extensionsHash may be non-zero", tail='        if (!PinLib.wellFormed')
drop("MM11", MM, '        if (!registry.isBindable(router)) revert RouterNotBindable();\n', "activate: the router need not be bindable", tail='        if (terms.extensionsHash')
drop("MM12", MM, "        if (l.exists) revert LineageExists();\n", "activate: a lineage can be created twice")
mut("MM13", MM, " || l.terminated || m.pause != 0 || m.retired) revert MandateNotConsumable();", " || l.terminated || m.retired) revert MandateNotConsumable();", "consume: the pause bits do not stop a charge")
mut("MM14", MM, "m.status != MS_ACTIVE || l.activeMandateId != mandateId || l.terminated", "m.status != MS_ACTIVE || l.terminated", "consume: a superseded mandate can charge")
mut("MM15", MM, " || l.terminated || m.pause != 0 || m.retired) revert MandateNotConsumable();", " || l.terminated || m.pause != 0) revert MandateNotConsumable();", "consume: a retired mandate can charge")
mut("MM16", MM, "if (block.timestamp >= m.expiresAt || block.timestamp < terms.anchorStartsAt) revert MandateNotConsumable();", "if (block.timestamp > m.expiresAt || block.timestamp < terms.anchorStartsAt) revert MandateNotConsumable();", "consume: the expiry second is still valid")
mut("MM17", MM, "if (block.timestamp >= m.expiresAt || block.timestamp < terms.anchorStartsAt) revert MandateNotConsumable();", "if (block.timestamp >= m.expiresAt) revert MandateNotConsumable();", "consume: a charge before startsAt is allowed")
drop("MM18", MM, "        if (msg.sender != m.router) revert WrongRouter();\n", "consume: any caller may consume")
drop("MM19", MM, "        if (!registry.isChargeable(m.router)) revert RouterNotChargeable();\n", "consume: a disabled router can charge")
drop("MM20", MM, "        if (T.hashStruct(pin) != m.pinHash) revert PinHashMismatch();\n", "consume: the pin is not bound by hash")
drop("MM21", MM, "        if (field != 0) revert AccountCodeChanged(m.customer, field);\n", "consume: PIN_OK is not checked")
drop("MM22", MM, '        if (T.hashStruct(terms) != m.termsHash) revert TermsHashMismatch();\n', "consume: the terms are not bound by hash", tail='        if (terms.extensionsHash')
drop("MM23", MM, "        ledger.charge(mandateId, m.lineageId, terms, c);\n", "consume: the ledger is not called (no counter moves)")
mut("MM24", MM, "        if (m.status != MS_ACTIVE) revert MandateNotActive();\n        if (!m.retired) _decStored(m);", "        if (!m.retired) _decStored(m);", "revoke: a revoked mandate can be revoked again")
mut("MM25", MM, "        if (!m.retired) _decStored(m);\n        m.status = MS_REVOKED;", "        _decStored(m);\n        m.status = MS_REVOKED;", "revoke: a retired mandate is released twice")
drop("MM26", MM, "        if (l.activeMandateId == mandateId) l.terminated = true;\n", "revoke: the lineage is not terminated")
mut("MM27", MM, "if (m.status != MS_ACTIVE || m.retired || block.timestamp < m.expiresAt) revert NotRetirable();", "if (m.status != MS_ACTIVE || m.retired) revert NotRetirable();", "retire: a live mandate can be retired")
mut("MM28", MM, "        _decStored(m);\n        m.retired = true;", "        m.retired = true;", "retire: the exposure index is not released")
mut("MM29", MM, "    function _setPause(Mandate storage m, bytes32 mandateId, uint8 value) internal {\n        if (m.status != MS_ACTIVE) revert MandateNotActive();", "    function _setPause(Mandate storage m, bytes32 mandateId, uint8 value) internal {", "pause: a revoked mandate can be paused")
mut("MM30", MM, "_setPause(m, mandateId, m.pause & ~PAUSE_CUSTOMER);\n    }\n\n    /// The risk service", "_setPause(m, mandateId, 0);\n    }\n\n    /// The risk service", "resume: it clears every pause bit")
drop("MM31", MM, "        if (bit != PAUSE_RISK && bit != PAUSE_DELEGATION) revert NotPauseAuthority();\n", "setPauseBit: the authority may set the customer's bit")
drop("MM32", MM, "        if (ContainLib.containedMask(newTerms, oldTerms) != 0) revert TermsNotContained();\n", "reduce: a reduction may widen")
drop("MM33", MM, '        if (T.hashStruct(oldTerms) != m.termsHash) revert TermsHashMismatch();\n', "reduce: the old terms are not bound by hash", tail='        ContainLib.requireShape(newTerms);')
drop("MM34", MM, "            if (!kept) _liveDec(m.customer, m.router, m.tokens[i]);\n", "reduce: a dropped token stays in the exposure index")
drop("MM35", MM, "        m.expiresAt = newTerms.expiresAt;\n        emit MandateReduced", "reduce: the expiry is not updated")
drop("MM36", MM, "        if (newPin.pinVersion != m.pinVersion + 1) revert PinVersionMismatch();\n", "updateAccountPin: the version may skip")
drop("MM37", MM, "        lineages[m.lineageId].pinVersion = newPin.pinVersion;\n", "updateAccountPin: the lineage keeps the old pin version")
mut("MM38", MM, "l.activeMandateId != r.auth.predecessorId || l.terminated || _terminal(p) || p.retired) revert WrongPredecessor();", "l.activeMandateId != r.auth.predecessorId || l.terminated || p.retired) revert WrongPredecessor();", "activateSuccessor: an expired predecessor may migrate")
mut("MM39", MM, "if (block.timestamp > r.auth.deadline) revert AuthorizationExpired(); // A2", "if (block.timestamp >= r.auth.deadline) revert AuthorizationExpired(); // A2", "activateSuccessor: the deadline second is expired")
drop("MM40", MM, '        if (usedNonce[customer][r.auth.nonce]) revert AuthorizationReplayed();\n', "activateSuccessor: a spent nonce is accepted", tail='        if (T.hashStruct(r.predTerms)')
drop("MM41", MM, "        if (T.hashStruct(r.predTerms) != p.termsHash) revert TermsHashMismatch();\n", "activateSuccessor: the predecessor's terms are not bound")
drop("MM42", MM, "        if (T.hashStruct(r.predPin) != p.pinHash) revert PinHashMismatch();\n", "activateSuccessor: the predecessor's pin is not bound")
drop("MM43", MM, "        validator.validate(_context(p, r));\n", "activateSuccessor: the predicates are not run")
drop("MM44", MM, "        usedNonce[p.customer][r.auth.nonce] = true;\n", "activateSuccessor: the nonce is not spent")
mut("MM45", MM, "        _decStored(p);\n        p.status = MS_REVOKED;\n        p.reason", "        p.status = MS_REVOKED;\n        p.reason", "activateSuccessor: the predecessor's exposure is not released")
mut("MM46", MM, "        p.status = MS_REVOKED;\n        p.reason", "        p.reason", "activateSuccessor: the predecessor stays ACTIVE")
drop("MM47", MM, "        n.pause = p.pause; // E3: the pause bits carry over\n", "activateSuccessor: the pause bits are not inherited")
drop("MM48", MM, "        _incTokens(p.customer, r.auth.newRouter, r.newTerms.tokens);\n", "activateSuccessor: the new exposure is not counted")
drop("MM49", MM, "        l.activeMandateId = nid;\n", "activateSuccessor: the lineage keeps the old active mandate")
mut("MM50", MM, "\n                || r.newTerms.anchorStartsAt != r.predTerms.anchorStartsAt || r.newTerms.periodSeconds != r.predTerms.periodSeconds\n", "\n                || r.newTerms.periodSeconds != r.predTerms.periodSeconds\n", "activateSuccessor: the window anchor may change")
mut("MM51", MM, "p.reason = r.auth.kind == REVISION ? RV_SUPERSEDED_REVISION : RV_SUPERSEDED_MIGRATION;", "p.reason = RV_SUPERSEDED_MIGRATION;", "activateSuccessor: a revision is recorded as a migration")
drop("MM52", MM, '        if (msg.sender != gateway) revert NotGateway();\n', "spendNonce: anyone may spend a nonce", tail='        if (usedNonce')
drop("MM53", MM, "        if (usedNonce[customer][nonce]) revert AuthorizationReplayed();\n", "spendNonce: a spent nonce is accepted", tail="        usedNonce[customer][nonce] = true;")
mut("MM54", MM, "        if (msg.sender != queue) _as(customer);\n", "", "activateSuccessor: anyone may call it")
mut("MM55", MM, "        if (msg.sender != queue) _as(customer);\n", "        _as(customer);\n", "activateSuccessor: the queue may not call it")
mut("MM56", MM, "        if (p.customer != customer) revert NotCustomer();\n        Lineage storage l", "        Lineage storage l", "activateSuccessor: the queue may migrate another customer's lineage")
mut("MM57", MM, "            r.newTerms.merchantId != r.predTerms.merchantId", "            false && r.newTerms.merchantId != r.predTerms.merchantId", "activateSuccessor: the merchant may change (the manager's own lineage-constant check)")

# ------------------------------------------------------------------------------------------------------------------- SuccessorValidator
mut("SV01", SV, "if (a.customer != x.customer || a.lineageId != x.lineageId || a.predecessorId != x.predecessorId) revert AuthorizationMismatch();", "if (a.lineageId != x.lineageId || a.predecessorId != x.predecessorId) revert AuthorizationMismatch();", "A3: the customer is not compared")
mut("SV02", SV, "if (a.customer != x.customer || a.lineageId != x.lineageId || a.predecessorId != x.predecessorId) revert AuthorizationMismatch();", "if (a.customer != x.customer || a.predecessorId != x.predecessorId) revert AuthorizationMismatch();", "A3: the lineage is not compared")
mut("SV03", SV, "if (a.customer != x.customer || a.lineageId != x.lineageId || a.predecessorId != x.predecessorId) revert AuthorizationMismatch();", "if (a.customer != x.customer || a.lineageId != x.lineageId) revert AuthorizationMismatch();", "A3: the predecessor is not compared")
drop("SV04", SV, "        if (a.newTermsHash != T.hashStruct(x.newTerms)) revert AuthorizationMismatch();\n", "A3: the new terms are not compared")
mut("SV05", SV, "if (a.newRouterCodeHash != registry.codeHashOf(a.newRouter) || a.newRouterVersion != registry.versionOf(a.newRouter)) {", "if (a.newRouterVersion != registry.versionOf(a.newRouter)) {", "A3: the router code hash is not compared")
mut("SV06", SV, "if (a.newRouterCodeHash != registry.codeHashOf(a.newRouter) || a.newRouterVersion != registry.versionOf(a.newRouter)) {", "if (a.newRouterCodeHash != registry.codeHashOf(a.newRouter)) {", "A3: the router version is not compared")
drop("SV07", SV, "        if (T.hashStruct(a.accountPin) != T.hashStruct(x.newPin)) revert AuthorizationMismatch();\n", "A3: the pin is not compared")
drop("SV08", SV, "        if (a.termsSnapshotHash != snap) revert AuthorizationMismatch();\n", "A3: the snapshot is not compared")
mut("SV09", SV, "T.snapshotHash(x.lineageId, x.predecessorOfPredecessor, x.generation, x.customer, x.predTerms)", "T.snapshotHash(x.lineageId, x.predecessorId, x.generation, x.customer, x.predTerms)", "A3: the snapshot names the wrong predecessor")
mut("SV10", SV, "T.snapshotHash(x.lineageId, x.predecessorOfPredecessor, x.generation, x.customer, x.predTerms)", "T.snapshotHash(x.lineageId, x.predecessorOfPredecessor, x.generation + 1, x.customer, x.predTerms)", "A3: the snapshot names the wrong generation")
drop("SV11", SV, "        if (!registry.isBindable(rNew)) revert RouterNotBindable();\n", "R1: the new router need not be bindable")
drop("SV12", SV, "        if (kind != REVISION && rNew == x.oldRouter) revert WrongKind();\n", "R2: a migration to the same router")
drop("SV13", SV, "        if (kind == REVISION && rNew != x.oldRouter) revert WrongKind();\n", "R2: a revision to another router")
drop("SV14", SV, "        if (kind != REVISION && registry.mode(x.oldRouter) == 1 && kind != EMERGENCY) revert ModeMismatch();\n", "R3: the mode is not enforced")
drop("SV15", SV, "        if (kind > REVISION) revert WrongKind();\n", "R2: an unknown kind")
drop("SV16", SV, "        if (x.newTerms.extensionsHash != bytes32(0) || x.predTerms.extensionsHash != bytes32(0)) revert ExtensionsNotSupported(); // X1\n", "X1: extensions allowed")
drop("SV17", SV, "        if (!PinLib.wellFormed(x.newPin)) revert AccountPinMalformed();\n", "K1: the new pin need not be well-formed")
drop("SV18", SV, "        if (PinLib.liveCheck(x.customer, x.newPin) != 0) revert AccountPinMismatch();\n", "K1: the new pin need not hold on the account")
drop("SV19", SV, "        if (x.newPin.pinVersion != PinLib.nextVersionSuccessor(x.predPin, x.newPin)) revert PinVersionMismatch();\n", "K1: the pin version may skip")
mut("SV20", SV, "if (amount < x.newTerms.tokens[i].perPaymentMax || block.timestamp > expiration) revert NewPermissionMissing(t);", "if (amount <= x.newTerms.tokens[i].perPaymentMax || block.timestamp > expiration) revert NewPermissionMissing(t);", "G1: the allowance must exceed the cap (not equal it)")
mut("SV21", SV, "if (amount < x.newTerms.tokens[i].perPaymentMax || block.timestamp > expiration) revert NewPermissionMissing(t);", "if (amount < x.newTerms.tokens[i].perPaymentMax || block.timestamp >= expiration) revert NewPermissionMissing(t);", "G1: the expiry second is expired")
mut("SV22", SV, "if (amount < x.newTerms.tokens[i].perPaymentMax || block.timestamp > expiration) revert NewPermissionMissing(t);", "if (block.timestamp > expiration) revert NewPermissionMissing(t);", "G1: the amount is not checked")
mut("SV23", SV, "if (amount < x.newTerms.tokens[i].perPaymentMax || block.timestamp > expiration) revert NewPermissionMissing(t);", "if (amount < x.newTerms.tokens[i].perPaymentMax) revert NewPermissionMissing(t);", "G1: the expiry is not checked")
mut("SV24", SV, "x.newTerms.tokens) > T.MAX_EXPOSED_TOKENS_PER_ROUTER) {", "x.newTerms.tokens) >= T.MAX_EXPOSED_TOKENS_PER_ROUTER) {", "X2: the bound is off by one")
mut("SV25", SV, "if (x.auth.kind != REVISION) {\n            if (ContainLib.containedMask(x.newTerms, x.predTerms) != 0) revert TermsNotContained();", "if (x.auth.kind != REVISION) {\n            if (false) revert TermsNotContained();", "C1: containment is not checked")
drop("SV26", SV, "            if (x.auth.widenedMask != 0) revert TermsNotContained();\n", "C1: a migration may declare a widening")
drop("SV27", SV, "            if (!ContainLib.lineageConstantsEqual(x.newTerms, x.predTerms)) revert LineageConstantsChanged();\n", "C2: the lineage constants may change")
drop("SV28", SV, "            if (x.auth.widenedMask != ContainLib.widenedMask(x.newTerms, x.predTerms)) revert WidenedMaskMismatch();\n", "C2: the widened mask is not checked")
mut("SV29", SV, "if (liveN - 1 == 0) {", "if (liveN == 0) {", "O1N: the sibling count is wrong (the lockdown is never required)")
mut("SV30", SV, "if (amount > 0 && block.timestamp <= expiration) revert OldPermissionNotRevoked(t);\n            } else if", "if (amount > 0 && block.timestamp < expiration) revert OldPermissionNotRevoked(t);\n            } else if", "O1N: usable at the expiry second is treated as unusable")
mut("SV31", SV, "} else if (amount >= type(uint160).max) {", "} else if (amount > type(uint160).max) {", "O1N: the unlimited allowance is accepted (never true)")
mut("SV32", SV, "            (uint160 amount, uint48 expiration,) = permit2.allowance(x.customer, t, x.oldRouter);\n            if (amount > 0 && block.timestamp <= expiration) revert OldPermissionNotRevoked(t);\n        }\n    }\n}", "            (uint160 amount, uint48 expiration,) = permit2.allowance(x.customer, t, x.oldRouter);\n            if (amount > 0 && block.timestamp < expiration) revert OldPermissionNotRevoked(t);\n        }\n    }\n}", "O1E: usable at the expiry second is treated as unusable")
mut("SV33", SV, "        uint256 n = mgr.exposedCount(x.customer, x.oldRouter);", "        uint256 n = 0;", "O1E: no exposed token is checked")
mut("SV34", SV, "        if (x.auth.kind == NORMAL) _o1n(x);\n        else if (x.auth.kind == EMERGENCY) _o1e(x);", "        if (x.auth.kind == NORMAL) _o1n(x);", "O1E: not run at all")
mut("SV35", SV, "        if (x.auth.kind == NORMAL) _o1n(x);\n        else if (x.auth.kind == EMERGENCY) _o1e(x);", "        if (x.auth.kind == EMERGENCY) _o1e(x);", "O1N: not run at all")
mut("SV36", SV, "        uint256 n = mgr.exposedCount(x.customer, x.oldRouter);\n        // loop-bound: EXPOSED | exposedCount <= MAX_EXPOSED_TOKENS_PER_ROUTER | the manager's _liveInc refuses a ninth token and predicate X2 refuses the activation\n        for (uint256 j = 0; j < n; ++j) {\n            address t = mgr.exposedAt(x.customer, x.oldRouter, j);", "        uint256 n = x.predTerms.tokens.length;\n        // loop-bound: EXPOSED | exposedCount <= MAX_EXPOSED_TOKENS_PER_ROUTER | the manager's _liveInc refuses a ninth token and predicate X2 refuses the activation\n        for (uint256 j = 0; j < n; ++j) {\n            address t = x.predTerms.tokens[j].token;", "O1E: only the predecessor's own tokens are checked (the model's M_O1E_PRED_ONLY)")

# ------------------------------------------------------------------------------------------------------------------- UsageLedger
drop("UL01", UL, "        if (msg.sender != manager) revert NotManager();\n", "charge: anyone may write the counters")
mut("UL02", UL, "if (cycleIndex > current) revert CycleNotYetDue();", "if (cycleIndex >= current) revert CycleNotYetDue();", "G9: the current cycle is refused")
drop("UL03", UL, "        if (cycleRecord[lineageId][cycleIndex] != bytes32(0)) revert PaymentAlreadySettled();\n", "G9: a settled cycle can settle again")
mut("UL04", UL, "count >= terms.maxChargesPerPeriod", "count > terms.maxChargesPerPeriod", "cadence: one charge too many per period")
mut("UL05", UL, "block.timestamp - k.lastChargeAt < terms.minIntervalSeconds", "block.timestamp - k.lastChargeAt <= terms.minIntervalSeconds", "cadence: the interval boundary is off by one")
mut("UL06", UL, "if (c.feeAmount * 10_000 > c.amount * terms.maxFeeBps) revert FeeTooHigh();", "if (c.feeAmount * 10_000 >= c.amount * terms.maxFeeBps) revert FeeTooHigh();", "fee: the cap itself is refused")
drop("UL07", UL, "        if (storedIdx != idx) used = 0;\n", "windows: a counter is never reset")
drop("UL08", UL, "        if (!ContainLib.withinCap(used, cap)) _capFail(1, fiat);\n", "windows: no window cap")
drop("UL09", UL, "        if (!ContainLib.withinCap(amount, caps[0])) _capFail(0, fiat);\n", "caps: no per-payment cap")
drop("UL10", UL, "        if (!ContainLib.withinCap(u.total, caps[5])) _capFail(2, fiat);\n", "caps: no total cap")
mut("UL11", UL, "(u.day, u.dayIdx) = _window(u.day, u.dayIdx, el / DAY, a, caps[1], fiat);", "(u.day, u.dayIdx) = _window(u.day, u.dayIdx, el / WEEK, a, caps[1], fiat);", "windows: the day window is a week long")
mut("UL12", UL, "(u.thirty, u.thirtyIdx) = _window(u.thirty, u.thirtyIdx, el / THIRTY_DAYS, a, caps[3], fiat);", "(u.thirty, u.thirtyIdx) = _window(u.thirty, u.thirtyIdx, el / DAY, a, caps[3], fiat);", "windows: the thirty-day window is a day long")
mut("UL13", UL, "(u.period, u.periodIdx) = _window(u.period, u.periodIdx, el / period, a, caps[4], fiat);", "(u.period, u.periodIdx) = _window(u.period, u.periodIdx, el / WEEK, a, caps[4], fiat);", "windows: the billing-period window is a week long")
drop("UL14", UL, "            if (!c.hasFiat) revert FiatQuoteRequired();\n", "fiat: a charge without a quote under a fiat cap")
mut("UL15", UL, "cycleRecord[lineageId][c.cycleIndex] = c.quoteDigest != bytes32(0) ? c.quoteDigest : bytes32(uint256(1));", "cycleRecord[lineageId][c.cycleIndex] = bytes32(0);", "G9: the cycle is not recorded")
drop("UL16", UL, "            _bump(fiatUse[lineageId], c.fiatValueMinor, el, terms.periodSeconds, _fiatCaps(terms.fiat), true);\n", "fiat: the fiat counters do not move")
mut("UL17", UL, "        u.total += a;", "        u.total = a;", "caps: the total counter does not accumulate")
mut("UL18", UL, "        _cadence(lineageId, terms, c.cycleIndex, el);\n", "", "G9: no cycle or cadence check")

# ------------------------------------------------------------------------------------------------------------------- PaymentRouter
drop("PR01", PR, "        if (!executors.isExecutor(msg.sender)) revert NotExecutor();\n", "anyone may submit")
drop("PR02", PR, "        if (s == 4) revert TokenBlocked();\n", "a blocked token reports another error")
mut("PR03", PR, "if (fee * 10_000 > gross * fees.feeBps()) revert FeeAboveCeiling();", "if (fee * 10_000 >= gross * fees.feeBps()) revert FeeAboveCeiling();", "the fee at the controller's rate is refused")
drop("PR04", PR, "            if (qb.signature.length == 0) revert FiatQuoteRequired();\n", "a missing quote reports another error")
drop("PR05", PR, "        if (signer == address(0)) revert QuoteSignatureInvalid();\n", "Q2: an unrecoverable signature")
drop("PR06", PR, "        signers.verifySigner(signer, q.signerSetVersion, q.issuedAt); // Q1, Q13\n", "Q1 and Q13: the signer is not checked")
mut("PR07", PR, "if (q.paymentId != paymentId || q.payer != customer || q.token != token || q.amountIn != amount || q.currency != terms.fiat.currency) {", "if (q.payer != customer || q.token != token || q.amountIn != amount || q.currency != terms.fiat.currency) {", "Q4: the payment id is not bound")
mut("PR08", PR, "if (q.paymentId != paymentId || q.payer != customer || q.token != token || q.amountIn != amount || q.currency != terms.fiat.currency) {", "if (q.paymentId != paymentId || q.token != token || q.amountIn != amount || q.currency != terms.fiat.currency) {", "Q5: the payer is not bound")
mut("PR09", PR, "if (q.paymentId != paymentId || q.payer != customer || q.token != token || q.amountIn != amount || q.currency != terms.fiat.currency) {", "if (q.paymentId != paymentId || q.payer != customer || q.amountIn != amount || q.currency != terms.fiat.currency) {", "Q6: the token is not bound")
mut("PR10", PR, "if (q.paymentId != paymentId || q.payer != customer || q.token != token || q.amountIn != amount || q.currency != terms.fiat.currency) {", "if (q.paymentId != paymentId || q.payer != customer || q.token != token || q.currency != terms.fiat.currency) {", "Q7: the amount is not bound")
mut("PR11", PR, "if (q.paymentId != paymentId || q.payer != customer || q.token != token || q.amountIn != amount || q.currency != terms.fiat.currency) {", "if (q.paymentId != paymentId || q.payer != customer || q.token != token || q.amountIn != amount) {", "Q8: the currency is not bound")
drop("PR12", PR, "        if (q.issuedAt > q.validAfter || q.validAfter > q.validUntil) revert QuoteTimesInvalid(); // Q9\n", "Q9: the times need not be ordered")
mut("PR13", PR, "if (q.validAfter > block.timestamp) revert QuoteNotYetValid(); // Q10", "if (q.validAfter >= block.timestamp) revert QuoteNotYetValid(); // Q10", "Q10: validAfter == now is not yet valid")
mut("PR14", PR, "if (block.timestamp > q.validUntil) revert QuoteExpired(); // Q11", "if (block.timestamp >= q.validUntil) revert QuoteExpired(); // Q11", "Q11: validUntil == now is expired")
mut("PR15", PR, "if (q.validUntil - q.issuedAt > maxAge) revert QuoteTtlTooLong(); // Q12", "if (q.validUntil - q.issuedAt >= maxAge) revert QuoteTtlTooLong(); // Q12", "Q12: the maximum life itself is refused")
mut("PR16", PR, "uint256 maxAge = mandateMaxAge < registryMaxTtl ? mandateMaxAge : registryMaxTtl;", "uint256 maxAge = mandateMaxAge;", "Q12: the registry's ceiling is ignored")
drop("PR17", PR, "        if (q.registryVersion != c.tokenVersion) revert RegistryVersionStale(); // Q14\n", "Q14: the token version is not checked")
drop("PR18", PR, "        if (q.boundsVersion != c.currentBoundsVersion) revert BoundsVersionStale(); // Q15\n", "Q15: the bounds version is not checked")
drop("PR19", PR, "        if (q.routeHash != keccak256(abi.encode(T.ROUTE_DIRECT_TAG, block.chainid, token))) revert QuoteRouteMismatch(); // Q16\n", "Q16: the route is not checked")
drop("PR20", PR, "        if (q.priceSourceSetHash != c.priceSourceSetHash) revert QuoteSourceSetMismatch(); // Q17\n", "Q17: the price source set is not checked")
drop("PR21", PR, "        if (!c.pinnedExists) revert BoundsNotPublished();\n", "Q18: a pinned version that was never published is accepted")
mut("PR22", PR, "uint256 lo = c.pinnedMin > c.currentMin ? c.pinnedMin : c.currentMin;", "uint256 lo = c.currentMin;", "Q18: the pinned lower bound is ignored (a wider band widens the mandate)")
mut("PR23", PR, "uint256 hi = c.pinnedMax < c.currentMax ? c.pinnedMax : c.currentMax;", "uint256 hi = c.currentMax;", "Q18: the pinned upper bound is ignored")
mut("PR24", PR, "if (price < lo || price > hi) revert PriceOutOfBounds();", "if (price <= lo || price > hi) revert PriceOutOfBounds();", "Q18: the lower edge of the band is outside")
mut("PR25", PR, "if (price < lo || price > hi) revert PriceOutOfBounds();", "if (price < lo || price >= hi) revert PriceOutOfBounds();", "Q18: the upper edge of the band is outside")
mut("PR26", PR, "uint256 value = (amount * priceE18 + divisor - 1) / divisor;", "uint256 value = (amount * priceE18) / divisor;", "the fiat value is rounded down")
drop("PR27", PR, "        if (value > type(uint64).max) revert FiatValueTooLarge();\n", "the fiat value is truncated to uint64")
drop("PR28", PR, "        manager.consume(req.mandateId, terms, pin, _input(req, x));\n", "charge: the manager is not asked (no mandate check, no counters)")
drop("PR29", PR, "        if (IERC20(token).balanceOf(recipient) - before < merchantAmount) revert BelowMinOut();\n", "charge: no minimum-output check")
drop("PR30", PR, "        if (feeAmount != 0) permit2.transferFrom(customer, fees.feeRecipient(), _u160(feeAmount), token);\n", "charge: the fee is not paid")
mut("PR31", PR, "if (block.timestamp > intent.validUntil || intent.validUntil > deadline) revert IntentExpired();", "if (block.timestamp > intent.validUntil) revert IntentExpired();", "payOnce: validUntil may exceed the signature deadline")
mut("PR32", PR, "if (block.timestamp > intent.validUntil || intent.validUntil > deadline) revert IntentExpired();", "if (block.timestamp >= intent.validUntil || intent.validUntil > deadline) revert IntentExpired();", "payOnce: validUntil == now is expired")
drop("PR33", PR, "        if (intent.grossAmountIn != intent.merchantAmount + intent.feeAmount) revert IntentInvalid();\n", "payOnce: the amounts need not add up")
drop("PR34", PR, "        if (merchants.settlement(intent.merchantId, intent.token) != intent.recipient) revert IntentInvalid();\n", "payOnce: the recipient is not the registry's")
drop("PR35", PR, "        if (intent.feeRecipient != fees.feeRecipient()) revert IntentInvalid();\n", "payOnce: the fee recipient is not the controller's")
drop("PR36", PR, "        routerRegistry.markSettled(intent.paymentId); // once only, across every router version\n", "payOnce: a payment can settle twice")
drop("PR37", PR, "        if (_lock != 1) revert Reentrancy();\n", "no reentrancy lock")
drop("PR38", PR, "        if (IERC20(intent.token).balanceOf(intent.recipient) - beforeMerchant < intent.merchantAmount) revert BelowMinOut(); // G8\n", "payOnce: no minimum-output check")
mut("PR39", PR, "T.hashStruct(intent),\n            T.PAY_ONCE_WITNESS_TYPESTRING,", "bytes32(0),\n            T.PAY_ONCE_WITNESS_TYPESTRING,", "payOnce: the witness is not the intent")
mut("PR40", PR, "details[0] = ISignatureTransfer.SignatureTransferDetails(intent.recipient, intent.merchantAmount);", "details[0] = ISignatureTransfer.SignatureTransferDetails(msg.sender, intent.merchantAmount);", "payOnce: the merchant amount goes to the caller")

# ------------------------------------------------------------------------------------------------------------------- MandateGateway
mut("GW01", GW, "if (block.timestamp > deadline) revert AuthorizationExpired();", "if (block.timestamp >= deadline) revert AuthorizationExpired();", "the deadline second is expired")
drop("GW02", GW, "        if (T.hashStruct(pin) != manager.pinHashOf(mandateId)) revert PinHashMismatch();\n", "the signed pin is not the stored pin")
drop("GW03", GW, "        if (a.routerCodeHash != registry.codeHashOf(a.router) || a.routerVersion != registry.versionOf(a.router)) revert AuthorizationMismatch();\n", "activation: the router code hash and version are not bound")
drop("GW04", GW, "        AuthLib.authAuthority(a.customer, _digest(T.hashStruct(a)), sig, a.accountPin);\n", "activation: no signature check")
drop("GW05", GW, '        manager.spendNonce(r.customer, r.nonce);\n', "revoke: the nonce is not spent", tail='        AuthLib.authExit(r.customer')
drop("GW06", GW, "        AuthLib.authExit(r.customer, _digest(T.hashStruct(r)), sig);\n", "revoke: no signature check")
mut("GW07", GW, "        AuthLib.authAuthority(r.customer, _digest(T.hashStruct(r)), sig, pin);\n        manager.resume(", "        AuthLib.authExit(r.customer, _digest(T.hashStruct(r)), sig);\n        manager.resume(", "resume: accepted under any pin mode")
drop("GW08", GW, "        if (r.oldTermsHash != T.hashStruct(oldTerms) || r.newTermsHash != T.hashStruct(newTerms)) revert AuthorizationMismatch();\n", "reduce: the signed terms are not the supplied ones")
drop("GW09", GW, "            _stored(u.mandateIds[i], curPin); // the pin that signed is the stored pin of every mandate named\n", "pin batch: the signing pin need not be stored")
drop("GW10", GW, "        if (u.mandateIds.length > T.MAX_BATCH) revert BatchTooLarge();\n", "pin batch: no bound", tail="        _fresh(u.deadline);\n        manager.spendNonce(u.customer, u.nonce);")
mut("GW11", GW, "return T.digest(T.mandatesDomainSeparator(block.chainid, address(manager)), structHash);", "return T.digest(T.mandatesDomainSeparator(block.chainid, address(this)), structHash);", "the signed domain names the gateway, not the manager")
drop("GW12", GW, "        AuthLib.authAuthority(r.auth.customer, _digest(T.hashStruct(r.auth)), sig, r.predPin);\n", "successor: no signature check")
drop("GW13", GW, "        _stored(r.auth.predecessorId, r.predPin);\n", "successor: the signing pin is not the stored pin")
mut("GW14", GW, "            manager.updateAccountPin(msg.sender, mandateIds[i], newPin);", "            manager.updateAccountPin(manager.mandateView(mandateIds[i]).customer, mandateIds[i], newPin);", "pin batch: anyone may re-pin anyone's mandates")

# ------------------------------------------------------------------------------------------------------------------- MigrationQueue
drop("MQ01", MQ, "        if (entries.length > T.MAX_BATCH) revert StepTooLarge();\n", "step: no bound")
mut("MQ02", MQ, "if (a.customer != p.customer || a.kind != p.kind || a.newRouter != p.newRouter) revert PlanEntryMismatch();", "if (a.kind != p.kind || a.newRouter != p.newRouter) revert PlanEntryMismatch();", "step: an entry of another customer")
mut("MQ03", MQ, "if (a.customer != p.customer || a.kind != p.kind || a.newRouter != p.newRouter) revert PlanEntryMismatch();", "if (a.customer != p.customer || a.newRouter != p.newRouter) revert PlanEntryMismatch();", "step: an entry of another kind")
mut("MQ04", MQ, "if (a.customer != p.customer || a.kind != p.kind || a.newRouter != p.newRouter) revert PlanEntryMismatch();", "if (a.customer != p.customer || a.kind != p.kind) revert PlanEntryMismatch();", "step: an entry for another router")
drop("MQ05", MQ, "        if (link(T.hashStruct(a), e.next) != head) revert PlanEntryMismatch();\n", "step: the chain is not checked")
drop("MQ06", MQ, "            if (head != bytes32(0)) revert PlanEntryMismatch(); // the chain ends exactly where the plan says\n", "step: the chain may end anywhere")
mut("MQ07", MQ, "if (p.status != ST_OPEN || block.timestamp > p.expiresAt) revert QueueClosed();", "if (p.status != ST_OPEN) revert QueueClosed();", "step: an expired plan runs")
drop("MQ08", MQ, "        if (msg.sender != p.customer) revert NotCustomer();\n", "skip: anyone may skip", tail="        bytes32 head = _advance(p, p.head, e);")
drop("MQ09", MQ, "        if (msg.sender != p.customer) revert NotCustomer();\n", "abort: anyone may abort", tail="        if (p.status != ST_OPEN) revert QueueClosed();")
drop("MQ10", MQ, "        if (p.status != ST_NONE) revert PlanExists();\n", "open: a plan can be reopened")
drop("MQ11", MQ, "        if (block.timestamp <= p.expiresAt) revert QueueNotExpired();\n", "expire: a live plan can be expired")
mut("MQ12", MQ, "if (done > p.total) revert PlanEntryMismatch();", "", "step: more entries than the plan holds")
drop("MQ13", MQ, "        if (!registry.isBindable(newRouter)) revert RouterNotBindable();\n", "open: any router")
mut("MQ14", MQ, "        if (kind > 1) revert WrongKind();\n", "", "open: a revision plan")
drop("MQ15", MQ, "            manager.activateSuccessor(p.customer, e.req);\n", "step: the successor is not activated")

# ------------------------------------------------------------------------------------------------------------------- libraries
mut("AL01", AL, "if (uint256(s) > HALF_N || (v != 27 && v != 28)) return address(0);", "if (v != 27 && v != 28) return address(0);", "recover: a high-s signature is accepted")
mut("AL02", AL, "if (uint256(s) > HALF_N || (v != 27 && v != 28)) return address(0);", "if (uint256(s) > HALF_N) return address(0);", "recover: any v is accepted")
drop("AL03", AL, "        if (sig.length != 65) return address(0);\n", "recover: any length (reads past the signature)")
drop("AL04", AL, "        if (account.code.length == 0) return false;\n", "ERC-1271: an account without code")
mut("AL05", AL, "return ok && bytes4(word) == ERC1271_MAGIC;", "return ok;", "ERC-1271: any return value is valid")
mut("AL06", AL, "            uint8 field = PinLib.liveCheck(customer, pinCtx);\n            if (field != 0) revert AccountCodeChanged(customer, field);\n", "", "authAuthority: ERC-1271 accepted without PIN_OK")
mut("AL07", AL, "        if (recover(digest, sig) == customer) return;\n", "", "authExit: no ECDSA path")
mut("AL08", AL, "if (recover(digest, sig) != customer) revert NotCustomer();", "if (false) revert NotCustomer();", "authAuthority: ECDSA mode accepts any signature")
mut("AL09", AL, "        } else {\n            revert SignatureModeNotPermitted();", "        } else if (mode == PinLib.SM_DIRECT_ONLY) {\n            if (recover(digest, sig) != customer) revert NotCustomer();\n        } else {\n            revert SignatureModeNotPermitted();", "authAuthority: DIRECT_ONLY accepts an ECDSA signature")

K_LINES = [
    ("CL01", "        if (succ.expiresAt > snap.expiresAt) m |= 1; // K.1\n", "K.1 expiry"),
    ("CL04", "        if (_capsViolated(succ, snap)) m |= 1 << 3; // K.4\n", "K.4 token caps"),
    ("CL06", "        if (succ.fiat.boundsVersion != snap.fiat.boundsVersion) m |= 1 << 5; // K.6 (ADR-020)\n", "K.6 bounds version"),
    ("CL08", "        if (succ.maxFeeBps > snap.maxFeeBps) m |= 1 << 7; // K.8\n", "K.8 fee"),
    ("CL09", "        if (succ.extensionsHash != bytes32(0) || snap.extensionsHash != bytes32(0)) m |= 1 << 8; // K.9\n", "K.9 extensions"),
]
for cid, line, name in K_LINES:
    drop(cid, CL, line, f"containment: {name} is not checked")
mut("CL03", CL, "        if (!_tokensSubset(succ, snap)) m |= 1 << 2; // K.3\n", "", "containment: K.3 tokens are not checked")
mut("CL05", CL, "        if (succ.fiat.currency != snap.fiat.currency || succ.fiat.maxQuoteAge > snap.fiat.maxQuoteAge || !_fiatCapsLe(succ.fiat, snap.fiat)) {\n            m |= 1 << 4; // K.5\n        }\n", "", "containment: K.5 fiat caps are not checked")
mut("CL07", CL, "if (!leE(succ.maxChargesPerPeriod, snap.maxChargesPerPeriod) || succ.minIntervalSeconds < snap.minIntervalSeconds) m |= 1 << 6; // K.7", "if (!leE(succ.maxChargesPerPeriod, snap.maxChargesPerPeriod)) m |= 1 << 6; // K.7", "containment: K.7 the interval is not checked")
mut("CL02", CL, "|| succ.periodSeconds != snap.periodSeconds || succ.anchorStartsAt != snap.anchorStartsAt\n        ) m |= 1 << 1; // K.2", "|| succ.periodSeconds != snap.periodSeconds\n        ) m |= 1 << 1; // K.2", "containment: K.2 the anchor is not checked")
mut("CL10", CL, "        if (b == 0) return true;\n        if (a == 0) return false;", "        if (b == 0) return true;\n        if (a == 0) return true;", "leE: no cap counts as narrow as a cap")
mut("CL11", CL, "        if (n == 0 || n > T.MAX_TOKENS_PER_MANDATE) revert TermsInvalid(TOKEN_COUNT);", "        if (n > T.MAX_TOKENS_PER_MANDATE) revert TermsInvalid(TOKEN_COUNT);", "shape: no tokens")
mut("CL12", CL, "(i > 0 && uint160(a) <= uint160(t.tokens[i - 1].token))", "(i > 0 && uint160(a) < uint160(t.tokens[i - 1].token))", "shape: duplicate tokens")
drop("CL13", CL, "        if (t.periodSeconds == 0) revert TermsInvalid(PERIOD_ZERO);\n", "shape: a zero billing period")
mut("CL14", CL, "        if (n.fiat.maxQuoteAge > snap.fiat.maxQuoteAge || n.fiat.boundsVersion != snap.fiat.boundsVersion) m |= 1 << 6;", "        if (n.fiat.maxQuoteAge > snap.fiat.maxQuoteAge) m |= 1 << 6;", "widened: a bounds-version change is not a widening")
mut("CL15", CL, "        if (n.expiresAt > snap.expiresAt) m |= 1;\n        if (!_tokensSubset(n, snap)) m |= 1 << 1;", "        if (!_tokensSubset(n, snap)) m |= 1 << 1;", "widened: a later expiry is not a widening")
mut("PL01", PL, "if (p.pinVersion < 1 || p.accountMode < 1 || p.accountMode > 4) return false;", "if (p.accountMode < 1 || p.accountMode > 4) return false;", "pin: version 0 is well-formed")
mut("PL02", PL, "p.accountCodeHash == T.PIN_EOA && p.delegate == address(0) && p.delegateCodeHash == bytes32(0)\n                && p.implementationFamily == bytes32(0) && p.signatureMode <= 1;", "p.accountCodeHash == T.PIN_EOA && p.delegate == address(0) && p.delegateCodeHash == bytes32(0)\n                && p.implementationFamily == bytes32(0);", "pin: an EOA pin with an ERC-1271 mode")
mut("PL03", PL, "if (p.accountMode == 1) return (h == bytes32(0) || h == KECCAK_EMPTY) ? 0 : FIELD_ACCOUNT_CODE;", "if (p.accountMode == 1) return 0;", "pin: an EOA pin holds on an account with code")
mut("PL04", PL, "            if (hd != p.delegateCodeHash) return FIELD_DELEGATE_CODE;\n", "", "pin: the delegate's code is not checked")
mut("PL05", PL, "&& a.delegateCodeHash == b.delegateCodeHash && a.implementationFamily == b.implementationFamily && a.signatureMode == b.signatureMode;", "&& a.delegateCodeHash == b.delegateCodeHash && a.implementationFamily == b.implementationFamily;", "pin: a signature-mode change keeps the version")
mut("PL06", PL, "return samePinExceptVersion(prev, p) ? prev.pinVersion : prev.pinVersion + 1;", "return prev.pinVersion;", "pin: a changed pin keeps the version")

# ------------------------------------------------------------------------------------------------------------------- registries
mut("RR01", RR, "if (liveRouters >= MAX_LIVE_ROUTERS) revert TooManyLiveRouters();", "if (liveRouters > MAX_LIVE_ROUTERS) revert TooManyLiveRouters();", "registry: a third live router")
mut("RR02", RR, "if (sunsetNotBefore_ < limit) revert NoticeTooShort();", "", "registry: no minimum notice")
mut("RR03", RR, "if (block.timestamp < r.sunsetNotBefore) revert NotYetSunset();", "", "registry: sunset before the notice")
mut("RR04", RR, "if (block.timestamp < uint256(r.sunsetAt) + RETENTION) revert RetentionNotElapsed();", "", "registry: retire before the retention")
mut("RR05", RR, "if (r.state == ST_DEPRECATED) return block.timestamp < uint256(r.deprecatedAt) + ROLLBACK_WINDOW;", "if (r.state == ST_DEPRECATED) return true;", "registry: a deprecated router stays bindable")
mut("RR06", RR, "if (r.state == ST_DEPRECATED) return r.reason == REASON_SECURITY ? 1 : 0;", "if (r.state == ST_DEPRECATED) return 0;", "registry: a security deprecation is not emergency mode")
mut("RR07", RR, "        return 1;\n    }\n\n    // ---- Pay Once", "        return 0;\n    }\n\n    // ---- Pay Once", "registry: a disabled router is not emergency mode")
mut("RR08", RR, "        if (s != ST_ACTIVE && s != ST_DEPRECATED) revert NotRouterOfRegistry();\n", "", "registry: anyone may mark a payment settled")
mut("RR09", RR, "        if (isSettled[paymentId]) revert PaymentAlreadySettled();\n", "", "registry: a payment settles twice")
mut("RR10", RR, "        if (msg.sender != guardian && msg.sender != governance) revert NotAuthorized();\n        Router storage r = routers[router];\n        if (r.state != ST_ACTIVE && r.state != ST_DEPRECATED)", "        Router storage r = routers[router];\n        if (r.state != ST_ACTIVE && r.state != ST_DEPRECATED)", "registry: anyone may disable a router")
mut("RR11", RR, "if (was && !now_) liveRouters -= 1;", "", "registry: the live counter never goes down")
mut("TP01", TP, "if ((diff + minPriceE18 - 1) / minPriceE18 > maxBandWidthBps) revert BandTooWide();", "", "bounds: no width ceiling")
mut("TP02", TP, "if ((diff + minPriceE18 - 1) / minPriceE18 > maxBandWidthBps) revert BandTooWide();", "if ((diff) / minPriceE18 > maxBandWidthBps) revert BandTooWide();", "bounds: the width is rounded down")
mut("TP03", TP, "if (minPriceE18 == 0 || minPriceE18 > maxPriceE18) revert InvalidBounds();", "if (minPriceE18 > maxPriceE18) revert InvalidBounds();", "bounds: a zero minimum")
mut("TP04", TP, "        if (msg.sender != guardian && msg.sender != governance) revert NotAuthorized();\n        TokenPolicy storage p = policy[token];\n        if (p.status == STATUS_UNLISTED || p.status == STATUS_BLOCKED) revert TokenNotListed();\n        p.status = STATUS_BLOCKED;", "        TokenPolicy storage p = policy[token];\n        if (p.status == STATUS_UNLISTED || p.status == STATUS_BLOCKED) revert TokenNotListed();\n        p.status = STATUS_BLOCKED;", "policy: anyone may block a token")
mut("TP05", TP, "if (status_ != STATUS_SETTLEMENT && status_ != STATUS_DIRECT_PAYMENT) revert TokenNotListed(); // SWAP_ONLY and BLOCKED cannot be listed in v1", "", "policy: a token can be listed as SWAP_ONLY or BLOCKED")
mut("TP06", TP, "        if (p.status == STATUS_UNLISTED || p.status == STATUS_BLOCKED) revert TokenNotListed(); // a blocked token is blocked for good", "        if (p.status == STATUS_UNLISTED) revert TokenNotListed();", "policy: a blocked token can be unblocked")
mut("TP07", TP, "        v = currentBoundsVersion[token][currency] + 1;\n        currentBoundsVersion[token][currency] = v;", "        v = currentBoundsVersion[token][currency] + 1;", "bounds: the current version never moves")
mut("TP08", TP, "        p.version += 1;\n        emit BoundsPublished", "        emit BoundsPublished", "bounds: a publication does not bump the token version")
mut("SS01", SS, "if (members.length > MAX_SIGNERS_PER_SET) revert TooManySigners(members.length, MAX_SIGNERS_PER_SET);", "", "signers: no bound on the set")
mut("SS02", SS, "if (removedAt[members[i]] != 0) revert QuoteSignerTombstoned(members[i]);", "", "signers: a tombstoned key can be proposed")
mut("SS03", SS, "if (removedAt[list[i]] != 0) revert QuoteSignerTombstoned(list[i]); // a key removed after the proposal cannot join", "", "signers: a key removed after the proposal can join")
mut("SS04", SS, "if (version != current + 1) revert SignerSetVersionOrder();", "", "signers: sets activate out of order")
mut("SS05", SS, "        if (msg.sender != guardian && msg.sender != governance) revert NotAuthorized();\n        if (removedAt[key] == 0) {", "        if (removedAt[key] == 0) {", "signers: anyone may remove a key")
mut("SS06", SS, "if (removedAt[key] != 0) revert QuoteSignerRemoved();", "", "signers: a removed key is accepted")
mut("SS07", SS, "if (s.stopped) revert QuoteSignerSetStopped();", "", "signers: a stopped set is accepted")
mut("SS08", SS, "if (s.activeFrom > issuedAt) revert QuoteSignerSetRetired();", "if (s.activeFrom >= issuedAt) revert QuoteSignerSetRetired();", "signers: a quote issued at the activation second is refused")
mut("SS09", SS, "if (!(issuedAt < s.retiredAt && block.timestamp <= uint256(s.retiredAt) + quoteSetGrace)) revert QuoteSignerSetRetired();", "if (!(issuedAt < s.retiredAt && block.timestamp < uint256(s.retiredAt) + quoteSetGrace)) revert QuoteSignerSetRetired();", "signers: the last second of the grace is refused")
mut("SS10", SS, "if (!(issuedAt < s.retiredAt && block.timestamp <= uint256(s.retiredAt) + quoteSetGrace)) revert QuoteSignerSetRetired();", "if (!(block.timestamp <= uint256(s.retiredAt) + quoteSetGrace)) revert QuoteSignerSetRetired();", "signers: a quote issued after the rotation is honoured under the retired set")
mut("SS11", SS, "if (grace < maxQuoteTtl || grace > 2 * maxQuoteTtl) revert InvalidBounds();", "", "signers: any grace")
mut("SS12", SS, "if (old != 0) sets[old].retiredAt = uint64(block.timestamp);", "", "signers: the old set is not retired")
mut("MR01", MR, "if (block.timestamp < p.readyAt) revert RecipientChangeNotReady();", "", "merchant: no recipient delay")
mut("MR02", MR, "if (block.timestamp < p.readyAt) revert RecipientChangeNotReady();", "if (block.timestamp <= p.readyAt) revert RecipientChangeNotReady();", "merchant: the ready second is not ready")
mut("MR03", MR, "uint256 public constant MIN_RECIPIENT_CHANGE_DELAY = 172_800;", "uint256 public constant MIN_RECIPIENT_CHANGE_DELAY = 86_400;", "merchant: a one-day delay")
mut("MR04", MR, "if (!accepts[merchantId][token]) revert MerchantTokenNotAccepted();", "", "merchant: any token")
mut("MR05", MR, "if (!m.active || m.paused) revert MerchantInactive();", "if (!m.active) revert MerchantInactive();", "merchant: a paused merchant settles")
mut("MR06", MR, "if (msg.sender != m.admin && msg.sender != guardian && msg.sender != governance) revert NotAuthorized();", "", "merchant: anyone may pause")
mut("ER01", ER, "        if (msg.sender != guardian && msg.sender != governance) revert NotAuthorized();\n", "", "executors: anyone may remove an executor")
mut("FC01", FC, "if (feeBps_ > ceilingBps) revert FeeAboveCeiling();", "", "fees: no ceiling on a change")

# ------------------------------------------------------------------------------------------------------------------- equivalents
EQUIVALENT = {
    "MM14": "a mandate that is not its lineage's active mandate is always REVOKED: E1 revokes the predecessor in the same transaction that makes the successor active, so the status test of consume already refuses it",
    "MM15": "retire requires block.timestamp >= expiresAt and consume refuses block.timestamp >= expiresAt, so a retired mandate is always expired and refused by the time test",
    "SV03": "ctx.predecessorId is built by the manager from auth.predecessorId, so the comparison cannot differ; it stays as a guard for a context built another way",
    "GW13": "the manager compares the hash of the supplied pin with the stored one and raises the same PinHashMismatch",
    "AL02": "the ecrecover precompile itself returns no address for a v other than 27 and 28",
    "AL04": "a call to an account without code returns no data, and the next line refuses return data shorter than one word",
}
