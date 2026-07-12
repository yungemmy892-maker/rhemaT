# VerseID — Comprehensive Application Audit

**Scope:** Django/MongoEngine backend, TanStack Start (React) frontend, standalone admin dashboard.
**Method:** Static code review tracing real user/data flows (auth, search/identify, payments, avatar upload, admin access, saved-verse toggling) end-to-end across frontend and backend. Findings below are based on the actual current code, not assumptions about typical stacks.

**Honesty note on coverage:** This audit is thorough but not exhaustive — a handful of items are explicitly marked *Needs Verification* where I could trace the code path but not observe runtime behavior (timing attacks, browser memory profiling, full WCAG contrast measurement, load-test-only race conditions). Everything else marked Confirmed or High Confidence was verified by reading the actual source referenced.

---

## Critical

None found. There is no unauthenticated data exposure, no broken access control allowing cross-user data access, and no trivially exploitable injection vector in the code as written.

---

## High

### H1 — No rate limiting anywhere in the API
**Category:** Security
**Location:** `config/settings.py` (`REST_FRAMEWORK` block); applies globally, most acutely to `auth_api/views.py` — `EmailLoginView`, `ForgotPasswordView`, `VerifyResetCodeView`
**Issue:** There is no `DEFAULT_THROTTLE_CLASSES`/`DEFAULT_THROTTLE_RATES` in DRF settings, no per-view `throttle_classes`, and no third-party rate-limiting package anywhere in `requirements.txt`.
**Impact:** `EmailLoginView` allows unlimited password-guessing attempts against any known email address, limited only by Argon2's inherent hashing cost (slow, but not a substitute for a real lockout). `ForgotPasswordView` can be called an unlimited number of times for any email, allowing an attacker to email-bomb a victim with reset codes. `VerifyResetCodeView`'s 5-attempt lockout is scoped per-code, not per-IP/per-account — an attacker who can also trigger new codes (they can, freely) isn't meaningfully slowed beyond the per-code limit.
**Evidence:**
```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["auth_api.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "EXCEPTION_HANDLER": "config.exceptions.custom_exception_handler",
    "UNAUTHENTICATED_USER": None,
}
```
No throttle keys present. `grep -rn "throttle|ratelimit" backend/` returns nothing.
**Reproduction:** Script repeated POSTs to `/api/v1/auth/login/` with a known email and varying passwords; no 429 ever returned, no lockout after N failures.
**Recommended fix:** Add `rest_framework.throttling.ScopedRateThrottle` (or `django-ratelimit`) with distinct scopes for `login` (e.g. 5/min per IP), `forgot-password` (e.g. 3/hour per IP+email), and `verify-reset-code`. Consider an account-level lockout after N failed logins in a rolling window, independent of IP.
**Confidence:** Confirmed

### H2 — Icon-only interactive elements lack accessible names across the app
**Category:** Accessibility
**Location:** Widespread; concretely verified in `frontend/src/routes/app.results.tsx` (4x back-navigation `<Link>` wrapping only `<ArrowLeft>`, lines 266/289/334/408), and reflected by the fact that `aria-label` appears **exactly once** in the entire `routes/` + `components/` tree.
**Issue:** Icon-only buttons/links (back navigation, share, copy, mic toggle, theme toggle, close/X on sheets, etc.) render only an SVG icon with no visible text, `aria-label`, or `sr-only` text.
**Impact:** Screen reader users hear "link" or "button" with no indication of purpose or destination. This fails WCAG 2.2 AA 4.1.2 (Name, Role, Value) and 2.4.4 (Link Purpose in Context) on what is very likely dozens of interactive elements across Results, Library, Settings, Voice, and Profile screens.
**Evidence:**
```tsx
<Link to="/app/home" className="h-10 w-10 rounded-full glass grid place-items-center">
  <ArrowLeft className="h-4.5 w-4.5" />
</Link>
```
No `aria-label="Back to Home"` or equivalent.
**Reproduction:** Navigate the app with VoiceOver/NVDA/TalkBack; back buttons, the mic toggle on Voice, the theme toggle, and sheet-close buttons announce no purpose.
**Recommended fix:** Add `aria-label` to every icon-only interactive element app-wide (a targeted `grep` for `<Link` / `<button` containing only a Lucide icon child, with no adjacent text node, will surface most instances). Consider a lint rule (`eslint-plugin-jsx-a11y`) to prevent regression.
**Confidence:** Confirmed for the cited instances; High Confidence that the pattern repeats broadly given the near-total absence of `aria-label` project-wide.

