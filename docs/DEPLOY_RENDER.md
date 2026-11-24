# Free live demo on Render + Neon (for your CV)

A public link to the real app with the ready-made starter data. About 15 minutes, no credit card.

**What you get:** the full website and API with 6,583 companies, 11,000+ jobs and the NL IND sponsor register. Search (keyword), filters, Companies, Market, pipeline and alerts all work. Visitors can register and save jobs.
**What is switched off:** the crawler worker (nothing is refreshed), semantic search, LaTeX export and Gmail connect, so it fits in free tiers. Job descriptions are empty in the starter data. The Crawler page is hidden from visitors.
**The catch:** Render's free service sleeps after ~15 minutes idle, so the first visit takes 30 to 60 seconds. Say so next to the link on your CV.

## 1. Database (Neon, free)
1. Sign up at <https://neon.tech>, create a project (region: Frankfurt or closest to you).
2. Open **Connect**, turn **Connection pooling off**, and copy the connection string (`postgresql://...?sslmode=require`).
3. pgvector is available on Neon: the migrations create the extension themselves.

## 2. Service (Render, free)
1. Push this repo to GitHub (it is already there).
2. At <https://render.com> choose **New → Blueprint**, pick the repo. It reads `render.yaml`.
3. When asked, paste the Neon string into **DATABASE_URL**. Leave the three URL variables empty for now. Apply.
4. The first build takes about 5 minutes. When it is live you get `https://<name>.onrender.com`.

## 3. Final settings
In Render → Environment set these three to your address, then let it redeploy:

| Variable | Value |
|---|---|
| `CAREERS_PUBLIC_URL` | `https://<name>.onrender.com` |
| `CAREERS_API_URL` | `https://<name>.onrender.com` |
| `CAREERS_CORS_ORIGINS` | `https://<name>.onrender.com` |

Open the address, register any account and search. Starter data loads on the first start (only into an empty database).

## Notes
- **Make yourself admin** (to see the Crawler page): set `CAREERS_ADMIN_EMAILS=you@example.com` and register with that address.
- **Sign-in:** without `CAREERS_FIREBASE_API_KEY` the app uses its built-in email and password accounts, so no Google setup is needed. Add the key later for Google sign-in.
- **Free-tier limits:** Neon's free database is about 0.5 GB; the starter data is a few MB. Render free has 512 MB RAM, enough for this setup.
- **Mobile app:** build with `--dart-define=API_URL=https://<name>.onrender.com`.
- **Full version with a live crawler:** see [DEPLOY_ORACLE.md](DEPLOY_ORACLE.md) (needs a VM).
