#!/usr/bin/env python3
"""Print the current state and recent events (read this first when a session starts).

Rebuilds ledger.db from events.jsonl, then shows:
  1. facts in the `wip` domain (work in progress / next steps)
  2. all other current facts
  3. the most recent events

Usage:
    python3 ledger/status.py [-n 15] [--domain ops]
"""
import argparse
import os
import sqlite3
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "ledger.db")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-n", type=int, default=15, help="number of recent events")
    ap.add_argument("--domain", help="limit to one domain")
    args = ap.parse_args()

    subprocess.run([sys.executable, os.path.join(HERE, "build_db.py")], check=True,
                   stdout=subprocess.DEVNULL)
    con = sqlite3.connect(DB)
    where, params = ("WHERE domain = ?", [args.domain]) if args.domain else ("", [])

    print("== 作業中・次にやること（domain=wip）")
    rows = con.execute("SELECT key, value, updated_at FROM facts WHERE domain = 'wip' ORDER BY updated_at, key").fetchall()
    for k, v, ts in rows or [("（なし）", "", "")]:
        print(f"  [{ts}] {k}: {v}" if ts else f"  {k}")

    print("\n== 現在の状態（facts）")
    q = "SELECT domain, key, value, updated_at FROM facts WHERE domain <> 'wip'"
    q += " AND domain = ?" if args.domain else ""
    for d, k, v, ts in con.execute(q + " ORDER BY domain, key", params):
        print(f"  {d}.{k} = {v}  ({ts})")

    print(f"\n== 直近 {args.n} 件のイベント")
    rows = con.execute(
        f"SELECT ts, domain, entity, action, summary FROM events {where} ORDER BY id DESC LIMIT ?",
        params + [args.n],
    ).fetchall()
    for ts, d, ent, act, s in reversed(rows):
        head = "/".join(x for x in (d, ent, act) if x)
        print(f"  {ts} [{head}] {s}")
    con.close()


if __name__ == "__main__":
    main()
