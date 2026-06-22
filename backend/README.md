# VerseID — "Shazam for Bible Verses"

A full-stack Bible verse identification app. Speak or type any fragment of a verse — VerseID finds it from the complete KJV and WEB public-domain texts using a multi-signal fuzzy matching engine.

---

## Architecture

```
verseid-frontend/   TanStack Start (React SSR) + Vite + Tailwind CSS
verseid-backend/    Django 6 + Django REST Framework
                    MongoDB (via MongoEngine — no SQL)
                    Paystack (NGN subscription billing)
                    Web Push (daily verse notifications)
```

---

## Prerequisites

| Tool | Version |
|---|---|
| Python | 3.11 or 3.12 |
| Node.js | 18+ |
| bun | latest (or npm) |
| MongoDB | 7+ (Community Edition) |

---

## 1 — Start MongoDB

```bash
# macOS (Homebrew)
brew services start mongodb-community

# Ubuntu/Debian
sudo systemctl start mongod

# Windows
net start MongoDB
```

Verify: `mongosh --eval "db.runCommand({ ping: 1 })"`

---

## 2 — Backend setup

```bash
cd verseid-backend

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env — fill in at minimum:
#   DJANGO_SECRET_KEY  (any long random string)
#   GOOGLE_CLIENT_ID   (from Google Cloud Console)
#   PAYSTACK_SECRET_KEY / PAYSTACK_PUBLIC_KEY (from Paystack dashboard)
```

### Generate VAPID keys (for Web Push)

```bash
python manage.py generate_vapid_keys
# Copy the output into backend/.env and frontend/.env
```

### Load the Bible corpus into MongoDB

```bash
# Load both KJV and WEB (≈62,000 verses total, takes ~30s)
python manage.py load_bible

# Load only KJV
python manage.py load_bible --version kjv

# Force reload (drops and reloads)
python manage.py load_bible --reset
```

### Run the backend

```bash
python manage.py runserver
# API available at http://localhost:8000/api/v1/
# Health check:  http://localhost:8000/health/
```

---

## 3 — Frontend setup

```bash
cd verseid-frontend

bun install          # or: npm install

cp .env.example .env
# Edit .env:
#   VITE_API_BASE_URL=http://localhost:8000/api/v1
#   VITE_GOOGLE_CLIENT_ID=<same as backend GOOGLE_CLIENT_ID>
#   VITE_VAPID_PUBLIC_KEY=<from generate_vapid_keys output>

bun dev              # or: npm run dev
# App at http://localhost:5173
```

---

## 4 — Google OAuth setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials
2. Create an **OAuth 2.0 Client ID** (Web application)
3. Add **Authorised JavaScript origins**:
   - `http://localhost:5173`
   - `http://localhost:3000`
   - Your production frontend URL
4. Copy the **Client ID** into both `backend/.env` (`GOOGLE_CLIENT_ID`) and `frontend/.env` (`VITE_GOOGLE_CLIENT_ID`)
5. The **Client Secret** goes only in `backend/.env` (`GOOGLE_CLIENT_SECRET`)

---

## 5 — Paystack setup (NGN subscriptions)

