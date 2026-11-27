# Connect Gmail (Google sign-in)

The Inbox page can read your Gmail **read-only** through Google OAuth: you sign in on Google's own page, and the app stores only a revocable, encrypted refresh token. No password is shared. The scope is `gmail.readonly`; nothing is changed, deleted or marked as read.

> Google limits unverified apps with this scope to **100 test users**, and logins expire after **7 days** (reconnect). That is fine for self-hosting: you create your own Google Cloud client below. Opening it to everyone would need Google's app verification and a yearly security assessment. Only Gmail is supported at the moment.

## Sign in with Google only

1. In [Google Cloud Console](https://console.cloud.google.com) create a project, then **APIs & Services → OAuth consent screen** (External, app name, your e-mail).
2. **Credentials → Create credentials → OAuth client ID → Web application**. Under **Authorized JavaScript origins** add `http://localhost:8787`.
3. Put `CAREERS_GOOGLE_CLIENT_ID=<client id>` in `.env` and restart. **Continue with Google** appears on the sign-in page.

## Connect Gmail: one-time setup (about 10 minutes, free)

1. Open [Google Cloud Console](https://console.cloud.google.com) and choose your project (the Firebase project works).
2. **APIs & Services → Library →** search **Gmail API → Enable**.
3. **APIs & Services → OAuth consent screen** (Google Auth platform): User type **External**, fill the app name and your e-mail, then add yourself under **Test users**. Under **Data access / Scopes** add `https://www.googleapis.com/auth/gmail.readonly`.
4. **Credentials → Create credentials → OAuth client ID → Web application** (or open your existing web client). Under **Authorized redirect URIs** add:
   `http://localhost:8787/api/v1/mail/gmail/callback` (for a deployed site use `https://your-domain/api/v1/mail/gmail/callback`).
5. Copy the **Client ID** and **Client secret** into `.env` in the project folder (never commit it):

```
CAREERS_GOOGLE_CLIENT_ID=<client id>
CAREERS_GOOGLE_CLIENT_SECRET=<client secret>
CAREERS_API_URL=http://localhost:8787
```

6. Restart (`./setup.sh`, or `docker compose up -d` in Docker mode). Then in the app:
   **Inbox → Connect Gmail** → pick your account → on "Google hasn't verified this app" choose **Advanced → continue** → allow read-only access →
   choose the AI model that reads the e-mails → **Sync now** (the worker must be running).

If the client ID is the same one used for "Sign in with Google" on the web, just add the secret and the redirect URI.

## Troubleshooting

| Message | Fix |
|---|---|
| `redirect_uri_mismatch` | The redirect URI in step 4 must match `CAREERS_API_URL` exactly. |
| `access_denied` / "app not verified" | Add your address under Test users; on the warning page choose Advanced → continue. |
| `Gmail API has not been used` | Enable the Gmail API (step 2). |
| Sync fails after a week | Testing mode expires logins after 7 days: click Connect Gmail again. |
| Revoke access | [myaccount.google.com/permissions](https://myaccount.google.com/permissions), or Disconnect in the app. |
