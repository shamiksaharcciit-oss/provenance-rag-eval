"""v1.11 custom_id grammar — extends v1.8's, and cannot reuse its parser.

`v18.batch.parse_custom_id` hard-asserts `parts[0] == "v18"` and exactly 8 fields, so a v111
id is unparseable by it. `v18/` is read-only, so the parser is defined here instead. The
**acceptor's** constraints are imported by identity, not restated: `CUSTOM_ID_PATTERN` and
`CUSTOM_ID_MAX` come from v1.8, so the API's own rule has one definition in the repository.

    v111-{exp}-{arm}-q{idx}-{variant}-r{rep}      8 -> 6 fields, one new coordinate `exp`
"""
from __future__ import annotations

from v18.batch import CUSTOM_ID_MAX, CUSTOM_ID_PATTERN   # the acceptor's rule, by identity

EXPS = ("ea", "eb", "ec", "ee")
VARIANTS = ("frozen", "v1", "v2", "xdoc", "sdoc", "none")
ARMS = ("f768", "u768", "c768")
INDEX_WIDTH = 3


def custom_id(exp: str, arm: str, idx: int, variant: str = "none", rep: int = 0) -> str:
    assert exp in EXPS, f"unknown exp {exp!r}"
    assert arm in ARMS, f"unknown arm {arm!r}"
    assert variant in VARIANTS, f"unknown variant {variant!r}"
    cid = "-".join(["v111", exp, arm, f"q{idx:0{INDEX_WIDTH}d}", variant, f"r{rep}"])
    assert CUSTOM_ID_PATTERN.match(cid), f"custom_id {cid!r} violates the API pattern"
    assert len(cid) <= CUSTOM_ID_MAX, f"custom_id {cid!r} exceeds {CUSTOM_ID_MAX}"
    return cid


def parse_custom_id(cid: str) -> dict:
    parts = cid.split("-")
    assert len(parts) == 6 and parts[0] == "v111", f"not a v111 custom_id: {cid!r}"
    _, exp, arm, q, variant, r = parts
    return {"exp": exp, "arm": arm, "index": int(q[1:]), "variant": variant, "rep": int(r[1:])}
