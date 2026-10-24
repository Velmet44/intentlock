import requests, time

msgs = [
    "I can't commit to Friday.",
    'Please send the invoice for $1,240.',
    "I won't share the file externally.",
    'Thanks — no apology needed.',
    'If the price drops below €400, I\'ll buy two.',
    "I'm unhappy with the delay.",
    'Could you loop in Priya?',
    'Version 2.1 fixed it, mostly.',
    'I decline the speaking invitation, but thank you warmly.',
    "We can't host this quarter.",
    "Please don't contact me on weekends.",
    "My budget is $80/month, hard cap.",
]

t0_total = time.time()
for i, msg in enumerate(msgs, 1):
    t0 = time.time()
    try:
        r = requests.post('http://127.0.0.1:8000/api/extract', json={'text': msg}, timeout=15)
        elapsed = round(time.time() - t0, 2)
        d = r.json()
        atoms = d.get('atoms', [])
        print(f"{i:2d}. atoms={len(atoms):2d} {elapsed:5}s  {msg}")
    except Exception as e:
        elapsed = round(time.time() - t0, 2)
        print(f"{i:2d}. TIMEOUT {elapsed:5}s  {type(e).__name__}")

total = round(time.time() - t0_total, 1)
print(f"\nTotal time: {total}s")