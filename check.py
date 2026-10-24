import requests, time
msg = "I can't commit to Friday."
t0 = time.time()
r = requests.post('http://127.0.0.1:8000/api/extract', json={"text": msg}, timeout=30)
elapsed = round(time.time() - t0, 2)
print("extract:", elapsed, "s")
d = r.json()
print("atoms:", d.get("atoms"))