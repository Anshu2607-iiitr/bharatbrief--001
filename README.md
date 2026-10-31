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

## Deploy (all free plans)

Database on **Neon**, backend on **Render**, frontend on **Vercel**, OTP email via **Brevo**.
(Render's free plan blocks SMTP ports, so Gmail SMTP will not work there; Brevo sends over HTTPS.)

1. **Neon** (neon.tech): create a project and copy the connection string (`postgresql://...`).
2. **Brevo** (brevo.com): sign up, go to *Senders, Domains & Dedicated IPs → Senders*, add and verify your Gmail. Then *SMTP & API → API Keys* and create a key.
3. **Render** (render.com): *New → Blueprint*, pick this repo. It reads `render.yaml` and asks for:
   - `DATABASE_URL`: the Neon string
   - `BREVO_API_KEY`, `BREVO_SENDER_EMAIL`
   - `FRONTEND_URL`: leave as `http://localhost:5173` for now, update after step 4
4. **Vercel** (vercel.com): *Add New → Project*, import this repo, set **Root Directory** to `frontend`, and add env var `VITE_API_URL` = your Render URL (e.g. `https://bharatbrief-api.onrender.com`). Deploy.
5. Back in Render, set `FRONTEND_URL` to your Vercel URL (e.g. `https://bharatbrief.vercel.app`) and save. It redeploys.

Note: Render's free service sleeps after 15 minutes without traffic, so the first request after that takes ~1 minute, and news collection only runs while it is awake.