### H3 — `SavedVerse` toggle is a non-atomic check-then-act race, can 500 on concurrent taps
**Category:** Race Condition / Reliability
**Location:** `backend/preferences/views.py` — `SavedVersesView.post()`; `frontend/src/hooks/queries/usePreferences.ts` — `useToggleSaved()`; call site `frontend/src/routes/app.results.tsx` line ~481
**Issue:** The save/unsave toggle reads current state, then acts on it, with no locking or idempotency key — and the frontend button has no `isPending`-based disable guard, so rapid double-tap is trivial to trigger.
**Impact:** Two near-simultaneous POSTs for the same verse can both read "not saved" before either writes. Since `SavedVerse` has a unique index on `(user_id, verse_id)`, the second `.save()` call raises `NotUniqueError`, which is **not caught** — the losing request gets an unhandled 500 instead of a clean toggle result. Even without the exception, a double-tap toggle can leave the verse in the opposite state from what the user intended.
**Evidence:**
```python
existing = SavedVerse.objects(user_id=user_id, verse_id=verse_id).first()
if existing:
    existing.delete()
    saved = False
else:
    SavedVerse(user_id=user_id, verse_id=verse_id, version=version).save()  # can raise NotUniqueError
    saved = True
```
```tsx
onClick={() =>
  toggleSaved.mutate({ verseId: verse.id, version: verse.version })
}
```
No `disabled={toggleSaved.isPending}` on the button.
**Reproduction:** Double-click/double-tap the Save button on a Results page fast enough that both requests are in flight simultaneously (throttle network to widen the window). Observe either an inconsistent final saved-state or a 500 in server logs.
**Recommended fix:** Disable the button while `toggleSaved.isPending`. Server-side, wrap the branch in a try/except for `NotUniqueError` (mongoengine) and treat it as "already saved" rather than propagating a 500. Longer-term, an atomic upsert avoids the read-then-write window entirely.
**Confidence:** Confirmed (code path and missing guard both directly verified); the unique-index collision behavior is High Confidence based on the declared index and absence of exception handling.

