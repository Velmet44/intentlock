# IntentLock

> The rewrite bot that isn't allowed to change what you meant.

Paste a hard message, state your intent, get a rewrite that provably keeps every
fact, refusal, and promise — and nothing touches your mailbox without your
explicit approval.

Built for the Hacktoberfest / Hugging Face 2026 challenge, targeting
**Best Use of Auth0 for AI Agents** ($100) and optionally **Best Use of Gemma**.

## Features

- **Meaning preservation** — names, numbers, asks, refusals, promises survive the
  rewrite, provably, with a per-atom ledger.
- **Authorized read access** — Auth0 FGA decides which senders' messages may be
  opened, every time.
- **Scoped, delegated access** — Auth0 Token Vault issues a short-lived,
  narrowly scoped Gmail token at the moment of action; the agent never holds
  mailbox credentials. `gmail.send` is never requested.
- **Human approval** — the save tool is inert until you approve it.

## Modes

- **A — Paste & rewrite** (zero-dep, always works).
- **B — Inbox reply** via Token Vault + FGA (headline).
- **C — Second connector** (Slack, stretch).

## Stack

- Backend: FastAPI (Python), SQLite
- Frontend: plain HTML/JS (no framework)
- Model: local Gemma via Ollama (`gemma3:4b`, fallback `gemma2:2b-it`)
- Auth: Auth0 (Universal Login / PKCE, FGA, Token Vault) via official `auth0-ai` SDK

## Quick start (mock mode, no Auth0 needed)

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# set MOCK_LLM=1 and MOCK_CONNECTORS=1 in .env (default-ish)
python -m uvicorn backend.app.main:app --port 8000
# open http://127.0.0.1:8000
```

## Real mode

1. Install Ollama and `ollama pull gemma3:4b`.
2. Create an Auth0 Free tenant + FGA store + Token Vault Google connection (see
   `docs/auth0-setup.md`).
3. Fill `.env` from `.env.example`, set `MOCK_LLM=0`, `MOCK_CONNECTORS=0`.
4. Run uvicorn.

## Tests

```bash
python -m pytest backend/tests -q
```

## Project layout

```
backend/   FastAPI app, validator, connectors, routes
frontend/  plain HTML/JS UI
tests/     (under backend/tests)
docs/      setup + architecture notes
```

## License

MIT — see [LICENSE](LICENSE).
