# TogoMCP チュートリアル — 教材一式

> **ただ読みたいだけの方へ:** 公開版が https://togomcp.rdfportal.org/tutorial/ja
> （英語版は https://togomcp.rdfportal.org/tutorial ）にあります。
> このフォルダは**講習会を開く人向けの教材一式**です。


<!-- nobuild -->
> **⚠️ 作業はこのフォルダで行ってください。** 教材の正本は `togomcp/tutorial/` **だけ**です。
> 以前は Google Drive にも作業コピーがありましたが（`Work/TogoMCP/Tutorial/`）、
> **同じものが複数あって正本が曖昧になり、実際に数値の乖離が起きた**ため退役しました。
> 制作過程の内部文書は `../internal_docs/tutorial-*.md` にあります（`.gitignore` 済み）。
<!-- /nobuild -->

生命科学のデータベースに、**SPARQL を書かずに自然言語で問い合わせる**ための実践チュートリアルです。

対象は、生命科学の研究者・大学院生。情報系のバックグラウンドは前提としません。RDF や SPARQL を知らなくても最後まで進めます。

---

## この教材で身につくこと

1. TogoMCP を自分の環境に繋いで、生命科学の主要データベース群に自然言語で問い合わせられるようになる
2. 返ってきた答えが**データベース由来なのか、AI の記憶由来なのか**を見分けられるようになる
3. 結果を論文や報告に使えるだけの**再現性のある形**で残せるようになる

3 番目が最も重要です。1 番目だけなら 10 分で終わります。

---

## 読み方 — まず `handbook/togomcp-handbook-ja.html` を開いてください

**受講者の方へ:** 全章をまとめた **`handbook/togomcp-handbook-ja.html`** をブラウザで開くのが正規の読み方です。ダブルクリックするだけで開きます。ソフトのインストールは不要、オフラインでも動きます。

- 左に目次、読んでいる位置が自動で追従します
- **プロンプトやクエリはワンクリックでコピーできます**（コードブロックにマウスを乗せると「コピー」が出ます）
- `◐` でダーク／ライト切替、`⎙` で印刷（PDF 保存もここから）
- スマートフォンでも読めます

> ⚠️ **`.md` ファイルを直接開かないでください。** 環境によっては記号がそのまま見えたり、表が崩れたり、章の間のリンクが動きません。`.md` は**編集用のソース**です。

**教材を編集する方へ:** `.md` を直したあと、`python3 build-handbook.py` を実行すると HTML が再生成されます（`pip install markdown` が必要）。

このフォルダの `.html` は**すべて生成物**です。直接編集せず、`.md` を直してビルドし直してください。

**例外はスライドです。** `slides/togomcp-tutorial-ja.html` は手書きで、ビルドの対象外です。本文の数値を直したら、スライドと講師台本にも同じ数値がないか確認してください。`build-handbook.py` の最後に走る `check-consistency.py` が、この 3 者にまたがる実測値のズレを検出します。

**英語版について:** 本文ソースは `handbook/*-en.md` ・ `handson/*-en.md` ・ `public/00-intro-en.md` にあります。**自動翻訳ではありません。** 日本語版を直したら、対応する `-en.md` も手で直してください。数値・識別子・SPARQL は両版で完全に一致させています。

現時点で英語版があるのは**公開版チュートリアル本文とスライド**です。講師台本・フォールバック素材・この文書は日本語のみです。

---

## 進め方

