# ledger — このリポジトリの作業・運用の記録

このリポジトリで起きたこと（調査・障害対応・修正・リリース・問い合わせ対応・判断）を時系列で残し、
**セッションが切れても「今どういう状態で、次に何をするか」を引き継げる**ようにするための台帳。

**append-only のイベントログ（`events.jsonl`）を正本**にし、そこから SQLite（`ledger.db`）を作って検索する。
**台帳はリポジトリごとに分ける。** 別のリポジトリの出来事はそちらの台帳に書く。

## ファイル構成

| ファイル | 役割 | git |
|---|---|---|
| `events.jsonl` | 追記専用イベントログ。**正本**。1行＝1イベント | コミットする |
| `add_event.py` | 1件を安全に追記する（日付付与・JSON 形式） | コミットする |
| `build_db.py` | `events.jsonl` から `ledger.db` を作り直す | コミットする |
| `status.py` | **セッション開始時に読む**。作業中の事項・現在の状態・直近のイベントを表示 | コミットする |
| `ledger.db` | 生成物（SQLite）。いつでも再生成できる | **gitignore** |

形式と「追記専用」は `tools/check_ledger.py` がコミット時に検査する（`.githooks/pre-commit`）。
clone 直後に1回 `git config core.hooksPath .githooks` を実行する。

## イベントの形（events.jsonl の1行）

```json
{"ts":"2026-10-08","domain":"ops","entity":"本番デプロイ","action":"deployed","summary":"…","refs":["pr:#12"],"facts":{"prod_version":"v1.2.3"}}
```

| フィールド | 必須 | 説明 |
|---|---|---|
| `ts` | ✓ | 発生日（`YYYY-MM-DD` か ISO8601 日時） |
| `domain` | ✓ | 分類（下記） |
| `entity` |  | 対象（例: 本番環境, Issue #35, 認証） |
| `action` |  | 動作（found / fixed / deployed / verified / answered / decided / started / blocked など） |
| `summary` | ✓ | 人が読む要約。**1〜2文・200字以内** |
| `refs` |  | 関連の配列（`issue:#35` / `pr:#43` / `commit:<hash>` / `drive:<id>` / `slack:<channel>` / `url:...`） |
| `facts` |  | **現在の状態の更新**。同じ `domain`+`key` は **ts が新しい方が勝つ**（同一 ts 内は追記順）。**空値（`key=`）で解消扱い**になり現在値から消える |
| `details` |  | 補足。`summary` に収まらない経緯・根拠・数字は `details.note` へ（`--note`） |

### domain

| domain | 書くこと |
|---|---|
| `wip` | **作業中・次にやること・判断待ち**。セッション引き継ぎの要。終わったら空値で消す |
| `dev` | 設計・実装・Issue / PR |
| `ops` | 本番運用：デプロイ・障害・復旧・設定変更 |
| `decision` | 合意した方針・判断と、その理由 |
| `data` | データの中身の確認結果（件数・欠け・整合性） |
| `support` | 問い合わせと回答 |

新しい domain は自由に足してよい。

## 使い方

```bash
# セッション開始時：今の状態を読む
python3 ledger/status.py

# 1件追記（今日の日付が自動で入る）
python3 ledger/add_event.py --domain ops --entity 本番環境 --action deployed \
  --summary "v1.2.3 を本番に出した" --ref pr:#12 --fact prod_version=v1.2.3

# 作業中の事項を置く／片づいたら消す
python3 ledger/add_event.py --domain wip --summary "…を確認中" --fact next_step="…"
python3 ledger/add_event.py --domain wip --summary "…が完了" --fact next_step=

# SQL で引く
python3 ledger/build_db.py
sqlite3 ledger/ledger.db "SELECT ts,domain,entity,summary FROM events ORDER BY id;"
sqlite3 ledger/ledger.db "SELECT * FROM facts ORDER BY domain,key;"
```

## いつ書くか

- **何かを確かめた・直した・決めた・答えた**とき（結論が出た時点で1件）
- **作業を中断する前**（`wip` に「どこまでやったか・次に何をするか」を置く）
- 前に記録した内容が**誤りだった**と分かったとき（過去行は直さず、訂正イベントを足す）

## 方針

- **機密情報（トークン・パスワード・APIキー・Webhook URL）は書かない**
- `events.jsonl` は**追記のみ**。訂正は「訂正イベント」を足す
- **確かめた事実と推測を分ける。** 推測は summary に「〜の可能性」と書くか、`details.note` に根拠と一緒に置く
