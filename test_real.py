import asyncio, httpx, json, time

BASE = 'http://127.0.0.1:8000'

async def test_one(msg):
    async with httpx.AsyncClient(timeout=30) as c:
        t0 = time.time()
        ex = (await c.post(f'{BASE}/api/extract', json={'text': msg})).json()
        atoms = ex.get('atoms', [])
        rw = (await c.post(f'{BASE}/api/rewrite', json={'original': msg, 'goal': 'Firm but not hostile', 'atoms': atoms})).json()
        rewrite = rw.get('rewrite', msg)
        jd = (await c.post(f'{BASE}/api/judge', json={'original': msg, 'rewrite': rewrite, 'atoms': atoms})).json()
        elapsed = round(time.time() - t0, 2)
        overall = jd.get('overall') or '?'
        l1 = jd.get('l1', {}).get('passed', False)
        passed = overall != 'FAIL' and l1
        return {"msg": msg, "atoms": len(atoms), "overall": str(overall).ljust(4), "l1_pass": l1, "elapsed": elapsed, "passed": passed}

msgs = [
    "I can't commit to Friday.",
    "Please send the invoice for $1,240.",
    "I won't share the file externally.",
    "Thanks — no apology needed.",
    "If the price drops below €400, I'll buy two.",
    "I'm unhappy with the delay.",
    "Could you loop in Priya?",
    "Version 2.1 fixed it, mostly.",
    "I decline the speaking invitation, but thank you warmly.",
    "We can't host this quarter.",
    "Please don't contact me on weekends.",
    "My budget is $80/month, hard cap.",
]

async def main():
    results = []
    for i, msg in enumerate(msgs, 1):
        r = await test_one(msg)
        results.append(r)
        ok = 'PASS' if r['passed'] else 'FAIL'
        print(f"{i:2d}. {ok} atoms={r['atoms']:2d} overall={r['overall']}l1={r['l1_pass']} {r['elapsed']}s")
    passed = sum(1 for r in results if r['passed'])
    print(f"\nTrap pass rate: {passed}/{len(results)} (target 12/12)")
    for r in results:
        if not r['passed']:
            print(f"   FAIL: {r['msg']}")

asyncio.run(main())