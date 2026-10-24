import requests, sys
msg = "I can't commit to Friday."
r = requests.post("http://127.0.0.1:8000/api/extract", json={"text": msg}, timeout=10)
print("status:", r.status_code)
d = r.json()
print("atoms:", d.get("atoms"))
print("raw:", d.get("raw")[:80] if d.get("raw") else None)