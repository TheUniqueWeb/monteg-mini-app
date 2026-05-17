# CybEarn — Complete Integration Guide

## 1. Project Directory Structure

```
cybearn/
├── main.py                          # FastAPI app entry point
├── config.py                        # Centralized configuration
├── requirements.txt
├── .env                             # Environment variables (never commit)
├── alembic.ini                      # DB migration config
│
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── router.py            # Aggregates all routers
│   │       └── endpoints/
│   │           ├── auth.py          # POST /auth/login
│   │           ├── tasks.py         # GET/POST /tasks
│   │           ├── users.py         # GET/PATCH /users/me, referrals, withdrawals
│   │           └── admin.py         # All /admin/* endpoints
│   ├── core/
│   │   └── security.py             # JWT + Telegram HMAC verification
│   ├── db/
│   │   └── session.py              # Async engine, session factory, Base
│   ├── middleware/
│   │   └── admin_guard.py          # Starlette middleware for /admin/* routes
│   ├── models/
│   │   └── models.py               # All SQLAlchemy ORM models
│   ├── schemas/
│   │   └── schemas.py              # All Pydantic v2 request/response schemas
│   └── services/
│       └── telegram_service.py     # Bot API messaging service
│
├── frontend/
│   ├── index.html
│   └── src/
│       └── App.jsx                 # Main React TMA frontend
│
└── scripts/
    └── create_admin.py             # Utility to seed an admin user
```

---

## 2. Environment Variables (.env)

```env
# Bot
BOT_TOKEN=7123456789:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
BOT_USERNAME=cybearn_bot

# Admins (comma-separated Telegram IDs)
ADMIN_IDS=[123456789, 987654321]

# JWT (generate with: python -c "import secrets; print(secrets.token_hex(32))")
JWT_SECRET_KEY=your_256bit_random_secret_here

# Database (PostgreSQL for production)
DATABASE_URL=postgresql+asyncpg://cybearn:password@localhost:5432/cybearn_db

# Montage SDK
MONTAGE_APP_ID=your_montage_app_id
MONTAGE_API_KEY=your_montage_api_key

# App URL (your VPS domain)
BASE_URL=https://yourdomain.com
CORS_ORIGINS=["https://yourdomain.com","https://web.telegram.org"]
```

---

## 3. Running the Backend

```bash
# 1. Create virtual environment
python -m venv venv && source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy and fill environment
cp .env.example .env

# 4. Run (development)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 5. Run (production with Gunicorn)
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

---

## 4. Admin Panel API — Security Architecture

The admin panel uses **two independent security layers**:

### Layer 1: Starlette Middleware (`AdminGuardMiddleware`)
Located in `app/middleware/admin_guard.py`. This runs **before** any route handler is invoked.

```
Request → AdminGuardMiddleware → [validate JWT] → [check ADMIN_IDS] → Route Handler
                                       ↓ (fail)
                                  403 JSON response
```

The middleware:
- Intercepts all requests to `/api/v1/admin/*`
- Decodes and validates the JWT signature
- Verifies `telegram_id` is in the `ADMIN_IDS` allow-list from `config.py`
- Writes audit logs (timestamp, user ID, method, path, response time)
- Returns `403 JSON` immediately on any failure

### Layer 2: FastAPI Dependency (`require_admin`)
Located in `app/core/security.py`. This runs **inside** each endpoint function.

```python
@router.post("/admin/tasks")
async def create_task(
    body: TaskCreate,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(require_admin),   # ← Layer 2 guard
):
    ...
```

**Why both?** Defence-in-depth: if a developer forgets to add `require_admin`, the middleware still blocks the request. If the middleware is bypassed via a misconfiguration, the dependency rejects it.

---

## 5. Montage SDK Integration Guide

Montage is an ad SDK for Telegram Mini Apps that rewards users for watching ads.

### Step 1: Add the Montage Script to `index.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>CybEarn</title>
  <!-- Telegram WebApp SDK (required first) -->
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <!-- Montage SDK -->
  <script src="https://sdk.montageads.io/v2/montage.min.js"></script>
</head>
<body>
  <div id="root"></div>
  <script type="module" src="/src/main.jsx"></script>
</body>
</html>
```

### Step 2: Initialize Montage in Your React App

Create `src/hooks/useMontage.js`:

```javascript
import { useEffect, useRef, useState } from 'react';

/**
 * useMontage — Hook to manage Montage ad SDK lifecycle.
 *
 * @param {string} appId   - Your Montage APP_ID from config
 * @param {string} userId  - The Telegram user ID (for reward tracking)
 */
