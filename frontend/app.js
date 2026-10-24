const state = { atoms: [], original: "", goal: "Firm but not hostile", rewrite: "", draftId: null, token: null };

// Tabs
document.querySelectorAll(".tabs button").forEach(b => {
  b.addEventListener("click", () => {
    document.querySelectorAll(".tabs button").forEach(x => x.classList.remove("active"));
    b.classList.add("active");
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.getElementById("tab-" + b.dataset.tab).classList.add("active");
  });
});

// chips
document.querySelectorAll(".chip").forEach(c => {
  c.addEventListener("click", () => { state.goal = c.dataset.goal; document.getElementById("customGoal").value = ""; });
});
document.getElementById("customGoal").addEventListener("input", e => { if (e.target.value.trim()) state.goal = e.target.value.trim(); });

async function api(path, opts = {}) {
  const headers = { "Content-Type": "application/json" };
  if (state.token) headers["Authorization"] = "Bearer " + state.token;
  const r = await fetch(path, { ...opts, headers: { ...headers, ...(opts.headers || {}) } });
  return r.json();
}

// Auth0 PKCE (minimal)
async function initAuth() {
  const cfg = await api("/api/config");
  if (!cfg.auth0_domain || !cfg.auth0_client_id) return;
  const params = new URLSearchParams(location.search);
  const code = params.get("code");
  if (code) {
    const verifier = sessionStorage.getItem("pkce_verifier");
    if (verifier) {
      try {
        const r = await fetch(`https://${cfg.auth0_domain}/oauth/token`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            grant_type: "authorization_code",
            client_id: cfg.auth0_client_id,
            code,
            code_verifier: verifier,
            redirect_uri: location.origin,
          }),
        });
        const data = await r.json();
        if (data.access_token) {
          state.token = data.access_token;
          document.getElementById("userLabel").textContent = "signed in";
          // clean url
          history.replaceState({}, "", location.pathname);
        }
      } catch (e) { console.error(e); }
    }
  }
}
initAuth();

