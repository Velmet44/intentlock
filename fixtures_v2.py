import requests, time

msgs = [
    "I can't commit to Friday.",
    "Please send the invoice for $1240.",
    "I won't share the file externally.",
    "Thanks -- no apology needed.",
    "If the price drops below 400, I'll buy two.",
    "I'm unhappy with the delay.",
    "Could you loop in Priya?",
    "Version 2.1 fixed it, mostly.",
    "I decline the speaking invitation, but thank you warmly.",
    "We can't host this quarter.",
    "Please don't contact me on weekends.",
    "My budget is $80/month, hard cap.",
]

results = []
for i, msg in enumerate(msgs, 1):
    t0 = time.time()
    try:
        r = requests.post('http://127.0.0.1:8000/api/extract', json={"text": msg}, timeout=45)
        d = r.json()
        atoms = d.get("atoms", [])
        rw = requests.post('http://127.0.0.1:8000/api/rewrite', json={"original": msg, "goal": "Firm but not hostile", "atoms": atoms}, timeout=45)
        rewrite = rw.json().get("rewrite", msg)
        jd = requests.post('http://127.0.0.1:8000/api/judge', json={"original": msg, "rewrite": rewrite, "atoms": atoms}, timeout=45)
        overall = jd.json().get("overall") or "?"
        l1 = jd.json().get("l1", {}).get("passed", False)
        passed = overall != "FAIL" and l1
        elapsed = round(time.time() - t0, 2)
        results.append({"id": i, "msg": msg[:40], "atoms": len(atoms), "overall": overall, "l1_pass": l1, "elapsed": elapsed, "passed": passed})
        ok = "PASS" if passed else "FAIL"
        print(f"{i:2d}. {ok} atoms={len(atoms):2d} overall={str(overall):4s} l1={l1} {elapsed:6}s")
    except Exception as e:
        elapsed = round(time.time() - t0, 2)
        results.append({"id": i, "msg": msg[:40], "error": str(type(e).__name__), "elapsed": elapsed, "passed": False})
        print(f"{i:2d}. ERR {elapsed:6}s {type(e).__name__}")

passed = sum(1 for r in results if r["passed"])
print(f"\nTrap pass rate: {passed}/{len(results)} (target 12/12)")
for r in results:
    if not r["passed"]:
        e = r.get("error", "?")
        print(f"   FAIL id={r['id']}: overall={r.get('overall','?')}, l1={r.get('l1_pass',None)}, err={e}, latency={r.get('elapsed')}s")