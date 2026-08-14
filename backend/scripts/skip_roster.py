"""RULING O (Howard sealed 2026-08-14 send-18): the full skip roster prints
in EVERY handback — each skip with its ruling text and its AGE IN SENDS. Any
skip older than three sends states what blocks it and who owes the unblock,
so a held ruling can never quietly die in an unread test skip.

Reads a pytest log produced with `-rs` on stdin (or a path arg) and prints
the roster. Age = CURRENT send − the send the skip was filed under (parsed
from the skip's file name, e.g. ...send13.py → 13, else from a '(send-NN)'
tag in the reason). CURRENT send via env HANDBACK_CURRENT_SEND (default 18).
"""
from __future__ import annotations

import os
import re
import sys

CURRENT_SEND = int(os.environ.get("HANDBACK_CURRENT_SEND", "18"))
OVERDUE_AGE = 3

SKIP_RE = re.compile(r"^SKIPPED \[\d+\] (?P<loc>[^:]+):(?P<line>\d+): (?P<reason>.*)$")


def _send_of(loc: str, reason: str):
    m = re.search(r"send[-_]?(\d+)", loc)
    if m:
        return int(m.group(1))
    m = re.search(r"send[-_ ]?(\d+)", reason)
    return int(m.group(1)) if m else None


def _unblock(reason: str) -> str:
    m = re.search(r"WHAT WOULD UNHOLD IT:\s*(.*)$", reason)
    return m.group(1).strip() if m else "(no unblock recorded — Ruling C wants one)"


def build(lines) -> str:
    skips = []
    for ln in lines:
        m = SKIP_RE.match(ln.strip())
        if m:
            skips.append(m.groupdict())
    out = [f"SKIP ROSTER (Ruling O) — {len(skips)} skip(s), current send {CURRENT_SEND}:"]
    if not skips:
        out.append("  (none)")
        return "\n".join(out)
    for s in skips:
        reason = s["reason"].replace("ruling:held: ", "")
        send = _send_of(s["loc"], reason)
        age = "?" if send is None else (CURRENT_SEND - send)
        head = f"  • {s['loc']}:{s['line']}  [age {age} send(s)]"
        overdue = isinstance(age, int) and age > OVERDUE_AGE
        if overdue:
            head += "  ⚠ OVERDUE (>3 sends)"
        out.append(head)
        out.append(f"      ruling: {reason[:400]}")
        if overdue:
            out.append(f"      BLOCKED ON / OWES UNBLOCK: {_unblock(reason)}")
    return "\n".join(out)


if __name__ == "__main__":
    src = open(sys.argv[1]) if len(sys.argv) > 1 else sys.stdin
    print(build(src.readlines()))