export function useMontage(appId, userId) {
  const [isReady, setIsReady] = useState(false);
  const [isWatching, setIsWatching] = useState(false);
  const montageRef = useRef(null);

  useEffect(() => {
    if (!window.MontageSDK || !appId || !userId) return;

    // Initialize the Montage SDK
    montageRef.current = new window.MontageSDK({
      appId: appId,
      userId: String(userId),
      environment: import.meta.env.PROD ? 'production' : 'sandbox',
    });

    montageRef.current.on('ready', () => {
      console.log('[Montage] SDK ready');
      setIsReady(true);
    });

    montageRef.current.on('error', (err) => {
      console.error('[Montage] SDK error:', err);
    });

    montageRef.current.init();

    return () => {
      montageRef.current?.destroy();
    };
  }, [appId, userId]);

  /**
   * showAd — Displays a rewarded ad.
   * @param {Function} onRewarded - Called with reward amount when ad completes.
   */
  const showAd = async (onRewarded) => {
    if (!isReady || isWatching) return;

    setIsWatching(true);
    try {
      await montageRef.current.showRewardedAd({
        onStart: () => console.log('[Montage] Ad started'),
        onComplete: async (rewardData) => {
          console.log('[Montage] Ad completed, reward:', rewardData);
          // Verify reward on your backend (IMPORTANT: never trust client-side only)
          await verifyMontageReward(rewardData.token);
          onRewarded?.(rewardData.amount);
        },
        onSkip: () => console.log('[Montage] Ad skipped – no reward'),
      });
    } catch (err) {
      console.error('[Montage] showAd error:', err);
    } finally {
      setIsWatching(false);
    }
  };

  return { isReady, isWatching, showAd };
}

