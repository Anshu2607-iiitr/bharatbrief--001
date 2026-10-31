# Bharat Brief

Official PIB news, collected automatically and sorted by category, with email + password accounts and email OTP verification on signup.

- **Backend:** FastAPI, SQLAlchemy, PostgreSQL, APScheduler (collects PIB news every 30 minutes)
- **Frontend:** React + Vite
- **Auth:** bcrypt-hashed passwords, JWT tokens (7 days), 6-digit email OTP on signup (10 min expiry, 5 attempts, 60s resend cooldown)

## Run locally

```bash
# backend (from the project root)
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # fill DATABASE_URL and SECRET_KEY
uvicorn backend.app.main:app --reload

# frontend (second terminal)
cd frontend
npm install
npm run dev                 # http://localhost:5173
```

If no email provider is set in `.env`, the signup OTP is printed in the backend terminal.

## Auth API

| Method | Route | Body |
| --- | --- | --- |
| POST | `/auth/register` | `{name, email, password}`: sends the OTP |
| POST | `/auth/verify-otp` | `{email, otp}`: creates the account, returns `{token, user}` |
| POST | `/auth/resend-otp` | `{email}` |
| POST | `/auth/login` | `{email, password}`: returns `{token, user}` |
| GET | `/auth/me` | header `Authorization: Bearer <token>` |

To protect any route: `def route(user = Depends(get_current_user))` (from `backend.app.auth`).

## Deploy on Vercel (free)

Two Vercel projects from this one repo: the **backend** (repo root, FastAPI) and the **frontend** (`frontend/` folder).
Database on **Neon**, OTP email via **Brevo** (Vercel functions should send mail over HTTPS, not SMTP).

1. **Neon** (neon.tech): create a project, copy the connection string (`postgresql://...`).
2. **Brevo** (brevo.com): *Senders* → add and verify your Gmail; *SMTP & API → API Keys* → create a key.
3. **Backend on Vercel**: *Add New → Project*, import this repo, keep Root Directory as `./`, project name e.g. `bharatbrief-api`. Environment variables:
   - `DATABASE_URL`: Neon string
   - `SECRET_KEY`: long random string
   - `CRON_SECRET`: another long random string
   - `BREVO_API_KEY`, `BREVO_SENDER_EMAIL`
   - `FRONTEND_URL`: `http://localhost:5173` for now

   Deploy, then open `https://<backend>.vercel.app/health`: it should say `healthy`.
4. **Frontend on Vercel**: *Add New → Project*, import the same repo again, set **Root Directory** to `frontend`, project name e.g. `bharatbrief`. Env var `VITE_API_URL` = backend URL. Deploy.
5. In the backend project, set `FRONTEND_URL` to the frontend URL, then *Deployments → Redeploy*.
6. **News every 30 minutes**: Vercel's free cron only runs once a day (`vercel.json`), so also create a free job on **cron-job.org**:
   URL `https://<backend>.vercel.app/cron/collect-news`, every 30 minutes, header `Authorization: Bearer <CRON_SECRET>`.
   Run it once by hand to fill the feed right away.