| 章 | 内容 | 目安 |
|---|---|---|
| [00 概要](handbook/00-overview.md) | なぜ TogoMCP か。**RDF / SPARQL とは** | 8 分 |
| [01 セットアップ](handbook/01-setup.md) | 接続する（インストール不要の経路あり） | 10 分 |
| [02 最初のデモ](handbook/02-first-demo.md) | 動かしてみる。裏で何が起きているかを見る | 10 分 |
| [03 仕組み](handbook/03-how-it-works.md) | MCP と MIE。なぜ正しい SPARQL が書けるのか | 20 分 |
| [04 やや複雑な問い](handbook/04-advanced-queries.md) | 複数 DB をまたぐ問い、と**失敗する問い** | 20 分 |
| [05 スキル](handbook/05-skills-workflows.md) | 方法論をパッケージ化したワークフロー | 10 分 |
| [06 良い問いの書き方](handbook/06-good-questions.md) | ★持ち帰り価値が最も高い章 | 10 分 |
| [07 検証と再現性](handbook/07-verification.md) | ★答えを論文に書く前にやること | 10 分 |
| [08 トラブルシュート](handbook/08-troubleshooting.md) | 動かないときに読む | 随時 |
| [99 付録：ローカル導入](handbook/99-appendix-local-install.md) | 開発者向け。KEGG を使う場合 | 15 分 |

演習は [handson/exercises-ja.md](handson/exercises-ja.md)、解答例は [handson/solutions-ja.md](handson/solutions-ja.md) にあります。

**急いでいる人へ:** 01 → 02 → 06 の 3 章だけでも実用になります。

---

## 講習会として実施する場合

**→ [RUNNING-A-WORKSHOP.md](RUNNING-A-WORKSHOP.md) を読んでください。** 90 分／60 分の進行表、削り順、開演前チェック、事故対応がまとまっています。

- 投影用スライド: [日本語](slides/togomcp-tutorial-ja.html) ／ [英語](slides/togomcp-tutorial-en.html)
- 逐語の講師台本: [instructor/script-ja.md](instructor/script-ja.md)
- **障害時の差し替え素材: [instructor/fallback/](instructor/fallback/)** ── ネットワーク障害は実際に起きます。省略しないでください

---

## この教材の数値について

本文中の実行結果（アクセッション番号、件数、分解能など）は**すべて実測**したものです。

**測定条件:**

| 項目 | 値 |
|---|---|
| 測定日 | 2026-08-20（初回）／ 2026-08-21（全件再測定・訂正） |
| モデル | セッション設定 `claude-opus-5` および `claude-sonnet-5` の 2 種で測定 |
| サーバ | ホスト版 `https://togomcp.rdfportal.org/mcp` |
| 言語 | 日本語プロンプト |

⚠️ **所要秒数とツールの使われ方はモデルによって変わります。** 同じ問いでも、あるモデルは検索を 1 回打ち、別のモデルは**データベースに一度も触れませんでした**。**返ってきた値（accession、件数など）はどちらも一致**しました。

データベースは更新されるので、**同じクエリを今日走らせても数値は変わります**。それは異常ではありません。数値そのものではなく、**クエリと、そこに至る考え方**を持ち帰ってください。本教材が結果の表よりクエリ本文を重視しているのはこのためです。

---

## ライセンスと引用

TogoMCP を研究に使った場合は、以下を引用してください。

> Kinjo, A. R., Yamamoto, Y., Bustamante-Larriet, S., Labra-Gayo, J.-E., & Fujisawa, T. (2026). TogoMCP: Natural Language Querying of Life-Science Knowledge Graphs via Schema-Guided LLMs and the Model Context Protocol. *Database* **2026**:baag042. https://doi.org/10.1093/database/baag042

MIE ファイルの設計根拠（アブレーション研究）については、こちらもあります。

> Kinjo, A. R., & Yamamoto, Y. (2026). Measure before you rewrite: ablation-driven redesign of LLM-facing RDF schema documentation in TogoMCP. *BioHackrXiv*. https://doi.org/10.37044/osf.io/6v5ra_v1

**あわせて、実際に使った個々のデータベースも引用してください。** TogoMCP は入り口であって、データの出どころではありません。

- TogoMCP リポジトリ: https://github.com/dbcls/togomcp
- ホスト版: https://togomcp.rdfportal.org/
- RDF Portal: https://rdfportal.org/
