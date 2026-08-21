# 01. セットアップ

3 つの経路があります。<!-- workshop-only -->**講習会では経路 A だけを使います。** B と C は必要な人が後で読んでください。<!-- /workshop-only --><!-- public-only -->**まずは経路 A を試してください。** インストール不要で 3 分です。B と C は必要になったときに読めば十分です。<!-- /public-only -->

| 経路 | 対象 | 所要 | インストール |
|---|---|---|---|
| **A. Claude のカスタムコネクタ** | ほぼ全員 | 3 分 | **不要** |
| B. Claude Code (CLI) | コマンドラインで作業する人 | 5 分 | Claude Code のみ |
| C. ローカル stdio | 開発者・KEGG を使う人 | 15 分 | Python, uv, git |

いずれの経路でも、TogoMCP 側のアカウント登録や API キーは要りません（NCBI ツールを使う場合のみ NCBI の API キーが要ります → 付録）。

---

## 経路 A：Claude のカスタムコネクタ（推奨）

Claude（Web / デスクトップ / Cowork）の**全プラン**で使えます。Free プランはカスタムコネクタを 1 つまで、有料プランは上限なしです。

### 手順

1. Claude を開き、**設定 → カスタマイズ → コネクタ** へ
2. **「+」** → **「カスタムコネクタを追加」**
3. MCP サーバの URL を入力：

   ```
   https://togomcp.rdfportal.org/mcp
   ```

4. 追加後、チャット画面の **「+」** ボタンから **コネクタ** を選び、その会話で有効化する

### Team / Enterprise プランの場合

**先に組織のオーナーが 1 手順を踏む必要があります。** メンバーが個人で追加することはできません。

1. オーナーが **組織設定 → コネクタ → 追加** で、**カスタム** にホバーして **Web** を選択し、組織全体に追加する
2. その後、各メンバーが **カスタマイズ → コネクタ** から自分で接続する

<!-- workshop-only -->> 💡 **講習会の主催者へ:** 参加者が Team/Enterprise アカウントの場合、これを**当日までに済ませておかないと全員が接続できません**。事前案内に必ず入れてください。<!-- /workshop-only --><!-- public-only -->> 💡 所属組織が Team/Enterprise プランの場合、**自分では追加できません。** 管理者に依頼してください。<!-- /public-only -->

### カスタムコネクタが使えない環境の場合

`mcp-remote` というローカルブリッジを経由する方法があります。コミュニティ製ツールであり Anthropic 公式の手順ではありませんが、動きます。

`claude_desktop_config.json` に以下を追加：

```json
{
  "mcpServers": {
    "togomcp": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://togomcp.rdfportal.org/mcp"]
    }
  }
}
```

---

## 経路 B：Claude Code (CLI)

**ターミナルで**（Claude のセッションに入る前に）以下を実行します。

```bash
claude mcp add --scope user --transport http togomcp https://togomcp.rdfportal.org/mcp
```

`--scope user` を付けると**すべてのプロジェクトで使える**ようになります。付けないと、そのディレクトリでしか有効になりません。

| スコープ | 保存先 | 有効範囲 |
|---|---|---|
| `--scope local`（既定） | `~/.claude.json` のプロジェクト別エントリ | そのプロジェクトのみ・自分だけ |
| `--scope project` | プロジェクト直下の `.mcp.json` | リポジトリを clone した全員 |
| `--scope user` | `~/.claude.json` のトップレベル | **自分の全プロジェクト** ← 推奨 |

### 接続の確認

```bash
claude mcp list
```

`togomcp` の横に **`✔ Connected`** と出れば成功です。

| 表示 | 意味 |
|---|---|
| `✔ Connected` | 成功 |
| `✘ Failed to connect` | URL に届いていない。末尾の `/mcp` を確認 |
| `! Connected · tools fetch failed` | 接続はしたがツール一覧が取れていない |
| `! Needs authentication` | 認証待ち（TogoMCP では出ないはず） |

