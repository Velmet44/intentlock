# Architecture

See `intentlock-build-spec.md` for the full spec. Summary:

```
Browser (plain HTML/JS)
   |  PKCE sign-in
   v
Auth0 Universal Login -- access token (RS256) --> IntentLock API (FastAPI, local)
                                                      |
        +---------------------------------------------+
        v                                             v
  Ollama (gemma3:4b, localhost)              SQLite (drafts, atoms, audit events)
        |  1) ATOM_EXTRACT (JSON)                     |
        |  2) REWRITE (style-only)                    v
        |  3) JUDGE (atom compare)          Approval gate UI (approve / decline+reason)
        v                                            | approved only
  Validator L1 (deterministic) + L2 (model judge)    v
                                           Token Vault exchange -> short-lived Gmail token
                                                      v
                                      Gmail API drafts.create (compose scope ONLY)
                                                      v
                                      Draft sits in Drafts. Never sent.
```

Mailbox access: every mailbox read or write passes through Auth0 first — FGA
decides what may be read, Token Vault issues the credential used to read/write,
and the approval gate decides what may be saved. `gmail.send` is never requested.
