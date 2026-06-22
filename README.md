# VerseID

> "Shazam for Bible Verses" — speak or type any fragment of a verse and VerseID finds it.

VerseID searches all 62 200 verses of the King James Version (KJV) and World English Bible (WEB) using a four-signal fuzzy matching engine (phrase match · partial match · token-set match · fuzzy-typo match) and returns the best match with a confidence score.

---

## Repository layout

```
verseid/
├── verseid-backend/     Django 6 API server (Python)
│   └── README.md        → Backend setup, MongoDB Atlas, API reference
└── verseid-frontend/    TanStack Start React app (TypeScript)
    └── README.md        → Frontend setup, env vars, project structure
```

**Start here, then follow the README inside each folder.**

---

## Quick start (5 minutes)

### Prerequisites

| Tool | Version |
|---|---|
| Python | 3.11 or 3.12 |
| Node.js | 18+ |
| bun | latest (or npm) |
| MongoDB | Atlas free tier **or** local mongod 7+ |

### Step 1 — MongoDB Atlas

1. Go to [cloud.mongodb.com](https://cloud.mongodb.com) → create a free M0 cluster.
2. Create a database user with read/write access.
3. Allow your IP under **Network Access**.
4. Copy your connection string — it looks like:
   `mongodb+srv://user:pass@cluster.xxxxx.mongodb.net/verseid?retryWrites=true&w=majority`

Full Atlas walkthrough → see `verseid-backend/README.md §1`.

### Step 2 — Backend

```bash
cd verseid-backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in MONGO_URI, DJANGO_SECRET_KEY, GOOGLE_CLIENT_ID, PAYSTACK keys
python manage.py generate_vapid_keys   # copy output into both .env files
python manage.py load_bible            # loads 62 200 KJV + WEB verses into MongoDB (~30s)
python manage.py runserver             # http://localhost:8000
```

### Step 3 — Frontend

```bash
cd verseid-frontend
bun install                   # or: npm install
cp .env.example .env          # fill in VITE_API_BASE_URL, VITE_GOOGLE_CLIENT_ID, VITE_VAPID_PUBLIC_KEY
bun dev                       # or: npm run dev  →  http://localhost:5173
```

---

## Architecture

```
┌─────────────────────────────────────────────┐
│  Browser                                    │
│  TanStack Start · React · Tailwind CSS      │
│  Web Speech API (voice transcript)          │
│  speechSynthesis (Listen button)            │
│  PushManager + service worker (sw.js)       │
└───────────────────┬─────────────────────────┘
                    │ HTTPS · JWT Bearer
                    │ Axios + React Query
┌───────────────────▼─────────────────────────┐
│  Django 6 · Django REST Framework           │
│  ├── auth_api     Google OAuth + JWT        │
│  ├── bible        KJV + WEB verse lookup    │
│  ├── search       Fuzzy matching engine     │
│  ├── billing      Paystack NGN (₦1,000/mo) │
│  ├── notifications Push + email delivery    │
│  └── preferences  Settings, saved, library │
└───────────────────┬─────────────────────────┘
                    │ MongoEngine ODM
┌───────────────────▼─────────────────────────┐
│  MongoDB Atlas                              │
│  ├── users             accounts + stats     │
│  ├── bible_verses      62 200 KJV+WEB rows  │
│  ├── search_history    per-user query log   │
│  ├── saved_verses      library              │
│  ├── notifications     in-app feed          │
│  ├── push_subscriptions Web Push endpoints  │
│  └── subscriptions     Paystack billing     │
└─────────────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────┐
│  External services                          │
│  Google Identity Services  (OAuth sign-in) │
│  Paystack                  (NGN payments)   │
│  Browser Push Service      (FCM / Mozilla) │
│  SMTP                      (email fallback) │
└─────────────────────────────────────────────┘
```

---

## Features

| Feature | Detail |
|---|---|
| Voice search | Web Speech API — transcript stays on-device, only text sent to backend |
| Text search | Type any partial phrase |
| Fuzzy matching | 4 signals · confidence score · searches KJV + WEB simultaneously |
| Listen | Text-to-speech on every result (browser speechSynthesis, free) |
| Read full chapter | Expandable panel on the Results screen |
| Save / Share / Copy | Per-verse actions |
| Daily quota | Free: 20 searches/day · Pro: unlimited |
| Library | Saved verses, 4 themed collections, full search history |
| Notifications | In-app feed + Web Push + email fallback (daily verse, streak milestones) |
| Profile photo | Upload from gallery or take a photo; EXIF-corrected, centre-cropped to 512 × 512 |
| Auth | Google OAuth or email/password; both on the same account |
| Pro plan | ₦1,000/month · ₦9,000/year via Paystack (NGN) |
| Privacy / Terms / Help | Dedicated routes with honest, accurate content |

---

## Files edited / created

### Backend — `verseid-backend/`

| File | What changed |
|---|---|
| `config/settings.py` | MongoDB, JWT, VAPID, email, Paystack, CORS, MEDIA settings |
| `config/urls.py` | Root URL conf — all six app URL includes + media serving |
| `config/exceptions.py` | **New** — custom DRF exception handler (uniform error shape) |
| `users/models.py` | **New** — User + RefreshToken + PasswordResetToken (MongoEngine) |
| `users/avatars.py` | **New** — image upload: validate · EXIF-correct · crop · resize · HEIC support |
| `auth_api/authentication.py` | **New** — DRF JWT auth class (reads MongoEngine User, not Django ORM) |
| `auth_api/tokens.py` | **New** — issue / verify / rotate / revoke JWT access + refresh tokens |
| `auth_api/passwords.py` | **New** — Argon2 password hashing helpers |
| `auth_api/google_oauth.py` | **New** — Google ID token verification |
| `auth_api/serializers.py` | **New** — request serializers for all auth endpoints |
| `auth_api/views.py` | **New** — Google login, email register/login, forgot/reset/change password, avatar upload, me PATCH/DELETE |
| `auth_api/urls.py` | **New** — auth URL routes |
| `bible/models.py` | **New** — Verse document (KJV + WEB, `resolve_verse` helper) |
| `bible/views.py` | **New** — verse of day, popular, single verse, chapter, books list |
| `bible/urls.py` | **New** — bible URL routes |
| `bible/management/commands/load_bible.py` | **New** — loads KJV + WEB fixtures into MongoDB |
| `search/models.py` | **New** — SearchHistory document |
| `search/matching.py` | **New** — 4-signal fuzzy matching engine (phraseMatch, partialMatch, tokenSetMatch, fuzzyTypoMatch) |
| `search/serializers.py` | **New** — IdentifySerializer (query + optional version) |
| `search/views.py` | **New** — IdentifyView (quota-enforced) + RecentSearchesView |
| `search/urls.py` | **New** — search URL routes |
| `preferences/models.py` | **New** — SavedVerse, UserSettings, Collection constants |
| `preferences/serializers.py` | **New** — SaveVerse, SettingsUpdate serializers |
| `preferences/views.py` | **New** — saved verse toggle, collections, settings GET/PATCH |
| `preferences/urls.py` | **New** — preferences URL routes |
| `notifications/models.py` | **New** — Notification, PushSubscription documents |
| `notifications/push.py` | **New** — Web Push delivery (py_vapid + requests, no aiohttp) |
| `notifications/email.py` | **New** — daily verse email fallback |
| `notifications/serializers.py` | **New** — PushSubscription serializer |
| `notifications/views.py` | **New** — feed list, mark-all-read, push subscribe/unsubscribe, VAPID key |
| `notifications/urls.py` | **New** — notifications URL routes |
| `notifications/management/commands/generate_vapid_keys.py` | **New** — generates VAPID keypair |
| `notifications/management/commands/send_daily_verse.py` | **New** — daily push + email delivery job |
| `billing/models.py` | **New** — Subscription, PaystackEvent documents |
| `billing/paystack.py` | **New** — Paystack API helpers (initialize, verify, webhook sig) |
| `billing/serializers.py` | **New** — InitiatePayment, VerifyPayment serializers |
| `billing/views.py` | **New** — pricing, initiate, verify, cancel, webhook handler |
| `billing/urls.py` | **New** — billing URL routes |
| `data/kjv_verses.json` | **New** — 31 102 KJV verses (public domain, generated from raw per-book JSON) |
| `data/web_verses.json` | **New** — 31 098 WEB verses (public domain, parsed from USFX XML) |
| `scripts/check_matching.py` | **New** — smoke-test the matching engine against live MongoDB |
| `requirements.txt` | **New** — pinned dependencies (replaces default empty file) |
| `.env.example` | **New** — all environment variable slots with comments |
| `.gitignore` | **New** — excludes venv, .env, media, pycache |
| `README.md` | **New** — full backend setup guide (this file replaces the old combined README) |

### Frontend — `verseid-frontend/`

| File | What changed |
|---|---|
| `vite.config.ts` | Replaced `@lovable.dev/vite-tanstack-config` with direct plugin imports (tanstackStart, tailwindcss, viteReact, nitro, tsConfigPaths); removed componentTagger; switched Nitro target to `node-server` |
| `package.json` | Removed `@lovable.dev/vite-tanstack-config`; added `axios` |
| `bunfig.toml` | Removed Lovable-specific `minimumReleaseAgeExcludes` entries |
| `.gitignore` | Added `.lovable/`, `.env`, `tsconfig.tsbuildinfo` |
| `.env.example` | **New** — VITE_API_BASE_URL, VITE_GOOGLE_CLIENT_ID, VITE_VAPID_PUBLIC_KEY |
| `public/sw.js` | **New** — service worker: handles push events, notification click → app navigation |
| `src/vite-env.d.ts` | **New** — TypeScript declarations for `import.meta.env` |
| `src/routes/__root.tsx` | Removed `reportLovableError`; added `AuthProvider` wrapper; added service worker registration; improved 404 and error components |
| `src/routes/app.tsx` | **Changed** — added auth guard (redirects to `/auth` when no session); shows spinner only while validating a stored token |
| `src/routes/index.tsx` | Footer: added Privacy/Terms/Help links; FAQ: corrected KJV/WEB-only copy, removed offline/NIV/ESV/semantic claims |
| `src/routes/auth.tsx` | **Rewired** — real Google OAuth (GIS hidden-button), real email/password auth, real forgot-password with inline feedback, Terms/Privacy links |
| `src/routes/app.home.tsx` | **Rewired** — real recent searches from API, daily quota pill, loading skeletons, empty state |
| `src/routes/app.voice.tsx` | **Rewired** — Web Speech API live transcript via `useVoiceRecognition`, real identify call, fallback to /text if unsupported |
| `src/routes/app.text.tsx` | No changes needed (already just navigates with query string) |
| `src/routes/app.results.tsx` | **Rewired** — real identify mutation, loading skeleton, quota-exceeded screen, Listen (speechSynthesis on/off), Read full chapter (expandable `ChapterPanel`), Save wired to toggle mutation |
| `src/routes/app.discover.tsx` | **Rewired** — real verse of day + popular verses; theme tiles navigate to `/app/results?q=...` |
| `src/routes/app.library.tsx` | **Rewired** — real saved verses, real collections, real history from API |
| `src/routes/app.notifications.tsx` | **Rewired** — real notification feed, per-kind icon/tint map, working Mark all read (optimistic update) |
| `src/routes/app.profile.tsx` | **Rewired** — real user stats; Pro badge only when isPro; Edit Profile + Privacy + Help links corrected; sign-out calls real `signOut()` |
| `src/routes/app.profile.edit.tsx` | **New** — change name, upload avatar (gallery or camera, with picker sheet), change/set password |
| `src/routes/app.settings.tsx` | **Rewired** — all 9 toggles + Bible version + daily time picker call real `updateSettings`; push subscribe/unsubscribe row; loading skeleton; delete/logout wired |
| `src/routes/app.subscription.tsx` | **Rewired** — NGN pricing from backend (₦1,000/mo · ₦9,000/yr), real Paystack checkout redirect, Pro status display, cancel with confirmation modal |
| `src/routes/privacy.tsx` | **New** — Privacy Policy (accurate to actual data handling) |
| `src/routes/terms.tsx` | **New** — Terms of Service (NGN pricing, Nigerian governing law) |
| `src/routes/help.tsx` | **New** — Help & Support with FAQ accordion, how-it-works steps, quick-link tiles |
| `src/context/AuthContext.tsx` | **New** — session management, all auth operations, uploadAvatar, updateProfile, changePassword |
| `src/services/api.ts` | **New** — all typed API service functions (auth, bible, search, billing, preferences, notifications) |
| `src/services/client.ts` | **New** — Axios instance with JWT Bearer header + single-flight 401 refresh interceptor |
| `src/hooks/queries/keys.ts` | **New** — centralised React Query cache keys |
| `src/hooks/queries/useBible.ts` | **New** — useVerseOfDay, usePopularVerses |
| `src/hooks/queries/useSearch.ts` | **New** — useIdentifyVerse, useRecentSearches |
| `src/hooks/queries/usePreferences.ts` | **New** — useSavedVerses, useToggleSaved, useCollections, useSettings, useUpdateSettings |
| `src/hooks/queries/useNotificationsBilling.ts` | **New** — useNotifications, useMarkAllRead, usePricing, useInitiatePayment, useVerifyPayment, useCancelSubscription |
| `src/hooks/useGoogleSignIn.ts` | **New** — loads GIS, renders hidden real Google button, forwards clicks from custom UI |
| `src/hooks/useVoiceRecognition.ts` | **New** — Web Speech API wrapper with interim transcripts and end-of-speech fallback |
| `src/hooks/usePushNotifications.ts` | **New** — VAPID subscribe/unsubscribe via PushManager + backend registration |
| `README.md` | **New** — this file |

---

## Pricing

| Plan | Monthly | Annual |
|---|---|---|
| Free | ₦0 | ₦0 |
| Pro | ₦1,000 / month | ₦9,000 / year |

Pro gives unlimited verse identifications per day. Free is capped at 20/day (resets midnight UTC).
