ATOM_EXTRACT = """Extract the intent atoms of the message below as JSON:
{"atoms":[{"type":"entity|number|ask|refusal|promise|condition","value":str,"evidence":str}]}
Rules: quote evidence verbatim; never infer commitments that are not literally stated;
a refusal includes "can't", "won't", "unable to", "not able to", "have to decline".
Message:
{original}
"""

REWRITE = """You are a style editor, not an author.
GOAL: {goal}
CONTRACT: rewrite the message so it matches the goal while keeping every atom
exactly true: same entities, same numbers, same asks, same refusals, same promises.
Do not add promises, apologies-as-commitments, dates, or enthusiasm that is not there.
If a sentence cannot be softened without breaking an atom, keep it.
MESSAGE: {original}
Return: {"rewrite": str, "changes": [str]}
"""

JUDGE = """For each contract atom, decide if it is PRESERVED, WEAKENED, STRENGTHENED, or LOST in the rewrite.
{"verdicts":[{"atom":str,"status":"PRESERVED|WEAKENED|STRENGTHENED|LOST","note":str}]}
Any LOST refusal or promise => overall FAIL. WEAKENED => WARN.
ORIGINAL: {original}
REWRITE: {rewrite}
ATOMS: {atoms}
"""
