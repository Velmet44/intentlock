import os, sys, time, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import httpx

BASE = os.getenv("BASE_URL", "http://127.0.0.1:8000")

from backend.tests.fixtures_data import TRAP_FIXTURES

async def main():
    async with httpx.AsyncClient(timeout=120) as c:
        results = []
        for i, msg in enumerate(TRAP_FIXTURES, 1):
            t0 = time.time()
            ex = (await c.post(f"{BASE}/api/extract", json={"text": msg})).json()
            atoms = ex.get("atoms", [])
            rw = (await c.post(f"{BASE}/api/rewrite", json={"original": msg, "goal": "Firm but not hostile", "atoms": atoms})).json()
            rewrite = rw.get("rewrite", msg)
            jd = (await c.post(f"{BASE}/api/judge", json={"original": msg, "rewrite": rewrite, "atoms": atoms})).json()
            overall = jd.get("overall", "?")
            l1 = jd.get("l1", {}).get("passed", False)
            elapsed = round(time.time() - t0, 2)
            trap_pass = (overall != "FAIL") and l1
            results.append({"id": i, "msg": msg, "atoms": len(atoms), "overall": overall, "l1": l1, "trap_pass": trap_pass, "latency_s": elapsed})
            print(f"{i:2d}. {trap_pass and 'PASS' or 'FAIL'}  atoms={len(atoms):2d}  overall={overall:4s}  l1={l1}  {elapsed}s  {msg}")
        passed = sum(1 for r in results if r["trap_pass"])
        print(f"\nTrap pass rate: {passed}/{len(results)}")
        print(f"Median latency: {sorted(r['latency_s'] for r in results)[len(results)//2]}s")
        with open("eval_results.json", "w") as f:
            json.dump(results, f, indent=2)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
