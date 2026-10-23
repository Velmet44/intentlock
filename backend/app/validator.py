import re
from typing import List, Dict, Any

REFUSAL_LEX = ["can't", "cannot", "won't", "unable", "not able", "have to decline", "not possible", "decline"]
PROMISE_LEX = ["i will", "i'll", "i can", "will send", "will deliver", "will review", "by tomorrow", "i'll get"]
ASK_MARKERS = ["please", "could you", "can you", "would you", "kindly"]

def _norm_num(tok: str) -> str:
    t = tok.strip().lower()
    for w in ["about", "roughly", "approximately", "~"]:
        t = t.replace(w, "")
    t = t.replace("$", "").replace("€", "").replace("£", "").replace(",", "").replace(" ", "")
    # strip trailing punctuation
    t = t.strip(".")
    return t

def extract_numbers(text: str) -> List[str]:
    # currency/number tokens
    pat = re.compile(r"[€$£]?\s?\d[\d,\.]*")
    toks = pat.findall(text)
    out = []
    for t in toks:
        n = _norm_num(t)
        if n and re.search(r"\d", n):
            out.append(n)
    return out

def _count_markers(text: str, markers: List[str]) -> int:
    low = text.lower()
    c = 0
    for m in markers:
        c += low.count(m)
    return c

def _capitalized_entities(text: str) -> set:
    # heuristic: words starting with capital letter, length>1, not sentence-initial? keep simple set
    toks = re.findall(r"\b[A-Z][a-zA-Z]{1,}\b", text)
    # filter common words
    stop = {"I", "The", "A", "An", "If", "But", "And", "Or", "We", "You", "He", "She", "It", "This", "That", "Thanks", "Thank", "Version"}
    return set(t for t in toks if t not in stop)

def l1_check(original: str, rewrite: str, atoms: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    failures: List[str] = []
    warnings: List[str] = []

    # Numbers: every normalized number in original must appear in rewrite
    orig_nums = extract_numbers(original)
    rew_nums = extract_numbers(rewrite)
    for n in orig_nums:
        if n not in rew_nums:
            failures.append(f"number lost/changed: {n}")

    # Refusal lexicon: count should not decrease
    orig_ref = _count_markers(original, REFUSAL_LEX)
    rew_ref = _count_markers(rewrite, REFUSAL_LEX)
    if orig_ref > 0 and rew_ref < orig_ref:
        failures.append(f"refusal weakened: {orig_ref} -> {rew_ref}")

    # Promise lexicon
    orig_pr = _count_markers(original, PROMISE_LEX)
    rew_pr = _count_markers(rewrite, PROMISE_LEX)
    if orig_pr > 0 and rew_pr < orig_pr:
        failures.append(f"promise weakened: {orig_pr} -> {rew_pr}")

    # Entity overlap
    orig_ent = _capitalized_entities(original)
    rew_ent = _capitalized_entities(rewrite)
    missing_ent = orig_ent - rew_ent
    if missing_ent:
        # entity could be paraphrased; warn not fail? spec: entity overlap check. Make fail for strictness? Use warn to avoid false positives but L1 overrides model PASS on failures only. We'll treat missing entities as warning, not failure, unless all? 
        warnings.append(f"entities possibly missing: {sorted(missing_ent)}")

    # Ask detection: count should not decrease
    orig_ask = _count_markers(original, ASK_MARKERS) + original.count("?")
    rew_ask = _count_markers(rewrite, ASK_MARKERS) + rewrite.count("?")
    if orig_ask > 0 and rew_ask < orig_ask:
        failures.append(f"ask weakened: {orig_ask} -> {rew_ask}")

    passed = (len(failures) == 0)
    return {
        "passed": passed,
        "failures": failures,
        "warnings": warnings,
        "details": {
            "numbers_original": orig_nums,
            "numbers_rewrite": rew_nums,
            "refusal_original": orig_ref,
            "refusal_rewrite": rew_ref,
            "promise_original": orig_pr,
            "promise_rewrite": rew_pr,
            "entities_original": sorted(orig_ent),
            "entities_rewrite": sorted(rew_ent),
            "ask_original": orig_ask,
            "ask_rewrite": rew_ask,
        },
    }
