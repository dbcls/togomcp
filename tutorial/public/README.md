# 公開版チュートリアル

`togomcp.rdfportal.org` から配信する**自習用チュートリアル**の成果物です。

| ファイル | 内容 |
|---|---|
| `tutorial-ja.html` | 日本語版（自習用・約 176 KB・外部依存ゼロ） |
| `tutorial-en.html` | 英語版（自習用・約 160 KB・外部依存ゼロ） |
| `00-intro-ja.md` | 日本語版の front matter（編集用ソース） |
| `00-intro-en.md` | 英語版の front matter（編集用ソース） |

生成物（`.html`）の出力先は `togo_mcp/data/docs/tutorial/` です。
リポジトリ外でビルドした場合のみ、このフォルダに出力されます。

英語版の本文ソースは `handbook/*-en.md` ・ `handson/*-en.md` にあります。
**日本語版を直したら、対応する `-en.md` も直してください。** 自動翻訳はしていません。

## 講習会版との違い

**ソースは同一です。** 同じ Markdown から、ビルド時に出し分けています。

`build-handbook.py` が `<!-- workshop-only -->` / `<!-- public-only -->` のマーカーで
ブロックを切り替えるので、**本文を二重管理する必要はありません。**

マーカーは 3 種類あります。

| マーカー | 講習会版 | 公開版 |
|---|---|---|
| `<!-- workshop-only -->` | 出る | 出ない |
| `<!-- public-only -->` | 出ない | 出る |
| `<!-- nobuild -->` | **出ない** | **出ない** |

`nobuild` は**教材を保守する人にだけ必要な注記**用です。`README.md` は講習会版の
「はじめに」の章でもあるので、作業手順の注意書きをそのまま書くと受講者への
配布物に混ざります。

⚠️ **マーカーは行内にも書けます**（文の途中で講習会版と公開版を出し分けるため）。
そのため `apply_variant()` は**前後の空白・改行に一切触りません。** 触ると直後の
空行が潰れて表や水平線が黙って消えます（2026-08-21 に実際に起きました）。

公開版で外れるもの:

- 「講習会では経路 A だけを使います」など、司会者がいる前提の記述
- 第5章の「講習会での扱い」→「試してみるには」に差し替え
- 第8章の「講習会の講師向け」節（開演前チェック、フォールバック運用、想定質問）
- 演習の「自由演習（講師は巡回）」→「最後に ── 自分のテーマで」

公開版で加わるもの:

- 専用の front matter（所要時間、急ぐ人向けの 3 章、測定条件、引用）
- **測定条件と「あなたの手元では数字が違う」の明示**（冒頭に配置）
- 「講習会を開きたい方へ」→ GitHub リポジトリへの案内
- 言語切替リンク（サイドバー）

## 再生成

```bash
python3 build-handbook.py     # 4 文書すべてを再生成
```

## サーバへの組み込み

`togo_mcp/data/docs/tutorial/` に置き、`server.py` に custom_route を追加します。
intro ページ（`/`）と同じ仕組みです。

```python
TUTORIAL_DIR = CWD.joinpath("docs", "tutorial")

@mcp.custom_route("/tutorial", methods=["GET"])
async def tutorial_en(request: Request) -> HTMLResponse:
    return HTMLResponse(TUTORIAL_DIR.joinpath("tutorial-en.html").read_text(encoding="utf-8"))

@mcp.custom_route("/tutorial/ja", methods=["GET"])
async def tutorial_ja(request: Request) -> HTMLResponse:
    return HTMLResponse(TUTORIAL_DIR.joinpath("tutorial-ja.html").read_text(encoding="utf-8"))
```

⚠️ **`data/` の下に置くこと。** wheel に含まれるのは `togo_mcp/data/` 以下です。

⚠️ ページ内の言語切替リンクは `/tutorial` と `/tutorial/ja` を指しています。
別のパスで配信する場合は `build-handbook.py` の `DOCS` を修正してください。

⚠️ intro ページへのリンク追加は `intro-page-updater` スキルの管轄です。
