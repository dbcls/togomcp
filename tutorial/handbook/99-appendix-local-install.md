# 付録：ローカル導入（経路 C）

開発者向け、および **KEGG ツールを使う場合の唯一の経路**です。

通常の利用には不要です。[経路 A（カスタムコネクタ）](01-setup.md)で十分機能します。以下が必要になるのは：

- KEGG ツールを使いたい（アカデミック機関所属者に限る）
- MIE ファイルを書く・直す
- サーバ自体を開発する
- 組織内に自前でホストする

---

## 前提

- Python >= 3.11
- [uv](https://docs.astral.sh/uv/) パッケージマネージャ

### uv を入れる

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

## 導入

```bash
git clone https://github.com/dbcls/togomcp.git
cd togomcp
uv sync
```

### NCBI API キー（NCBI 系ツールを使う場合は必須）

[NCBI のドキュメント](https://www.ncbi.nlm.nih.gov/datasets/docs/v2/api/api-keys/)からキーを取得して：

```bash
export NCBI_API_KEY="your-key-here"
```

---

## Claude Desktop の設定

設定ファイルの場所：

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `~\AppData\Roaming\Claude\claude_desktop_config.json`

```json
{
    "mcpServers": {
        "togomcp": {
            "command": "/path/to/uv",
            "args": [
                "--directory",
                "/path/to/togomcp",
                "run",
                "togo-mcp-local"
            ],
            "env": {
                "NCBI_API_KEY": "your-key-here"
            }
        }
    }
}
```

> 💡 `uv` の絶対パスは `which uv`（macOS/Linux）または `where uv`（Windows）で調べられます。相対パスや `uv` だけでは動きません。

設定後、**Claude Desktop を完全に終了して再起動**してください。

---

## KEGG（オプトイン・ローカル stdio 限定）

> **KEGG は既定でオフです。必要ありません。TogoMCP は KEGG なしで完全に機能します。**
> この節は、資格があって、かつ使いたい場合にのみ関係します。

`kegg_find` / `kegg_get_entry` / `kegg_conv` / `kegg_link` / `kegg_pathway_graph` / `kegg_pathway_neighborhood` / `kegg_pathway_paths` / `kegg_pathway_cycles` の 8 ツールは、**次の 2 条件が両方成立したときだけ**有効になります。

1. ローカルの stdio エントリポイント `togo-mcp-local` で動かしている
2. `TOGOMCP_ENABLE_KEGG=1` を設定している

### なぜ 2 つの門があるのか — 理由は別々です

**(1) 通信経路の制限は構造的なもので、設定では変えられません。**

[KEGG API](https://www.kegg.jp/kegg/rest/) は「アカデミック機関に所属するアカデミックユーザーの学術利用のため」に提供されており、KEGG を用いた**サービスの提供**には別途 academic service-provider license が必要です（[KEGG の利用条件](https://www.kegg.jp/kegg/legal.html)）。

公開サーバは呼び出し元の所属を検証できません。したがって togomcp.rdfportal.org を含む**あらゆる HTTP 配備は `rest.kegg.jp` に到達しません**。**環境変数では変えられません** ── `TOGOMCP_ENABLE_KEGG` は HTTP 経路に対して何の効果もありません。

**(2) オプトインが存在するのは、資格の主張があなたのものだから。**

stdio では**あなた自身が**呼び出し元です。しかし、あなたの所属機関のアクセス権があなたを含むかどうかは、あなたにしか分かりません。

既定で KEGG を有効にすると、**あなたに権利がないかもしれない API 呼び出しを、最も抵抗の少ない経路に置くこと**になります。AI アシスタントは、見えている道具は使います。アカデミック用途でない利用者にとって、変数を設定しないことが正しい構成であり、他には何の影響もありません。

### 有効にする

```json
"env": {
    "NCBI_API_KEY": "your-key-here",
    "TOGOMCP_ENABLE_KEGG": "1"
}
```

### 制約

- 呼び出しは **毎秒 3 リクエスト**に制限されます（プロセス全体で強制。403/429 のリトライは行いません）
- **KEGG は RDF Portal の一部ではありません。** SPARQL エンドポイントを持たないので、`run_sparql` で `database="kegg"` は無効です
- RDF データベースと繋ぐには、`kegg_conv` で KEGG の識別子を UniProt / NCBI Gene / NCBI Protein / ChEBI / PubChem に変換してから使ってください

---

## Docker

```bash
cp .env.example .env                                # NCBI_API_KEY を記入
docker build -t localhost/togo-mcp:latest .
docker compose up -d togomcp-main                   # ポート 8000
```

`compose.yaml` は `togomcp-main`（8000）と `togomcp-test`（8001）の 2 サービスを定義しているので、本番と検証を同じイメージから並走させられます。

```bash
docker compose logs -f togomcp-main    # ログ
docker compose down                    # 停止・削除
```

### リバースプロキシの背後に置く場合

**2 つの環境変数が効いてきます。どちらも誤診しやすい壊れ方をします。**

**`TOGOMCP_ALLOWED_HOSTS`** — `Host` ヘッダが検証され（DNS リバインディング対策）、許可リストにないホストには **421** を返します。既定は localhost と DBCLS の公開 vhost のみ。**自分のホスト名を追加しないと、プロキシ経由のリクエストが全部拒否されます。**

**`TOGOMCP_FORWARDED_ALLOW_IPS`** — どのピアアドレスが `X-Forwarded-Proto` / `-For` を設定してよいか。uvicorn は既定で `127.0.0.1` しか信用せず、公開ポート経由のコンテナはループバックとして到着しません。設定を誤ると、ヘッダは**拒否されず黙って捨てられます**。するとアプリは平文 HTTP で提供していると信じ込み、`https://` を `http://` に降格するリダイレクトを吐きます。

**プロキシ側も `X-Forwarded-Proto` を送る必要があります。** nginx は既定で送りません：

```nginx
proxy_set_header X-Forwarded-Proto $scheme;
```

Caddy と Traefik は送ります。**両方が揃って初めて機能します。片方だけでは動きません。**

---

## ツール呼び出しログ（オプション）

TogoMCP は全ツール呼び出しを 1 行 1 JSON で記録できます（タイムスタンプ、ツール名、引数、状態、所要ミリ秒、セッション/リクエスト/クライアント ID、トランスポート、クライアント IP）。SPARQL 呼び出しにはエンドポイント URL、HTTP コード、行数・バイト数、クエリの SHA-256 が付きます。

**ベンチマーク、MIE の改良、複数ツールにまたがる手順の再構成に有用です。** 第 7 章の再現性の記録を自動化したい場合にも使えます。

オン・オフは環境変数 `TOGOMCP_QUERY_LOG` ひとつ。未設定＝無効（オーバーヘッドゼロ）。書き込み可能なファイルパスを設定すると有効になります。

Claude Desktop（ローカル stdio）の場合、`env` ブロックに追加します。**絶対パスを使い**（起動プロセスの作業ディレクトリは予測できません）、**親ディレクトリを先に作っておいてください**：

```json
"env": {
    "NCBI_API_KEY": "your-key-here",
    "TOGOMCP_QUERY_LOG": "/Users/you/togomcp-logs/togomcp.jsonl"
}
```

```bash
mkdir -p ~/togomcp-logs
```

そのあと Claude Desktop を完全に再起動します。

> ⚠️ **プライバシー:** IP は既定でソルト付きハッシュ（`ip_hash`）として記録されます。`TOGOMCP_LOG_RAW_IP=1` を設定すると平文でも記録され、不正利用者の特定・遮断が可能になりますが、**ログが個人データになります**。フィールドごとの詳細はリポジトリの `log_file_specs.md` を参照。

---

## データベースを追加する場合（開発者向け）

**5 箇所あります。2 箇所ではありません。** 最初の 2 つだけがサーバの検証に影響し、残りは静かにずれていくドキュメント面です。テストがそれを捕まえます。

1. `togo_mcp/data/resources/endpoints.csv` — 登録行（**これだけが有効な `database=` 値を決めます**）
2. `togo_mcp/data/mie/<db>.yaml` — MIE ファイル（仕様は `togo_mcp/data/docs/` に）
3. `uv run python scripts/generate_usage_guide_catalog.py` — 使い方ガイドのデータベース目録を再生成
4. `togo_mcp/data/resources/usage_guide_v6/02_budgets_and_discovery.md` — **生成器が触らない手書きの写し**。件数とキーの両方を更新
5. `togo_mcp/data/docs/togomcp-intro.html` — ランディングページのカード（非生成）

---

[← 目次に戻る](../README.md)
