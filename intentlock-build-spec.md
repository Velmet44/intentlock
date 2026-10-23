# IntentLock — Full Build Spec (Week 3: Slow and Steady)

**Category target:** Best Use of Auth0 for AI Agents ($100, new). Optional secondary listing: Best Use of Gemma (it genuinely runs local Gemma — but only one win applies).
**Budget:** $0 — Auth0 Free plan (25k MAU, Token Vault standard flows on Free), local Gemma via Ollama, Gmail connector in "Testing" mode with yourself as the only test user.
**Inputs:** pasted text, plus messages from a mailbox the user has explicitly connected and authorized (digital only). **Modes:** A — paste & rewrite (zero-dep, always works) · B — inbox reply via Token Vault + FGA (headline) · C — second connector (Slack, stretch). **Hard non-goals:** never sends messages, no calendar/scheduling, no receipts, no career screening, no hardware.

---

## 1. Product definition

**One-liner:** Paste a hard message, state your intent, get a rewrite that provably keeps every fact, refusal, and promise — and nothing touches your mailbox without your explicit approval.

**Who it's for:** anyone writing a difficult message — declining an invitation, pushing back on scope, rejecting a vendor, setting a boundary, saying no to a colleague. Also non-native English speakers who want to be firm without sounding rude.

**The four guarantees (the product's spine):**

1. **Meaning preservation** — names, numbers, asks, refusals, and promises survive the rewrite, provably, with a per-atom ledger.
2. **Authorized read access** — the agent may only open messages from senders you have authorized; Auth0 FGA decides, every time.
3. **Scoped, delegated access** — the agent never holds your mailbox credentials; it asks Auth0's Token Vault for a short-lived, narrowly scoped token at the moment of action.
4. **Human approval** — the save tool is inert until you approve it. The agent can draft; only you can commit.

---

## 2. Core concepts

- **Intent atom** — an atomic, checkable unit of meaning extracted from your message:
  - `entity` — names, orgs, products ("Ada", "the Q3 report")
  - `number` — amounts, quantities, versions ("$1,240", "three files")
  - `ask` — a request directed at the recipient ("please send the invoice")
  - `refusal` — inability/unwillingness ("I can't commit", "I won't share")
  - `promise` — a positive future commitment ("I'll review it Monday")
  - `condition` — contingency ("if the price drops")
- **Intent contract** — the extracted atom list plus your chosen style goal, confirmed by you *before* any rewrite happens. The rewrite is only allowed to change style relative to this contract.
- **Verdicts** — the validator returns `PASS`, `WARN` (shown in the diff, save still allowed), or `FAIL` (save blocked, reason fed back to the model for regeneration).

---

## 3. Architecture

```
Browser (plain HTML/JS)
   │  PKCE sign-in
   ▼
Auth0 Universal Login ── access token (RS256) ──► IntentLock API (FastAPI, local)
                                                     │
        ┌────────────────────────────────────────────┤
        ▼                                            ▼
  Ollama (gemma3:4b, localhost)              SQLite (drafts, atoms, audit events)
        │  1) ATOM_EXTRACT (JSON)                     │
        │  2) REWRITE (style-only)                    ▼
        │  3) JUDGE (atom compare)          Approval gate UI (approve / decline+reason)
        ▼                                            │ approved only
  Validator L1 (deterministic)  +  L2 (model judge) ▼
                                          Token Vault exchange → short-lived Gmail token
                                                     ▼
                                     Gmail API drafts.create (compose scope ONLY)
                                                     ▼
                                     Draft sits in Drafts. Never sent.
```

**Mailbox access:** every mailbox read or write passes through Auth0 first — **FGA** decides *what may be read* (sender gate), **Token Vault** issues *the credential used to read/write* (`gmail.read` / `gmail.compose` only), and the **approval gate** decides *what may be saved*. `gmail.send` is never requested anywhere.

**Model settings:** `gemma3:4b` (fallback `gemma2:2b-it`); temperature 0 for extraction/judging, 0.3 for rewriting; JSON-schema-constrained outputs for extraction and judging.

---

## 4. The three AI steps (prompts)

### Step 1 — ATOM_EXTRACT (temperature 0, JSON out)

```text
Extract the intent atoms of the message below as JSON:
{"atoms":[{"type":"entity|number|ask|refusal|promise|condition","value":str,"evidence":str}]}
Rules: quote evidence verbatim; never infer commitments that are not literally stated;
a refusal includes "can't", "won't", "unable to", "not able to", "have to decline".
Message:
{original}
```

### Step 2 — REWRITE (temperature 0.3)

```text
You are a style editor, not an author.
GOAL: {goal}
CONTRACT: rewrite the message so it matches the goal while keeping every atom
exactly true: same entities, same numbers, same asks, same refusals, same promises.
Do not add promises, apologies-as-commitments, dates, or enthusiasm that is not there.
If a sentence cannot be softened without breaking an atom, keep it.
MESSAGE: {original}
Return: {"rewrite": str, "changes": [str]}
```

### Step 3 — JUDGE (temperature 0, JSON out)

```text
For each contract atom, decide if it is PRESERVED, WEAKENED, STRENGTHENED, or LOST in the rewrite.
{"verdicts":[{"atom":str,"status":"PRESERVED|WEAKENED|STRENGTHENED|LOST","note":str}]}
Any LOST refusal or promise ⇒ overall FAIL. WEAKENED ⇒ WARN.
```

### Deterministic layer L1 (runs regardless of the model)

- **Number normalization:** strip currency symbols/commas/"about"/"roughly"; compare numeric values (`$1,240` ≡ `1240` but ≠ `$124`).
- **Refusal lexicon:** can't / cannot / won't / unable / not able / have to decline / not possible.
- **Promise lexicon:** i will / i'll / i can / i'll get / will send / will deliver / by tomorrow (future-tense commitments).
- **Entity overlap:** proper-noun set before/after (local NER or capitalized-token heuristic as a fallback).
- **Ask detection:** imperative/"could you"/"please" requests must appear in both versions in count.
- L1 failures override any model `PASS` — deterministic beats vibes.

---

## 5. Auth0 integration (the category proof)

| Category requirement | Where IntentLock uses it |
|---|---|
| "Sign users in to an agent" | Universal Login (SPA + PKCE); API validates the RS256 access token via JWKS. The agent only ever runs for an authenticated principal. |
| "Call tools on a user's behalf with Token Vault" | One connected app (Gmail via a custom social connection in your own Google Cloud project, Testing mode, yourself as test user). At save time the API does a Token Vault exchange for a short-lived token scoped to `gmail.compose` only. The agent and the server never store Google credentials. |
| "Ask a person to approve a risky action" | The save-draft tool is gated: it renders an approval card (what will be saved, where, with which scope) and returns `declined(reason)` otherwise. Decline reasons are fed back to the model for regeneration. |
| Fine-grained access (scope) | Only `gmail.compose` (save) and `gmail.read` (Mode B read) are ever requested; `gmail.send` is never in any scope string, and an automated test asserts that. |
| "Limit what a RAG pipeline can retrieve with fine-grained authorization" (4th category bullet) | **Auth0 FGA free trial** (currently not time-limited; 100 MAU / 50k tuples): relations `user can_read_from sender` (read gate) and `user can_draft_to contact` (save gate) — in inbox mode the agent may open a thread only if FGA allows it. See the v2 section. |

> **⚠ CIBA warning (verified against Auth0 docs, Oct 2026):** Auth0's official *asynchronous authorization* (CIBA / Guardian push / email consent) **requires an Enterprise plan or a paid add-on** — it is **not** on the Free plan. Do not build or claim it. IntentLock's approval gate is the **Free-plan equivalent** (in-app, deterministic, layered on the Free token-exchange flow); the post should say so explicitly and name CIBA as the paid upgrade path. Official partner docs: https://auth0.com/ai/docs — official SDKs: `auth0-ai` / `auth0-ai-langchain` (Python), `@auth0/ai` / `@auth0/ai-vercel` / `@auth0/ai-langchain` (JS), which provide Token Vault tool wrappers, FGA tool authorizers and a RAG retriever. **Use the official SDK rather than hand-rolled exchange calls** — the code should visibly be Auth0's.

**Setup checklist (~60–105 min, the only human-setup step):** create Public Cloud tenant (Free) → create App (SPA + API) → enable PKCE → enable Gmail API in your Google Cloud project (OAuth consent screen in *Testing* mode, yourself as test user) → configure Token Vault + one custom social connection → add `gmail.compose` + `gmail.read` scopes → create an **Auth0 FGA store** and write the `can_read_from` / `can_draft_to` model (~15 min) → copy domain/client IDs and FGA store ID into `.env`.

**Do not claim CIBA/asynchronous authorization** (enterprise-flavored); mention it in the post only as the upgrade path.

---

## 6. UX flow

1. **Compose** — paste box, intent chips (*Clear & kind · Firm but not hostile · Warm decline · Short & neutral*), optional custom goal.
2. **Contract** — the atom list ("here's what you said; confirm this is what you mean"), one Approve button.
3. **Result** — three panels: original / rewrite / **atom ledger** (kept / changed / added / removed) + word-level diff. Actions: **Approve & save draft** · **Regenerate with reason** · **Copy only** (no save, no token).
4. **Approval card** — shows target mailbox + scope before the Token Vault exchange; Approve / Decline (+reason).
5. **Activity log** — timestamped audit: what was saved, which token scope, `fga_check` results, verdict history. Screenshot bait for the post.

**Mode B (inbox) additions:** a pick-one-message list where unauthorized senders appear **locked** (the FGA refusal is a feature on screen, not an error); the contract then contains **their ask + your constraints**; the approval card shows thread subject, recipient, and token scope before the exchange.

---

## 7. Data model (SQLite)

```sql
drafts(id, auth0_sub, mode, original, goal, rewrite, atoms_json, verdict, status, gmail_draft_id, created_at)
threads(id, auth0_sub, contact_id, sender_email, subject, snippet, fetched_at)  -- Mode B metadata only
contacts(id, auth0_sub, name, email)   -- UI listing only; the Auth0 FGA store is the source of truth
events(id, draft_id, kind, payload_json, created_at)   -- fga_check | extract | rewrite | judge | exchange | approve | decline
```

`status ∈ {pending, approved, declined, copied_only}` — `copied_only` proves the no-token path exists.

---

## 8. Test plan (all free, mostly offline)

- **Unit:** number normalizer, lexicons, diff rendering, JWT validation against a mock JWKS.
- **Contract fixtures (12):** every one has expected atoms and an expected verdict.
  1. "I can't commit to Friday." → must never become a commitment.
  2. "Please send the invoice for $1,240." → number exact.
  3. "I won't share the file externally." → refusal survives, not weakened to "maybe".
  4. "Thanks — no apology needed." → no apology injected.
  5. "If the price drops below €400, I'll buy two." → condition + promise both survive.
  6. "I'm unhappy with the delay." → stance survives (not laundered into "I'd love an update").
  7. "Could you loop in Priya?" → ask survives; entity survives.
  8. "Version 2.1 fixed it, mostly." → hedge survives.
  9. "I decline the speaking invitation, but thank you warmly." → refusal + warmth both.
  10. "We can't host this quarter." → refusal with time reference (not a tracker, just preserved text).
  11. "Please don't contact me on weekends." → boundary refusal.
  12. "My budget is $80/month, hard cap." → number + condition.
- **Property test:** random numbers/amounts injected into generated sentences; assert exact survival.
- **Security test:** assert no scope string in the codebase ever contains `gmail.send`; assert provider token is never written to disk or logs.
- **FGA tests:** tuple absent → read blocked with a friendly refusal (mocked FGA client); tuple present → read proceeds; every decision logged as an `fga_check` event.
- **Mode B fixtures (2):** sender's ask extracted correctly; your constraint (e.g. "no weekend commitments") preserved through the reply.
- **E2E (mocked):** approve path, decline path, copied-only path.
- **Metrics to report in the post:** trap pass rate (target 12/12), WARN/FAIL counts, regeneration rate, median latency, cost $0.00.

---

## 9. Demo script (≈4 min video)

1. Title card: **IntentLock — local model + Auth0 Free = $0.00**.
2. Sign in through Auth0.
3. **Double-gate moment (FGA):** inbox list shows an authorized sender; attempt to open a message from an *unauthorized* sender → locked ("not allowed to open that one").
4. Open the authorized thread — or paste fixture #1+#2 in Mode A; pick *Firm but not hostile*; show the contract; approve.
5. Rewrite appears; zoom on the ledger: refusal PRESERVED, number PRESERVED.
6. Approve & save → Token Vault exchange (masked) → Gmail → draft appears in Drafts, unsent.
7. Decline with "too blunt about the delay" → regenerated version, diff.
8. Copy-only path (no token used, activity log proves it).
9. Repo + metrics table + "why open innovation matters" card.

---

## 10. DEV post outline

1. **Hook:** screenshot of the trap — *"I can't commit to Friday" is still "I can't commit to Friday"* after the rewrite.
2. What I built + demo video.
3. How it works (architecture diagram above).
4. The intent-lock validator: the 12-fixture table and results.
5. The Auth0 part: identity, **FGA read-gate**, Token Vault (compose + read scopes, official `auth0-ai` SDK), approval gate; what's free vs paid, citing https://auth0.com/ai/docs.
6. Why open innovation matters: private drafts deserve a local model; the fixtures/eval are open so anyone can verify the guarantee instead of trusting me.
7. Limitations (honest): judge model can miss paraphrased drift; Gmail-only connector; single user; **Auth0's async approval (CIBA) is Enterprise-only — the in-app gate is the free-plan equivalent**.
8. **Prize Categories:** Best Use of Auth0 for AI Agents (+ Best Use of Gemma).

---

## 11. Build order & time (Mode A core ≈ 8–9 h; with Mode B ≈ 9–11 h — the v2 order in §13 supersedes this table)

| Block | Hours | Notes |
|---|---|---|
| Scaffold + Ollama prompts + atom schema | 1.5 | fixtures written first (TDD-ish) |
| Validator L1/L2 + 12 fixtures green | 1.5 | the entry's backbone |
| UI + ledger + diff | 1.0 | plain HTML/JS, no framework |
| **Auth0 tenant + PKCE + token validation** | 1.5 | start this *first* in parallel — it's the only human-signup step |
| Token Vault + Gmail drafts connector + approval gate | 1.5 | keep mock connector in code for CI |
| Tests + metrics collection | 0.5 | |
| Video + post draft | 1.0 | |

**Cut list if the clock runs out:** activity log → regenerate-with-reason → word-level diff (keep ledger) → Gmail connector (fall back to an in-app "vault-like" sandbox store and downgrade the post's Auth0 claims — only as a last resort, since partner use must remain meaningful).

**Stretch (only after everything green):** second Token Vault connector (Slack draft) to show vault generality; publish the run transcript as a shareable agent-session log (could add Best Use of Entire to the post's category list).

---

## 12. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Token Vault misconfiguration eats the schedule | Tenant setup starts first; mock connector keeps CI green; category demo needs exactly one real exchange |
| Google verification friction | Personal Google Cloud project in Testing mode (Gmail API enabled), yourself as the test user — no verification needed |
| FGA trial signup is a new unknown | Store + model ≈ 15 min in the first parallel block; if it stalls, Mode A + Token Vault still honestly covers 3 category bullets (cut order in §13) |
| Judges see "another rewrite bot" | Post leads with the trap table + ledger + approval gate, not with rewriting |
| Judge-model misses paraphrase drift | L1 lexicons catch the classics; limitations section names the gap honestly |
| Ollama RAM | `gemma3:4b` ≈ 4–6 GB; document `gemma2:2b-it` fallback |
| Time overrun | Hard cut list above; the app is submittable with mock + one real Auth0 exchange |

**Working title:** *IntentLock: the rewrite bot that isn't allowed to change what you meant*

---

# 13. Research Update v2 (partner deep-dive)

## What the research established

| Question | Finding | Source |
|---|---|---|
| Is the Auth0 field empty in Week 3? | **Scanned 500 #hf26challenge posts (pages 1–5): zero Auth0 mentions in titles/descriptions.** Category entries usually signal the sponsor somewhere, so the field is thin to empty. (Body-only mentions can't be fully ruled out.) | DevRelay `get_articles` scan, Oct 23 |
| Free plan coverage | Free = $0, 25k MAU; Token Vault standard retrieval + custom OAuth connections on Free (Auth0 staff, Oct 14, 2026); **CIBA = Enterprise/paid add-on — excluded** | auth0.com/pricing, community.auth0.com, Auth0 docs |
| Official SDKs | `auth0-ai`, `auth0-ai-langchain` (Python), `@auth0/ai-vercel` etc. provide `withTokenVault`, FGA tool authorizers, RAG retriever, interrupts | auth0.com/ai/docs |
| FGA free tier | Auth0 FGA **free trial, currently not time-limited**: 100 MAU, 50k tuples, US/EU/AU — far beyond a demo | docs.fga.dev/subscription-plans |
| Partner doc for the challenge | HF26 hub links **https://auth0.com/ai/docs** as the Auth0 partner doc | dev.to/challenges/hf26 |
| Near-neighbours | Generic rewrite/reply tools exist in the feed (e.g. *LazyReply AI*; "Stillroom — review the repetition without losing the message"); none combine meaning-preservation + delegated access + approval | #hf26challenge feed |

## Idea upgrade: three Auth0 layers (now covering the category's bullets)

The category lists four possible uses — IntentLock now touches **four of four**, all on $0:

1. **Identity** — Universal Login; the agent runs only for an authenticated principal.
2. **Permissions (new)** — **Auth0 FGA**: tuples like `user:sathyajith can_draft_to contact:manager`. In **inbox mode**, before the agent may read a received thread, an `FGAAuthorizer`-style check runs; unauthorized senders produce a friendly "I'm not allowed to open that one" (fed back to the model, not an exception).
3. **Delegated credentials** — **Token Vault** via the official `auth0-ai` SDK: short-lived `gmail.compose`-scoped token at save time; agent never sees credentials; `gmail.send` asserted absent.
4. **Human approval** — in-app approval card (the Free-plan stand-in for paid CIBA — stated honestly in the post).

## New product mode (the stronger real-life story)

- **Mode A — Paste & rewrite:** as specced above (zero-dep fallback, always works).
- **Mode B — Inbox reply (headline for the post):** connect your mailbox once through Token Vault → pick **one** received message → FGA confirms the sender is someone you've authorized → local Gemma extracts the sender's ask + your constraints into an intent contract → rewrite/draft reply → approval → draft saved (never sent).
- **Mode C (stretch only):** second Token Vault connector (Slack) to prove the vault is generic.

The demo moment: *"The agent cannot even open an email from a sender you haven't approved — and it cannot save anything you haven't approved."* Two gates on one screen, both Auth0-powered.

## Rubric mapping (what each judging criterion gets)

| Criterion (weight) | Evidence in the entry |
|---|---|
| Writing Quality (heaviest) | Post opens with the trap-table screenshot; honest limitations section (incl. the CIBA/paid-boundary note) |
| Relevance to Theme | Sloth payoff: hard messages take 20 anxious minutes; IntentLock makes it paste→approve; the agent does the careful part |
| Creativity | "Intent contract" + atom ledger + double-gated agent (can't read what you didn't allow, can't save what you didn't approve) |
| Technical Execution | 12-fixture adversarial harness, deterministic L1 overriding the model judge, FGA check demo, cost $0.00 on screen |
| Use of Partner Technology | 4 of 4 category bullets, official `auth0-ai` SDK in the code, Free-plan facts cited in the post |

## Revised build order (v2)

1. **First (parallel):** Auth0 tenant (Free) + App (SPA+PKCE) + API + Token Vault + one Google test connection — *and* create an FGA store + write the `can_draft_to` model (~15 extra minutes).
2. Scaffold + atom schema + 12 fixtures.
3. Validator L1/L2 green.
4. Mode A UI + ledger + approval card.
5. Mode B: Token Vault via `auth0-ai` SDK + FGA check + Gmail drafts connector (mock in CI).
6. Tests, metrics, video, post.

**Cut order if the clock runs out:** Mode C → Mode B's Gmail write (keep FGA read-gate + pasted mode) → activity log polish. The entry remains valid with Mode A + Token Vault save + FGA check, because the three built layers still cover three category bullets honestly.

**Updated ratings (/5):** Odds **5** (no visible Auth0 entries in 500 scanned posts) · Theme **4** · Partner **5** (4/4 bullets) · Diff **5** (no one else has FGA-gated message access) · Risk **3.5** (CIBA trap avoided; FGA trial signup is the new unknown) · Free **4** (all Free-tier/trial, no card) · Agent **3.5** · Story **5** (the double-gate demo) · Time **9–11 h** · Use **4.5**
