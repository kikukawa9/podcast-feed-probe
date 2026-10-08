#!/usr/bin/env python3
"""Build ledger.db (SQLite) from events.jsonl.

events.jsonl is the append-only source of truth (committed to git).
ledger.db is a regenerable query artifact (gitignored).

Usage:
    python3 build_db.py [--events events.jsonl] [--db ledger.db]
"""
import argparse
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load_events(path):
    events = []
    with open(path, encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            line = raw.strip()
            if not line:
                continue
            try:
                events.append((lineno, json.loads(line)))
            except json.JSONDecodeError as e:
                sys.exit(f"events.jsonl line {lineno}: invalid JSON: {e}")
    return events


def build(events_path, db_path):
    events = load_events(events_path)
    if os.path.exists(db_path):
        os.remove(db_path)
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.executescript(
        """
        CREATE TABLE events (
            id      INTEGER PRIMARY KEY,
            ts      TEXT NOT NULL,
            domain  TEXT NOT NULL,
            entity  TEXT,
            action  TEXT,
            summary TEXT,
            refs    TEXT,   -- JSON array
            details TEXT    -- JSON object
        );
        CREATE TABLE facts (
            domain     TEXT,
            key        TEXT,
            value      TEXT,
            updated_at TEXT,
            PRIMARY KEY (domain, key)
        );
        """
    )

    # events は「記録した順」を保つため、ファイル順のまま id を振って投入する。
    for i, (lineno, e) in enumerate(events, 1):
        ts, domain = e.get("ts"), e.get("domain")
        if not ts or not domain:
            sys.exit(f"events.jsonl line {lineno}: 'ts' and 'domain' are required")
        cur.execute(
            "INSERT INTO events (id, ts, domain, entity, action, summary, refs, details) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                i, ts, domain, e.get("entity"), e.get("action"), e.get("summary"),
                json.dumps(e.get("refs", []), ensure_ascii=False),
                json.dumps(e.get("details", {}), ensure_ascii=False),
            ),
        )

    # facts は「現在値」なので ts 昇順で畳み込む（ファイル順ではない）。
    # 過去日のイベントを後から追記しても、新しい日付の値が勝つようにするため。
    # sorted は安定ソートなので、同一 ts 内では従来どおりファイル順（＝追記順）で後勝ちになる。
    fact_state = {}  # (domain, key) -> (value, ts)  -- 日付が新しい方が勝つ
    for lineno, e in sorted(events, key=lambda t: t[1]["ts"]):
        ts, domain = e["ts"], e["domain"]
        for k, v in (e.get("facts") or {}).items():
            fact_state[(domain, k)] = (str(v), ts)

    for (domain, k), (v, ts) in fact_state.items():
        if v == "":  # 空値は「解消済み」の意味。現在値から外す
            continue
        cur.execute(
            "INSERT INTO facts (domain, key, value, updated_at) VALUES (?,?,?,?)",
            (domain, k, v, ts),
        )

    cur.executescript(
        """
        CREATE VIEW latest_by_entity AS
        SELECT e.domain, e.entity, e.ts, e.action, e.summary
        FROM events e
        JOIN (
            SELECT domain, entity, MAX(id) AS mid
            FROM events WHERE entity IS NOT NULL
            GROUP BY domain, entity
        ) m ON e.domain = m.domain AND e.entity = m.entity AND e.id = m.mid;
        """
    )
    con.commit()
    n_ev = cur.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    n_fa = cur.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    con.close()
    print(f"Built {db_path}: {n_ev} events, {n_fa} facts")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--events", default=os.path.join(HERE, "events.jsonl"))
    ap.add_argument("--db", default=os.path.join(HERE, "ledger.db"))
    args = ap.parse_args()
    build(args.events, args.db)