Claude のセッション内では `/mcp` と打つと同じ状態が見られます。

### 削除・確認

```bash
claude mcp list              # 一覧
claude mcp remove togomcp    # 削除
claude mcp remove togomcp --scope user   # スコープを指定して削除
```

### よくある間違い

1. **`claude mcp add` を Claude のセッション内で打ってしまう。** これは**ターミナルで**打つコマンドです。`claude` と入力してセッションに入ったあとでは動きません。
2. **URL の末尾の `/mcp` を落とす。** 404 になります。
3. **スコープを忘れる。** 既定の `local` は、そのディレクトリでしか効きません。「昨日は動いたのに」の大半はこれです。
4. **設定ファイルの場所を間違える。** Claude Code が読むのは `~/.claude.json` と、プロジェクト直下の `.mcp.json` だけです。`~/.claude/.mcp.json` などは読まれません。

> 上記は Claude Code v2.1.210 以降で確認。`claude --version` で自分のバージョンを確認できます。

---

## 経路 C：ローカル stdio

開発者向け、および **KEGG ツールを使いたい場合の唯一の経路**です。手順は [付録](99-appendix-local-install.md) にまとめました。

---

## 接続できたかの確認（全経路共通）

Claude にこう聞いてください。

```
TogoMCP からどんなデータベースが使えるの？
```

**期待される反応:** 10 秒ほどで、UniProt・PDB・ChEMBL・TogoVar などを含む 37 データベースの一覧が、分野ごとに整理されて返ってきます。

**うまくいかない場合:**

| 症状 | 確認すること |
|---|---|
| TogoMCP の話を一切せず一般論を答える | コネクタがその会話で**有効化**されているか（経路 A では会話ごとに「+」から選ぶ必要があります） |
| 「ツールが使えない」と言われる | URL、`claude mcp list` の状態 |
| ツールを呼ぼうとして失敗する | ネットワーク。社内プロキシ・VPN の可能性 |

詳しくは [08. トラブルシュート](08-troubleshooting.md) へ。

---

## 補足：ChatGPT / Gemini から使う場合

TogoMCP は Claude 専用ではありません。ただしホスト側の事情で癖があります。

- **ChatGPT:** Developer Mode（Web のみ、モバイル非対応）。Pro は read/fetch のみですが**それで足ります**。Plus はカスタム MCP コネクタが使えません。
  ⚠️ **ChatGPT はコネクタ追加時にツール一覧を記録したきり、自動で取り直しません。** 後から追加されたツールは見えないままです。「あるはずのツールが無い」と言われたら **Scan Tools を再実行**するか、コネクタを削除して追加し直してください。なお**データベースの追加は影響しません**（データベース目録は問い合わせ時に配信されるため常に最新です）。
- **Gemini / Antigravity:** `~/.gemini/config/mcp_config.json` に `"serverUrl"` として指定。TogoMCP は **Streamable HTTP であって SSE ではない**点に注意。

---

## 一緒に使うと強い MCP サーバ

TogoMCP 単体でも動きますが、以下と併用すると扱える範囲が広がります。第 5 章のスキルはこれらを前提にしているものがあります。

| サーバ | URL | 役割 |
|---|---|---|
| **PubMed** | [Claude 公式コネクタ](https://support.claude.com/en/articles/12614801-using-the-pubmed-connector-in-claude) | 文献検索・全文取得 |
| **OLS4** (EMBL-EBI) | `https://www.ebi.ac.uk/ols4/mcp` | オントロジー用語の探索・階層関係 |
| **PubDictionaries** | `https://pubdictionaries.org/mcp` | 自然言語のラベル → オントロジー ID |

典型的な連携は「OLS4 で正規の用語 ID を確定 → TogoMCP でその ID を使って照会」。第 6 章で、なぜこの順序が効くのかが分かります。

---

次 → [02. 最初のデモ](02-first-demo.md)
