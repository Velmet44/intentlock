import requests, time

msgs = [
    "I can't commit to Friday.",
    "Please send the invoice for $1240.",
    "I won't share the file externally.",
]

for msg in msgs:
    t0 = time.time()
    r = requests.post('http://127.0.0.1:8000/api/extract', json={"text": msg}, timeout=30)
    d = r.json()
    atoms = d.get("atoms", [])
    rw = requests.post('http://127.0.0.1:8000/api/rewrite', json={"original": msg, "goal": "Firm but not hostile", "atoms": atoms}, timeout=30)
    rewrite = rw.json().get("rewrite", msg)
    jd = requests.post('http://127.0.0.1:8000/api/judge', json={"original": msg, "rewrite": rewrite, "atoms": atoms}, timeout=30)
    overall = jd.json().get("overall") or "?"
    l1 = jd.json().get("l1", {}).get("passed", False)
    elapsed = round(time.time() - t0, 2)
    ok = "PASS" if (overall != "FAIL" and l1) else "FAIL"
    print(f"{ok}  {msg[:40]:42} atoms={len(atoms):2d} overall={str(overall):4s} l1={l1} {elapsed}s")
    print(f"  rewrite: {rewrite[:80]}")