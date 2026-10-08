#!/usr/bin/env python3
"""Append one event to events.jsonl (keeps the log valid and timestamped).

Example:
    python3 add_event.py \
        --domain company_setup --entity 定款 --action created \
        --summary "ExeLikeで定款生成" \
        --ref drive:1Lo1My... --fact teikan_status=作成済

A fact with an empty value (--fact key=) clears it from the current state.
"""
import argparse
import datetime
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--domain", required=True)
    ap.add_argument("--entity")
    ap.add_argument("--action")
    ap.add_argument("--summary", required=True)
    ap.add_argument("--ref", action="append", default=[], dest="refs",
                    help="related link, repeatable (e.g. drive:<id>, gmail:<threadId>)")
    ap.add_argument("--fact", action="append", default=[], dest="facts",
                    help="current-state update key=value, repeatable")
    ap.add_argument("--note", help="long explanation that does not fit in summary (goes to details.note)")
    ap.add_argument("--ts", help="ISO date/datetime; default = today")
    ap.add_argument("--events", default=os.path.join(HERE, "events.jsonl"))
    args = ap.parse_args()

    facts = {}
    for f in args.facts:
        if "=" not in f:
            ap.error(f"--fact must be key=value, got: {f}")
        k, v = f.split("=", 1)
        facts[k] = v

    ev = {"ts": args.ts or datetime.date.today().isoformat(), "domain": args.domain}
    if args.entity:
        ev["entity"] = args.entity
    if args.action:
        ev["action"] = args.action
    ev["summary"] = args.summary
    if args.refs:
        ev["refs"] = args.refs
    if facts:
        ev["facts"] = facts
    if args.note:
        ev["details"] = {"note": args.note}

    line = json.dumps(ev, ensure_ascii=False)
    with open(args.events, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print("appended:", line)


if __name__ == "__main__":
    main()
