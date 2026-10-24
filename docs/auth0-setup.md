# Auth0 Setup for IntentLock

Follow these steps to configure Auth0 for IntentLock. This is the **only human-setup step** (≈60–105 min). Completing it enables the real mode (`MOCK_CONNECTORS=0`).

## 1. Create a Free Auth0 Tenant

1. Go to [auth0.com](https://auth0.com) and click **Get Started**.
2. Sign up with your email — the Free plan includes: 25k MAU, Universal Login, Token Vault (standard retrieval), custom OAuth connections, and FGA free trial.
3. Verify your email and log in to the Auth0 Dashboard.

## 2. Create a SPA + API Application

1. In the Dashboard, click **Applications** → **Create Application**.
2. **Name**: `IntentLock`, **Type**: **Single Page Application**.
3. Click **Create**.
4. In the app dashboard, note the **Domain** (e.g., `your-tenant.us.auth0.com`) and **Client ID**.
5. Under **Settings**, configure:
   - **Allowed Callback URLs**: `http://localhost:8000/callback`
   - **Allowed Logout URLs**: `http://localhost:8000`
   - **Allowed Web Origins**: `http://localhost:8000`
   - **Enable PKCE** (already on by default for SPA).
6. Under **Advanced Settings**, set **Token Endpoint Authentication**: `none` (for PKCE-only flow).
7. Click **Save**.
8. Copy the **Client ID** into `.env` as `AUTH0_CLIENT_ID`.

### 2b. Create the API (for Token Vault validation)

1. In the Dashboard, click **Applications** → **APIs** → **Create API**.
2. **Name**: `IntentLock API`, **Identifier**: `https://intentlock-api`.
3. Click **Create**.
4. Note the **Client Secret** — copy it into `.env` as `AUTH0_CLIENT_SECRET`.
5. Under **Signing algorithms**, ensure `RS256` is enabled.
6. Click **Save**.

## 3. Configure Google Cloud Project for Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com).
2. Create a **New Project** named `IntentLock`.
3. Navigate to **APIs & Services** → **Library**, search for **Gmail API**, and click **Enable**.
4. Navigate to **APIs & Services** → **OAuth consent screen**.
   - Select **External** user type.
   - App name: `IntentLock`, User support email: your email.
   - Add your email as a **Test user** (click "Add another test user").
   - Click **Save**.
5. Navigate to **APIs & Services** → **Credentials** → **Create credentials** → **OAuth client ID**.
   - Application type: **Desktop app**.
   - Name: `IntentLock Desktop`.
   - Click **Create**.
   - Download the **OAuth 2.0 client credentials** — you'll need the `client_id` and `client_secret` later for the custom social connection (Step 5).
6. Enable **Gmail API** in the same project (if not already enabled).

## 4. Configure Auth0 Token Vault + Google Connection

1. In the Auth0 Dashboard, go to **Authentication** → **Token Vault**.
2. Click **Get started** (or **Configure**) if prompted.
3. Under **Connections**, click **Custom Social Connections** → **Build a custom connection**.
4. **Name**: `google-oauth2`.
5. Follow Auth0's guide to configure the Token Vault for Google:
   - The connection name must be `google-oauth2` (as referenced in `.env`).
   - Use the `auth0-ai` SDK `withTokenVault` wrapper on the backend (already included).
   - Scopes: enable `gmail.read` and `gmail.compose` — **never** `gmail.send`.
   - Test mode: use your own Google account as the test user.
6. Save the connection. The `TOKEN_VAULT_CONNECTION` in `.env` should be `google-oauth2`.

## 5. Create Auth0 FGA Store & Authorization Model

Auth0 FGA (Fine-Grained Authorization) provides the read-gate and save-gate.

1. Go to [fga.dev](https://fga.dev) and sign up for the **free trial** (no time limit, 100 MAU, 50k tuples — far beyond a demo).
2. Create a new store, e.g., named `intentlock-fga`.
3. Create an authorization model with the following schema (v1.1):

```yaml
model
  schema 1.1
type user
type sender
  relations
    define can_read_from: [user]
type contact
  relations
    define can_draft_to: [user]
```

4. Under **Data**, add tuples manually for testing (or leave empty for now; the app handles tuple creation at runtime):
   - `user:your-auth0-sub can_read_from sender:manager@example.com`  (authorized sender)
   - `user:your-auth0-sub can_draft_to contact:manager@example.com`  (save gate target)
5. Create **API credentials**:
   - Method: `client_credentials`.
   - Note the **Client ID** and **Client Secret** — copy into `.env` as `FGA_CLIENT_ID` and `FGA_CLIENT_SECRET`.
6. Set the following in `.env`:
   - `FGA_STORE_ID`: your store ID from FGA.
   - `FGA_MODEL_ID`: the model ID from FGA.
   - `FGA_API_URL`: `https://api.us1.fga.dev` (or your region's endpoint).
   - `FGA_API_TOKEN_ISSUER`: `auth.fga.dev`.
   - `FGA_API_AUDIENCE`: `https://api.us1.fga.dev/`.

## 6. Fill .env and Test

Copy `.env.example` to `.env` and fill in all values. Then:

1. Start the server: `python -m uvicorn backend.app.main:app --port 8000`.
2. Open `http://localhost:8000` in your browser.
3. Click **Sign in (Auth0)** — you'll be redirected to Auth0's Universal Login, then back to the app with a session.
4. Try **Compose** → paste a hard message → **Firm but not hostile** → approve.
5. Check that the draft appears in Gmail Drafts (unsent).
6. Try opening an **unauthorized sender's** message in Inbox — it should appear **locked** ("I'm not allowed to open that one").

## 7. CIBA / Paid Upgrade Note

Auth0's asynchronous authorization (CIBA / Guardian push / email consent) requires an **Enterprise plan** or paid add-on. It is **not** available on the Free plan. IntentLock's approval gate is the **Free-plan equivalent** (in-app, deterministic, layered on the Free token-exchange flow). The DEV post explicitly names CIBA as the paid upgrade path: https://auth0.com/ai/docs.

## Quick Checklist (before running)

- [ ] `AUTH0_DOMAIN` set (e.g., `dev-to-hacktober.auth0.com`)
- [ ] `AUTH0_CLIENT_ID` set
- [ ] `AUTH0_CLIENT_SECRET` set
- [ ] `AUTH0_AUDIENCE` = `https://intentlock-api`
- [ ] `TOKEN_VAULT_CONNECTION` = `google-oauth2`
- [ ] `GMAIL_SCOPES` = `gmail.read,gmail.compose`
- [ ] `FGA_STORE_ID` set
- [ ] `FGA_MODEL_ID` set
- [ ] `FGA_CLIENT_ID` set
- [ ] `FGA_CLIENT_SECRET` set
- [ ] `MOCK_LLM=0`, `MOCK_CONNECTORS=0`
- [ ] Ollama running with `gemma3:4b`

## Troubleshooting

- **Token Vault exchange fails**: verify the Token Vault connection name is `google-oauth2` and scopes include `gmail.read,gmail.compose`.
- **FGA check always fails**: ensure the FGA store ID and model ID are correct, and the API credentials have `client_credentials` method.
- **Gmail draft creation fails**: verify the Google Cloud project has Gmail API enabled and your account is in the OAuth consent screen's Test users.
- **Auth0 PKCE sign-in loops**: ensure `Allowed Callback URLs` and `Allowed Web Origins` include `http://localhost:8000`.