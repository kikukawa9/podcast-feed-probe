#!/usr/bin/env python3
"""ledger/events.jsonl の形と「追記専用」を検査する。pre-commit フック（.githooks/pre-commit）から呼ばれる。

    python3 tools/check_ledger.py    # ERROR があれば終了コード 1

既存行を意図して書き換えるときだけ LEDGER_ALLOW_REWRITE=1 を付ける。
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = "ledger/events.jsonl"
SUMMARY_MAX_CHARS = 200  # ledger/README.md §イベントの形
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2})?.*)?$")


def main():
    errors = []
    with open(os.path.join(ROOT, PATH), encoding="utf-8") as f:
        lines = f.read().split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    else:
        errors.append(f"{PATH}: 末尾が改行で終わっていない")

    for i, line in enumerate(lines, 1):
        where = f"{PATH}:{i}"
        try:
            e = json.loads(line)
        except json.JSONDecodeError as ex:
            errors.append(f"{where}: JSON として読めない（{ex.msg}）")
            continue
        if not isinstance(e, dict):
            errors.append(f"{where}: 1行が JSON オブジェクトでない")
            continue
        for k in ("ts", "domain", "summary"):
            if not e.get(k):
                errors.append(f"{where}: 必須の `{k}` が無い")
        if e.get("ts") and not TS_RE.match(str(e["ts"])):
            errors.append(f"{where}: `ts` が YYYY-MM-DD 形式でない（{e['ts']}）")
        s = e.get("summary") or ""
        if len(s) > SUMMARY_MAX_CHARS:
            errors.append(f"{where}: `summary` が {len(s)} 字（上限 {SUMMARY_MAX_CHARS}）。溢れた分は `details.note` へ")
        if "refs" in e and not isinstance(e["refs"], list):
            errors.append(f"{where}: `refs` が配列でない")
        for k in ("facts", "details"):
            if k in e and not isinstance(e[k], dict):
                errors.append(f"{where}: `{k}` がオブジェクトでない")

    # 追記専用：HEAD にある行は1文字も変えない
    r = subprocess.run(["git", "-C", ROOT, "show", f"HEAD:{PATH}"], capture_output=True, text=True)
    if r.returncode == 0 and os.environ.get("LEDGER_ALLOW_REWRITE") != "1":
        old = r.stdout.split("\n")
        if old and old[-1] == "":
            old.pop()
        for i, o in enumerate(old, 1):
            if i > len(lines):
                errors.append(f"{PATH}: 既存の行が削除された（HEAD は {len(old)} 行、今は {len(lines)} 行）")
                break
            if lines[i - 1] != o:
                errors.append(f"{PATH}:{i}: 既存の行が書き換えられた（追記専用。意図した書き換えなら LEDGER_ALLOW_REWRITE=1）")
                break

    for e in errors:
        print("ERROR", e, file=sys.stderr)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
