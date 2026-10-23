# Auth0 setup for IntentLock

Follow these steps to move from mock mode to real Auth0 integration.

1. Create a Free Public Cloud tenant at auth0.com.
2. Create an Application (Single Page Application) and an API (identifier `https://intentlock-api`).
3. Enable PKCE (default for SPA). Copy domain + client ID into `.env`.
4. Enable Gmail API in your Google Cloud project; configure OAuth consent screen in **Testing** mode with yourself as the test user.
5. Configure Token Vault + one custom social connection (Google) with scopes `gmail.read` and `gmail.compose`. Never request `gmail.send`.
6. Create an Auth0 FGA store and write the model:

```
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

7. Copy FGA store ID, model ID, client ID/secret into `.env`.
8. Set `MOCK_LLM=0`, `MOCK_CONNECTORS=0`.

## CIBA note

Auth0 asynchronous authorization (CIBA / Guardian push) requires an Enterprise plan
or paid add-on and is **not** available on Free. IntentLock's approval gate is the
Free-plan equivalent (in-app, deterministic, layered on the Free token-exchange
flow). The post names CIBA as the paid upgrade path.