1. Sign up at [paystack.com](https://paystack.com)
2. Go to Settings → API Keys & Webhooks
3. Copy **Test Secret Key** (`sk_test_...`) and **Test Public Key** (`pk_test_...`) into `backend/.env`
4. Set your **Webhook URL** to `https://your-backend-domain/api/v1/billing/webhook/`
   - For local testing use [ngrok](https://ngrok.com): `ngrok http 8000`

**Plans configured:**

| Plan | Amount | Billing |
|---|---|---|
| Monthly | ₦2,500 | Per month |
| Annual | ₦20,000 | Per year (saves ₦10,000) |

---

## 6 — Daily verse notifications

The `send_daily_verse` management command delivers the verse-of-the-day notification to every user who has Daily verse enabled. It tries Web Push first (for users with browser permission) and falls back to email.

**Schedule it with cron (Linux/macOS):**

```bash
crontab -e
# Add one of these lines depending on the user's preferred time:
# Morning (8am WAT = 7am UTC):
0 7 * * * /path/to/venv/bin/python /path/to/verseid-backend/manage.py send_daily_verse

# Midday (12pm WAT = 11am UTC):
0 11 * * * /path/to/venv/bin/python /path/to/verseid-backend/manage.py send_daily_verse

# Evening (7pm WAT = 6pm UTC):
0 18 * * * /path/to/venv/bin/python /path/to/verseid-backend/manage.py send_daily_verse
```

**Email backend (for email fallback):**

```dotenv
# backend/.env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password      # Gmail App Password, not your login password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=VerseID <noreply@verseid.app>
```

In development, `EMAIL_BACKEND` defaults to the console backend, which prints emails to the terminal — no SMTP setup needed.

---

## 7 — Rebuild the Bible fixtures (optional)

If you want to regenerate the source fixtures from scratch (e.g. to update to a newer WEB edition):

```bash
# From the project root (not inside verseid-backend/)
pip install lxml

# KJV — already bundled as data/kjv_verses.json (no download needed)
# WEB — re-download and parse from seven1m/open-bibles
curl -o eng-web.usfx.xml https://raw.githubusercontent.com/seven1m/open-bibles/master/eng-web.usfx.xml
python3 build_web_fixture.py          # produces web_verses.json
cp web_verses.json verseid-backend/data/

python manage.py load_bible --reset   # reload both
```

---

## 8 — Matching engine verification

After loading data, verify the matching engine against a set of known verses:

```bash
cd verseid-backend
python scripts/check_matching.py
```

Expected output: 6/6 well-known queries matched correctly, noise queries returning NO MATCH.

---

## Project structure

```
verseid-backend/
├── auth_api/           Google OAuth + email/password auth, JWT, avatar upload
├── bible/              KJV+WEB verse documents, chapter/verse endpoints
├── billing/            Paystack NGN subscription, webhook handler
├── config/             Django settings, root urls, exception handler
├── data/               kjv_verses.json + web_verses.json (source fixtures)
├── notifications/      Notification feed, Web Push delivery, daily command
├── preferences/        Saved verses, collections, user settings
├── scripts/            Matching engine verification script
├── search/             Fuzzy verse matching engine, search history
└── users/              User model (MongoEngine), avatar processing

verseid-frontend/
├── public/sw.js        Service worker (Web Push background handler)
├── src/
│   ├── context/        AuthContext (session, Google OAuth, profile edit)
│   ├── hooks/
│   │   ├── queries/    React Query hooks (bible, search, preferences, billing)
│   │   ├── useGoogleSignIn.ts
│   │   ├── usePushNotifications.ts
│   │   └── useVoiceRecognition.ts   (Web Speech API wrapper)
│   ├── routes/
│   │   ├── index.tsx               Landing page
│   │   ├── auth.tsx                Sign in / Register
│   │   ├── privacy.tsx             Privacy Policy
│   │   ├── terms.tsx               Terms of Service
│   │   ├── help.tsx                Help & FAQ
│   │   └── app/
│   │       ├── home.tsx            Home + daily quota pill
│   │       ├── voice.tsx           Voice search (Web Speech API → backend)
│   │       ├── text.tsx            Text search
│   │       ├── results.tsx         Results + Listen + Read chapter + Save
│   │       ├── discover.tsx        Verse of day + Popular + Theme tiles
│   │       ├── library.tsx         Saved / Collections / History
│   │       ├── notifications.tsx   Notification feed + Mark all read
│   │       ├── profile.tsx         Stats + Menu
│   │       ├── profile.edit.tsx    Edit name + avatar + password
│   │       ├── settings.tsx        All toggles + Push subscribe + Version
│   │       └── subscription.tsx    NGN pricing + Paystack + Cancel
│   └── services/
│       ├── api.ts                  All typed endpoint functions
│       └── client.ts               Axios instance + JWT refresh interceptor
```

---

## API reference (quick)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/auth/google/` | – | Google Sign-In |
| POST | `/api/v1/auth/register/` | – | Email registration |
| POST | `/api/v1/auth/login/` | – | Email login |
| POST | `/api/v1/auth/forgot-password/` | – | Send reset link |
| POST | `/api/v1/auth/reset-password/` | – | Reset with token |
| POST | `/api/v1/auth/change-password/` | ✓ | Authenticated password change |
| PATCH | `/api/v1/auth/me/` | ✓ | Update name |
| POST | `/api/v1/auth/avatar/` | ✓ | Upload profile photo |
| POST | `/api/v1/search/identify/` | ✓ | Identify a verse (quota-enforced) |
| GET | `/api/v1/search/recent/` | ✓ | Last 10 searches |
| GET | `/api/v1/bible/verse-of-day/` | – | Today's featured verse |
| GET | `/api/v1/bible/popular/` | – | Top 5 curated verses |
| GET | `/api/v1/bible/chapter/` | – | Full chapter |
| GET | `/api/v1/preferences/settings/` | ✓ | User settings |
| PATCH | `/api/v1/preferences/settings/` | ✓ | Update any setting |
| GET/POST | `/api/v1/preferences/saved/` | ✓ | Saved verses toggle |
| GET | `/api/v1/notifications/` | ✓ | Notification feed |
| POST | `/api/v1/notifications/mark-all-read/` | ✓ | Mark all read |
| POST | `/api/v1/notifications/push/subscribe/` | ✓ | Register push subscription |
| GET | `/api/v1/billing/pricing/` | – | NGN plan prices |
| POST | `/api/v1/billing/initiate/` | ✓ | Start Paystack checkout |
| POST | `/api/v1/billing/verify/` | ✓ | Verify payment + activate Pro |
| POST | `/api/v1/billing/cancel/` | ✓ | Cancel Pro subscription |
| POST | `/api/v1/billing/webhook/` | – | Paystack webhook (signed) |

---

## Free vs Pro

| Feature | Free | Pro |
|---|---|---|
| Daily verse identifications | 20/day | Unlimited |
| KJV + WEB search | ✓ | ✓ |
| Saved verses | ✓ | ✓ |
| Search history | ✓ | ✓ |
| Collections | ✓ | ✓ |
| Daily notifications | ✓ | ✓ |
| Price | Free | ₦2,500/mo · ₦20,000/yr |