### H4 — Destructive account deletion has no double-submit guard or in-flight feedback
**Category:** Reliability / UX
**Location:** `frontend/src/routes/app.settings.tsx` — `onDelete()` handler and its confirm button (~line 453)
**Issue:** `onDelete` is `async` and calls `deleteAccount()` with no local pending state, and the triggering button has no `disabled` guard tied to an in-flight request.
**Impact:** A user who taps "Delete account" and doesn't see instant feedback (slow network) may tap again, firing a second concurrent delete request against an already-being-deleted account. Best case this just 404s harmlessly server-side; worst case (depending on how account deletion cascades — not fully traced in this pass) a second concurrent delete could race with in-progress cleanup of related collections (SavedVerse, SearchHistory, Subscription, etc.) with undefined ordering.
**Evidence:**
```tsx
const onDelete = async () => {
  await deleteAccount();
  setConfirm(false);
  navigate({ to: "/" });
};
```
No `isDeleting` state; no `disabled` prop found on the confirm button in this file.
**Reproduction:** Trigger the delete confirmation, then rapidly tap the confirm button twice on a throttled connection.
**Recommended fix:** Add local `isDeleting` state, disable the button and show a spinner while true, and treat this the same as any other mutation — ideally via `useMutation` with `isPending` rather than a bare async handler.
**Confidence:** Confirmed for the missing guard; the downstream cascade-race impact is Needs Verification (didn't trace the full account-deletion cascade this pass).

---

## Medium

### M1 — User-supplied `name` is interpolated unescaped into HTML emails
**Category:** Security (stored HTML injection)
**Location:** `backend/notifications/email.py` — `_welcome_html()`, `_daily_verse_html()`, and the welcome/reset code paths that pass `user.name`/`first_name` into an f-string template
**Issue:** `User.name` (settable at registration via `EmailRegisterSerializer`, or via Edit Profile) is inserted directly into HTML email templates via Python f-strings, which do not HTML-escape. A name like `<img src=x onerror=alert(1)>` becomes live markup in the rendered email.
**Impact:** Limited in practice — these emails are only ever sent to the *same* user's own inbox (no verse-sharing/social feature exists that broadcasts a name to other users), so this is effectively self-inflicted HTML injection in your own inbox rather than a cross-user attack. Real email clients also generally strip `<script>` and disable JS execution in HTML mail, so script execution is unlikely; CSS-based phishing/spoofing within the rendered email is more plausible. Still a genuine trust-boundary violation worth closing.
**Evidence:**
```python
f"Hi {name},<br/><br/>Your account is ready. ..."
```
No `escape()`/equivalent applied to `name` before interpolation, unlike the admin dashboard's `script.js` which does escape equivalent fields.
**Recommended fix:** HTML-escape any user-supplied string (`name`, and anything else user-controlled) before interpolating into these f-string templates — e.g. `html.escape(name)` from Python's stdlib.
**Confidence:** Confirmed (code path directly read); real-world severity is genuinely low given the single-recipient-is-the-attacker constraint, hence Medium rather than High.

### M2 — Admin key comparison is not constant-time
**Category:** Security
**Location:** `backend/analytics/views.py` — `HasAdminKey.has_permission()`
**Issue:** `request.headers.get("X-Admin-Key") == key` uses Python's standard `==`, which short-circuits on the first mismatched byte and is not constant-time.
**Impact:** In principle enables a timing side-channel to recover the admin key byte-by-byte. In practice, network jitter over HTTP makes this extremely hard to exploit remotely — but combined with H1 (no rate limiting), nothing stops high-volume timing measurement attempts either, which makes this more practically relevant than it would otherwise be.
**Evidence:**
```python
return bool(key) and request.headers.get("X-Admin-Key") == key
```
**Recommended fix:** Use `hmac.compare_digest(request.headers.get("X-Admin-Key", ""), key)`.
**Confidence:** Confirmed as written; practical exploitability is Needs Verification (would require actual timing measurement against production infrastructure to assess).

### M3 — Avatar upload's content-type allowlist is dead code
**Category:** Security / Reliability
**Location:** `backend/users/avatars.py`
**Issue:** `ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}` is declared but never referenced anywhere else in the file. Actual validation relies solely on `Image.open(uploaded_file); image.verify()` — Pillow's own format sniffing — with no explicit check against the declared allowlist or the request's actual `Content-Type` header.
**Impact:** The code reads as if content-type is being validated (the constant exists, is named clearly, sits right next to the validation logic) but isn't actually enforced — any format Pillow can parse is accepted, a broader surface than the five formats the constant implies were intended. False sense of security more than an active exploit path, since Pillow's `verify()` still rejects non-image files.
**Evidence:** `grep -n "ALLOWED_CONTENT_TYPES" users/avatars.py` returns only the declaration, no usage.
**Recommended fix:** Either enforce it (`if uploaded_file.content_type not in ALLOWED_CONTENT_TYPES: raise AvatarUploadError(...)`) or remove the unused constant so the code doesn't imply a control that isn't active.
**Confidence:** Confirmed.

### M4 — `callback_url` passed to Paystack is not validated against an allowlist
**Category:** Security (open redirect)
**Location:** `backend/billing/views.py` — `InitiatePaymentView.post()`; `backend/billing/serializers.py` — `InitiatePaymentSerializer`
**Issue:** The client-supplied `callback_url` is forwarded to Paystack's `initialize_transaction()` unvalidated, and Paystack will redirect the user's browser there after payment completes.
**Impact:** Low in isolation — this endpoint requires authentication, and exploiting it to redirect *someone else's* browser would require either an XSS vector to fire the request cross-user (none found in this audit) or CSRF (mitigated by this being a Bearer-token API, not cookie-authenticated). Worth closing as defense-in-depth regardless, since payment-flow redirects are a common phishing vector class.
**Evidence:**
```python
"cancel_action": data["callback_url"].replace("status=success", "status=cancelled"),
...
callback_url=data["callback_url"],
```
No domain allowlist check on `data["callback_url"]`.
**Recommended fix:** Validate `callback_url` starts with `settings.FRONTEND_URL` (or an explicit allowlist) before passing it to Paystack.
**Confidence:** Confirmed as written; realistic exploitability without a separate XSS/CSRF vector is low.

### M5 — In-process schedulers can double-charge/double-send under multi-worker deployment
**Category:** Race Condition / Reliability
**Location:** `backend/notifications/scheduler.py`, `backend/billing/scheduler.py`, and their respective management commands
**Issue:** Documented in the code's own comments as a known limitation: each gunicorn worker process starts its own copy of the in-process scheduler thread. The daily-verse and subscription-renewal dedup guards (`last_daily_sent_date`, `last_renewal_attempt_date`) are date-granularity, not lock-based, so two workers racing within the same check-then-write window can both pass the "not yet done today" check before either writes.
**Impact:** Under a single-worker deployment (the documented assumption) this is a non-issue. If deployed with multiple workers — a completely normal production configuration — a user could receive two renewal charges or two daily-verse emails on rare unlucky timing.
**Evidence:** Self-documented in `billing/scheduler.py`'s module docstring; the underlying guard is a plain field comparison with no atomic-claim mechanism.
**Recommended fix:** Either enforce single-worker deployment explicitly (document/guard at startup), or replace the date-flag guard with an atomic conditional update (e.g. `Subscription.objects(id=sub.id, last_renewal_attempt_date__ne=today).update(set__last_renewal_attempt_date=today)`, proceeding only if the update matched one document), which closes the race regardless of worker count.
**Confidence:** Confirmed (this is the authors' own documented caveat, verified against the actual guard implementation).

### M6 — No visible loading/disabled state on several async action buttons
**Category:** Reliability / Accessibility
**Location:** Pattern observed in `app.results.tsx` (Save button), `app.settings.tsx` (Delete account, sign out); not exhaustively traced across every screen
**Issue:** Beyond the two confirmed instances in H3/H4, the broader pattern of calling `mutate()`/an async handler directly from `onClick` without surfacing `isPending` in the button's `disabled`/visual state appears to repeat. Not exhaustively verified screen-by-screen.
**Impact:** Users on slow networks get no feedback that an action registered, encouraging repeat taps and the downstream race conditions described above; screen reader users get no `aria-busy` signal either.
**Recommended fix:** Audit every `useMutation` call site for a corresponding `disabled={mutation.isPending}` on its trigger element, and add `aria-busy="true"` while pending.
**Confidence:** Needs Verification beyond the two confirmed instances — flagged as a pattern worth a dedicated pass, not a fully traced finding.

---

## Low

### L1 — `localStorage` used for access + refresh tokens
**Category:** Security
**Location:** `frontend/src/services/client.ts`
**Issue:** Both tokens are stored in `localStorage`, which is readable by any JavaScript executing on the page.
**Impact:** In the absence of a confirmed XSS vector (this audit found none — see P1), this is a defense-in-depth gap rather than an active vulnerability. If an XSS vector is ever introduced elsewhere in the app, token theft becomes trivial and session-lifetime rather than single-request.
**Recommended fix:** Consider httpOnly cookies for the refresh token at minimum (requires backend changes to set/read cookies and CSRF protection for cookie-authenticated requests — a real architectural change, not a quick win). Short of that, keep the current no-XSS-vector posture intact and treat any future `dangerouslySetInnerHTML` addition as high-risk.
**Confidence:** Confirmed as the storage mechanism; real-world risk is contingent on an XSS vector that doesn't currently exist.

### L2 — DRA version excluded from default multi-version search pool without user-facing explanation
**Category:** Reliability / UX
**Location:** `backend/search/matching.py` — `_version_pool()`
**Issue:** Users who haven't explicitly selected DRA as their Bible version will never get DRA matches, and users who have selected DRA lose the benefit of semantic search's cross-version routing due to DRA's differing verse numbering. Not surfaced in the UI (the Help FAQ mentions it, partially mitigating).
**Impact:** A DRA user may perceive search quality as worse without understanding why.
**Recommended fix:** Consider a subtle in-app hint when DRA is selected; no urgent code change needed given the FAQ already covers it.
**Confidence:** Confirmed as designed behavior; classified Low since it's a documented tradeoff rather than an oversight.

### L3 — Avatar upload relies on Pillow's default decompression-bomb threshold rather than an explicit one
**Category:** Reliability
**Location:** `backend/users/avatars.py`
**Issue:** No explicit `Image.MAX_IMAGE_PIXELS` is set; relies on Pillow's built-in default (~89 million pixels).
**Impact:** Low — the default is active and reasonable. Worth being explicit rather than implicit.
**Recommended fix:** Set `Image.MAX_IMAGE_PIXELS` explicitly near the top of `avatars.py`.
**Confidence:** Confirmed absence of an explicit setting; the mitigating default is High Confidence based on documented Pillow behavior, not independently re-verified in this environment.

### L4 — CSV export in the admin dashboard doesn't escape formula-injection characters
**Category:** Security
**Location:** `admin-dashboard/script.js` — `exportCsv()`
**Issue:** User-controlled fields (`name`, `email`) are written into CSV rows without checking for a leading `=`, `+`, `-`, or `@`, which spreadsheet applications can interpret as formulas on open (CSV injection).
**Impact:** If a user registers with a formula-like name and an admin later opens the exported CSV in a spreadsheet app with legacy dynamic-execution support, it could trigger. Modern Excel/Sheets increasingly block this by default, but not universally.
**Evidence:**
```js
...state.data.recentUsers.map(
  (u) => `"${u.name}","${u.email}",${u.plan},${u.signupMethod},${u.identifiedCount},${u.createdAt}`
),
```
**Recommended fix:** Prefix any field starting with `=`, `+`, `-`, or `@` with a single quote before writing to CSV.
**Confidence:** Confirmed code path; real-world exploitability depends on the admin's specific spreadsheet application/version.

### L5 — Reduced-motion preference not respected
**Category:** Accessibility
**Location:** Frontend-wide — Framer Motion is used extensively with no `prefers-reduced-motion` handling found.
**Issue:** No `useReducedMotion` or CSS `@media (prefers-reduced-motion: reduce)` override was found gating the animations.
**Impact:** Users with vestibular disorders who've set their OS-level reduced-motion preference still get the full set of slide/fade/scale transitions throughout the app.
**Recommended fix:** Wrap shared animation variants with a check against `useReducedMotion()`, falling back to instant/opacity-only transitions when true.
**Confidence:** High Confidence (absence verified via search for "reduced-motion" and "useReducedMotion" — zero matches), not exhaustively confirmed against every single animated component.

---

## Informational

### I1 — Unused shadcn `chart.tsx` component contains `dangerouslySetInnerHTML`
**Location:** `frontend/src/components/ui/chart.tsx`
Dead code (no importers found anywhere in the codebase) that injects CSS custom properties via `dangerouslySetInnerHTML`. Not exploitable as-is (input is a developer-provided config object, not user data), but worth removing as unused boilerplate to reduce audit surface for future reviewers.
**Confidence:** Confirmed unused via project-wide import search.

### I2 — `search_verses()` in the matching engine is unreferenced
**Location:** `backend/search/matching.py`
This multi-result search function exists and is fully implemented but is not called from any view. Not a security or reliability issue, just dead code worth either wiring up or removing.
**Confidence:** Confirmed via grep for callers.

---

## Positive findings (things done correctly)

- **P1 — No confirmed XSS vector.** `dangerouslySetInnerHTML` usage is limited to one unused dead component and one static, developer-authored script string (theme-init). All user-facing dynamic content in the React app goes through JSX's default auto-escaping.
- **P2 — Paystack webhook signature verification is present and correctly gates processing**, with event-ID-based idempotency preventing duplicate-event side effects (`billing/views.py`).
- **P3 — CSRF is a non-issue for this API by design**: authentication is Bearer-token-based (Authorization header), not cookie-based, so Django's CSRF protection concerns (which exist specifically for cookie-authenticated state-changing requests) don't apply here. Confirmed by reading `JWTAuthentication`.
- **P4 — Payment amounts are server-derived, not client-supplied** (`NGN_PRICES[interval]`), closing off the classic price-tampering vulnerability class entirely.
- **P5 — IDOR protection pattern is consistent**: every checked endpoint (`SavedVersesView`, search history, notifications) scopes its MongoEngine queries by `user_id=str(request.user.id)` derived from the authenticated JWT, not from client-supplied identifiers.
- **P6 — Password reset correctly revokes all sessions** on successful reset (`RefreshToken.objects(user_id=...).delete()`), a good security default most apps skip.
- **P7 — Argon2 is used for password hashing**, a strong, modern, memory-hard choice rather than a weaker legacy algorithm.
- **P8 — MongoDB documents are hardened against schema-evolution crashes** (`strict: False` applied project-wide after a real production incident earlier in this project's history), preventing an entire class of `FieldDoesNotExist` 500s as the schema continues to change.
- **P9 — Google sign-in correctly separates account creation from re-authentication** (as of the most recent fix): returning logins no longer silently overwrite a user's in-app profile customizations.

---

# Prioritized Remediation Plan

1. **H1 — Add rate limiting** to `login`, `forgot-password`, `verify-reset-code` at minimum. Highest real-world risk item in the report; no legitimate reason to ship without this.
2. **H3 — Fix the SavedVerse race** (disable button while pending + catch `NotUniqueError` server-side). Small, contained fix, real user-facing bug.
3. **H4 — Add pending-state guard to account deletion.** Small fix, high-consequence action.
4. **H2 — Accessibility pass for icon-only elements.** Larger surface area but mechanically straightforward; consider an `eslint-plugin-jsx-a11y` rule to catch regressions going forward rather than a one-time manual sweep.
5. **M1/M2/M3/M4 — Security hardening batch**: escape email HTML interpolation, switch to `hmac.compare_digest`, enforce (or remove) the avatar content-type allowlist, validate `callback_url`. All independent, all small.
6. **M5 — Scheduler race**: fine to defer if genuinely running single-worker today, but should be fixed before scaling to multiple workers.
7. **L1-L5 / I1-I2** — batch into ordinary backlog; none are urgent.

## Quick wins (low regression risk, fix now)
- M2: swap `==` for `hmac.compare_digest` (one line)
- M3: enforce or delete `ALLOWED_CONTENT_TYPES` (one conditional)
- M4: validate `callback_url` prefix (one conditional)
- L4: CSV formula-injection prefix guard (one helper function)
- H4: add `isDeleting` state + `disabled` prop (contained to one component)
- H3 (partial): add `disabled={toggleSaved.isPending}` immediately; the server-side `NotUniqueError` catch is equally quick

## Requires deeper investigation or architectural change
- H1: rate limiting strategy needs a decision on library (`django-ratelimit` vs DRF throttle classes) and on whether limits are IP-based, account-based, or both.
- H2: full accessibility remediation is a genuine multi-file sweep, best done with a linter enforcing the rule going forward rather than as a one-time patch.
- L1: moving off localStorage to httpOnly cookies is a real architectural change (needs CSRF protection added back for cookie auth, backend cookie-setting logic, SameSite/domain decisions for the cross-subdomain frontend/backend split this app uses).
- M5: the scheduler race is only worth fixing with urgency once multi-worker deployment is actually in play; the atomic-update fix itself is small, but the timing depends on infrastructure plans not visible in the code.
- H4's cascade-race impact: needs a real trace of everything account deletion touches (SavedVerse, SearchHistory, Subscription, PushSubscription, RefreshToken, notifications) to confirm whether concurrent deletes can interleave harmfully — flagged, not fully resolved, in this pass.

---

# Release Recommendation

**Ship with known risks.**

Nothing found rises to a Critical, actively-exploited-in-the-wild-style vulnerability — there's no broken authentication, no cross-user data leakage, no unauthenticated admin access, no client-controlled pricing, and no confirmed XSS vector. The architecture's core security decisions (Bearer-token auth sidestepping CSRF, server-derived payment amounts, consistent per-user query scoping, webhook signature verification) are sound.

That said, **H1 (no rate limiting)** is the one item I'd push hardest against calling this fully "safe to ship" without — an unthrottled login endpoint on a public production app is a well-understood, commonly-exploited gap, and it's a genuinely quick fix relative to its risk reduction. I'd treat H1 as a should-fix-before-wider-launch item even though it doesn't block a limited/soft launch. H3 and H4 are real but narrow bugs, not systemic issues — fine to ship while fixed in a fast follow-up, given their blast radius is a single user's single action, not data exposure or cross-user impact.