// ── Backend reward verification ──────────────────────────────────────────────
async function verifyMontageReward(token) {
  const jwtToken = localStorage.getItem('cybearn_token');
  const res = await fetch('/api/v1/tasks/montage/verify', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${jwtToken}`,
    },
    body: JSON.stringify({ reward_token: token }),
  });
  if (!res.ok) throw new Error('Reward verification failed');
  return res.json();
}
```

### Step 3: Use the Hook in the Earn Page

```jsx
import { useMontage } from '../hooks/useMontage';
import { MONTAGE_APP_ID } from '../config';

function AdTaskCard({ task, userId, onRewarded }) {
  const { isReady, isWatching, showAd } = useMontage(MONTAGE_APP_ID, userId);

  return (
    <div className="task-card">
      <h3>{task.title}</h3>
      <p>+{task.reward_amount} ⚡</p>
      <button
        onClick={() => showAd(onRewarded)}
        disabled={!isReady || isWatching}
      >
        {isWatching ? '▶ Watching Ad…' : isReady ? '▶ Watch Ad' : 'Loading…'}
      </button>
    </div>
  );
}
```

### Step 4: Backend Verification Endpoint

Add to `app/api/v1/endpoints/tasks.py`:

```python
import httpx
from config import settings

@router.post("/montage/verify", summary="Verify Montage ad reward server-side")
async def verify_montage_reward(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Verify a Montage reward token server-side.
    NEVER credit rewards based on client-side data alone.
    """
    token = body.get("reward_token")
    if not token:
        raise HTTPException(status_code=422, detail="Missing reward_token")

    # Verify with Montage API
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.montageads.io/v2/verify",
            json={"token": token, "app_id": settings.MONTAGE_APP_ID},
            headers={"X-API-Key": settings.MONTAGE_API_KEY},
            timeout=10.0,
        )

    if resp.status_code != 200 or not resp.json().get("valid"):
        raise HTTPException(status_code=400, detail="Invalid or already-used reward token")

    reward_data = resp.json()
    reward_amount = reward_data["amount"] * settings.MONTAGE_REWARD_MULTIPLIER

    # Credit user
    result = await db.execute(select(User).where(User.telegram_id == current_user_id))
    user: User = result.scalar_one()
    user.balance += reward_amount
    user.total_earned += reward_amount

    return {"credited": reward_amount, "new_balance": user.balance}
```

---

## 6. Telegram WebApp Authentication Flow

```
[Telegram Client]                    [CybEarn Backend]
      │                                      │
      │  1. User opens Mini App              │
      │  2. Telegram injects initData        │
      │                                      │
      │  POST /api/v1/auth/login             │
      │  { init_data: "<raw string>" }       │
      │ ──────────────────────────────────►  │
      │                                      │  3. HMAC-SHA256 verify
      │                                      │  4. Upsert user in DB
      │                                      │  5. Apply referral bonus
      │  { access_token, user }              │
      │ ◄──────────────────────────────────  │
      │                                      │
      │  6. Store token in memory            │
      │  7. All subsequent requests use:     │
      │     Authorization: Bearer <token>    │
```

**Frontend login code:**
```javascript
async function loginWithTelegram() {
  const initData = window.Telegram?.WebApp?.initData;
  if (!initData) throw new Error('Not running inside Telegram');

  // Get referral code from start_param
  const startParam = window.Telegram.WebApp.initDataUnsafe?.start_param;

  const res = await fetch(`/api/v1/auth/login?ref=${startParam || ''}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ init_data: initData }),
  });

  const data = await res.json();
  // Store in memory (NOT localStorage for security in TMA context)
  window.__cybearn_token = data.access_token;
  return data.user;
}
```

---

## 7. API Endpoint Reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/login` | None | Authenticate via Telegram initData |
| GET | `/api/v1/tasks` | User | List active tasks |
| POST | `/api/v1/tasks/submit` | User | Submit task with proof |
| GET | `/api/v1/tasks/my` | User | My submission history |
| GET | `/api/v1/users/me` | User | Get profile |
| PATCH | `/api/v1/users/me` | User | Update wallet address |
| GET | `/api/v1/users/me/referrals` | User | Referral stats & link |
| POST | `/api/v1/users/me/withdraw` | User | Request withdrawal |
| GET | `/api/v1/users/leaderboard` | User | Top 50 earners |
| POST | `/api/v1/admin/tasks` | Admin | Create a task |
| DELETE | `/api/v1/admin/tasks/{id}` | Admin | Delete a task |
| PATCH | `/api/v1/admin/tasks/{id}/toggle` | Admin | Toggle task active |
| GET | `/api/v1/admin/submissions` | Admin | List submissions by status |
| POST | `/api/v1/admin/submissions/{id}/review` | Admin | Approve / Reject |
| GET | `/api/v1/admin/withdrawals` | Admin | List withdrawal requests |
| POST | `/api/v1/admin/withdrawals/{id}/review` | Admin | Process withdrawal |
| GET | `/api/v1/admin/users` | Admin | List all users |
| POST | `/api/v1/admin/users/{id}/ban` | Admin | Ban / Unban user |
| POST | `/api/v1/admin/broadcast` | Admin | Send Telegram message |

---

## 8. Deployment (Production)

```nginx
# /etc/nginx/sites-available/cybearn
server {
    listen 443 ssl;
    server_name yourdomain.com;

    # SSL certs (Let's Encrypt recommended)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Frontend (built React app)
    location / {
        root /var/www/cybearn/dist;
        try_files $uri /index.html;
    }

    # Backend API (proxied to Gunicorn)
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # File uploads
    location /uploads/ {
        alias /var/www/cybearn/uploads/;
        expires 30d;
    }
}
```

**Set the WebApp URL in BotFather:**
1. Open @BotFather → `/mybots` → Select your bot
2. `Bot Settings` → `Menu Button` → Set URL to `https://yourdomain.com`