function b64url(buf) {
  return btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
async function pkceChallenge() {
  const verifier = [...crypto.getRandomValues(new Uint8Array(32))].map(b => "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"[b % 66]).join("");
  const data = new TextEncoder().encode(verifier);
  const digest = await crypto.subtle.digest("SHA-256", data);
  const challenge = b64url(digest);
  sessionStorage.setItem("pkce_verifier", verifier);
  return challenge;
}

document.getElementById("signinBtn").addEventListener("click", async () => {
  const cfg = await api("/api/config");
  if (!cfg.auth0_domain) { alert("Auth0 not configured (dev mode)."); return; }
  const challenge = await pkceChallenge();
  const redirect = encodeURIComponent(location.origin);
  location.href = `https://${cfg.auth0_domain}/authorize?response_type=code&client_id=${cfg.auth0_client_id}&redirect_uri=${redirect}&scope=openid%20profile%20email&audience=${encodeURIComponent(cfg.auth0_audience)}&code_challenge=${challenge}&code_challenge_method=S256`;
});

// Extract
document.getElementById("extractBtn").addEventListener("click", async () => {
  const text = document.getElementById("original").value.trim();
  if (!text) return;
  state.original = text;
  const data = await api("/api/extract", { method: "POST", body: JSON.stringify({ text }) });
  state.atoms = data.atoms || [];
  renderAtoms();
  document.getElementById("contractPanel").classList.remove("hidden");
});

function renderAtoms() {
  const ul = document.getElementById("atomList");
  ul.innerHTML = "";
  state.atoms.forEach(a => {
    const li = document.createElement("li");
    li.textContent = `[${a.type}] ${a.value}  — "${a.evidence}"`;
    ul.appendChild(li);
  });
}

document.getElementById("approveContractBtn").addEventListener("click", async () => {
  // rewrite
  const data = await api("/api/rewrite", { method: "POST", body: JSON.stringify({ original: state.original, goal: state.goal, atoms: state.atoms }) });
  state.rewrite = data.rewrite;
  document.getElementById("origView").textContent = state.original;
  document.getElementById("rewriteView").textContent = state.rewrite;
  // judge
  const j = await api("/api/judge", { method: "POST", body: JSON.stringify({ original: state.original, rewrite: state.rewrite, atoms: state.atoms }) });
  renderLedger(j);
  // save pending draft
  const d = await api("/api/drafts", { method: "POST", body: JSON.stringify({ mode: "A", original: state.original, goal: state.goal, rewrite: state.rewrite, atoms: state.atoms, verdict: j.overall }) });
  state.draftId = d.id;
  document.getElementById("resultPanel").classList.remove("hidden");
});

function renderLedger(j) {
  const ul = document.getElementById("ledger");
  ul.innerHTML = "";
  (j.verdicts || []).forEach(v => {
    const li = document.createElement("li");
    li.textContent = `${v.status}: ${v.atom} ${v.note ? "— " + v.note : ""}`;
    ul.appendChild(li);
  });
  const li = document.createElement("li");
  li.textContent = "Overall: " + j.overall;
  ul.appendChild(li);
}

// Approval save
document.getElementById("approveSaveBtn").addEventListener("click", () => {
  document.getElementById("approvalCard").classList.remove("hidden");
  document.getElementById("approvalInfo").textContent = "Target: your Gmail Drafts. Scope: gmail.compose only. Draft id: " + state.draftId;
});

document.getElementById("approvalApprove").addEventListener("click", async () => {
  const data = await api("/api/save", { method: "POST", body: JSON.stringify({ draft_id: state.draftId, approved: true, recipient: "", subject: "IntentLock draft", user_access_token: state.token, }) });
  alert("Save result: " + JSON.stringify(data));
  document.getElementById("approvalCard").classList.add("hidden");
});

document.getElementById("approvalDecline").addEventListener("click", async () => {
  const reason = document.getElementById("declineReason").value.trim() || "declined";
  const data = await api("/api/save", { method: "POST", body: JSON.stringify({ draft_id: state.draftId, approved: false, decline_reason: reason }) });
  alert("Declined: " + JSON.stringify(data));
  document.getElementById("approvalCard").classList.add("hidden");
});

// Regenerate
document.getElementById("regenBtn").addEventListener("click", () => {
  document.getElementById("regenBox").classList.remove("hidden");
});
document.getElementById("regenConfirm").addEventListener("click", async () => {
  const reason = document.getElementById("regenReason").value.trim();
  // re-run rewrite with reason appended to goal
  const newGoal = state.goal + " (regenerate: " + reason + ")";
  const data = await api("/api/rewrite", { method: "POST", body: JSON.stringify({ original: state.original, goal: newGoal, atoms: state.atoms }) });
  state.rewrite = data.rewrite;
  document.getElementById("rewriteView").textContent = state.rewrite;
  const j = await api("/api/judge", { method: "POST", body: JSON.stringify({ original: state.original, rewrite: state.rewrite, atoms: state.atoms }) });
  renderLedger(j);
  document.getElementById("regenBox").classList.add("hidden");
});

// Copy only
document.getElementById("copyOnlyBtn").addEventListener("click", async () => {
  await navigator.clipboard.writeText(state.rewrite);
  await api("/api/copy_only", { method: "POST", body: JSON.stringify({ draft_id: state.draftId }) });
  alert("Copied. No token used.");
});

// Inbox
document.getElementById("loadInboxBtn").addEventListener("click", async () => {
  const msgs = await api("/api/inbox/messages");
  const ul = document.getElementById("inboxList");
  ul.innerHTML = "";
  msgs.forEach(m => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="${m.allowed ? 'allowed' : 'locked'}">${m.allowed ? '✓' : '🔒'}</span> ${m.from || m.sender_email} — ${m.subject}`;
    li.style.cursor = "pointer";
    li.addEventListener("click", async () => {
      const d = await api("/api/inbox/messages/" + m.id);
      document.getElementById("threadView").classList.remove("hidden");
      document.getElementById("threadSubject").textContent = d.subject || m.subject;
      document.getElementById("threadBody").textContent = d.locked ? d.reason : (d.body || d.snippet || "");
      if (!d.locked) {
        document.getElementById("useThreadBtn").onclick = () => {
          document.getElementById("original").value = d.body || d.snippet || "";
          // switch to compose tab
          document.querySelector('.tabs button[data-tab="compose"]').click();
        };
      }
    });
    ul.appendChild(li);
  });
});

// Activity
document.getElementById("loadActivityBtn").addEventListener("click", async () => {
  const rows = await api("/api/inbox/activity");
  document.getElementById("activityView").textContent = JSON.stringify(rows, null, 2);
});
